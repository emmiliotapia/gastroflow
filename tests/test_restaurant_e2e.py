"""
Suite de Pruebas de Integración End-to-End (E2E) - Flujo Restaurante A&B
========================================================================
Casino Intelligent Hub (PRESTIGE)

Valida los siguientes flujos de principio a fin:
- Flujo 1: Pedido completo desde Catálogo QR, enrutamiento a KDS, cuenta abierta en Cashier,
           cobro/liquidación financiera, descuento atómico de stock e impacto en Corte de Caja (Reporte Z).
- Flujo 2: Asistencia en Piso (Llamar Mesero, Recarga de Créditos con Runners, Falla Técnica con Sistemas).
- Flujo 3: Registro de Mermas valorizadas y auditoría en el arqueo de turno.
"""

import sys
import os
from decimal import Decimal

# Configurar SQLite en memoria para tests aislados
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key-e2e-suite-2026"
os.environ["NTFY_SERVER"] = "https://ntfy.smartopsia.com"
os.environ["NTFY_TOPIC_PREFIX"] = "prestige-"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.models.base import Base
from backend.main import app
from backend.core.deps import get_db
from backend.core.security import get_password_hash, get_pin_hash
from backend.models.enums import (
    MembershipTier, KDSStation, StockLocation, UserRole,
    ProductType, UnitOfMeasure, PaymentStatus, OrderStatus, TicketStatus, MachineStatus
)
from backend.models.ingredient import Ingredient
from backend.models.product import Product, RecipeItem
from backend.models.stock import StockLevel
from backend.models.user import User, Role
from backend.models.machine import Machine
from backend.models.waste import WasteLog


