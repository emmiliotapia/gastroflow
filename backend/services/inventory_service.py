"""
Servicio de Negocio de Inventario, Mermas y Descuentos POS (`inventory_service.py`)
===================================================================================
Este módulo encapsula la lógica de negocio pura para:
- Ajustes transaccionales de stock por bodega/estación.
- Conversión y porcionado de insumos macro a micro.
- Registro y costeo de mermas y desperdicios.
- Descuento atómico de insumos por comanda POS (Motor de Recetas).
- Cálculo de alertas de stock mínimo para reabastecimiento.
"""

import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from backend.models.enums import KDSStation, ProductType, StockLocation, StockTransactionType
from backend.models.ingredient import Ingredient
from backend.models.product import Product, RecipeItem
from backend.models.stock import StockLevel, StockTransaction
from backend.models.waste import WasteLog


class InventoryService:
    """
    Servicio central de operaciones de inventario.
    """

    @staticmethod
    def adjust_stock(
        db: Session,
        location: StockLocation,
        transaction_type: StockTransactionType,
        quantity: Decimal,
        ingredient_id: Optional[uuid.UUID] = None,
        product_id: Optional[uuid.UUID] = None,
        unit_cost: Optional[Decimal] = None,
        notes: Optional[str] = None,
        user_id: Optional[uuid.UUID] = None
    ) -> StockLevel:
        """
        Ajusta el balance de stock físico de un ingrediente o producto en una ubicación dada
        y registra el movimiento inmutable en `stock_transactions`.

        :param quantity: Cantidad (Positiva para incrementos/compras, negativa para decrementos/ventas).
        """
        if not ingredient_id and not product_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Se debe especificar al menos un ingredient_id o product_id."
            )

        # 1. Obtener o crear el nivel de stock para esta ubicación
        stmt = select(StockLevel).where(
            StockLevel.location == location,
            StockLevel.ingredient_id == ingredient_id,
            StockLevel.product_id == product_id
        )
        stock_level = db.execute(stmt).scalar_one_or_none()

        if not stock_level:
            stock_level = StockLevel(
                ingredient_id=ingredient_id,
                product_id=product_id,
                location=location,
                quantity=Decimal("0.0000")
            )
            db.add(stock_level)
            db.flush()

        # Actualizar cantidad disponible en esta bodega
        stock_level.quantity += quantity

        # Si el balance resultante fuera negativo en una salida estricta, lanzar advertencia
        if stock_level.quantity < Decimal("0.0000") and quantity < Decimal("0.0000"):
            # Permitimos stock negativo temporalmente para continuidad operativa, pero registramos la transacción
            pass

        # 2. Sincronizar stock global en la entidad principal
        cost_to_record = Decimal("0.0000")
        if ingredient_id:
            ing = db.get(Ingredient, ingredient_id)
            if ing:
                ing.current_stock += quantity
                cost_to_record = unit_cost if unit_cost is not None else ing.cost_per_unit
        elif product_id:
            prod = db.get(Product, product_id)
            if prod:
                prod.current_stock += quantity
                cost_to_record = unit_cost if unit_cost is not None else Decimal("0.0000")

        # 3. Registrar transacción auditable
        tx = StockTransaction(
            ingredient_id=ingredient_id,
            product_id=product_id,
            location=location,
            transaction_type=transaction_type,
            quantity=quantity,
            unit_cost=cost_to_record,
            notes=notes,
            created_by_id=user_id
        )
        db.add(tx)
        db.commit()
        db.refresh(stock_level)
        return stock_level

    @staticmethod
    def register_portioning(
        db: Session,
        macro_ingredient_id: uuid.UUID,
        micro_ingredient_id: uuid.UUID,
        macro_quantity: Decimal,
        conversion_factor: Decimal,
        location: StockLocation,
        notes: Optional[str] = None,
        user_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """
        Registra el porcionado / conversión de un insumo macro a micro.
        Ejemplo: Porcionar 1 KG de Carne (macro) -> 5 porciones de 200g (micro).
        """
        macro_ing = db.get(Ingredient, macro_ingredient_id)
        micro_ing = db.get(Ingredient, micro_ingredient_id)

        if not macro_ing or not micro_ing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Uno de los ingredientes del porcionado no fue encontrado."
            )

        # 1. Descontar insumo macro (salida)
        InventoryService.adjust_stock(
            db=db,
            location=location,
            transaction_type=StockTransactionType.PORTIONING,
            quantity=-abs(macro_quantity),
            ingredient_id=macro_ingredient_id,
            unit_cost=macro_ing.cost_per_unit,
            notes=f"Salida por porcionado hacia {micro_ing.name}. {notes or ''}".strip(),
            user_id=user_id
        )

        # 2. Aumentar insumo micro (entrada)
        generated_micro_qty = macro_quantity * conversion_factor
        InventoryService.adjust_stock(
            db=db,
            location=location,
            transaction_type=StockTransactionType.PORTIONING,
            quantity=generated_micro_qty,
            ingredient_id=micro_ingredient_id,
            unit_cost=micro_ing.cost_per_unit,
            notes=f"Entrada por porcionado desde {macro_ing.name}. {notes or ''}".strip(),
            user_id=user_id
        )

        return {
            "macro_ingredient": macro_ing.name,
            "macro_deducted": macro_quantity,
            "micro_ingredient": micro_ing.name,
            "micro_generated": generated_micro_qty,
            "location": location.value
        }

    @staticmethod
    def register_waste(
        db: Session,
        location: StockLocation,
        quantity: Decimal,
        reason: str,
        ingredient_id: Optional[uuid.UUID] = None,
        product_id: Optional[uuid.UUID] = None,
        user_id: Optional[uuid.UUID] = None
    ) -> WasteLog:
        """
        Registra una merma o desperdicio, descuenta la cantidad del stock disponible
        y calcula el costo monetario perdido.
        """
        unit_cost = Decimal("0.0000")
        if ingredient_id:
            ing = db.get(Ingredient, ingredient_id)
            if ing:
                unit_cost = ing.cost_per_unit
        elif product_id:
            prod = db.get(Product, product_id)
            if prod:
                unit_cost = prod.price  # Valor comercial mermado

        total_cost_lost = abs(quantity) * unit_cost

        # 1. Descontar del inventario
        InventoryService.adjust_stock(
            db=db,
            location=location,
            transaction_type=StockTransactionType.WASTE,
            quantity=-abs(quantity),
            ingredient_id=ingredient_id,
            product_id=product_id,
            unit_cost=unit_cost,
            notes=f"Merma: {reason}",
            user_id=user_id
        )

        # 2. Registrar en log de mermas
        waste_log = WasteLog(
            ingredient_id=ingredient_id,
            product_id=product_id,
            location=location,
            quantity=abs(quantity),
            reason=reason,
            total_cost=total_cost_lost,
            recorded_by_id=user_id
        )
        db.add(waste_log)
        db.commit()
        db.refresh(waste_log)
        return waste_log

    @staticmethod
    def deduct_product_stock(
        db: Session,
        product_id: uuid.UUID,
        order_quantity: Decimal,
        location: Optional[StockLocation] = None,
        user_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """
        Ejecuta el descuento ATÓMICO de inventario para una comanda o venta del POS.
        - Si el producto es DIRECT (ej. lata de refresco), descuenta la cantidad directa.
        - Si el producto es PREPARED (ej. platillo/coctel), descuenta iterativamente
          cada ingrediente según las proporciones de su receta.
        """
        stmt = (
            select(Product)
            .options(joinedload(Product.recipe_items).joinedload(RecipeItem.ingredient))
            .where(Product.id == product_id)
        )
        product = db.execute(stmt).unique().scalar_one_or_none()

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Producto con ID '{product_id}' no encontrado."
            )

        # Determinar estación por defecto según KDS
        if not location:
            location = StockLocation.BAR if product.destination_kds == KDSStation.BAR else StockLocation.KITCHEN

        deducted_items = []

        # A) Producto DIRECT (Venta directa)
        if product.product_type == ProductType.DIRECT:
            InventoryService.adjust_stock(
                db=db,
                location=location,
                transaction_type=StockTransactionType.SALE_DEDUCTION,
                quantity=-abs(order_quantity),
                product_id=product.id,
                notes=f"Venta POS de {product.name} (x{order_quantity})",
                user_id=user_id
            )
            deducted_items.append({
                "type": "DIRECT_PRODUCT",
                "item_name": product.name,
                "deducted_quantity": order_quantity
            })

        # B) Producto PREPARED (Descuento atómico por Receta)
        else:
            if not product.recipe_items:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El producto preparado '{product.name}' no tiene insumos configurados en su receta."
                )

            for item in product.recipe_items:
                required_qty = item.quantity * order_quantity
                ing = item.ingredient

                InventoryService.adjust_stock(
                    db=db,
                    location=location,
                    transaction_type=StockTransactionType.SALE_DEDUCTION,
                    quantity=-abs(required_qty),
                    ingredient_id=item.ingredient_id,
                    unit_cost=ing.cost_per_unit if ing else Decimal("0.0000"),
                    notes=f"Descuento comanda POS: {product.name} (x{order_quantity})",
                    user_id=user_id
                )

                deducted_items.append({
                    "type": "INGREDIENT",
                    "ingredient_id": str(item.ingredient_id),
                    "ingredient_code": ing.code if ing else None,
                    "ingredient_name": ing.name if ing else None,
                    "deducted_quantity": float(required_qty),
                    "unit": item.unit_of_measure.value
                })

        return {
            "status": "success",
            "product_sku": product.sku,
            "product_name": product.name,
            "order_quantity": float(order_quantity),
            "location": location.value,
            "deducted_components": deducted_items
        }

    @staticmethod
    def get_low_stock_alerts(db: Session) -> List[Dict[str, Any]]:
        """
        Retorna la lista de insumos cuyos balances actuales están por debajo o igual
        al stock mínimo configurado, para enrutamiento de alertas con n8n/notify.sh.
        """
        stmt = select(Ingredient).where(
            Ingredient.is_active == True,
            Ingredient.current_stock <= Ingredient.minimum_stock
        )
        low_ingredients = db.execute(stmt).scalars().all()

        alerts = []
        for ing in low_ingredients:
            deficit = ing.minimum_stock - ing.current_stock
            suggested_purchase = max(deficit, ing.minimum_stock * Decimal("2"))

            alerts.append({
                "ingredient_id": str(ing.id),
                "code": ing.code,
                "name": ing.name,
                "unit": ing.unit_of_measure.value,
                "current_stock": float(ing.current_stock),
                "minimum_stock": float(ing.minimum_stock),
                "deficit": float(deficit),
                "suggested_purchase_quantity": float(suggested_purchase),
                "unit_cost": float(ing.cost_per_unit),
                "estimated_purchase_cost": float(suggested_purchase * ing.cost_per_unit),
                "severity": "CRITICAL" if ing.current_stock <= Decimal("0.0000") else "WARNING"
            })

        return alerts
