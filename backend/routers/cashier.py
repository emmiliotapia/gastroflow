"""
Router REST para el Portal de Caja y POS Central (`/api/v1/cashier`)
===================================================================
Este router expone los endpoints para:
- Crear órdenes y comandas directamente desde la caja/barra.
- Listar y gestionar cuentas abiertas en orden FIFO (`PENDING` y `COMPLIMENTARY`).
- Cobro y liquidación financiera con soporte de cortesías VIP y validación PIN de supervisor.
- Gestión y trazabilidad de inventario de Barra (`StockLocation.BAR`).
"""

import uuid
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from backend.core.deps import get_current_user, get_db, require_role, get_optional_current_user
from backend.core.security import verify_pin
from backend.models.enums import UserRole, PaymentStatus, OrderStatus, StockLocation, StockTransactionType, KDSStation
from backend.models.machine import Machine
from backend.models.order import Order, OrderItem
from backend.models.product import Product
from backend.models.user import User
from backend.schemas.order import OrderRead, OrderPay, OrderCreate, OrderItemRead
from backend.services.inventory_service import InventoryService
from backend.websockets.kds_manager import kds_manager
from backend.utils.n8n import trigger_order_webhook

router = APIRouter(prefix="/api/v1/cashier", tags=["Portal de Caja y Control de Cobros"])


def _build_cashier_order_dto(order: Order) -> OrderRead:
    """Helper para estructurar la comanda con datos de máquina y colaborador."""
    dto = OrderRead.model_validate(order)
    dto.machine_code = order.machine.asset_code if order.machine else "000"
    dto.created_by_name = order.created_by.full_name if order.created_by else "Cajero / Barra"
    
    dto.items = []
    for item in order.items:
        it_dto = OrderItemRead.model_validate(item)
        if item.product:
            it_dto.product_name = item.product.name
            it_dto.destination_kds = item.product.destination_kds
        else:
            it_dto.product_name = "Artículo"
            it_dto.destination_kds = KDSStation.BAR
        dto.items.append(it_dto)
    return dto


# ------------------------------------------------------------------------------
# 1. LISTADO DE CUENTAS PENDIENTES (FIFO)
# ------------------------------------------------------------------------------