# Crear motor SQLite en memoria aislado
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Crear tablas
Base.metadata.create_all(bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def seed_restaurant_e2e_data():
    """Siembra los datos base de prueba para ejecutar los flujos E2E."""
    db = TestingSessionLocal()

    # 1. Roles y Usuarios (Admin, Supervisor con PIN)
    role_admin = Role(name=UserRole.ADMIN, description="Administrador General")
    role_jefe = Role(name=UserRole.JEFE_DE_SALA, description="Jefe de Sala / Supervisor")
    db.add_all([role_admin, role_jefe])
    db.flush()

    supervisor = User(
        username="supervisor_sala",
        email="supervisor@prestige.com",
        hashed_password=get_password_hash("super_pass"),
        full_name="Jefe de Sala Turno A",
        role_id=role_jefe.id,
        hashed_pin=get_pin_hash("9999"),
        is_active=True
    )
    db.add(supervisor)


    # 2. Máquina Tragamonedas (Slot)
    machine = Machine(
        asset_code="SLOT-101",
        serial_number="SN-ARIST-101",
        model="Aristocrat Helix+",
        zone="SALA VIP ORO",
        qr_code_token="QR-SLOT-101-TOKEN",
        status=MachineStatus.OPERATIONAL,
        is_active=True
    )
    db.add(machine)
    db.flush()

    # 3. Insumos (Carne Sirloin, Pan Brioche, Ron Blanco, Menta)
    ing_carne = Ingredient(
        code="ING-CAR-SIR",
        name="Carne Sirloin 200g",
        category="PROTEINAS",
        unit_of_measure=UnitOfMeasure.GR,
        cost_per_unit=Decimal("0.45"),
        current_stock=Decimal("10000.00"),
        minimum_stock=Decimal("1000.00")
    )
    ing_pan = Ingredient(
        code="ING-PAN-BRI",
        name="Pan Brioche Artesanal",
        category="PANADERIA",
        unit_of_measure=UnitOfMeasure.PIECE,
        cost_per_unit=Decimal("12.00"),
        current_stock=Decimal("100.00"),
        minimum_stock=Decimal("20.00")
    )
    ing_ron = Ingredient(
        code="ING-LIC-RON",
        name="Ron Bacardi Carta Blanca 750ml",
        category="LICORES",
        unit_of_measure=UnitOfMeasure.ML,
        cost_per_unit=Decimal("0.25"),
        current_stock=Decimal("5000.00"),
        minimum_stock=Decimal("1000.00")
    )
    db.add_all([ing_carne, ing_pan, ing_ron])
    db.flush()

    # Stock inicial en Cocina (KITCHEN) y Barra (BAR)
    stock_carne_kitchen = StockLevel(
        ingredient_id=ing_carne.id,
        location=StockLocation.KITCHEN,
        quantity=Decimal("5000.0000")
    )
    stock_pan_kitchen = StockLevel(
        ingredient_id=ing_pan.id,
        location=StockLocation.KITCHEN,
        quantity=Decimal("50.0000")
    )
    stock_ron_bar = StockLevel(
        ingredient_id=ing_ron.id,
        location=StockLocation.BAR,
        quantity=Decimal("3000.0000")
    )
    db.add_all([stock_carne_kitchen, stock_pan_kitchen, stock_ron_bar])

    # 4. Platillos y Bebidas de Menú
    # A) Hamburguesa Especial (Cocina - PREPARED con Receta)
    burger = Product(
        sku="AYB-HAM-SIR",
        name="Hamburguesa Sirloin Gourmet",
        category="Hamburguesas Gourmet",
        product_type=ProductType.PREPARED,
        destination_kds=KDSStation.KITCHEN,
        price=Decimal("180.00"),
        courtesy_tier_min=MembershipTier.VIP,
        is_active=True
    )
    db.add(burger)
    db.flush()

    rec_item_1 = RecipeItem(product_id=burger.id, ingredient_id=ing_carne.id, quantity=Decimal("200.00"), unit_of_measure=UnitOfMeasure.GR)
    rec_item_2 = RecipeItem(product_id=burger.id, ingredient_id=ing_pan.id, quantity=Decimal("1.00"), unit_of_measure=UnitOfMeasure.PIECE)
    db.add_all([rec_item_1, rec_item_2])

    # B) Mojito Clásico (Barra - DIRECT con descuento de botella/ml)
    mojito = Product(
        sku="AYB-COCT-MOJ",
        name="Mojito Cubano Bacardi",
        category="Coctelería Clásica",
        product_type=ProductType.PREPARED,
        destination_kds=KDSStation.BAR,
        price=Decimal("95.00"),
        courtesy_tier_min=MembershipTier.ORO,
        is_active=True
    )
    db.add(mojito)
    db.flush()

    rec_mojito = RecipeItem(product_id=mojito.id, ingredient_id=ing_ron.id, quantity=Decimal("60.00"), unit_of_measure=UnitOfMeasure.ML)
    db.add(rec_mojito)

    db.commit()
    b_id = str(burger.id)
    m_id = str(mojito.id)
    c_id = str(ing_carne.id)
    p_id = str(ing_pan.id)
    r_id = str(ing_ron.id)
    db.close()
    return {
        "burger_id": b_id,
        "mojito_id": m_id,
        "carne_id": c_id,
        "pan_id": p_id,
        "ron_id": r_id
    }



def test_restaurant_e2e_full_lifecycle():

    print("=================================================================")
    print("INICIANDO SUITE DE PRUEBAS END-TO-END (E2E) - RESTAURANTE PRESTIGE")
    print("=================================================================")

    ids = seed_restaurant_e2e_data()
    burger_id = ids["burger_id"]
    mojito_id = ids["mojito_id"]
    carne_id = ids["carne_id"]
    ron_id = ids["ron_id"]

    # =========================================================================
    # FLUJO 1: PEDIDO COMPLETO DESDE QR, KDS, CASHIER, LIQUIDACIÓN Y CORTE
    # =========================================================================
    print("\n--- FLUJO 1: Ciclo Completo de Comanda y Liquidación Financiera ---")

    # 1.1 Consultar Catálogo Público
    res_cat = client.get("/api/v1/products")
    assert res_cat.status_code == 200, f"Error obteniendo catálogo: {res_cat.text}"
    products = res_cat.json()
    assert len(products) >= 2, "Deben existir al menos 2 productos en el catálogo"
    print(f"[OK] 1.1 Catálogo consultado con {len(products)} productos.")

    # 1.2 Crear Comanda Anónima vía QR vinculada a SLOT-101 (1 Hamburguesa + 2 Mojitos)
    order_payload = {
        "machine_code": "SLOT-101",
        "notes": "Hamburguesa término medio, mojitos con poco hielo",
        "items": [
            {"product_id": burger_id, "quantity": 1.0, "is_courtesy": False},
            {"product_id": mojito_id, "quantity": 2.0, "is_courtesy": False}
        ]
    }
    res_order = client.post("/api/v1/orders/", json=order_payload)
    assert res_order.status_code == 201, f"Error creando comanda: {res_order.text}"
    order_data = res_order.json()
    order_id = order_data["id"]
    order_num = order_data["order_number"]
    total_expected = 180.00 + (95.00 * 2)  # $370.00
    assert float(order_data["total_amount"]) == total_expected, f"Total esperado: {total_expected}, obtenido: {order_data['total_amount']}"
    assert order_data["machine_code"] == "SLOT-101"
    assert order_data["payment_status"] == "PENDING"
    print(f"[OK] 1.2 Comanda anónima {order_num} creada por ${order_data['total_amount']} para SLOT-101.")

    # 1.3 Verificar que la comanda llegó a las colas de Cocina y Barra en KDS
    res_kds_kitchen = client.get("/api/v1/kds/orders?station=KITCHEN")
    assert res_kds_kitchen.status_code == 200
    kitchen_orders = res_kds_kitchen.json()
    assert any(o["id"] == order_id for o in kitchen_orders), "La orden debe figurar en la estación KITCHEN"

    res_kds_bar = client.get("/api/v1/kds/orders?station=BAR")
    assert res_kds_bar.status_code == 200
    bar_orders = res_kds_bar.json()
    assert any(o["id"] == order_id for o in bar_orders), "La orden debe figurar en la estación BAR"
    print(f"[OK] 1.3 Orden {order_num} enrutada exitosamente a KDS Cocina y KDS Barra.")

    # 1.4 Verificar que la cuenta aparece activa (PENDING) en Cashier vinculada a SLOT-101
    res_cashier_pending = client.get("/api/v1/cashier/orders")
    assert res_cashier_pending.status_code == 200
    pending_list = res_cashier_pending.json()
    matched_cashier_order = next((o for o in pending_list if o["id"] == order_id), None)
    assert matched_cashier_order is not None, "La orden debe estar en la lista de cuentas abiertas de caja"
    assert matched_cashier_order["machine_code"] == "SLOT-101"
    print(f"[OK] 1.4 Cuenta abierta confirmada en Cashier para Máquina SLOT-101.")

    # 1.5 Cambiar estado en KDS: PENDING -> PREPARING -> READY
    res_prep = client.patch(f"/api/v1/kds/orders/{order_id}/status", json={"status": "PREPARING"})
    assert res_prep.status_code == 200
    assert res_prep.json()["status"] == "PREPARING"

    res_ready = client.patch(f"/api/v1/kds/orders/{order_id}/status", json={"status": "READY"})
    assert res_ready.status_code == 200
    assert res_ready.json()["status"] == "READY"
    print(f"[OK] 1.5 KDS avanzó orden a READY (Alerta de despacho emitida a meseros).")

    # 1.6 Cobrar y Liquidar en Caja en Efectivo (CASH)
    pay_payload = {
        "payment_method": "CASH"
    }
    res_pay = client.post(f"/api/v1/cashier/orders/{order_id}/pay", json=pay_payload)
    assert res_pay.status_code == 200, f"Error cobrando comanda: {res_pay.text}"
    paid_data = res_pay.json()
    assert paid_data["payment_status"] == "PAID"
    assert paid_data["payment_method"] == "CASH"
    print(f"[OK] 1.6 Comanda {order_num} liquidada en Caja con método CASH por ${paid_data['total_amount']}.")

    # 1.7 Verificar descuento atómico de stock
    # Inicial Carne en KITCHEN: 5000g - 200g = 4800g
    # Inicial Ron en BAR: 3000ml - (60ml * 2) = 2880ml
    res_stock = client.get("/api/v1/inventory/levels")
    assert res_stock.status_code == 200
    levels = res_stock.json()
    carne_level = next((l for l in levels if l["ingredient_id"] == carne_id and l["location"] == "KITCHEN"), None)
    ron_level = next((l for l in levels if l["ingredient_id"] == ron_id and l["location"] == "BAR"), None)
    assert carne_level is not None and float(carne_level["quantity"]) == 4800.0, f"Stock Carne incorrecto: {carne_level}"
    assert ron_level is not None and float(ron_level["quantity"]) == 2880.0, f"Stock Ron incorrecto: {ron_level}"
    print(f"[OK] 1.7 Descuento atómico de insumos verificado (Carne: 4,800g, Ron: 2,880ml).")

    # 1.8 Verificar que figure en Historial de Caja y en el Corte de Caja (Reporte Z)
    res_hist = client.get("/api/v1/cashier/history")
    assert res_hist.status_code == 200
    hist_list = res_hist.json()
    assert any(o["id"] == order_id for o in hist_list), "La orden debe figurar en el historial"

    res_corte = client.get("/api/v1/cashier/corte-caja")
    assert res_corte.status_code == 200
    corte_data = res_corte.json()
    assert corte_data["paid_orders_count"] >= 1
    assert corte_data["cash_total"] >= total_expected
    assert corte_data["total_sales_amount"] >= total_expected
    print(f"[OK] 1.8 Corte de Caja (Reporte Z) validado con ventas totales de ${corte_data['total_sales_amount']}.")

    # =========================================================================
    # FLUJO 2: ASISTENCIA EN PISO (RUNNERS, MESEROS Y SISTEMAS)
    # =========================================================================
    print("\n--- FLUJO 2: Asistencia de Runners, Meseros y Reportes Técnicos ---")

    # 2.1 Solicitud de Recarga de Saldo desde SLOT-101 (Canal Runners)
    tkt_recharge = {
        "title": "🟡 [SOLICITUD DE RECARGA] Máquina SLOT-101",
        "description": "Cliente en máquina SLOT-101 solicita recarga de créditos en su terminal.",
        "machine_id": None
    }
    res_tkt_rec = client.post("/api/v1/tickets/", json=tkt_recharge)
    assert res_tkt_rec.status_code == 201
    assert res_tkt_rec.json()["status"] == "PENDIENTE"
    print(f"[OK] 2.1 Alerta de Recarga de Créditos emitida para Máquina SLOT-101 (Canal prestige-runners).")

    # 2.2 Llamado de Mesero desde SLOT-101 (Canal Meseros)
    tkt_waiter = {
        "title": "🛎️ [LLAMAR MESERO] Máquina SLOT-101",
        "description": "Cliente en máquina SLOT-101 solicita la atención de un mesero en sala.",
        "machine_id": None
    }
    res_tkt_w = client.post("/api/v1/tickets/", json=tkt_waiter)
    assert res_tkt_w.status_code == 201
    print(f"[OK] 2.2 Alerta de Llamado de Mesero emitida para Máquina SLOT-101 (Canal prestige-meseros).")

    # 2.3 Reporte de Falla Técnica en SLOT-101 (Canal Sistemas)
    tkt_fault = {
        "title": "🔴 [FALLA TÉCNICA CLIENTE] Máquina SLOT-101",
        "description": "Reporte de cliente en máquina SLOT-101: Billetero atascado al ingresar billete de $500",
        "machine_id": None
    }
    res_tkt_f = client.post("/api/v1/tickets/", json=tkt_fault)
    assert res_tkt_f.status_code == 201
    fault_ticket = res_tkt_f.json()
    print(f"[OK] 2.3 Ticket de Falla Técnica {fault_ticket['folio']} creado para Sistemas (Canal prestige-sistemas).")

    # =========================================================================
    # FLUJO 3: REGISTRO DE MERMAS Y ARQUEO NETO
    # =========================================================================
    print("\n--- FLUJO 3: Registro de Mermas Valorizadas y Balance Neto ---")

    # 3.1 Registrar Merma de 300g de Carne Sirloin ($0.45 x 300 = $135.00)
    waste_payload = {
        "ingredient_id": carne_id,
        "location": "KITCHEN",
        "quantity": 300.0,
        "reason": "Quemado durante cocción a la parrilla"
    }
    res_waste = client.post("/api/v1/inventory/waste", json=waste_payload)
    assert res_waste.status_code == 201
    waste_data = res_waste.json()
    assert float(waste_data["total_cost"]) == 135.00
    print(f"[OK] 3.1 Merma registrada por ${waste_data['total_cost']} ({waste_data['quantity']}g de carne).")

    # 3.2 Verificar lista de mermas
    res_waste_list = client.get("/api/v1/inventory/waste")
    assert res_waste_list.status_code == 200
    assert len(res_waste_list.json()) >= 1
    print(f"[OK] 3.2 Historial de mermas consultado exitosamente.")

    # 3.3 Verificar que el Corte de Caja refleje las mermas y calcule el balance neto
    res_corte_final = client.get("/api/v1/cashier/corte-caja")
    assert res_corte_final.status_code == 200
    corte_final = res_corte_final.json()
    assert corte_final["total_waste_cost"] >= 135.00
    assert corte_final["net_revenue"] == corte_final["total_sales_amount"] - corte_final["total_waste_cost"]
    print(f"[OK] 3.3 Balance Neto en Corte de Caja: Ventas ${corte_final['total_sales_amount']:.2f} - Mermas ${corte_final['total_waste_cost']:.2f} = Neto ${corte_final['net_revenue']:.2f}")

    print("\n=================================================================")
    print("¡TODAS LAS PRUEBAS E2E DEL RESTAURANTE PASARON CON 100% DE ÉXITO!")
    print("=================================================================\n")


if __name__ == "__main__":
    test_restaurant_e2e_full_lifecycle()

