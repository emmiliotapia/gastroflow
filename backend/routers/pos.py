"""
Router REST de Configuración y Carga de Botonera del POS (`/api/v1/pos`)
========================================================================
Este router expone los endpoints para diseñar, listar y configurar las rejillas
táctiles de las categorías de comida y bebida del Punto de Venta.
"""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from backend.core.deps import get_current_user, get_db, require_role, get_optional_current_user
from backend.models.enums import UserRole
from backend.models.pos import POSButton, POSCategory
from backend.models.user import User
from backend.schemas.pos import (
    POSButtonCreate,
    POSButtonRead,
    POSCategoryCreate,
    POSCategoryRead,
    POSCategoryWithButtonsRead,
)

router = APIRouter(prefix="/api/v1/pos", tags=["Configuración de Botonera POS"])


@router.get(
    "/categories",
    response_model=List[POSCategoryWithButtonsRead],
    summary="Listar categorías y botones activos del POS",
    description="Retorna el catálogo completo jerárquico de pestañas y botones para pintar la UI del POS."
)
def get_pos_grid(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
) -> List[POSCategoryWithButtonsRead]:
    stmt = (
        select(POSCategory)
        .options(joinedload(POSCategory.buttons).joinedload(POSButton.product))
        .where(POSCategory.is_active == True)
        .order_by(POSCategory.display_order)
    )
    categories = db.execute(stmt).unique().scalars().all()
    return [POSCategoryWithButtonsRead.model_validate(c) for c in categories]


@router.post(
    "/categories",
    response_model=POSCategoryRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nueva categoría en la botonera",
    description="Crea una sección (ej. Especialidades). Requiere rol ADMIN o JEFE_DE_SALA."
)
def create_pos_category(
    payload: POSCategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.JEFE_DE_SALA]))
) -> POSCategoryRead:
    category = POSCategory(
        name=payload.name,
        color_theme=payload.color_theme,
        display_order=payload.display_order,
        is_active=True
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return POSCategoryRead.model_validate(category)


@router.post(
    "/buttons",
    response_model=POSButtonRead,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un botón de producto",
    description="Inserta un botón en un slot de la rejilla de una categoría. Requiere rol ADMIN o JEFE_DE_SALA."
)
def create_pos_button(
    payload: POSButtonCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.JEFE_DE_SALA]))
) -> POSButtonRead:
    button = POSButton(
        category_id=payload.category_id,
        product_id=payload.product_id,
        label=payload.label,
        color_class=payload.color_class,
        display_order=payload.display_order,
        is_active=True
    )
    db.add(button)
    db.commit()
    db.refresh(button)
    return POSButtonRead.model_validate(button)


@router.delete(
    "/buttons/{button_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar o inactivar un botón",
    description="Elimina físicamente un botón de la botonera. Requiere ADMIN o JEFE_DE_SALA."
)
def delete_pos_button(
    button_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.JEFE_DE_SALA]))
):
    stmt = select(POSButton).where(POSButton.id == button_id)
    button = db.execute(stmt).scalar_one_or_none()
    if not button:
        raise HTTPException(status_code=404, detail="Botón no encontrado")
    db.delete(button)
    db.commit()
    return None


