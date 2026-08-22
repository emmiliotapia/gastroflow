"""
Script de Carga de Datos Iniciales (Seeding) - Fichas Técnicas Reales del Casino
==============================================================================
Este script automatiza la inicialización de la base de datos con los datos reales
de insumos, costos por unidad y recetas completas de Alimentos y Bebidas del Casino.
"""

import sys
from decimal import Decimal
from typing import Dict, Any
from sqlalchemy import select
from sqlalchemy.orm import Session

# Garantizar resolución de módulos
sys.path.insert(0, ".")

from backend.core.database import SessionLocal, engine
from backend.core.security import get_password_hash, get_pin_hash
from backend.models.enums import KDSStation, ProductType, UnitOfMeasure, UserRole, MachineStatus, StockLocation
from backend.models.ingredient import Ingredient
from backend.models.product import Product, RecipeItem
from backend.models.user import Role, User
from backend.models.pos import POSCategory, POSButton
from backend.models.machine import Machine
from backend.models.stock import StockLevel


# ==============================================================================
# DATOS REALES DE INSUMOS Y COSTOS UNITARIOS DEL CASINO
# ==============================================================================
INGREDIENTS_DATA = [
    {"code": "ING-PAN-BARR", "name": "PAN DE BARRA", "unit": UnitOfMeasure.PIECE, "cost": Decimal("6.40")},
    {"code": "ING-PAN-BRIO", "name": "PAN BRIOCHE", "unit": UnitOfMeasure.PIECE, "cost": Decimal("9.25")},
    {"code": "ING-MOL-RES", "name": "MOLIDA DE RES", "unit": UnitOfMeasure.GR, "cost": Decimal("114.20")},
    {"code": "ING-PECH-POL", "name": "PECHUGA DE POLLO", "unit": UnitOfMeasure.GR, "cost": Decimal("105.50")},
    {"code": "ING-PIÑA-AMI", "name": "PIÑA EN AMIBAS", "unit": UnitOfMeasure.GR, "cost": Decimal("49.50")},
    {"code": "ING-LECH-BOL", "name": "LECHUGA BOLA", "unit": UnitOfMeasure.GR, "cost": Decimal("19.80")},
    {"code": "ING-TOM-SAL", "name": "TOMATE SALADES", "unit": UnitOfMeasure.GR, "cost": Decimal("24.92")},
    {"code": "ING-QUES-AME", "name": "QUESO AMERICANO", "unit": UnitOfMeasure.PIECE, "cost": Decimal("110.00")},
    {"code": "ING-CEB-MOR", "name": "CEBOLLA MORADA", "unit": UnitOfMeasure.GR, "cost": Decimal("15.90")},
    {"code": "ING-JAM-PAV", "name": "JAMON DE PAVO", "unit": UnitOfMeasure.GR, "cost": Decimal("95.50")},
    {"code": "ING-BBQ-SAU", "name": "BBQ 4.5 ML", "unit": UnitOfMeasure.GR, "cost": Decimal("190.00")},
    {"code": "ING-PAP-GAJ", "name": "PAPAS GAJO", "unit": UnitOfMeasure.GR, "cost": Decimal("911.87")},
    {"code": "ING-TOCINO", "name": "TOCINO", "unit": UnitOfMeasure.GR, "cost": Decimal("225.00")},
    {"code": "ING-CHIL-VIN", "name": "CHILES EN VINAGRE", "unit": UnitOfMeasure.GR, "cost": Decimal("90.00")},
    {"code": "ING-MAYONESA", "name": "ADEREZO MAYONESA", "unit": UnitOfMeasure.GR, "cost": Decimal("138.90")},
    {"code": "ING-CATSUP", "name": "CAT SUP", "unit": UnitOfMeasure.GR, "cost": Decimal("106.90")},
    {"code": "ING-PAP-ENC", "name": "PAPEL ENCERADO", "unit": UnitOfMeasure.PIECE, "cost": Decimal("245.00")},
    {"code": "ING-SOUF-2OZ", "name": "SOUFLES 2 Oz", "unit": UnitOfMeasure.PIECE, "cost": Decimal("932.00")},
    {"code": "ING-TAP-2OZ", "name": "TAPADERA 2 Oz", "unit": UnitOfMeasure.PIECE, "cost": Decimal("950.20")},
    {"code": "ING-AC-VEG", "name": "ACEITE VEGETAL", "unit": UnitOfMeasure.ML, "cost": Decimal("800.00")},
    {"code": "ING-APIO", "name": "APIO", "unit": UnitOfMeasure.GR, "cost": Decimal("18.00")},
    {"code": "ING-ZANAH", "name": "ZANAHORIA", "unit": UnitOfMeasure.GR, "cost": Decimal("15.60")},
    {"code": "ING-RANCH", "name": "RANCH", "unit": UnitOfMeasure.GR, "cost": Decimal("305.00")},
    {"code": "ING-RED-HOT", "name": "SALSA RED HOT", "unit": UnitOfMeasure.PIECE, "cost": Decimal("219.50")},
    {"code": "ING-HARINA", "name": "HARINA", "unit": UnitOfMeasure.GR, "cost": Decimal("23.80")},
    {"code": "ING-PAPRIKA", "name": "PAPRIKA", "unit": UnitOfMeasure.GR, "cost": Decimal("160.00")},
    {"code": "ING-CONS-POL", "name": "CONOSME DE POLLO", "unit": UnitOfMeasure.GR, "cost": Decimal("1410.00")},
    {"code": "ING-PIM-NEG", "name": "PIMIENTA NEGRA", "unit": UnitOfMeasure.PIECE, "cost": Decimal("220.00")},
    {"code": "ING-TORT-AMA", "name": "TORTILLA AMARILLA", "unit": UnitOfMeasure.PIECE, "cost": Decimal("22.00")},
    {"code": "ING-CREM-ZUI", "name": "CREMA ZUISA", "unit": UnitOfMeasure.GR, "cost": Decimal("129.00")},
    {"code": "ING-CREM-AGR", "name": "CREMA AGRIA", "unit": UnitOfMeasure.GR, "cost": Decimal("260.00")},
    {"code": "ING-CILANTRO", "name": "CILANTRO", "unit": UnitOfMeasure.PIECE, "cost": Decimal("5.50")},
    {"code": "ING-MOZZ", "name": "QUESO MOZZARRELLA", "unit": UnitOfMeasure.GR, "cost": Decimal("344.00")},
    {"code": "ING-FRIJOLES", "name": "FRIJOLES", "unit": UnitOfMeasure.GR, "cost": Decimal("135.00")},
    {"code": "ING-COTIJA", "name": "QUESO COTIJA", "unit": UnitOfMeasure.GR, "cost": Decimal("200.00")},
    {"code": "ING-PICAD", "name": "PICADIENTES", "unit": UnitOfMeasure.PIECE, "cost": Decimal("0.00")},
]


