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
from typing import Any, List, Optional
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
    description="Permite al cajero o barman levantar un pedido con idempotencia anti-double tap, descontar stock de forma atómica y disparar KDS."
)
def create_cashier_order(
    payload: OrderCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
) -> OrderRead:
    # 0. Control de Idempotencia / Anti-Double Tap
    if payload.client_order_id:
        stmt_existing = (
            select(Order)
            .options(
                joinedload(Order.items).joinedload(OrderItem.product),
                joinedload(Order.machine),
                joinedload(Order.created_by),
                joinedload(Order.cancelled_by)
            )
            .where(Order.client_order_id == payload.client_order_id.strip())
        )
        existing_order = db.execute(stmt_existing).unique().scalar_one_or_none()
        if existing_order:
            return _build_cashier_order_dto(existing_order)

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
            client_order_id=payload.client_order_id.strip() if payload.client_order_id else None,
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


# ------------------------------------------------------------------------------
# 6. CORTE DE CAJA / REPORTE Z Y AUDITORÍA FINANCIERA
# ------------------------------------------------------------------------------

from datetime import date, datetime, time
from backend.models.waste import WasteLog

class CorteCajaSummary(BaseModel):
    shift_date: str
    generated_at: str
    total_sales_amount: float
    cash_total: float
    card_total: float
    courtesy_total: float
    paid_orders_count: int
    complimentary_orders_count: int
    pending_orders_count: int
    total_orders_count: int
    total_waste_cost: float
    waste_records_count: int
    net_revenue: float
    items_breakdown: List[dict]


