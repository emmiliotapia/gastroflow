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


# --- ALIAS PARA COMPATIBILIDAD CON FRONTENDS DE PEDIDOS ---
from backend.schemas.order import OrderCreate, OrderRead
from backend.routers.kds import create_order

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
