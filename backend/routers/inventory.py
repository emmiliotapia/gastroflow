"""
Router REST de Gestión de Inventario, Mermas, Alertas y POS (`/api/v1/inventory`)
================================================================================
Este módulo expone los endpoints HTTP para la administración física de bodegas,
porcionado de recetas, control de mermas valorizadas, alertas de compra y el
simulador del motor de descuento atómico del POS.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.core.deps import get_current_user, get_db, require_role
from backend.models.enums import StockLocation, UserRole
from backend.models.stock import StockLevel
from backend.models.user import User
from backend.models.waste import WasteLog
from backend.schemas.inventory import (
    LowStockAlertRead,
    POSDeductRequest,
    POSDeductResponse,
    PortioningRequest,
    StockLevelRead,
    StockTransactionCreate,
    StockTransactionRead,
    WasteLogCreate,
    WasteLogRead,
)
from backend.services.inventory_service import InventoryService

router = APIRouter(prefix="/api/v1/inventory", tags=["Gestión de Inventario y Mermas"])


@router.get(
    "/levels",
    response_model=List[StockLevelRead],
    summary="Consultar niveles de stock por bodega/estación",
    description="Retorna el balance físico actual de existencias por ingrediente o producto."
)
def get_stock_levels(
    location: Optional[StockLocation] = Query(None, description="Filtrar por bodega (WAREHOUSE, KITCHEN, BAR)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[StockLevelRead]:
    stmt = select(StockLevel)
    if location:
        stmt = stmt.where(StockLevel.location == location)

    levels = db.execute(stmt).scalars().all()
    return [StockLevelRead.model_validate(l) for l in levels]


@router.post(
    "/adjust",
    response_model=StockLevelRead,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar compras o ajustes de inventario",
    description="Registra una compra o ajuste físico de stock. (Requiere rol ADMIN o JEFE_DE_SALA)."
)
def adjust_inventory_stock(
    payload: StockTransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.JEFE_DE_SALA]))
) -> StockLevelRead:
    stock_level = InventoryService.adjust_stock(
        db=db,
        location=payload.location,
        transaction_type=payload.transaction_type,
        quantity=payload.quantity,
        ingredient_id=payload.ingredient_id,
        product_id=payload.product_id,
        unit_cost=payload.unit_cost,
        notes=payload.notes,
        user_id=current_user.id
    )
    return StockLevelRead.model_validate(stock_level)


@router.post(
    "/portion",
    summary="Porcionar / Convertir insumos macro a micro",
    description="Descuenta insumos macro de volumen (ej. KG de Carne) y genera porciones micro (ej. porciones de 200g)."
)
def portion_ingredients(
    payload: PortioningRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.JEFE_DE_SALA]))
):
    result = InventoryService.register_portioning(
        db=db,
        macro_ingredient_id=payload.macro_ingredient_id,
        micro_ingredient_id=payload.micro_ingredient_id,
        macro_quantity=payload.macro_quantity,
        conversion_factor=payload.conversion_factor,
        location=payload.location,
        notes=payload.notes,
        user_id=current_user.id
    )
    return result


@router.post(
    "/waste",
    response_model=WasteLogRead,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar merma o desperdicio de insumo",
    description="Registra la pérdida de un insumo/producto, descuenta el stock y calcula el costo valorizado."
)
def log_waste(
    payload: WasteLogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.JEFE_DE_SALA]))
) -> WasteLogRead:
    waste_entry = InventoryService.register_waste(
        db=db,
        location=payload.location,
        quantity=payload.quantity,
        reason=payload.reason,
        ingredient_id=payload.ingredient_id,
        product_id=payload.product_id,
        user_id=current_user.id
    )
    return WasteLogRead.model_validate(waste_entry)


@router.get(
    "/waste/report",
    response_model=List[WasteLogRead],
    summary="Consultar reporte e historial de mermas"
)
def get_waste_report(
    location: Optional[StockLocation] = Query(None, description="Filtrar por bodega/estación"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[WasteLogRead]:
    stmt = select(WasteLog)
    if location:
        stmt = stmt.where(WasteLog.location == location)

    stmt = stmt.order_by(WasteLog.created_at.desc())
    wastes = db.execute(stmt).scalars().all()
    return [WasteLogRead.model_validate(w) for w in wastes]


@router.get(
    "/alerts",
    response_model=List[LowStockAlertRead],
    summary="Consultar alertas de stock mínimo",
    description="Devuelve la lista de ingredientes por debajo de su stock de seguridad, con propuesta de compra (útil para enrutamiento con n8n)."
)
def get_low_stock_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[LowStockAlertRead]:
    alerts = InventoryService.get_low_stock_alerts(db)
    return [LowStockAlertRead(**a) for a in alerts]


@router.post(
    "/pos-deduct-test",
    response_model=POSDeductResponse,
    summary="Simulador de Descuento Atómico de Comanda POS",
    description="Simula una comanda del POS y ejecuta el descuento atómico en tiempo real del stock de receta."
)
def pos_deduct_test(
    payload: POSDeductRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> POSDeductResponse:
    result = InventoryService.deduct_product_stock(
        db=db,
        product_id=payload.product_id,
        order_quantity=payload.order_quantity,
        location=payload.location,
        user_id=current_user.id
    )
    return POSDeductResponse(**result)