@router.get(
    "/corte-caja",
    response_model=CorteCajaSummary,
    summary="Generar Corte de Caja / Reporte Z del Turno",
    description="Calcula el arqueo financiero del turno segregado por método de pago (CASH, CARD, COURTESY), cuentas liquidadas y valorización de mermas."
)
def get_corte_caja(
    target_date: Optional[str] = Query(None, description="Fecha en formato YYYY-MM-DD (por defecto hoy)"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
) -> CorteCajaSummary:
    now = datetime.now()
    if target_date:
        try:
            day_obj = datetime.strptime(target_date, "%Y-%m-%d").date()
        except ValueError:
            day_obj = now.date()
    else:
        day_obj = now.date()

    start_day = datetime.combine(day_obj, time.min)
    end_day = datetime.combine(day_obj, time.max)

    # 1. Consultar comandas del día
    stmt_orders = (
        select(Order)
        .options(
            joinedload(Order.items).joinedload(OrderItem.product),
            joinedload(Order.machine),
            joinedload(Order.created_by)
        )
        .where(Order.created_at >= start_day, Order.created_at <= end_day)
    )
    orders = db.execute(stmt_orders).unique().scalars().all()

    cash_total = Decimal("0.00")
    card_total = Decimal("0.00")
    courtesy_total = Decimal("0.00")
    paid_orders_count = 0
    complimentary_orders_count = 0
    pending_orders_count = 0

    items_dict = {}

    for o in orders:
        if o.payment_status == PaymentStatus.PAID:
            paid_orders_count += 1
            if o.payment_method == "CASH":
                cash_total += o.total_amount
            elif o.payment_method == "CARD":
                card_total += o.total_amount
            else:
                cash_total += o.total_amount
        elif o.payment_status == PaymentStatus.COMPLIMENTARY:
            complimentary_orders_count += 1
            for it in o.items:
                orig_price = it.product.price if it.product else Decimal("0.00")
                courtesy_total += orig_price * it.quantity
        elif o.payment_status == PaymentStatus.PENDING:
            pending_orders_count += 1

        # Sumar ítems vendidos
        for it in o.items:
            p_name = it.product.name if it.product else "Artículo"
            if p_name not in items_dict:
                items_dict[p_name] = {"name": p_name, "quantity": 0.0, "total": 0.0}
            items_dict[p_name]["quantity"] += float(it.quantity)
            items_dict[p_name]["total"] += float(it.subtotal)

    total_sales = cash_total + card_total

    # 2. Consultar mermas del día
    stmt_waste = (
        select(WasteLog)
        .where(WasteLog.created_at >= start_day, WasteLog.created_at <= end_day)
    )
    waste_logs = db.execute(stmt_waste).scalars().all()
    total_waste_cost = sum([w.total_cost for w in waste_logs], Decimal("0.00"))

    return CorteCajaSummary(
        shift_date=day_obj.isoformat(),
        generated_at=now.strftime("%Y-%m-%d %H:%M:%S"),
        total_sales_amount=float(total_sales),
        cash_total=float(cash_total),
        card_total=float(card_total),
        courtesy_total=float(courtesy_total),
        paid_orders_count=paid_orders_count,
        complimentary_orders_count=complimentary_orders_count,
        pending_orders_count=pending_orders_count,
        total_orders_count=len(orders),
        total_waste_cost=float(total_waste_cost),
        waste_records_count=len(waste_logs),
        net_revenue=float(total_sales - total_waste_cost),
        items_breakdown=list(items_dict.values())
    )


# ------------------------------------------------------------------------------
# 7. HISTORIAL GENERAL Y AUDITORÍA DE COMANDAS DE CAJA
# ------------------------------------------------------------------------------

@router.get(
    "/history",
    response_model=List[OrderRead],
    summary="Historial general y auditoría de comandas de caja",
    description="Permite consultar comandas pasadas (pagadas, cortesías, pendientes) con filtros de fecha, máquina o folio."
)
def get_cashier_history(
    target_date: Optional[str] = Query(None, description="Fecha YYYY-MM-DD"),
    payment_status: Optional[PaymentStatus] = Query(None, description="Filtrar por estado de pago"),
    machine_code: Optional[str] = Query(None, description="Filtrar por máquina"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
) -> List[OrderRead]:
    stmt = (
        select(Order)
        .options(
            joinedload(Order.items).joinedload(OrderItem.product),
            joinedload(Order.machine),
            joinedload(Order.created_by)
        )
    )

    if target_date:
        try:
            day_obj = datetime.strptime(target_date, "%Y-%m-%d").date()
            start_day = datetime.combine(day_obj, time.min)
            end_day = datetime.combine(day_obj, time.max)
            stmt = stmt.where(Order.created_at >= start_day, Order.created_at <= end_day)
        except ValueError:
            pass

    if payment_status:
        stmt = stmt.where(Order.payment_status == payment_status)

    if machine_code:
        stmt = stmt.join(Order.machine, isouter=True).where(
            (Machine.asset_code.ilike(f"%{machine_code}%")) |
            (Order.notes.ilike(f"%{machine_code}%"))
        )

    stmt = stmt.order_by(Order.created_at.desc()).limit(limit)
    orders = db.execute(stmt).unique().scalars().all()
    return [_build_cashier_order_dto(o) for o in orders]


# ------------------------------------------------------------------------------
# 8. CIERRE DE TURNO / REPORTE Z INMUTABLE Y CANCELACIONES AUDITADAS
# ------------------------------------------------------------------------------

from pydantic import ConfigDict
from backend.models.shift import ShiftClosing
from backend.schemas.order import OrderCancel

class ShiftCloseRequest(BaseModel):
    declared_cash: Decimal = Field(..., ge=0, description="Efectivo físico contado en caja")
    supervisor_pin: str = Field(..., min_length=4, max_length=6, description="PIN del supervisor para autorizar el arqueo definitivo")
    cashier_name: Optional[str] = Field("Cajero en Turno", description="Nombre o identificador del cajero")
    notes: Optional[str] = Field(None, description="Observaciones o justificaciones de diferencias")


class ShiftClosingRead(BaseModel):
    id: uuid.UUID
    folio: str
    shift_date: str
    cashier_name: str
    expected_cash: Decimal
    declared_cash: Decimal
    difference: Decimal
    card_total: Decimal
    courtesy_total: Decimal
    total_sales: Decimal
    total_waste: Decimal
    net_balance: Decimal
    paid_orders_count: int
    complimentary_orders_count: int
    supervisor_name: Optional[str] = None
    notes: Optional[str] = None
    created_at: Any

    model_config = ConfigDict(from_attributes=True)


@router.post(
    "/corte-caja/close",
    response_model=ShiftClosingRead,
    status_code=status.HTTP_201_CREATED,
    summary="Cierre Definitivo de Turno / Reporte Z con Arqueo",
    description="Exige PIN de supervisor. Registra de forma inmutable el arqueo, calcula diferencias y blinda el turno."
)
def close_cashier_shift(
    payload: ShiftCloseRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
) -> ShiftClosingRead:
    # 1. Validar PIN de supervisor
    stmt_sup = select(User).options(joinedload(User.role)).where(User.is_active == True)
    users = db.execute(stmt_sup).unique().scalars().all()
    supervisor = next((u for u in users if u.role.name in [UserRole.JEFE_DE_SALA, UserRole.ADMIN] and u.hashed_pin and verify_pin(payload.supervisor_pin, u.hashed_pin)), None)

    if not supervisor:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El PIN de supervisor ingresado no es válido para autorizar el cierre de turno."
        )

    # 2. Calcular datos del turno actual (hoy)
    now = datetime.now()
    day_obj = now.date()
    start_day = datetime.combine(day_obj, time.min)
    end_day = datetime.combine(day_obj, time.max)

    stmt_orders = (
        select(Order)
        .options(
            joinedload(Order.items).joinedload(OrderItem.product),
            joinedload(Order.machine),
            joinedload(Order.created_by)
        )
        .where(Order.created_at >= start_day, Order.created_at <= end_day)
    )
    orders = db.execute(stmt_orders).unique().scalars().all()

    cash_total = Decimal("0.00")
    card_total = Decimal("0.00")
    courtesy_total = Decimal("0.00")
    paid_count = 0
    comp_count = 0

    for o in orders:
        if o.payment_status == PaymentStatus.PAID:
            paid_count += 1
            if o.payment_method == "CARD":
                card_total += o.total_amount
            else:
                cash_total += o.total_amount
        elif o.payment_status == PaymentStatus.COMPLIMENTARY:
            comp_count += 1
            for it in o.items:
                orig_price = it.product.price if it.product else Decimal("0.00")
                courtesy_total += orig_price * it.quantity

    total_sales = cash_total + card_total

    # Mermas
    stmt_waste = select(WasteLog).where(WasteLog.created_at >= start_day, WasteLog.created_at <= end_day)
    waste_logs = db.execute(stmt_waste).scalars().all()
    total_waste = sum([w.total_cost for w in waste_logs], Decimal("0.00"))

    # Diferencia de arqueo
    difference = payload.declared_cash - cash_total
    net_balance = total_sales - total_waste

    # Generar folio único
    count_stmt = select(func.count(ShiftClosing.id))
    closing_count = db.execute(count_stmt).scalar() or 0
    date_str = day_obj.strftime("%Y%m%d")
    folio = f"CRTE-{date_str}-{closing_count + 1:04d}"

    closing = ShiftClosing(
        folio=folio,
        shift_date=day_obj.isoformat(),
        cashier_name=payload.cashier_name or (current_user.full_name if current_user else "Cajero General"),
        expected_cash=cash_total,
        declared_cash=payload.declared_cash,
        difference=difference,
        card_total=card_total,
        courtesy_total=courtesy_total,
        total_sales=total_sales,
        total_waste=total_waste,
        net_balance=net_balance,
        paid_orders_count=paid_count,
        complimentary_orders_count=comp_count,
        supervisor_id=supervisor.id,
        notes=payload.notes
    )
    db.add(closing)
    db.commit()
    db.refresh(closing)

    dto = ShiftClosingRead.model_validate(closing)
    dto.supervisor_name = supervisor.full_name
    return dto


@router.get(
    "/corte-caja/closures",
    response_model=List[ShiftClosingRead],
    summary="Listar cierres de turno y arqueos inmutables",
    description="Retorna el histórico de cierres de caja y Reportes Z autorizados por supervisor."
)
def get_shift_closings(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
) -> List[ShiftClosingRead]:
    stmt = (
        select(ShiftClosing)
        .options(joinedload(ShiftClosing.supervisor))
        .order_by(ShiftClosing.created_at.desc())
        .limit(limit)
    )
    closings = db.execute(stmt).scalars().all()
    res = []
    for c in closings:
        dto = ShiftClosingRead.model_validate(c)
        dto.supervisor_name = c.supervisor.full_name if c.supervisor else "Supervisor"
        res.append(dto)
    return res


@router.post(
    "/orders/{order_id}/cancel",
    response_model=OrderRead,
    summary="Cancelar comanda desde caja con PIN de supervisor",
    description="Permite al cajero o supervisor cancelar una comanda abierta o en proceso con PIN y justificación."
)
def cancel_cashier_order(
    order_id: uuid.UUID,
    payload: OrderCancel,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
) -> OrderRead:
    # 1. Validar PIN
    if not payload.supervisor_pin:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="PIN de supervisor requerido.")
    stmt_sup = select(User).options(joinedload(User.role)).where(User.is_active == True)
    users = db.execute(stmt_sup).unique().scalars().all()
    supervisor = next((u for u in users if u.role.name in [UserRole.JEFE_DE_SALA, UserRole.ADMIN] and u.hashed_pin and verify_pin(payload.supervisor_pin, u.hashed_pin)), None)
    if not supervisor:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="PIN de supervisor inválido.")

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
    if order.status == OrderStatus.CANCELLED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La comanda ya fue cancelada.")

    if order.status in [OrderStatus.PREPARING, OrderStatus.READY, OrderStatus.DELIVERED]:
        for item in order.items:
            reason = f"Cancelación caja #{order.order_number}: {payload.reason} (Autorizó: {supervisor.full_name})"
            InventoryService.record_order_cancellation_waste(
                db=db,
                product_id=item.product_id,
                order_quantity=item.quantity,
                reason=reason,
                user_id=supervisor.id
            )
    else:
        for item in order.items:
            notes = f"Reversa por cancelación caja #{order.order_number}: {payload.reason} (Autorizó: {supervisor.full_name})"
            InventoryService.revert_product_stock(
                db=db,
                product_id=item.product_id,
                order_quantity=item.quantity,
                notes=notes,
                user_id=supervisor.id
            )

    order.status = OrderStatus.CANCELLED
    order.cancellation_reason = payload.reason
    order.cancelled_by_id = supervisor.id
    order.cancelled_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(order)

    dto = _build_cashier_order_dto(order)
    order_payload = dto.model_dump(mode="json")
    kds_manager.broadcast_sync(station="WAITERS", message={"event": "ORDER_CANCELLED", "order_id": str(order.id), "order": order_payload})
    return dto



