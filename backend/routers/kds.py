"""
Router REST y WebSocket de Comandas y Kitchen Display System (KDS) (`/backend/routers/kds.py`)
========================================================================================
Este router expone la creación de pedidos (POS), consulta y actualización de
comandas para Cocina y Barra (KDS), y maneja las suscripciones en tiempo real
vía WebSockets.
"""

import uuid
import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from backend.core.deps import get_current_user, get_db, require_role, get_optional_current_user
from backend.core.security import verify_pin
from backend.models.enums import KDSStation, OrderStatus, UserRole, PaymentStatus, MembershipTier
from backend.models.machine import Machine
from backend.models.order import Order, OrderItem
from backend.models.product import Product
from backend.models.user import User
from backend.schemas.order import KDSOrderUpdate, OrderCreate, OrderRead, OrderItemRead, OrderCancel
from backend.services.inventory_service import InventoryService
from backend.websockets.kds_manager import kds_manager
from backend.utils.n8n import trigger_order_webhook, trigger_order_ready_notification

router = APIRouter(tags=["Comandas y KDS (Kitchen Display System)"])


def _build_order_dto(order: Order) -> OrderRead:
    """Helper para serializar la orden con metadatos de producto, máquina, mesero y cancelación."""
    dto = OrderRead.model_validate(order)
    dto.machine_code = order.machine.asset_code if order.machine else "000"
    dto.created_by_name = order.created_by.full_name if order.created_by else "Staff Piso"
    dto.cancelled_by_name = order.cancelled_by.full_name if hasattr(order, 'cancelled_by') and order.cancelled_by else None
    
    dto.items = []
    for item in order.items:
        it_dto = OrderItemRead.model_validate(item)
        if item.product:
            it_dto.product_name = item.product.name
            it_dto.destination_kds = item.product.destination_kds
        else:
            it_dto.product_name = "Artículo AyB"
            it_dto.destination_kds = KDSStation.KITCHEN
        dto.items.append(it_dto)
    return dto


