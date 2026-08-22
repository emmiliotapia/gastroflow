"""
Router REST de Catálogos de Insumos, Productos y Recetas (`/api/v1`)
====================================================================
Este módulo implementa los endpoints para:
- Gestión completa de Ingredientes e Insumos (`/api/v1/ingredients`).
- Gestión de Productos de AyB y Fichas Técnicas de Recetas (`/api/v1/products`).
- Cálculo dinámico de Costos de Producción y Márgenes de Ganancia.
"""

import uuid
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from backend.core.deps import get_current_user, get_db, require_role, get_optional_current_user
from backend.models.enums import KDSStation, ProductType, UserRole
from backend.models.ingredient import Ingredient
from backend.models.product import Product, RecipeItem
from backend.models.user import User
from backend.schemas.catalog import (
    IngredientCreate,
    IngredientRead,
    IngredientUpdate,
    ProductCreate,
    ProductRead,
    ProductUpdate,
    RecipeCostSummary,
    RecipeItemCreate,
    RecipeItemRead,
)

router = APIRouter(prefix="/api/v1", tags=["Catálogos de AyB y Recetas"])


# ==============================================================================
# Helper de Cálculo de Ficha Técnica
# ==============================================================================

def _build_product_read_schema(product: Product) -> ProductRead:
    """
    Función auxiliar para construir el esquema `ProductRead` calculando
    los subtotales de cada insumo y el costo total de producción.
    """
    recipe_read_items: List[RecipeItemRead] = []
    total_cost = Decimal("0.0000")

    for item in product.recipe_items:
        ing = item.ingredient
        unit_cost = ing.cost_per_unit if ing else Decimal("0.0000")
        subtotal = item.quantity * unit_cost
        total_cost += subtotal

        recipe_read_items.append(
            RecipeItemRead(
                id=item.id,
                ingredient_id=item.ingredient_id,
                ingredient_code=ing.code if ing else None,
                ingredient_name=ing.name if ing else None,
                quantity=item.quantity,
                unit_of_measure=item.unit_of_measure,
                unit_cost=unit_cost,
                subtotal_cost=subtotal
            )
        )

    return ProductRead(
        id=product.id,
        sku=product.sku,
        name=product.name,
        description=product.description,
        category=product.category,
        image_url=product.image_url,
        product_type=product.product_type,
        destination_kds=product.destination_kds,
        price=product.price,
        courtesy_tier_min=product.courtesy_tier_min,
        current_stock=product.current_stock if product.current_stock is not None else Decimal("0.0000"),
        is_active=product.is_active if product.is_active is not None else True,
        recipe_items=recipe_read_items,
        total_production_cost=total_cost
    )



# ==============================================================================
# Endpoints de Ingredientes (/api/v1/ingredients)
# ==============================================================================

@router.post(
    "/ingredients",
    response_model=IngredientRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un nuevo ingrediente / insumo",
    description="Crea un nuevo insumo en la base de datos."
)
def create_ingredient(
    payload: IngredientCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
) -> IngredientRead:
    # Validar que el código no exista previamente
    existing = db.execute(
        select(Ingredient).where(Ingredient.code == payload.code)
    ).scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe un ingrediente registrado con el código '{payload.code}'."
        )

    ingredient = Ingredient(
        code=payload.code,
        name=payload.name,
        category=payload.category or "ABARROTES",
        unit_of_measure=payload.unit_of_measure,
        cost_per_unit=payload.cost_per_unit,
        current_stock=payload.current_stock,
        minimum_stock=payload.minimum_stock,
        is_active=True
    )
    db.add(ingredient)
    db.commit()
    db.refresh(ingredient)
    return IngredientRead.model_validate(ingredient)