@router.get(
    "/orders",
    response_model=List[OrderRead],
    summary="Listar cuentas abiertas y pendientes de cobro (FIFO)",
    description="Retorna todas las comandas no liquidadas ordenadas cronológicamente con datos del colaborador y máquina."
)
def get_pending_orders(
    machine_id: Optional[uuid.UUID] = Query(None, description="Filtrar por máquina/slot específica"),
    include_complimentary: bool = Query(True, description="Incluir cuentas de cortesía abiertas"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
) -> List[OrderRead]:
    valid_statuses = [PaymentStatus.PENDING]
    if include_complimentary:
        valid_statuses.append(PaymentStatus.COMPLIMENTARY)

    stmt = (
        select(Order)
        .options(
            joinedload(Order.items).joinedload(OrderItem.product),
            joinedload(Order.machine),
            joinedload(Order.created_by)
        )
        .where(Order.payment_status.in_(valid_statuses))
    )

    if machine_id:
        stmt = stmt.where(Order.machine_id == machine_id)

    # Ordenar cronológicamente ascendente (FIFO)
    stmt = stmt.order_by(Order.created_at.asc())
    orders = db.execute(stmt).unique().scalars().all()
    
    return [_build_cashier_order_dto(o) for o in orders]


# ------------------------------------------------------------------------------
# 2. GENERACIÓN DIRECTA DE ÓRDENES DESDE CAJA / BARRA
# ------------------------------------------------------------------------------

@router.post(
    "/orders",
    response_model=OrderRead,
    status_code=status.HTTP_201_CREATED,
    summary="Generar nueva orden / comanda desde caja",
    description="Permite al cajero o barman levantar un pedido, descontar stock de forma atómica y disparar KDS."
)
def create_cashier_order(
    payload: OrderCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
) -> OrderRead:
    # 1. Validar máquina o asignar general 000
    target_machine = None
    if payload.machine_id:
        target_machine = db.get(Machine, payload.machine_id)
    elif payload.machine_code and payload.machine_code.upper() not in ["000", "SALA", "BARRA"]:
        stmt_m = select(Machine).where(
            (Machine.asset_code.ilike(payload.machine_code.strip())) |
            (Machine.serial_number.ilike(payload.machine_code.strip()))
        )
        target_machine = db.execute(stmt_m).scalars().first()

    # 2. Iniciar Transacción de Comanda
    try:
        count_stmt = select(func.count(Order.id))
        order_count = db.execute(count_stmt).scalar() or 0
        folio = f"COM-{order_count + 1:05d}"

        order = Order(
            machine_id=target_machine.id if target_machine else None,
            order_number=folio,
            status=OrderStatus.PENDING,
            total_amount=Decimal("0.00"),
            notes=payload.notes,
            created_by_id=current_user.id if current_user else None
        )
        db.add(order)
        db.flush()

        total_accumulated = Decimal("0.00")
        stations_affected = set()

        for item in payload.items:
            product = db.get(Product, item.product_id)
            if not product or not product.is_active:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Producto con ID '{item.product_id}' no disponible."
                )

            item_price = Decimal("0.00") if item.is_courtesy else product.price
            
            # Si es cortesía y se suministró PIN
            if item.is_courtesy and payload.supervisor_pin:
                stmt_sup = select(User).options(joinedload(User.role)).where(User.is_active == True)
                users = db.execute(stmt_sup).unique().scalars().all()
                supervisor = next((u for u in users if u.role.name in [UserRole.JEFE_DE_SALA, UserRole.ADMIN] and u.hashed_pin and verify_pin(payload.supervisor_pin, u.hashed_pin)), None)
                if not supervisor:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="PIN de supervisor inválido para cortesía."
                    )

            subtotal = item_price * item.quantity
            total_accumulated += subtotal

            order_item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=item.quantity,
                unit_price=item_price,
                subtotal=subtotal
            )
            db.add(order_item)
            stations_affected.add(product.destination_kds)

            # Descontar stock
            dest_loc = StockLocation.BAR if product.destination_kds == KDSStation.BAR else StockLocation.KITCHEN
            InventoryService.deduct_product_stock(
                db=db,
                product_id=product.id,
                order_quantity=item.quantity,
                location=dest_loc,
                user_id=current_user.id if current_user else None
            )

        order.total_amount = total_accumulated
        if total_accumulated == Decimal("0.00"):
            order.payment_status = PaymentStatus.COMPLIMENTARY
            order.payment_method = "COURTESY"
        else:
            order.payment_status = PaymentStatus.PENDING

        db.commit()
        db.refresh(order)

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error creando orden desde caja: {str(e)}"
        )

    # Broadcast KDS y n8n
    stmt = (
        select(Order)
        .options(
            joinedload(Order.items).joinedload(OrderItem.product),
            joinedload(Order.machine),
            joinedload(Order.created_by)
        )
        .where(Order.id == order.id)
    )
    final_order = db.execute(stmt).unique().scalar_one()
    dto = _build_cashier_order_dto(final_order)
    order_payload = dto.model_dump(mode="json")

    for st in stations_affected:
        kds_manager.broadcast_sync(
            station=st.value,
            message={
                "event": "NEW_ORDER",
                "station": st.value,
                "order": order_payload
            }
        )

    trigger_order_webhook(order_payload)
    return dto


# ------------------------------------------------------------------------------
# 3. PROCESAR COBRO Y CIERRE FINANCIERO
# ------------------------------------------------------------------------------

@router.post(
    "/orders/{order_id}/pay",
    response_model=OrderRead,
    summary="Procesar pago y cerrar cuenta de comanda",
    description="Liquida la comanda actualizando su estado a PAID o COMPLIMENTARY con PIN de supervisor si aplica."
)
def pay_order(
    order_id: uuid.UUID,
    payload: OrderPay,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
) -> OrderRead:
    stmt = (
        select(Order)
        .options(
            joinedload(Order.items).joinedload(OrderItem.product),
            joinedload(Order.machine),
            joinedload(Order.created_by)
        )
        .where(Order.id == order_id)
    )
    order = db.execute(stmt).unique().scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Comanda con ID '{order_id}' no encontrada."
        )

    if order.payment_status == PaymentStatus.PAID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esta comanda ya ha sido liquidada previamente."
        )

    method = payload.payment_method.upper()
    if method not in ["CASH", "CARD", "COURTESY"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Método de pago no válido. Debe ser CASH, CARD o COURTESY."
        )

    if method == "COURTESY":
        if not payload.supervisor_pin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Se requiere el PIN de supervisor para autorizar una cortesía."
            )
        
        stmt_sup = select(User).options(joinedload(User.role)).where(User.is_active == True)
        users = db.execute(stmt_sup).unique().scalars().all()
        supervisor = next((u for u in users if u.role.name in [UserRole.JEFE_DE_SALA, UserRole.ADMIN] and u.hashed_pin and verify_pin(payload.supervisor_pin, u.hashed_pin)), None)
        
        if not supervisor:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="El PIN de supervisor ingresado no es válido."
            )
        
        for item in order.items:
            item.unit_price = Decimal("0.00")
            item.subtotal = Decimal("0.00")
        order.total_amount = Decimal("0.00")
        order.payment_status = PaymentStatus.COMPLIMENTARY
        order.payment_method = "COURTESY"
    else:
        order.payment_status = PaymentStatus.PAID
        order.payment_method = method

    db.commit()
    db.refresh(order)
    return _build_cashier_order_dto(order)