@router.post(
    "/api/v1/orders/",
    response_model=OrderRead,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar una nueva comanda de AyB",
    description="Crea la comanda de forma atómica con soporte anti-double tap (idempotencia). Ejecuta el descuento de stock de insumos y notifica vía WebSocket."
)
def create_order(
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
            # Retornar comanda ya creada para evitar duplicación y doble descuento
            return _build_order_dto(existing_order)

    # 1. Validar máquina por ID o por código (ej. SLOT-101)
    target_machine = None
    if payload.machine_id:
        target_machine = db.get(Machine, payload.machine_id)
        if not target_machine:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Máquina con ID '{payload.machine_id}' no encontrada."
            )
    elif payload.machine_code and payload.machine_code.upper() not in ["000", "SALA", "BARRA"]:
        stmt_m = select(Machine).where(
            (Machine.asset_code.ilike(payload.machine_code.strip())) |
            (Machine.serial_number.ilike(payload.machine_code.strip()))
        )
        target_machine = db.execute(stmt_m).scalars().first()

    # 2. Iniciar Transacción de Comanda de forma Atómica
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

        # Rangos de membresía para cortesía
        TIER_RANKS = {
            "CLASSIC": 0, "PLATA": 0, None: 0,
            "GOLD": 1, "ORO": 1,
            "PLATINUM": 2, "PLATINO": 2,
            "VIP": 3, "PRESTIGE": 3
        }

        user_tier_str = "CLASSIC"
        if current_user and current_user.membership_tier:
            user_tier_str = current_user.membership_tier.value

        for item in payload.items:
            product = db.get(Product, item.product_id)
            if not product or not product.is_active:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Producto con ID '{item.product_id}' no encontrado o inactivo."
                )

            item_price = product.price
            is_courtesy = False

            if item.is_courtesy:
                is_courtesy = True
            elif product.courtesy_tier_min:
                req_tier = product.courtesy_tier_min.upper()
                if TIER_RANKS.get(user_tier_str.upper(), 0) >= TIER_RANKS.get(req_tier, 0):
                    is_courtesy = True
                else:
                    if payload.supervisor_pin:
                        stmt_sup = select(User).options(joinedload(User.role)).where(User.is_active == True)
                        users = db.execute(stmt_sup).unique().scalars().all()
                        supervisor = next((u for u in users if u.role.name in [UserRole.JEFE_DE_SALA, UserRole.ADMIN] and u.hashed_pin and verify_pin(payload.supervisor_pin, u.hashed_pin)), None)
                        if supervisor:
                            is_courtesy = True
                        else:
                            raise HTTPException(
                                status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="El PIN de supervisor ingresado no es válido para autorizar esta cortesía."
                            )

            if is_courtesy:
                item_price = Decimal("0.00")

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

            # Descontar stock atómicamente
            InventoryService.deduct_product_stock(
                db=db,
                product_id=product.id,
                order_quantity=item.quantity,
                user_id=current_user.id if current_user else None
            )

        order.total_amount = total_accumulated
        if total_accumulated == Decimal("0.00"):
            order.payment_status = PaymentStatus.COMPLIMENTARY
            order.payment_method = "COURTESY"
        else:
            order.payment_status = PaymentStatus.PENDING
            order.payment_method = None

        db.commit()
        db.refresh(order)

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error procesando el descuento de inventario o comanda: {str(e)}"
        )

    # 3. Transmitir alerta WebSocket a las pantallas KDS
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
    dto = _build_order_dto(final_order)

    order_payload = dto.model_dump(mode="json")

    # Broadcast a pantallas KDS específicas y al canal ALL y WAITERS
    for station in stations_affected:
        kds_manager.broadcast_sync(
            station=station.value,
            message={
                "event": "NEW_ORDER",
                "station": station.value,
                "order": order_payload
            }
        )

    # Avisar a canal de meseros
    kds_manager.broadcast_sync(
        station="WAITERS",
        message={
            "event": "ORDER_REGISTERED",
            "station": "WAITERS",
            "order": order_payload
        }
    )

    # Disparar webhook n8n de nueva orden
    trigger_order_webhook(order_payload)

    return dto