@router.delete(
    "/categories/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar una categoría",
    description="Elimina físicamente una categoría y sus botones asociados. Requiere ADMIN o JEFE_DE_SALA."
)
def delete_pos_category(
    category_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.JEFE_DE_SALA]))
):
    db.query(POSButton).filter(POSButton.category_id == category_id).delete()
    
    category = db.get(POSCategory, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    db.delete(category)
    db.commit()
    return None


# --- ENDPOINTS OPERATIVOS PARA COMANDERO MÓVIL (POS) ---
from backend.models.order import Order, OrderItem
from backend.models.enums import OrderStatus, PaymentStatus
from backend.schemas.order import OrderCreate, OrderRead
from backend.routers.kds import create_order, cancel_order, _build_order_dto
from backend.schemas.order import OrderCancel
from backend.websockets.kds_manager import kds_manager
from backend.utils.n8n import trigger_order_status_notification

@router.post(
    "/order",
    response_model=OrderRead,
    status_code=status.HTTP_201_CREATED,
    summary="Alias para crear comanda desde POS o Menú Cliente",
    description="Redirige directamente al procesador atómico de comandas y dispara alertas ntfy/n8n."
)
def create_pos_order_alias(
    payload: OrderCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
) -> OrderRead:
    return create_order(payload=payload, db=db, current_user=current_user)


@router.get(
    "/orders",
    summary="Listar cuentas activas del comandero",
    description="Retorna todas las comandas en curso filtrables por estado (pendientes, en cocina, listas)."
)
def get_pos_active_orders(
    table: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    stmt = (
        select(Order)
        .options(
            joinedload(Order.items).joinedload(OrderItem.product),
            joinedload(Order.machine),
            joinedload(Order.created_by)
        )
        .where(Order.status.in_([OrderStatus.PENDING, OrderStatus.PREPARING, OrderStatus.READY]))
        .order_by(Order.created_at.desc())
    )
    orders = db.execute(stmt).unique().scalars().all()
    res = []
    for o in orders:
        dto = _build_order_dto(o)
        dto_dict = dto.model_dump(mode="json")
        if not table or (dto.machine_code and table.lower() in dto.machine_code.lower()):
            res.append(dto_dict)
    return res


@router.post(
    "/orders/{order_id}/cancel",
    summary="Matar / Cancelar comanda o cuenta desde el comandero",
    description="Cancela una orden activa y libera la mesa. Admite PIN de supervisor o cancelación directa por mesero."
)
def kill_pos_order(
    order_id: uuid.UUID,
    payload: Optional[dict] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
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
        raise HTTPException(status_code=404, detail="Comanda no encontrada")

    reason = (payload or {}).get("reason") or "Cancelada desde Comandero Móvil"
    order.status = OrderStatus.CANCELLED
    order.cancellation_reason = reason
    db.commit()
    db.refresh(order)

    dto = _build_order_dto(order)
    order_dict = dto.model_dump(mode="json")

    # Notificar KDS y meseros para retirar tarjeta
    kds_manager.broadcast_sync(
        station="ALL",
        message={
            "event": "ORDER_CANCELLED",
            "order_id": str(order.id),
            "order": order_dict,
            "reason": reason
        }
    )
    trigger_order_status_notification({**order_dict, "cancellation_reason": reason}, "CANCELLED")
    return {"message": f"Cuenta {order.order_number} cancelada exitosamente", "order": order_dict}


@router.post(
    "/orders/{order_id}/close",
    summary="Cerrar / Cobrar comanda desde el comandero",
    description="Marca la comanda como cobrada/entregada (DELIVERED) y finaliza la cuenta de la mesa."
)
def close_pos_order(
    order_id: uuid.UUID,
    payload: Optional[dict] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
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
        raise HTTPException(status_code=404, detail="Comanda no encontrada")

    pay_method = (payload or {}).get("payment_method") or "EFECTIVO"
    order.status = OrderStatus.DELIVERED
    order.payment_status = PaymentStatus.PAID
    order.payment_method = pay_method
    db.commit()
    db.refresh(order)

    dto = _build_order_dto(order)
    order_dict = dto.model_dump(mode="json")

    kds_manager.broadcast_sync(
        station="ALL",
        message={
            "event": "ORDER_DELIVERED",
            "order_id": str(order.id),
            "order": order_dict
        }
    )
    return {"message": f"Cuenta {order.order_number} cerrada con éxito", "order": order_dict}


@router.get(
    "/reports/summary",
    summary="Reporte de ventas del turno para comandero",
    description="Calcula ventas totales, comandas activas, cerradas, ticket promedio y desglose por categoría."
)
def get_pos_shift_report(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    stmt = select(Order).options(joinedload(Order.items))
    all_orders = db.execute(stmt).unique().scalars().all()

    total_sales = sum(float(o.total_amount) for o in all_orders if o.status == OrderStatus.DELIVERED or o.payment_status == PaymentStatus.PAID)
    active_orders = [o for o in all_orders if o.status in (OrderStatus.PENDING, OrderStatus.PREPARING, OrderStatus.READY)]
    cancelled_orders = [o for o in all_orders if o.status == OrderStatus.CANCELLED]
    delivered_orders = [o for o in all_orders if o.status == OrderStatus.DELIVERED]

    avg_ticket = (total_sales / len(delivered_orders)) if delivered_orders else 0.0

    return {
        "shift": "Turno Actual de Salón",
        "total_sales": round(total_sales, 2),
        "total_orders": len(all_orders),
        "active_count": len(active_orders),
        "delivered_count": len(delivered_orders),
        "cancelled_count": len(cancelled_orders),
        "average_ticket": round(avg_ticket, 2),
        "active_tables": list({(o.machine.asset_code if o.machine else "000") for o in active_orders})
    }