@router.get(
    "/ingredients",
    response_model=List[IngredientRead],
    summary="Listar catálogo de ingredientes e insumos",
    description="Retorna el catálogo maestro de ingredientes con su costo y existencias vigentes."
)
def list_ingredients(
    search: Optional[str] = Query(None, description="Filtrar por nombre o código"),
    is_active: Optional[bool] = Query(None, description="Filtrar por estado activo/inactivo"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
) -> List[IngredientRead]:
    stmt = select(Ingredient)
    if is_active is not None:
        stmt = stmt.where(Ingredient.is_active == is_active)
    if search:
        stmt = stmt.where(
            (Ingredient.name.ilike(f"%{search}%")) | (Ingredient.code.ilike(f"%{search}%"))
        )

    stmt = stmt.order_by(Ingredient.name.asc())
    ingredients = db.execute(stmt).scalars().all()
    return [IngredientRead.model_validate(i) for i in ingredients]


@router.get(
    "/ingredients/{ingredient_id}",
    response_model=IngredientRead,
    summary="Obtener un ingrediente por ID"
)
def get_ingredient(
    ingredient_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
) -> IngredientRead:
    ingredient = db.get(Ingredient, ingredient_id)
    if not ingredient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ingrediente no encontrado."
        )
    return IngredientRead.model_validate(ingredient)


@router.put(
    "/ingredients/{ingredient_id}",
    response_model=IngredientRead,
    summary="Actualizar un ingrediente"
)
def update_ingredient(
    ingredient_id: uuid.UUID,
    payload: IngredientUpdate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
) -> IngredientRead:
    ingredient = db.get(Ingredient, ingredient_id)
    if not ingredient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ingrediente no encontrado."
        )

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(ingredient, field, value)

    db.commit()
    db.refresh(ingredient)
    return IngredientRead.model_validate(ingredient)


@router.delete(
    "/ingredients/{ingredient_id}",
    summary="Desactivar ingrediente (Soft Delete)"
)
def delete_ingredient(
    ingredient_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    ingredient = db.get(Ingredient, ingredient_id)
    if not ingredient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ingrediente no encontrado."
        )

    ingredient.is_active = False
    db.commit()
    return {"message": f"Ingrediente '{ingredient.name}' desactivado exitosamente."}


# ==============================================================================
# Endpoints de Productos y Recetas (/api/v1/products)
# ==============================================================================

@router.post(
    "/products",
    response_model=ProductRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un nuevo producto final AyB",
    description="Crea un producto de menú. Si el tipo es PREPARED, se vinculan sus elementos de receta."
)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
) -> ProductRead:
    # Verificar SKU único
    existing = db.execute(
        select(Product).where(Product.sku == payload.sku)
    ).scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe un producto registrado con el SKU '{payload.sku}'."
        )

    product = Product(
        sku=payload.sku,
        name=payload.name,
        description=payload.description,
        category=payload.category,
        image_url=payload.image_url,
        product_type=payload.product_type,
        destination_kds=payload.destination_kds,
        price=payload.price,
        courtesy_tier_min=payload.courtesy_tier_min,
        current_stock=payload.current_stock,
        is_active=True
    )
    db.add(product)
    db.flush()  # Obtener UUID de producto

    # Si se especificó una receta para un producto preparado
    if payload.product_type == ProductType.PREPARED and payload.recipe_items:
        for r_item in payload.recipe_items:
            ing = db.get(Ingredient, r_item.ingredient_id)
            if not ing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El ingrediente con ID '{r_item.ingredient_id}' no existe."
                )

            recipe_entity = RecipeItem(
                product_id=product.id,
                ingredient_id=r_item.ingredient_id,
                quantity=r_item.quantity,
                unit_of_measure=r_item.unit_of_measure
            )
            db.add(recipe_entity)

    db.commit()

    # Re-consultar con relaciones precargadas
    stmt = (
        select(Product)
        .options(joinedload(Product.recipe_items).joinedload(RecipeItem.ingredient))
        .where(Product.id == product.id)
    )
    product_loaded = db.execute(stmt).scalar_one()
    return _build_product_read_schema(product_loaded)


