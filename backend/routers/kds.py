"""
Router REST y WebSocket de Comandas y Kitchen Display System (KDS) (`/backend/routers/kds.py`)
========================================================================================
Este router expone la creación de pedidos (POS), consulta y actualización de
comandas para Cocina y Barra (KDS), y maneja las suscripciones en tiempo real
vía WebSockets.
"""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from backend.core.deps import get_current_user, get_db, require_role
from backend.models.enums import KDSStation, OrderStatus, UserRole
from backend.models.machine import Machine
from backend.models.order import Order, OrderItem
from backend.models.product import Product
from backend.models.user import User
from backend.schemas.order import KDSOrderUpdate, OrderCreate, OrderRead
from backend.services.inventory_service import InventoryService
from backend.websockets.kds_manager import kds_manager

router = APIRouter(tags=["Comandas y KDS (Kitchen Display System)"])


@router.post(
    "/api/v1/orders/",
    response_model=OrderRead,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar una nueva comanda de AyB",
    description="Crea la comanda de forma atómica. Ejecuta el descuento de stock de insumos. Dispara WebSockets a KDS."
)
def create_order(
    payload: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> OrderRead:
    # 1. Validar máquina si se proporciona
    if payload.machine_id:
        machine = db.get(Machine, payload.machine_id)
        if not machine:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Máquina con ID '{payload.machine_id}' no encontrada."
            )

    # 2. Iniciar Transacción de Comanda de forma Atómica
    try:
        # Generar folio incremental
        count_stmt = select(func.count(Order.id))
        order_count = db.execute(count_stmt).scalar() or 0
        folio = f"COM-{order_count + 1:05d}"

        # Instanciar orden base
        order = Order(
            machine_id=payload.machine_id,
            order_number=folio,
            status=OrderStatus.PENDING,
            total_amount=0.0,
            notes=payload.notes,
            created_by_id=current_user.id
        )
        db.add(order)
        db.flush()  # Obtener ID de la orden sin confirmar

        total_accumulated = 0.0

        # Mapeo de estaciones KDS afectadas para avisar a WebSockets
        stations_affected = set()

        for item in payload.items:
            product = db.get(Product, item.product_id)
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Producto con ID '{item.product_id}' no encontrado."
                )

            # Validar e incrementar totales
            subtotal = product.price * item.quantity
            total_accumulated += float(subtotal)

            # Crear renglón
            order_item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=item.quantity,
                unit_price=product.price,
                subtotal=subtotal
            )
            db.add(order_item)

            # Determinar estación KDS
            stations_affected.add(product.destination_kds)

            # 3. Descontar Stock de Insumos/Materia prima de forma Atómica
            # Si falla, lanzará una excepción y la transacción hará rollback completo.
            InventoryService.deduct_product_stock(
                db=db,
                product_id=product.id,
                order_quantity=item.quantity,
                user_id=current_user.id
            )

        order.total_amount = total_accumulated
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

    # 4. Transmitir alerta WebSocket a las pantallas KDS
    # Para cada estación afectada, mandamos notificación
    # Volvemos a buscar la orden con relaciones para estructurar bien la respuesta
    stmt = (
        select(Order)
        .options(joinedload(Order.items).joinedload(OrderItem.product))
        .where(Order.id == order.id)
    )
    final_order = db.execute(stmt).unique().scalar_one()
    dto = OrderRead.model_validate(final_order)
    
    # Inyectar nombres de productos en los ítems
    for idx, item in enumerate(final_order.items):
        dto.items[idx].product_name = item.product.name

    import asyncio
    for station in stations_affected:
        asyncio.run_coroutine_threadsafe(
            kds_manager.broadcast_to_station(
                station=station.value,
                message={
                    "event": "NEW_ORDER",
                    "station": station.value,
                    "order": dto.model_dump(mode="json")
                }
            ),
            asyncio.get_event_loop()
        )

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
    current_user: User = Depends(get_current_user)
) -> List[OrderRead]:
    stmt = (
        select(Order)
        .options(joinedload(Order.items).joinedload(OrderItem.product))
        .where(Order.status.in_([OrderStatus.PENDING, OrderStatus.PREPARING, OrderStatus.READY]))
    )

    orders = db.execute(stmt).unique().scalars().all()

    # Filtrar en memoria por estación KDS de sus productos
    filtered_orders = []
    for order in orders:
        matching_items = []
        for item in order.items:
            # Si no hay filtro o coincide la estación del KDS del producto
            if not station or item.product.destination_kds == station:
                matching_items.append(item)
        
        if matching_items:
            dto = OrderRead.model_validate(order)
            # Sobrescribir items solo con los correspondientes a la estación elegida
            dto.items = []
            for item in matching_items:
                item_dto = OrderItemRead.model_validate(item)
                item_dto.product_name = item.product.name
                dto.items.append(item_dto)
            filtered_orders.append(dto)

    # Ordenar FIFO (cronológico ascendente)
    filtered_orders.sort(key=lambda x: x.created_at)
    return filtered_orders


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
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.JEFE_DE_SALA, UserRole.KITCHEN_STAFF, UserRole.BARMAN]))
) -> OrderRead:
    stmt = (
        select(Order)
        .options(joinedload(Order.items).joinedload(OrderItem.product))
        .where(Order.id == order_id)
    )
    order = db.execute(stmt).unique().scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Comanda con ID '{order_id}' no encontrada."
        )

    order.status = payload.status
    db.commit()
    db.refresh(order)

    dto = OrderRead.model_validate(order)
    for idx, item in enumerate(order.items):
        dto.items[idx].product_name = item.product.name

    # Notificar cambio de estado vía WebSocket
    import asyncio
    stations = {item.product.destination_kds.value for item in order.items}
    for st in stations:
        asyncio.run_coroutine_threadsafe(
            kds_manager.broadcast_to_station(
                station=st,
                message={
                    "event": "STATUS_UPDATE",
                    "order_id": str(order.id),
                    "status": order.status.value,
                    "order": dto.model_dump(mode="json")
                }
            ),
            asyncio.get_event_loop()
        )

    return dto


@router.websocket("/ws/kds")
async def websocket_kds_endpoint(
    websocket: WebSocket,
    station: str = Query("ALL", description="Filtro de suscripción (KITCHEN, BAR, ALL)")
):
    """
    Suscripción en tiempo real vía WebSocket para KDS.
    """
    await kds_manager.connect(websocket, station)
    try:
        while True:
            # Mantener conexión abierta y responder pings/mensajes si los hubiera
            data = await websocket.receive_text()
            # KDS es principalmente receptor, pero respondemos eco o pings
            await websocket.send_text(f"Echo: {data}")
    except WebSocketDisconnect:
        kds_manager.disconnect(websocket, station)