# ==============================================================================
# FICHAS TÉCNICAS COMPLETAS DE PRODUCTOS DE ALIMENTOS Y BEBIDAS
# ==============================================================================
PRODUCTS_RECIPES_DATA = [
    {
        "sku": "AYB-HAM-BBQ",
        "name": "HAMBURGUESA BBQ",
        "category": "Especialidades",
        "price": Decimal("130.00"),
        "destination_kds": KDSStation.KITCHEN,
        "items": [
            ("ING-PAN-BRIO", Decimal("1"), UnitOfMeasure.PIECE),
            ("ING-MOL-RES", Decimal("0.15"), UnitOfMeasure.GR),
            ("ING-PIÑA-AMI", Decimal("0.045"), UnitOfMeasure.GR),
            ("ING-LECH-BOL", Decimal("0.07"), UnitOfMeasure.GR),
            ("ING-QUES-AME", Decimal("0.017"), UnitOfMeasure.PIECE),
            ("ING-CEB-MOR", Decimal("0.035"), UnitOfMeasure.GR),
            ("ING-BBQ-SAU", Decimal("0.05"), UnitOfMeasure.GR),
            ("ING-PAP-GAJ", Decimal("0.2"), UnitOfMeasure.GR),
            ("ING-TOCINO", Decimal("0.08"), UnitOfMeasure.GR),
            ("ING-CHIL-VIN", Decimal("0.055"), UnitOfMeasure.GR),
            ("ING-MAYONESA", Decimal("0.08"), UnitOfMeasure.GR),
            ("ING-CATSUP", Decimal("0.08"), UnitOfMeasure.GR),
            ("ING-PAP-ENC", Decimal("1"), UnitOfMeasure.PIECE),
            ("ING-SOUF-2OZ", Decimal("2"), UnitOfMeasure.PIECE),
            ("ING-TAP-2OZ", Decimal("2"), UnitOfMeasure.PIECE),
            ("ING-AC-VEG", Decimal("0.1"), UnitOfMeasure.ML),
        ]
    },
    {
        "sku": "AYB-HAM-PRES",
        "name": "HAMBURGUESA PRESTIGE",
        "category": "Especialidades",
        "price": Decimal("145.00"),
        "destination_kds": KDSStation.KITCHEN,
        "items": [
            ("ING-PAN-BRIO", Decimal("1"), UnitOfMeasure.PIECE),
            ("ING-MOL-RES", Decimal("0.2"), UnitOfMeasure.GR),
            ("ING-TOM-SAL", Decimal("0.05"), UnitOfMeasure.GR),
            ("ING-LECH-BOL", Decimal("0.07"), UnitOfMeasure.GR),
            ("ING-QUES-AME", Decimal("0.017"), UnitOfMeasure.PIECE),
            ("ING-CEB-MOR", Decimal("0.035"), UnitOfMeasure.GR),
            ("ING-JAM-PAV", Decimal("0.05"), UnitOfMeasure.GR),
            ("ING-PAP-GAJ", Decimal("0.2"), UnitOfMeasure.GR),
            ("ING-TOCINO", Decimal("0.08"), UnitOfMeasure.GR),
            ("ING-CHIL-VIN", Decimal("0.055"), UnitOfMeasure.GR),
            ("ING-MAYONESA", Decimal("0.08"), UnitOfMeasure.GR),
            ("ING-CATSUP", Decimal("0.08"), UnitOfMeasure.GR),
            ("ING-PAP-ENC", Decimal("1"), UnitOfMeasure.PIECE),
            ("ING-SOUF-2OZ", Decimal("2"), UnitOfMeasure.PIECE),
            ("ING-TAP-2OZ", Decimal("2"), UnitOfMeasure.PIECE),
            ("ING-AC-VEG", Decimal("0.1"), UnitOfMeasure.ML),
        ]
    },
    {
        "sku": "AYB-HAM-CLAS",
        "name": "HAMBURGUESA CLASICA",
        "category": "Clásicos",
        "price": Decimal("100.00"),
        "destination_kds": KDSStation.KITCHEN,
        "items": [
            ("ING-PAN-BRIO", Decimal("1"), UnitOfMeasure.PIECE),
            ("ING-MOL-RES", Decimal("0.1"), UnitOfMeasure.GR),
            ("ING-CEB-MOR", Decimal("0.035"), UnitOfMeasure.GR),
            ("ING-QUES-AME", Decimal("0.017"), UnitOfMeasure.PIECE),
            ("ING-LECH-BOL", Decimal("0.07"), UnitOfMeasure.GR),
            ("ING-TOM-SAL", Decimal("0.05"), UnitOfMeasure.GR),
            ("ING-PAP-GAJ", Decimal("0.2"), UnitOfMeasure.GR),
            ("ING-CHIL-VIN", Decimal("0.055"), UnitOfMeasure.GR),
            ("ING-MAYONESA", Decimal("0.08"), UnitOfMeasure.GR),
            ("ING-CATSUP", Decimal("0.08"), UnitOfMeasure.GR),
            ("ING-PAP-ENC", Decimal("1"), UnitOfMeasure.PIECE),
            ("ING-SOUF-2OZ", Decimal("2"), UnitOfMeasure.PIECE),
            ("ING-TAP-2OZ", Decimal("2"), UnitOfMeasure.PIECE),
            ("ING-AC-VEG", Decimal("0.1"), UnitOfMeasure.ML),
        ]
    },
    {
        "sku": "AYB-HAM-POL",
        "name": "HAMBURGUESA DE POLLO",
        "category": "Especialidades",
        "price": Decimal("145.00"),
        "destination_kds": KDSStation.KITCHEN,
        "items": [
            ("ING-PAN-BRIO", Decimal("1"), UnitOfMeasure.PIECE),
            ("ING-PECH-POL", Decimal("0.15"), UnitOfMeasure.GR),
            ("ING-TOM-SAL", Decimal("0.05"), UnitOfMeasure.GR),
            ("ING-LECH-BOL", Decimal("0.07"), UnitOfMeasure.GR),
            ("ING-QUES-AME", Decimal("0.017"), UnitOfMeasure.PIECE),
            ("ING-CEB-MOR", Decimal("0.035"), UnitOfMeasure.GR),
            ("ING-JAM-PAV", Decimal("0.05"), UnitOfMeasure.GR),
            ("ING-PAP-GAJ", Decimal("0.2"), UnitOfMeasure.GR),
            ("ING-TOCINO", Decimal("0.08"), UnitOfMeasure.GR),
            ("ING-CHIL-VIN", Decimal("0.055"), UnitOfMeasure.GR),
            ("ING-MAYONESA", Decimal("0.08"), UnitOfMeasure.GR),
            ("ING-CATSUP", Decimal("0.08"), UnitOfMeasure.GR),
            ("ING-PAP-ENC", Decimal("1"), UnitOfMeasure.PIECE),
            ("ING-SOUF-2OZ", Decimal("2"), UnitOfMeasure.PIECE),
            ("ING-TAP-2OZ", Decimal("2"), UnitOfMeasure.PIECE),
            ("ING-AC-VEG", Decimal("0.1"), UnitOfMeasure.ML),
        ]
    },
    {
        "sku": "AYB-BON-BUF",
        "name": "BONELESS BUFALO",
        "category": "Botanas",
        "price": Decimal("140.00"),
        "destination_kds": KDSStation.KITCHEN,
        "items": [
            ("ING-PECH-POL", Decimal("0.3"), UnitOfMeasure.GR),
            ("ING-APIO", Decimal("0.08"), UnitOfMeasure.GR),
            ("ING-ZANAH", Decimal("0.08"), UnitOfMeasure.GR),
            ("ING-RANCH", Decimal("0.08"), UnitOfMeasure.GR),
            ("ING-RED-HOT", Decimal("0.22"), UnitOfMeasure.PIECE),
            ("ING-PAP-ENC", Decimal("1"), UnitOfMeasure.PIECE),
            ("ING-SOUF-2OZ", Decimal("2"), UnitOfMeasure.PIECE),
            ("ING-TAP-2OZ", Decimal("2"), UnitOfMeasure.PIECE),
            ("ING-AC-VEG", Decimal("0.1"), UnitOfMeasure.ML),
            ("ING-HARINA", Decimal("0.22"), UnitOfMeasure.GR),
            ("ING-PAPRIKA", Decimal("0.005"), UnitOfMeasure.GR),
            ("ING-CONS-POL", Decimal("0.01"), UnitOfMeasure.GR),
            ("ING-PIM-NEG", Decimal("0.002"), UnitOfMeasure.PIECE),
        ]
    },
    {
        "sku": "AYB-ENC-SUI",
        "name": "ENCHILADAS SUIZAS",
        "category": "Platillos",
        "price": Decimal("130.00"),
        "destination_kds": KDSStation.KITCHEN,
        "items": [
            ("ING-TORT-AMA", Decimal("4"), UnitOfMeasure.PIECE),
            ("ING-PECH-POL", Decimal("0.1"), UnitOfMeasure.GR),
            ("ING-CREM-ZUI", Decimal("0.14"), UnitOfMeasure.GR),
            ("ING-CREM-AGR", Decimal("0.08"), UnitOfMeasure.GR),
            ("ING-CILANTRO", Decimal("0.003"), UnitOfMeasure.PIECE),
            ("ING-CEB-MOR", Decimal("0.05"), UnitOfMeasure.GR),
            ("ING-MOZZ", Decimal("0.05"), UnitOfMeasure.GR),
            ("ING-FRIJOLES", Decimal("0.12"), UnitOfMeasure.GR),
            ("ING-COTIJA", Decimal("0.01"), UnitOfMeasure.GR),
        ]
    },
    {
        "sku": "AYB-BON-BBQ",
        "name": "BONELESS BBQ",
        "category": "Botanas",
        "price": Decimal("140.00"),
        "destination_kds": KDSStation.KITCHEN,
        "items": [
            ("ING-PECH-POL", Decimal("0.3"), UnitOfMeasure.GR),
            ("ING-APIO", Decimal("0.1"), UnitOfMeasure.GR),
            ("ING-ZANAH", Decimal("0.1"), UnitOfMeasure.GR),
            ("ING-RANCH", Decimal("0.08"), UnitOfMeasure.GR),
            ("ING-BBQ-SAU", Decimal("0.22"), UnitOfMeasure.GR),
            ("ING-PAP-ENC", Decimal("1"), UnitOfMeasure.PIECE),
            ("ING-SOUF-2OZ", Decimal("2"), UnitOfMeasure.PIECE),
            ("ING-TAP-2OZ", Decimal("2"), UnitOfMeasure.PIECE),
            ("ING-AC-VEG", Decimal("0.1"), UnitOfMeasure.ML),
            ("ING-HARINA", Decimal("0.22"), UnitOfMeasure.GR),
            ("ING-PAPRIKA", Decimal("0.005"), UnitOfMeasure.GR),
            ("ING-CONS-POL", Decimal("0.01"), UnitOfMeasure.GR),
            ("ING-PIM-NEG", Decimal("0.002"), UnitOfMeasure.PIECE),
        ]
    },
    {
        "sku": "AYB-CLU-SAN",
        "name": "CLUB SANDWICH",
        "category": "Sandwiches",
        "price": Decimal("135.00"),
        "destination_kds": KDSStation.KITCHEN,
        "items": [
            ("ING-PAN-BARR", Decimal("3"), UnitOfMeasure.PIECE),
            ("ING-PECH-POL", Decimal("0.1"), UnitOfMeasure.GR),
            ("ING-CEB-MOR", Decimal("0.035"), UnitOfMeasure.GR),
            ("ING-QUES-AME", Decimal("0.017"), UnitOfMeasure.GR),
            ("ING-LECH-BOL", Decimal("0.1"), UnitOfMeasure.GR),
            ("ING-JAM-PAV", Decimal("0.05"), UnitOfMeasure.GR),
            ("ING-PAP-GAJ", Decimal("0.2"), UnitOfMeasure.GR),
            ("ING-CHIL-VIN", Decimal("0.055"), UnitOfMeasure.GR),
            ("ING-MAYONESA", Decimal("0.1"), UnitOfMeasure.GR),
            ("ING-CATSUP", Decimal("0.1"), UnitOfMeasure.GR),
            ("ING-PAP-ENC", Decimal("1"), UnitOfMeasure.PIECE),
            ("ING-SOUF-2OZ", Decimal("2"), UnitOfMeasure.PIECE),
            ("ING-TAP-2OZ", Decimal("2"), UnitOfMeasure.PIECE),
            ("ING-AC-VEG", Decimal("0.1"), UnitOfMeasure.ML),
            ("ING-TOCINO", Decimal("0.08"), UnitOfMeasure.GR),
            ("ING-PICAD", Decimal("0"), UnitOfMeasure.PIECE),
            ("ING-TOM-SAL", Decimal("0.045"), UnitOfMeasure.GR),
        ]
    },
    {
        "sku": "AYB-DRK-CERV",
        "name": "CERVEZA CLASICA",
        "category": "Bebidas",
        "price": Decimal("45.00"),
        "destination_kds": KDSStation.BAR,
        "product_type": ProductType.DIRECT,
        "items": []
    },
    {
        "sku": "AYB-DRK-LIMO",
        "name": "LIMONADA MINERAL",
        "category": "Bebidas",
        "price": Decimal("35.00"),
        "destination_kds": KDSStation.BAR,
        "product_type": ProductType.DIRECT,
        "items": []
    }
]


