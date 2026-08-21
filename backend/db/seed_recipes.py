"""
Script de Carga de Datos Iniciales (Seeding) - Catálogos de Insumos y Recetas Realistas
======================================================================================
Este script automatiza la inicialización de:
1. Roles del sistema (`ADMIN`, `JEFE_DE_SALA`, `WAITER`, `BARMAN`, `KITCHEN_STAFF`, `TECHNICIAN`, `CUSTOMER`).
2. Usuario Administrador (`admin` / `AdminPass2026!`) y Supervisor de Sala (`jefe_sala` / `PIN: 1234`).
3. Catálogo de Insumos / Ingredientes reales con costos por unidad.
4. Fichas técnicas de Recetas Clave:
   - Hamburguesa BBQ (SKU: AYB-BBQ-01 | Costo total: ~$83.59 | Precio Venta: $240.00)
   - Hamburguesa Prestige (SKU: AYB-PRES-01 | Costo total: ~$90.43 | Precio Venta: $290.00)
"""

import sys
import uuid
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import Session

# Garantizar resolución de módulos
sys.path.insert(0, ".")

from backend.core.database import SessionLocal, engine
from backend.core.security import get_password_hash, get_pin_hash
from backend.models.base import Base
from backend.models.enums import KDSStation, ProductType, UnitOfMeasure, UserRole
from backend.models.ingredient import Ingredient
from backend.models.product import Product, RecipeItem
from backend.models.user import Role, User


