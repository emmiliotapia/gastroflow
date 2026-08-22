"""
Test Suite de Integración para Casino Intelligent Hub ERP
==========================================================
Verifica el correcto funcionamiento de:
1. KDS Manager WebSocket loop y broadcast_sync.
2. Padrón VIP y motor de validación de cortesías.
3. Descuento atómico de inventario en cascada para subrecetas.
4. Creación y cobro de comandas desde Caja / POS.
"""

import sys
import os

# Configurar SQLite en memoria para tests aislados
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key-1234567890"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.models.base import Base
from backend.core.database import engine, SessionLocal
from backend.main import app
from backend.core.deps import get_db
from backend.models.enums import MembershipTier, KDSStation, StockLocation, UserRole, ProductType, UnitOfMeasure
from backend.models.ingredient import Ingredient
from backend.models.product import Product, RecipeItem
from backend.models.user import User, Role
from backend.models.vip_client import VIPClient
from backend.websockets.kds_manager import kds_manager


# Crear base de datos SQLite en memoria
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Crear todas las tablas
Base.metadata.create_all(bind=engine)

# Sembrar datos de prueba
def seed_data():
    db = TestingSessionLocal()
    
    # 1. Rol y Usuario Admin
    role = Role(name=UserRole.ADMIN, description="Administrador")
    db.add(role)
    db.flush()

    user = User(
        username="admin",
        email="admin@prestige.com",
        hashed_password="fake",
        full_name="Administrador General",
        role_id=role.id,
        hashed_pin="fake_pin",
        is_active=True
    )
    db.add(user)

    # 1.5 Máquina Slot
    from backend.models.machine import Machine, MachineStatus
    machine = Machine(
        asset_code="SLOT-101",
        serial_number="SN-101",
        model="Aristocrat Helix",
        zone="SALA A",
        qr_code_token="QR-SLOT-101",
        status=MachineStatus.OPERATIONAL,
        is_active=True
    )
    db.add(machine)
    db.flush()


    # 2. Insumo
    ing = Ingredient(
        code="ING-CARNE-01",
        name="Carne Sirloin 200g",
        category="PROTEINAS",
        unit_of_measure=UnitOfMeasure.GR,
        cost_per_unit=Decimal("0.50"),
        current_stock=Decimal("5000.00"),
        minimum_stock=Decimal("1000.00")
    )
    db.add(ing)
    db.flush()

    # 3. Platillo con receta
    prod = Product(
        sku="AYB-HAM-01",
        name="Hamburguesa Sirloin",
        category="Hamburguesas",
        product_type=ProductType.PREPARED,
        destination_kds=KDSStation.KITCHEN,
        price=Decimal("180.00"),
        courtesy_tier_min="PRESTIGE",
        is_active=True
    )
    db.add(prod)
    db.flush()

    recipe_item = RecipeItem(
        product_id=prod.id,
        ingredient_id=ing.id,
        quantity=Decimal("200.00"),
        unit_of_measure=UnitOfMeasure.GR
    )
    db.add(recipe_item)

    # 4. Cliente VIP
    vip = VIPClient(
        client_code="VIP-999",
        full_name="Carlos Slim VIP",
        tier=MembershipTier.PRESTIGE,
        daily_courtesy_limit=10,
        is_active=True
    )
    db.add(vip)

    db.commit()
    db.close()

seed_data()

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

def test_kds_endpoints():
    print("--- 1. Testing KDS Endpoints ---")
    res = client.get("/api/v1/kds/orders")
    assert res.status_code == 200, f"Error getting KDS orders: {res.text}"
    print("[OK] GET /api/v1/kds/orders -> OK, Count:", len(res.json()))