# ------------------------------------------------------------------------------
# 4. AGREGAR CONSUMOS A CUENTA ABIERTA
# ------------------------------------------------------------------------------

class OrderItemAdd(BaseModel):
    product_id: uuid.UUID = Field(..., description="ID del producto a agregar")
    quantity: Decimal = Field(..., gt=0, description="Cantidad a agregar")
    is_courtesy: bool = Field(default=False, description="Indica si se otorga como cortesía ($0.00)")


class OrderAddItems(BaseModel):
    items: List[OrderItemAdd] = Field(..., min_length=1)
    supervisor_pin: Optional[str] = Field(None, description="PIN de supervisor si se incluye alguna cortesía")


@router.post(
    "/orders/{order_id}/items",
    response_model=OrderRead,
    summary="Agregar consumos a una comanda abierta"
)
def add_items_to_order(
    order_id: uuid.UUID,
    payload: OrderAddItems,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
) -> OrderRead:
    stmt = (
        select(Order)
        .options(
            joinedload(Order.items).joinedload(OrderItem.product),
            joinedload(Order.machine),
            joinedload(Order.created_by)
        )
        .where(Order.id == order_id)
    )
    order = db.execute(stmt).unique().scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comanda no encontrada.")

    if order.payment_status == PaymentStatus.PAID:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pueden agregar productos a una comanda ya pagada.")

    # Validar PIN si hay cortesía
    if any(item.is_courtesy for item in payload.items) and payload.supervisor_pin:
        stmt_sup = select(User).options(joinedload(User.role)).where(User.is_active == True)
        users = db.execute(stmt_sup).unique().scalars().all()
        supervisor = next((u for u in users if u.role.name in [UserRole.JEFE_DE_SALA, UserRole.ADMIN] and u.hashed_pin and verify_pin(payload.supervisor_pin, u.hashed_pin)), None)
        if not supervisor:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="PIN de supervisor inválido.")

    stations_affected = set()
    total_added = Decimal("0.00")

    try:
        for item in payload.items:
            product = db.get(Product, item.product_id)
            if not product or not product.is_active:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no disponible.")

            price = Decimal("0.00") if item.is_courtesy else product.price
            subtotal = price * item.quantity
            total_added += subtotal

            existing_item = next((oi for oi in order.items if oi.product_id == product.id and oi.unit_price == price), None)
            if existing_item:
                existing_item.quantity += item.quantity
                existing_item.subtotal += subtotal
            else:
                new_item = OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    quantity=item.quantity,
                    unit_price=price,
                    subtotal=subtotal
                )
                db.add(new_item)

            stations_affected.add(product.destination_kds)

            dest_loc = StockLocation.BAR if product.destination_kds == KDSStation.BAR else StockLocation.KITCHEN
            InventoryService.deduct_product_stock(
                db=db,
                product_id=product.id,
                order_quantity=item.quantity,
                location=dest_loc,
                user_id=current_user.id if current_user else None
            )

        order.total_amount += total_added
        db.commit()
        db.refresh(order)

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Error agregando consumos: {str(e)}")

    dto = _build_cashier_order_dto(order)
    order_payload = dto.model_dump(mode="json")

    for st in stations_affected:
        kds_manager.broadcast_sync(
            station=st.value,
            message={"event": "NEW_ORDER", "station": st.value, "order": order_payload}
        )

    return dto


# ------------------------------------------------------------------------------
# 5. STOCK DE BARRA (`StockLocation.BAR`)
# ------------------------------------------------------------------------------

@router.get(
    "/bar-stock",
    summary="Consultar existencias de Barra (Bebidas, Licores, Cigarros)"
)
def get_bar_stock(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """Retorna las existencias físicas en la bodega de Barra (BAR)."""
    return InventoryService.get_stock_by_location(db=db, location=StockLocation.BAR)