@router.get(
    "/products",
    response_model=List[ProductRead],
    summary="Listar catálogo de productos AyB",
    description="Retorna el catálogo completo de alimentos y bebidas con el detalle de receta y costo de producción."
)
def list_products(
    category: Optional[str] = Query(None, description="Filtrar por categoría (ej. Hamburguesas Gourmet)"),
    product_type: Optional[ProductType] = Query(None, description="PREPARED vs DIRECT"),
    destination_kds: Optional[KDSStation] = Query(None, description="KITCHEN vs BAR"),
    is_active: Optional[bool] = Query(None, description="Estado activo/inactivo"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
) -> List[ProductRead]:
    stmt = (
        select(Product)
        .options(joinedload(Product.recipe_items).joinedload(RecipeItem.ingredient))
    )

    if is_active is not None:
        stmt = stmt.where(Product.is_active == is_active)
    if category:
        stmt = stmt.where(Product.category.ilike(f"%{category}%"))
    if product_type:
        stmt = stmt.where(Product.product_type == product_type)
    if destination_kds:
        stmt = stmt.where(Product.destination_kds == destination_kds)

    stmt = stmt.order_by(Product.name.asc())
    products = db.execute(stmt).unique().scalars().all()
    return [_build_product_read_schema(p) for p in products]


@router.get(
    "/products/{product_id}",
    response_model=ProductRead,
    summary="Obtener producto por ID con ficha técnica"
)
def get_product(
    product_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
) -> ProductRead:
    stmt = (
        select(Product)
        .options(joinedload(Product.recipe_items).joinedload(RecipeItem.ingredient))
        .where(Product.id == product_id)
    )
    product = db.execute(stmt).unique().scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado."
        )

    return _build_product_read_schema(product)


@router.put(
    "/products/{product_id}",
    response_model=ProductRead,
    summary="Actualizar producto de AyB"
)
def update_product(
    product_id: uuid.UUID,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
) -> ProductRead:
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado.")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    return _build_product_read_schema(product)


from fastapi import UploadFile, File
import shutil
import os

@router.post(
    "/products/{product_id}/image",
    response_model=ProductRead,
    summary="Subir o actualizar fotografía del producto"
)
async def upload_product_image(
    product_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
) -> ProductRead:
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado.")

    upload_dir = os.path.join("uploads", "products")
    os.makedirs(upload_dir, exist_ok=True)

    extension = os.path.splitext(file.filename)[1] or ".jpg"
    filename = f"{product.id}_{uuid.uuid4().hex[:8]}{extension}"
    file_path = os.path.join(upload_dir, filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    product.image_url = f"/uploads/products/{filename}"
    db.commit()
    db.refresh(product)
    return _build_product_read_schema(product)


@router.delete(
    "/products/{product_id}",
    summary="Desactivar / eliminar producto de AyB"
)
def delete_product(
    product_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado.")
    
    product.is_active = False
    db.commit()
    return {"message": f"Producto '{product.name}' desactivado exitosamente."}


@router.post(
    "/products/{product_id}/recipe",
    response_model=ProductRead,
    summary="Configurar o actualizar la receta de un producto",
    description="Reemplaza los insumos de la ficha técnica del producto preparado."
)
def set_product_recipe(
    product_id: uuid.UUID,
    recipe_items: List[RecipeItemCreate],
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
) -> ProductRead:
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado."
        )

    if product.product_type != ProductType.PREPARED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo los productos de tipo 'PREPARED' pueden tener una receta asociada."
        )

    # Eliminar elementos previos de receta
    db.execute(
        RecipeItem.__table__.delete().where(RecipeItem.product_id == product_id)
    )

    # Insertar los nuevos insumos
    for item in recipe_items:
        ing = db.get(Ingredient, item.ingredient_id)
        if not ing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ingrediente con ID '{item.ingredient_id}' no encontrado."
            )

        recipe_entity = RecipeItem(
            product_id=product_id,
            ingredient_id=item.ingredient_id,
            quantity=item.quantity,
            unit_of_measure=item.unit_of_measure
        )
        db.add(recipe_entity)

    db.commit()

    # Re-consultar con relaciones precargadas
    stmt = (
        select(Product)
        .options(joinedload(Product.recipe_items).joinedload(RecipeItem.ingredient))
        .where(Product.id == product_id)
    )
    product_updated = db.execute(stmt).unique().scalar_one()
    return _build_product_read_schema(product_updated)