def seed_database():
    """
    Puebla la base de datos con roles, usuarios por defecto, insumos y recetas de prueba.
    """
    print("[INFO] Iniciando proceso de seeding en la base de datos...")

    # Crear tablas si no existen en entorno local
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()

    try:
        # ----------------------------------------------------------------------
        # 1. Crear Roles del Sistema
        # ----------------------------------------------------------------------
        roles_map = {}
        for role_enum in UserRole:
            stmt = select(Role).where(Role.name == role_enum)
            role_obj = db.execute(stmt).scalar_one_or_none()
            if not role_obj:
                role_obj = Role(
                    name=role_enum,
                    description=f"Rol de sistema para {role_enum.value}",
                    permissions={"all": True} if role_enum == UserRole.ADMIN else {"read": True}
                )
                db.add(role_obj)
                db.flush()
                print(f"  + Rol creado: {role_enum.value}")
            roles_map[role_enum] = role_obj

        # ----------------------------------------------------------------------
        # 2. Crear Usuarios por Defecto
        # ----------------------------------------------------------------------
        # Usuario Admin
        admin_user = db.execute(select(User).where(User.username == "admin")).scalar_one_or_none()
        if not admin_user:
            admin_user = User(
                username="admin",
                email="admin@casino.com",
                full_name="Administrador General",
                hashed_password=get_password_hash("AdminPass2026!"),
                role_id=roles_map[UserRole.ADMIN].id,
                is_active=True
            )
            db.add(admin_user)
            print("  + Usuario creado: admin")

        # Usuario Jefe de Sala (con PIN 1234 Poka-Yoke)
        jefe_user = db.execute(select(User).where(User.username == "jefe_sala")).scalar_one_or_none()
        if not jefe_user:
            jefe_user = User(
                username="jefe_sala",
                email="supervisor@casino.com",
                full_name="Carlos Mendoza (Jefe de Sala)",
                hashed_password=get_password_hash("JefePass2026!"),
                hashed_pin=get_pin_hash("1234"),
                role_id=roles_map[UserRole.JEFE_DE_SALA].id,
                is_active=True
            )
            db.add(jefe_user)
            print("  + Usuario creado: jefe_sala (PIN NIP: 1234)")

        # ----------------------------------------------------------------------
        # 3. Crear Catálogo de Ingredientes / Insumos Base
        # ----------------------------------------------------------------------
        ingredients_data = [
            {
                "code": "ING-PAN-01",
                "name": "Pan Brioche para Hamburguesa",
                "unit_of_measure": UnitOfMeasure.PIECE,
                "cost_per_unit": Decimal("8.5000"),
                "current_stock": Decimal("200.0000"),
                "minimum_stock": Decimal("50.0000")
            },
            {
                "code": "ING-CAR-01",
                "name": "Carne Molida de Res Sirloin",
                "unit_of_measure": UnitOfMeasure.G,
                "cost_per_unit": Decimal("0.2200"),  # $220/kg
                "current_stock": Decimal("50000.0000"), # 50kg
                "minimum_stock": Decimal("10000.0000")
            },
            {
                "code": "ING-QUE-01",
                "name": "Queso Cheddar rebanado",
                "unit_of_measure": UnitOfMeasure.PIECE,
                "cost_per_unit": Decimal("4.5000"),
                "current_stock": Decimal("300.0000"),
                "minimum_stock": Decimal("60.0000")
            },
            {
                "code": "ING-TOC-01",
                "name": "Tocino Ahumado de Cerdo",
                "unit_of_measure": UnitOfMeasure.G,
                "cost_per_unit": Decimal("0.3500"),  # $350/kg
                "current_stock": Decimal("10000.0000"),
                "minimum_stock": Decimal("2000.0000")
            },
            {
                "code": "ING-SAL-BBQ",
                "name": "Salsa BBQ Artesanal Especial",
                "unit_of_measure": UnitOfMeasure.ML,
                "cost_per_unit": Decimal("0.0800"),  # $80/L
                "current_stock": Decimal("15000.0000"),
                "minimum_stock": Decimal("3000.0000")
            },
            {
                "code": "ING-CEB-CAR",
                "name": "Cebolla Caramelizada",
                "unit_of_measure": UnitOfMeasure.G,
                "cost_per_unit": Decimal("0.0500"),
                "current_stock": Decimal("5000.0000"),
                "minimum_stock": Decimal("1000.0000")
            },
            {
                "code": "ING-AGU-01",
                "name": "Aguacate Hass Fresco",
                "unit_of_measure": UnitOfMeasure.G,
                "cost_per_unit": Decimal("0.1210"),  # $121/kg
                "current_stock": Decimal("8000.0000"),
                "minimum_stock": Decimal("1500.0000")
            },
            {
                "code": "ING-MAN-01",
                "name": "Mantequilla con Sal",
                "unit_of_measure": UnitOfMeasure.G,
                "cost_per_unit": Decimal("0.1500"),
                "current_stock": Decimal("4000.0000"),
                "minimum_stock": Decimal("1000.0000")
            },
            {
                "code": "ING-PAP-01",
                "name": "Papas a la Francesa Corte Delgado",
                "unit_of_measure": UnitOfMeasure.G,
                "cost_per_unit": Decimal("0.059857"),  # ~$60/kg
                "current_stock": Decimal("40000.0000"),
                "minimum_stock": Decimal("10000.0000")
            }
        ]

        ingredients_dict = {}
        for ing_item in ingredients_data:
            stmt = select(Ingredient).where(Ingredient.code == ing_item["code"])
            ing_obj = db.execute(stmt).scalar_one_or_none()
            if not ing_obj:
                ing_obj = Ingredient(**ing_item, is_active=True)
                db.add(ing_obj)
                db.flush()
                print(f"  + Ingrediente creado: {ing_item['name']} ({ing_item['code']})")
            ingredients_dict[ing_item["code"]] = ing_obj

        # ----------------------------------------------------------------------
        # 4. Crear Productos y Fichas Técnicas de Recetas
        # ----------------------------------------------------------------------

        # RECETA 1: Hamburguesa BBQ (AYB-BBQ-01)
        prod_bbq = db.execute(select(Product).where(Product.sku == "AYB-BBQ-01")).scalar_one_or_none()
        if not prod_bbq:
            prod_bbq = Product(
                sku="AYB-BBQ-01",
                name="Hamburguesa BBQ Especial",
                description="200g Sirloin, queso cheddar fundido, tocino crujiente, salsa BBQ especial y papas a la francesa.",
                category="Hamburguesas Gourmet",
                product_type=ProductType.PREPARED,
                destination_kds=KDSStation.KITCHEN,
                price=Decimal("240.00"),
                courtesy_tier_min="GOLD",
                is_active=True
            )
            db.add(prod_bbq)
            db.flush()

            # Insumos de la Receta BBQ:
            # 1. Pan Brioche: 1 pza ($8.50)
            # 2. Carne Sirloin: 200g ($44.00)
            # 3. Queso Cheddar: 2 pzas ($9.00)
            # 4. Tocino: 40g ($14.00)
            # 5. Salsa BBQ: 30ml ($2.40)
            # 6. Mantequilla: 10g ($1.50)
            # 7. Papas: 70g ($4.19)
            # COSTO TOTAL ESTIMADO: $83.59
            recipe_bbq = [
                RecipeItem(product_id=prod_bbq.id, ingredient_id=ingredients_dict["ING-PAN-01"].id, quantity=Decimal("1.0000"), unit_of_measure=UnitOfMeasure.PIECE),
                RecipeItem(product_id=prod_bbq.id, ingredient_id=ingredients_dict["ING-CAR-01"].id, quantity=Decimal("200.0000"), unit_of_measure=UnitOfMeasure.G),
                RecipeItem(product_id=prod_bbq.id, ingredient_id=ingredients_dict["ING-QUE-01"].id, quantity=Decimal("2.0000"), unit_of_measure=UnitOfMeasure.PIECE),
                RecipeItem(product_id=prod_bbq.id, ingredient_id=ingredients_dict["ING-TOC-01"].id, quantity=Decimal("40.0000"), unit_of_measure=UnitOfMeasure.G),
                RecipeItem(product_id=prod_bbq.id, ingredient_id=ingredients_dict["ING-SAL-BBQ"].id, quantity=Decimal("30.0000"), unit_of_measure=UnitOfMeasure.ML),
                RecipeItem(product_id=prod_bbq.id, ingredient_id=ingredients_dict["ING-MAN-01"].id, quantity=Decimal("10.0000"), unit_of_measure=UnitOfMeasure.G),
                RecipeItem(product_id=prod_bbq.id, ingredient_id=ingredients_dict["ING-PAP-01"].id, quantity=Decimal("70.0000"), unit_of_measure=UnitOfMeasure.G),
            ]
            db.add_all(recipe_bbq)
            print("  + Producto y Receta creada: Hamburguesa BBQ Especial (AYB-BBQ-01) - Costo: ~$83.59")

        # RECETA 2: Hamburguesa Prestige (AYB-PRES-01)
        prod_pres = db.execute(select(Product).where(Product.sku == "AYB-PRES-01")).scalar_one_or_none()
        if not prod_pres:
            prod_pres = Product(
                sku="AYB-PRES-01",
                name="Hamburguesa Prestige Signature",
                description="220g Sirloin, queso cheddar doble, tocino, cebolla caramelizada, abanico de aguacate y papas.",
                category="Hamburguesas Gourmet",
                product_type=ProductType.PREPARED,
                destination_kds=KDSStation.KITCHEN,
                price=Decimal("290.00"),
                courtesy_tier_min="PLATINUM",
                is_active=True
            )
            db.add(prod_pres)
            db.flush()

            # Insumos de la Receta Prestige:
            # 1. Pan Brioche: 1 pza ($8.50)
            # 2. Carne Sirloin: 220g ($48.40)
            # 3. Queso Cheddar: 2 pzas ($9.00)
            # 4. Tocino: 40g ($14.00)
            # 5. Cebolla Caramelizada: 30g ($1.50)
            # 6. Aguacate: 40g ($4.84)
            # 7. Mantequilla: 10g ($1.50)
            # 8. Papas: 45g ($2.69)
            # COSTO TOTAL ESTIMADO: $90.43
            recipe_pres = [
                RecipeItem(product_id=prod_pres.id, ingredient_id=ingredients_dict["ING-PAN-01"].id, quantity=Decimal("1.0000"), unit_of_measure=UnitOfMeasure.PIECE),
                RecipeItem(product_id=prod_pres.id, ingredient_id=ingredients_dict["ING-CAR-01"].id, quantity=Decimal("220.0000"), unit_of_measure=UnitOfMeasure.G),
                RecipeItem(product_id=prod_pres.id, ingredient_id=ingredients_dict["ING-QUE-01"].id, quantity=Decimal("2.0000"), unit_of_measure=UnitOfMeasure.PIECE),
                RecipeItem(product_id=prod_pres.id, ingredient_id=ingredients_dict["ING-TOC-01"].id, quantity=Decimal("40.0000"), unit_of_measure=UnitOfMeasure.G),
                RecipeItem(product_id=prod_pres.id, ingredient_id=ingredients_dict["ING-CEB-CAR"].id, quantity=Decimal("30.0000"), unit_of_measure=UnitOfMeasure.G),
                RecipeItem(product_id=prod_pres.id, ingredient_id=ingredients_dict["ING-AGU-01"].id, quantity=Decimal("40.0000"), unit_of_measure=UnitOfMeasure.G),
                RecipeItem(product_id=prod_pres.id, ingredient_id=ingredients_dict["ING-MAN-01"].id, quantity=Decimal("10.0000"), unit_of_measure=UnitOfMeasure.G),
                RecipeItem(product_id=prod_pres.id, ingredient_id=ingredients_dict["ING-PAP-01"].id, quantity=Decimal("45.0000"), unit_of_measure=UnitOfMeasure.G),
            ]
            db.add_all(recipe_pres)
            print("  + Producto y Receta creada: Hamburguesa Prestige Signature (AYB-PRES-01) - Costo: ~$90.43")

        db.commit()
        print("[SUCCESS] Seeding completado exitosamente con insumos y recetas de prueba.")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Error durante el seeding: {e}")
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