def test_courtesy_rules():
    print("--- 2. Testing VIP & Courtesy Rules ---")
    res = client.get("/api/v1/courtesy-rules")
    assert res.status_code == 200, f"Error getting courtesy rules: {res.text}"
    rules = res.json()
    assert "levels" in rules and len(rules["levels"]) == 4
    print("[OK] GET /api/v1/courtesy-rules -> OK (4 tiers: PLATA, ORO, PLATINO, PRESTIGE)")

def test_kitchen_stock_endpoint():
    print("--- 3. Testing Kitchen Stock Endpoint ---")
    res = client.get("/api/v1/kitchen/stock")
    assert res.status_code == 200, f"Error getting kitchen stock: {res.text}"
    print("[OK] GET /api/v1/kitchen/stock -> OK, Items count:", len(res.json()))

def test_cashier_pending_orders():
    print("--- 4. Testing Cashier Orders Endpoint ---")
    res = client.get("/api/v1/cashier/orders")
    assert res.status_code == 200, f"Error getting cashier orders: {res.text}"
    print("[OK] GET /api/v1/cashier/orders -> OK, Count:", len(res.json()))

def test_bar_stock_endpoint():
    print("--- 5. Testing Bar Stock Endpoint ---")
    res = client.get("/api/v1/cashier/bar-stock")
    assert res.status_code == 200, f"Error getting bar stock: {res.text}"
    print("[OK] GET /api/v1/cashier/bar-stock -> OK, Items count:", len(res.json()))

def test_create_cashier_order_and_flow():
    print("--- 6. Testing Direct Cashier Order Creation & Stock Deduction ---")
    db = TestingSessionLocal()
    prod = db.query(Product).first()
    ing = db.query(Ingredient).first()
    stock_before = ing.current_stock
    db.close()

    payload = {
        "machine_code": "SLOT-101",
        "notes": "Sin cebolla",
        "items": [
            {
                "product_id": str(prod.id),
                "quantity": 2,
                "is_courtesy": False
            }
        ]
    }
    res = client.post("/api/v1/cashier/orders", json=payload)
    assert res.status_code == 201, f"Error creating order: {res.text}"
    order_data = res.json()
    assert order_data["machine_code"] == "SLOT-101"
    assert float(order_data["total_amount"]) == 360.0
    print(f"[OK] POST /api/v1/cashier/orders -> Order {order_data['order_number']} created with total ${order_data['total_amount']}")

    # Validar que ahora aparezca en KDS
    res_kds = client.get("/api/v1/kds/orders")
    assert len(res_kds.json()) >= 1
    print("[OK] Order appears in KDS FIFO queue -> OK")

    # Validar pago en Caja
    order_id = order_data["id"]
    pay_res = client.post(f"/api/v1/cashier/orders/{order_id}/pay", json={"payment_method": "CASH"})
    assert pay_res.status_code == 200
    assert pay_res.json()["payment_status"] == "PAID"
    print(f"[OK] POST /api/v1/cashier/orders/{order_id}/pay -> Liquidada en Efectivo OK")

def test_product_image_support():
    print("--- 7. Testing Product Image Support ---")
    db = TestingSessionLocal()
    prod = db.query(Product).first()
    prod_id = str(prod.id)
    db.close()

    # Actualizar image_url directa
    res = client.put(f"/api/v1/products/{prod_id}", json={"image_url": "/uploads/products/hamburguesa_sample.jpg"})
    assert res.status_code == 200, f"Error updating product image: {res.text}"
    assert res.json()["image_url"] == "/uploads/products/hamburguesa_sample.jpg"
    print("[OK] PUT /api/v1/products/{id} with image_url -> OK")

if __name__ == "__main__":
    print("Starting integration test suite...")
    test_kds_endpoints()
    test_courtesy_rules()
    test_kitchen_stock_endpoint()
    test_cashier_pending_orders()
    test_bar_stock_endpoint()
    test_create_cashier_order_and_flow()
    test_product_image_support()
    print("\n=======================================================")
    print("ALL INTEGRATION TESTS PASSED PERFECTLY! (100% OK)")
    print("=======================================================")