@router.get(
    "/api/v1/kds/orders",
    response_model=List[OrderRead],
    summary="Listar comandas activas para pantalla KDS",
    description="Retorna la lista de comandas pendientes o en preparación filtradas por estación (KITCHEN o BAR)."
)
def get_kds_orders(
    station: Optional[KDSStation] = Query(None, description="Filtrar por estación del KDS (KITCHEN o BAR)"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
) -> List[OrderRead]:
    stmt = (
        select(Order)
        .options(
            joinedload(Order.items).joinedload(OrderItem.product),
            joinedload(Order.machine),
            joinedload(Order.created_by),
            joinedload(Order.cancelled_by)
        )
        .where(Order.status.in_([OrderStatus.PENDING, OrderStatus.PREPARING, OrderStatus.READY]))
        .order_by(Order.created_at.asc())
    )

    orders = db.execute(stmt).unique().scalars().all()

    filtered_orders = []
    for order in orders:
        matching_items = []
        for item in order.items:
            if not station or (item.product and item.product.destination_kds == station):
                matching_items.append(item)

        if matching_items:
            dto = _build_order_dto(order)
            dto.items = []
            for item in matching_items:
                item_dto = OrderItemRead.model_validate(item)
                item_dto.product_name = item.product.name if item.product else "Artículo"
                item_dto.destination_kds = item.product.destination_kds if item.product else (station or KDSStation.KITCHEN)
                dto.items.append(item_dto)
            filtered_orders.append(dto)

    return filtered_orders


@router.get(
    "/api/v1/kds/history",
    summary="Consultar historial de comandas despachadas en KDS",
    description="Retorna el histórico de órdenes despachadas (DELIVERED) con métricas de tiempo de preparación."
)
def get_kds_history(
    station: Optional[KDSStation] = Query(None, description="Filtrar por estación (KITCHEN o BAR)"),
    limit: int = Query(50, ge=1, le=200, description="Cantidad máxima de órdenes a retornar"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    stmt = (
        select(Order)
        .options(
            joinedload(Order.items).joinedload(OrderItem.product),
            joinedload(Order.machine),
            joinedload(Order.created_by),
            joinedload(Order.cancelled_by)
        )
        .where(Order.status == OrderStatus.DELIVERED)
        .order_by(Order.updated_at.desc())
        .limit(limit)
    )


    orders = db.execute(stmt).unique().scalars().all()

    history = []
    total_prep_minutes = 0.0
    valid_prep_counts = 0

    for o in orders:
        matching_items = []
        for it in o.items:
            if not station or (it.product and it.product.destination_kds == station):
                matching_items.append({
                    "product_name": it.product.name if it.product else "Artículo",
                    "quantity": float(it.quantity),
                    "subtotal": float(it.subtotal)
                })

        if matching_items:
            # Calcular tiempo transcurrido en minutos entre creación y entrega
            prep_time_minutes = 0.0
            if o.created_at and o.updated_at:
                diff = (o.updated_at - o.created_at).total_seconds() / 60.0
                prep_time_minutes = round(max(0.1, diff), 1)
                total_prep_minutes += prep_time_minutes
                valid_prep_counts += 1

            history.append({
                "id": str(o.id),
                "order_number": o.order_number,
                "status": o.status.value,
                "machine_code": o.machine.asset_code if o.machine else "000",
                "created_by": o.created_by.full_name if o.created_by else "Staff Piso",
                "total_amount": float(o.total_amount),
                "created_at": o.created_at.isoformat() if o.created_at else None,
                "delivered_at": o.updated_at.isoformat() if o.updated_at else None,
                "prep_time_minutes": prep_time_minutes,
                "notes": o.notes,
                "items": matching_items
            })

    avg_prep_time = round(total_prep_minutes / valid_prep_counts, 1) if valid_prep_counts > 0 else 0.0

    return {
        "count": len(history),
        "avg_prep_time_minutes": avg_prep_time,
        "orders": history
    }



@router.patch(
    "/api/v1/kds/orders/{order_id}/status",
    response_model=OrderRead,
    summary="Actualizar estado de preparación de la comanda",
    description="Permite a Cocina o Barra mover estados del flujo (PENDING -> PREPARING -> READY -> DELIVERED)."
)
def update_kds_order_status(
    order_id: uuid.UUID,
    payload: KDSOrderUpdate,
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

    previous_status = order.status
    order.status = payload.status
    db.commit()
    db.refresh(order)

    dto = _build_order_dto(order)
    order_payload = dto.model_dump(mode="json")

    # Notificar cambio de estado vía WebSocket
    stations = {item.product.destination_kds.value for item in order.items if item.product}
    if not stations:
        stations = {"KITCHEN"}

    for st in stations:
        kds_manager.broadcast_sync(
            station=st,
            message={
                "event": "STATUS_UPDATE",
                "order_id": str(order.id),
                "status": order.status.value,
                "order": order_payload
            }
        )

    # Si la orden fue marcada como READY, notificar a Meseros y Runners inmediatamente
    if payload.status == OrderStatus.READY:
        kds_manager.broadcast_sync(
            station="WAITERS",
            message={
                "event": "ORDER_READY",
                "order_id": str(order.id),
                "order": order_payload,
                "message": f"¡Comanda #{order.order_number} lista para entrega!"
            }
        )
        kds_manager.broadcast_sync(
            station="RUNNERS",
            message={
                "event": "ORDER_READY",
                "order_id": str(order.id),
                "order": order_payload
            }
        )
        trigger_order_ready_notification(order_payload)
    elif payload.status == OrderStatus.DELIVERED:
        kds_manager.broadcast_sync(
            station="WAITERS",
            message={
                "event": "ORDER_DELIVERED",
                "order_id": str(order.id),
                "order": order_payload
            }
        )

    return dto


@router.post(
    "/api/v1/orders/{order_id}/cancel",
    response_model=OrderRead,
    summary="Cancelar una comanda con PIN de supervisor y registro de merma/reversa",
    description="Exige PIN de supervisor. Si la comanda estaba en preparación o lista, registra merma justificada. Si estaba pendiente, revierte el stock."
)
@router.post(
    "/api/v1/kds/orders/{order_id}/cancel",
    response_model=OrderRead,
    include_in_schema=False
)
def cancel_order(
    order_id: uuid.UUID,
    payload: OrderCancel,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
) -> OrderRead:
    # 1. Validar PIN de supervisor
    if not payload.supervisor_pin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Se requiere el PIN de supervisor para autorizar la cancelación."
        )

    stmt_sup = select(User).options(joinedload(User.role)).where(User.is_active == True)
    users = db.execute(stmt_sup).unique().scalars().all()
    supervisor = next((u for u in users if u.role.name in [UserRole.JEFE_DE_SALA, UserRole.ADMIN] and u.hashed_pin and verify_pin(payload.supervisor_pin, u.hashed_pin)), None)

    if not supervisor:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El PIN de supervisor ingresado no es válido para autorizar la cancelación."
        )

    # 2. Consultar la comanda
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

    if order.status == OrderStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esta comanda ya ha sido cancelada previamente."
        )

    # 3. Lógica de Reversa o Merma según el estado de producción
    try:
        if order.status in [OrderStatus.PREPARING, OrderStatus.READY, OrderStatus.DELIVERED]:
            # Alimentos ya cocinados/preparados -> Generar merma justificada
            for item in order.items:
                reason = f"Cancelación comanda #{order.order_number}: {payload.reason} (Autorizó: {supervisor.full_name})"
                InventoryService.record_order_cancellation_waste(
                    db=db,
                    product_id=item.product_id,
                    order_quantity=item.quantity,
                    reason=reason,
                    user_id=supervisor.id
                )
        else:
            # Orden en PENDING -> Revertir stock al almacén/estación limpia
            for item in order.items:
                notes = f"Reversa por cancelación comanda #{order.order_number}: {payload.reason} (Autorizó: {supervisor.full_name})"
                InventoryService.revert_product_stock(
                    db=db,
                    product_id=item.product_id,
                    order_quantity=item.quantity,
                    notes=notes,
                    user_id=supervisor.id
                )

        # 4. Actualizar estado de comanda y auditoría
        order.status = OrderStatus.CANCELLED
        order.cancellation_reason = payload.reason
        order.cancelled_by_id = supervisor.id
        order.cancelled_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(order)

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error procesando cancelación: {str(e)}"
        )

    # 5. Broadcast WebSocket a KDS y meseros
    dto = _build_order_dto(order)
    order_payload = dto.model_dump(mode="json")

    stations = {item.product.destination_kds.value for item in order.items if item.product}
    if not stations:
        stations = {"KITCHEN", "BAR"}

    for st in stations:
        kds_manager.broadcast_sync(
            station=st,
            message={
                "event": "ORDER_CANCELLED",
                "order_id": str(order.id),
                "order": order_payload,
                "reason": payload.reason,
                "authorized_by": supervisor.full_name
            }
        )

    kds_manager.broadcast_sync(
        station="WAITERS",
        message={
            "event": "ORDER_CANCELLED",
            "order_id": str(order.id),
            "order": order_payload,
            "reason": payload.reason
        }
    )

    return dto


@router.websocket("/ws/kds")
@router.websocket("/api/v1/ws/kds")
@router.websocket("/api/v1/kds/ws")
async def websocket_kds_endpoint(
    websocket: WebSocket,
    station: str = Query("ALL", description="Filtro de suscripción (KITCHEN, BAR, WAITERS, ALL)")
):

    """
    Suscripción en tiempo real vía WebSocket para KDS, Barra y Meseros.
    """
    await kds_manager.connect(websocket, station)
    try:
        while True:
            data = await websocket.receive_text()
            # Responder con heartbeat / pong
            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong", "timestamp": str(uuid.uuid4())}))
            else:
                await websocket.send_text(json.dumps({"type": "ack", "data": data}))
    except WebSocketDisconnect:
        kds_manager.disconnect(websocket, station)