@router.get(
    "/products/{product_id}/cost",
    response_model=RecipeCostSummary,
    summary="Calcular costo de producción dinámico y margen de ganancia",
    description="Calcula en tiempo real la suma ponderada del costo de insumos y determina el margen bruto."
)
def calculate_product_cost(
    product_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> RecipeCostSummary:
    stmt = (
        select(Product)
        .options(joinedload(Product.recipe_items).joinedload(RecipeItem.ingredient))
        .where(Product.id == product_id)
    )
    product = db.execute(stmt).unique().scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado."
        )

    product_dto = _build_product_read_schema(product)
    cost = product_dto.total_production_cost
    price = product.price

    margin_amount = price - cost
    margin_percent = ((margin_amount / price) * Decimal("100")) if price > 0 else Decimal("0.00")

    return RecipeCostSummary(
        product_id=product.id,
        product_sku=product.sku,
        product_name=product.name,
        sale_price=price,
        total_production_cost=cost,
        profit_margin_amount=margin_amount,
        profit_margin_percent=round(margin_percent, 2),
        recipe_items=product_dto.recipe_items
    )


# ==============================================================================
# Endpoints de Clientes VIP y Tabulador de Cortesías (/api/v1/vip-clients)
# ==============================================================================

from backend.models.vip_client import VIPClient
from backend.models.enums import MembershipTier, StockLocation
from backend.schemas.catalog import (
    VIPClientCreate,
    VIPClientRead,
    CourtesyValidationRequest,
    CourtesyValidationResponse,
)
from backend.services.inventory_service import InventoryService