def seed_database():
    """
    Carga e inicializa todos los roles, usuarios por defecto, insumos reales
    y fichas técnicas de producción de Alimentos y Bebidas en la base de datos.
    """
    print("[INFO] Iniciando proceso de seeding con fichas técnicas reales del Casino...")

    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    try:
        # 1. Creación de Roles
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

        # 2. Usuarios Iniciales
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

        # Usuarios Clientes de Prueba
        from backend.models.enums import MembershipTier

        classic_client = db.execute(select(User).where(User.username == "classic_client")).scalar_one_or_none()
        if not classic_client:
            classic_client = User(
                username="classic_client",
                email="classic@client.com",
                full_name="Juan Pérez (Classic Client)",
                hashed_password=get_password_hash("ClassicPass2026!"),
                role_id=roles_map[UserRole.CUSTOMER].id,
                membership_tier=MembershipTier.CLASSIC,
                is_active=True
            )
            db.add(classic_client)
            print("  + Cliente creado: classic_client (Membresía: CLASSIC)")

        gold_client = db.execute(select(User).where(User.username == "gold_client")).scalar_one_or_none()
        if not gold_client:
            gold_client = User(
                username="gold_client",
                email="gold@client.com",
                full_name="María López (Gold Client)",
                hashed_password=get_password_hash("GoldPass2026!"),
                role_id=roles_map[UserRole.CUSTOMER].id,
                membership_tier=MembershipTier.GOLD,
                is_active=True
            )
            db.add(gold_client)
            print("  + Cliente creado: gold_client (Membresía: GOLD)")

        vip_client = db.execute(select(User).where(User.username == "vip_client")).scalar_one_or_none()
        if not vip_client:
            vip_client = User(
                username="vip_client",
                email="vip@client.com",
                full_name="Sofía Castro (VIP Client)",
                hashed_password=get_password_hash("VipPass2026!"),
                role_id=roles_map[UserRole.CUSTOMER].id,
                membership_tier=MembershipTier.VIP,
                is_active=True
            )
            db.add(vip_client)
            print("  + Cliente creado: vip_client (Membresía: VIP)")

        # 3. Carga de Insumos Base Reales
        ingredients_dict: Dict[str, Ingredient] = {}
        for ing_item in INGREDIENTS_DATA:
            stmt = select(Ingredient).where(Ingredient.code == ing_item["code"])
            ing_obj = db.execute(stmt).scalar_one_or_none()
            if not ing_obj:
                ing_obj = Ingredient(
                    code=ing_item["code"],
                    name=ing_item["name"],
                    unit_of_measure=ing_item["unit"],
                    cost_per_unit=ing_item["cost"],
                    current_stock=Decimal("1000.0000"),
                    minimum_stock=Decimal("100.0000"),
                    is_active=True
                )
                db.add(ing_obj)
                db.flush()
                print(f"  + Insumo insertado: {ing_item['name']} ({ing_item['code']}) - Costo: ${ing_item['cost']}")
            else:
                ing_obj.cost_per_unit = ing_item["cost"]
                ing_obj.unit_of_measure = ing_item["unit"]
                db.flush()

            # Asegurar niveles de stock por bodega (KITCHEN y WAREHOUSE)
            for loc in [StockLocation.KITCHEN, StockLocation.WAREHOUSE]:
                stk_stmt = select(StockLevel).where(
                    StockLevel.ingredient_id == ing_obj.id,
                    StockLevel.location == loc
                )
                stk = db.execute(stk_stmt).scalar_one_or_none()
                if not stk:
                    stk = StockLevel(
                        ingredient_id=ing_obj.id,
                        location=loc,
                        current_stock=Decimal("500.0000"),
                        minimum_stock=Decimal("50.0000")
                    )
                    db.add(stk)

            ingredients_dict[ing_item["code"]] = ing_obj


        # 4. Carga de Productos y Recetas Reales
        for prod_data in PRODUCTS_RECIPES_DATA:
            stmt = select(Product).where(Product.sku == prod_data["sku"])
            product = db.execute(stmt).scalar_one_or_none()

            if not product:
                product = Product(
                    sku=prod_data["sku"],
                    name=prod_data["name"],
                    description=f"Ficha técnica oficial de {prod_data['name']}",
                    category=prod_data["category"],
                    product_type=prod_data.get("product_type", ProductType.PREPARED),
                    destination_kds=prod_data["destination_kds"],
                    price=prod_data["price"],
                    courtesy_tier_min="GOLD",
                    is_active=True
                )
                db.add(product)
                db.flush()
                print(f"\n  [PRODUCTO] {prod_data['name']} (SKU: {prod_data['sku']}) - Precio Venta: ${prod_data['price']}")

            # Reemplazar / insertar ítems de la receta
            db.execute(
                RecipeItem.__table__.delete().where(RecipeItem.product_id == product.id)
            )

            total_recipe_cost = Decimal("0.0000")

            for ing_code, qty, unit in prod_data["items"]:
                if ing_code not in ingredients_dict:
                    print(f"  ! Advertencia: Insumo '{ing_code}' no encontrado.")
                    continue

                ing_entity = ingredients_dict[ing_code]
                item_cost = qty * ing_entity.cost_per_unit
                total_recipe_cost += item_cost

                recipe_item = RecipeItem(
                    product_id=product.id,
                    ingredient_id=ing_entity.id,
                    quantity=qty,
                    unit_of_measure=unit
                )
                db.add(recipe_item)

            margin_amount = prod_data["price"] - total_recipe_cost
            margin_percent = ((margin_amount / prod_data["price"]) * Decimal("100")) if prod_data["price"] > 0 else Decimal("0.00")

            print(f"    -> Insumos vinculados: {len(prod_data['items'])} ítems.")
            print(f"    -> Costo Total Producción: ${round(total_recipe_cost, 2)} | Margen: ${round(margin_amount, 2)} ({round(margin_percent, 1)}%)")

        # 5. Cargar Botonera POS (Categorías y Botones)
        print("\n--- CARGANDO CONFIGURACIÓN DE BOTONERA POS ---")
        
        # Categoría Alimentos
        cat_alimentos = db.execute(select(POSCategory).where(POSCategory.name == "Alimentos")).scalar_one_or_none()
        if not cat_alimentos:
            cat_alimentos = POSCategory(name="Alimentos", display_order=1, is_active=True)
            db.add(cat_alimentos)
            db.flush()
            print("  + Categoría POS creada: Alimentos")

        # Categoría Bebidas
        cat_bebidas = db.execute(select(POSCategory).where(POSCategory.name == "Bebidas")).scalar_one_or_none()
        if not cat_bebidas:
            cat_bebidas = POSCategory(name="Bebidas", display_order=2, is_active=True)
            db.add(cat_bebidas)
            db.flush()
            print("  + Categoría POS creada: Bebidas")

        # Vincular todos los productos activos a botones en Alimentos
        all_products = db.execute(select(Product).where(Product.is_active == True)).scalars().all()
        for idx, prod in enumerate(all_products):
            # Verificar si ya tiene botón
            btn = db.execute(select(POSButton).where(POSButton.product_id == prod.id)).scalar_one_or_none()
            if not btn:
                target_cat = cat_bebidas if prod.category.lower() == "bebidas" else cat_alimentos
                btn = POSButton(
                    category_id=target_cat.id,
                    product_id=prod.id,
                    display_order=idx + 1,
                    label=prod.name,
                    color_class="gold",
                    is_active=True
                )
                db.add(btn)
                print(f"    -> Botón creado para: {prod.name} en categoría {target_cat.name}")

        # 6. Cargar Máquinas de Casino (Slots) de prueba
        print("\n--- CARGANDO MÁQUINAS (SLOTS) DE PRUEBA ---")
        machines_data = [
            {"serial": "SN-SLOT-101", "asset": "SLOT-101", "model": "IGT PeakSlant", "zone": "Piso Principal", "token": "tok_slot_101"},
            {"serial": "SN-SLOT-102", "asset": "SLOT-102", "model": "Bally Alpha II", "zone": "Piso Principal", "token": "tok_slot_102"},
            {"serial": "SN-SLOT-VIP", "asset": "SLOT-VIP", "model": "Aria Premium", "zone": "Zona VIP", "token": "tok_slot_vip"}
        ]
        for m_data in machines_data:
            m = db.execute(select(Machine).where(Machine.asset_code == m_data["asset"])).scalar_one_or_none()
            if not m:
                m = Machine(
                    serial_number=m_data["serial"],
                    asset_code=m_data["asset"],
                    model=m_data["model"],
                    zone=m_data["zone"],
                    qr_code_token=m_data["token"],
                    status=MachineStatus.OPERATIONAL,
                    is_active=True
                )
                db.add(m)
                print(f"  + Máquina creada: {m_data['asset']} (Token: {m_data['token']})")

        db.commit()
        print("\n[SUCCESS] Seeding de fichas técnicas, configuración de botonera POS y máquinas completado exitosamente.")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Error durante el seeding: {e}")
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