@router.get(
    "/vip-clients",
    response_model=List[VIPClientRead],
    summary="Listar padrón de clientes VIP",
    description="Consulta y búsqueda de clientes del padrón VIP de marketing."
)
def list_vip_clients(
    search: Optional[str] = Query(None, description="Buscar por nombre, código o tarjeta"),
    tier: Optional[str] = Query(None, description="Filtrar por nivel (PLATA, ORO, PLATINO, PRESTIGE)"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
) -> List[VIPClientRead]:
    stmt = select(VIPClient).where(VIPClient.is_active == True)
    if search:
        stmt = stmt.where(
            (VIPClient.full_name.ilike(f"%{search}%")) |
            (VIPClient.client_code.ilike(f"%{search}%")) |
            (VIPClient.card_number.ilike(f"%{search}%"))
        )
    if tier:
        stmt = stmt.where(VIPClient.tier == tier.upper())

    stmt = stmt.order_by(VIPClient.full_name.asc())
    clients = db.execute(stmt).scalars().all()
    return [VIPClientRead.model_validate(c) for c in clients]


@router.post(
    "/vip-clients",
    response_model=VIPClientRead,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar socio en padrón VIP"
)
def create_vip_client(
    payload: VIPClientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.JEFE_DE_SALA]))
) -> VIPClientRead:
    # Validar código único
    existing = db.execute(select(VIPClient).where(VIPClient.client_code == payload.client_code)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe un cliente con el código '{payload.client_code}'."
        )

    # Validar tier enum
    tier_enum = MembershipTier.PLATA
    try:
        tier_enum = MembershipTier[payload.tier.upper()]
    except KeyError:
        pass

    client = VIPClient(
        client_code=payload.client_code,
        full_name=payload.full_name,
        card_number=payload.card_number,
        phone=payload.phone,
        tier=tier_enum,
        daily_courtesy_limit=payload.daily_courtesy_limit,
        is_active=True,
        notes=payload.notes
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return VIPClientRead.model_validate(client)


@router.post(
    "/vip-clients/validate-courtesy",
    response_model=CourtesyValidationResponse,
    summary="Validar elegibilidad de cortesía para un cliente VIP"
)
def validate_courtesy(
    payload: CourtesyValidationRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
) -> CourtesyValidationResponse:
    # 1. Buscar producto
    product = db.get(Product, payload.product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado.")

    # 2. Buscar cliente por código, tarjeta o nombre
    ident = payload.client_identifier.strip()
    stmt = select(VIPClient).where(
        (VIPClient.client_code.ilike(ident)) |
        (VIPClient.card_number.ilike(ident)) |
        (VIPClient.full_name.ilike(f"%{ident}%"))
    )
    client = db.execute(stmt).scalars().first()

    client_tier = client.tier.value if client else "CLASSIC"
    client_name = client.full_name if client else "Cliente General"

    TIER_RANKS = {
        "CLASSIC": 0, "PLATA": 0, None: 0,
        "GOLD": 1, "ORO": 1,
        "PLATINUM": 2, "PLATINO": 2,
        "VIP": 3, "PRESTIGE": 3
    }

    req_tier = product.courtesy_tier_min or "PRESTIGE"
    is_eligible = TIER_RANKS.get(client_tier.upper(), 0) >= TIER_RANKS.get(req_tier.upper(), 0)

    return CourtesyValidationResponse(
        is_eligible=is_eligible,
        client_name=client_name,
        client_tier=client_tier,
        required_tier=req_tier,
        product_name=product.name,
        product_price=product.price,
        final_price=Decimal("0.00") if is_eligible else product.price,
        requires_supervisor_pin=not is_eligible,
        message="Cortesía autorizada por nivel VIP" if is_eligible else f"Requiere PIN de supervisor (Nivel mínimo: {req_tier})"
    )


@router.get(
    "/courtesy-rules",
    summary="Consultar tabulador y reglas de cortesías por nivel VIP"
)
def get_courtesy_rules():
    """Retorna la matriz de beneficios y tabulador de cortesías."""
    return {
        "levels": [
            {
                "tier": "PLATA",
                "alias": "CLASSIC",
                "badge_color": "#94a3b8",
                "benefits": "Cafetería, aguas embotelladas y refrescos seleccionados",
                "allowed_categories": ["Cafetería", "Bebidas no alcohólicas"],
                "daily_limit": 3
            },
            {
                "tier": "ORO",
                "alias": "GOLD",
                "badge_color": "#f59e0b",
                "benefits": "Cervezas nacionales, coctelería clásica y botanas/snacks",
                "allowed_categories": ["Cafetería", "Bebidas", "Cervezas", "Entradas", "Snacks"],
                "daily_limit": 6
            },
            {
                "tier": "PLATINO",
                "alias": "PLATINUM",
                "badge_color": "#e2e8f0",
                "benefits": "Coctelería premium, destilados importados y platos fuertes",
                "allowed_categories": ["Cafetería", "Coctelería", "Especialidades", "Hamburguesas Gourmet", "Bebidas"],
                "daily_limit": 10
            },
            {
                "tier": "PRESTIGE",
                "alias": "VIP",
                "badge_color": "#d4af37",
                "benefits": "Cortesías 100% libres en todo el menú de Alimentos y Bebidas",
                "allowed_categories": ["*"],
                "daily_limit": 99
            }
        ]
    }


@router.get(
    "/kitchen/stock",
    summary="Consultar existencias dedicadas en el área de producción / cocina"
)
def get_kitchen_stock(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """Retorna las existencias físicas en la bodega de Cocina (KITCHEN)."""
    return InventoryService.get_stock_by_location(db=db, location=StockLocation.KITCHEN)


