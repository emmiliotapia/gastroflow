"""
Módulo de Enumeraciones del Dominio
==================================
Este módulo contiene todas las enumeraciones utilizadas por los modelos ORM
para garantizar la integridad de datos en PostgreSQL y mantener un tipado estricto
en la lógica de negocio.
"""

from enum import Enum


class UnitOfMeasure(str, Enum):
    """
    Unidades de medida estandarizadas para inventario, insumos y recetas.
    """
    KG = "KG"              # Kilogramos
    G = "G"                # Gramos
    GR = "GR"              # Gramos (alias Fichas Técnicas)
    L = "L"                # Litros
    ML = "ML"              # Mililitros
    PIECE = "PIECE"        # Pieza / Unidad entera
    OZ = "OZ"              # Onzas líquidas o sólidas
    BOTTLE = "BOTTLE"      # Botella
    CAN = "CAN"            # Lata
    PACK = "PACK"          # Paquete / Caja


class ProductType(str, Enum):
    """
    Clasificación del tipo de producto final de AyB.
    Determina cómo se descuenta el inventario al realizar una venta o comanda.
    """
    PREPARED = "PREPARED"  # Producto preparado que deduce insumos según receta (ej. Hamburguesa, Coctel)
    DIRECT = "DIRECT"      # Producto directo de venta sin receta (ej. Botella de agua, Lata de refresco)


class KDSStation(str, Enum):
    """
    Estaciones de despliegue en pantalla KDS (Kitchen Display System).
    Define hacia qué pantalla táctil u operativa se enruta el pedido.
    """
    KITCHEN = "KITCHEN"    # Cocina principal
    BAR = "BAR"            # Barra de bebidas / Barman
    SNACK_BAR = "SNACK_BAR"# Estación de snacks y postres


class MachineStatus(str, Enum):
    """
    Estados operativos de las máquinas / slots en la sala de juego.
    """
    OPERATIONAL = "OPERATIONAL"        # Operativa y en servicio
    MAINTENANCE = "MAINTENANCE"        # En mantenimiento técnico preventivo/correctivo
    OUT_OF_SERVICE = "OUT_OF_SERVICE"  # Fuera de servicio por falla grave o retiro


class UserRole(str, Enum):
    """
    Roles del sistema para control de acceso basado en roles (RBAC)
    y flujo de autorizaciones Poka-Yoke.
    """
    ADMIN = "ADMIN"                    # Administrador general del sistema
    JEFE_DE_SALA = "JEFE_DE_SALA"      # Supervisor / Jefe de Sala (Autoriza con PIN NIP)
    WAITER = "WAITER"                  # Mesero / Runner de atención a máquinas
    KITCHEN_STAFF = "KITCHEN_STAFF"    # Personal de Cocina (Operador KDS)
    BARMAN = "BARMAN"                  # Personal de Barra (Operador KDS Barra)
    TECHNICIAN = "TECHNICIAN"          # Técnico de Sistemas / Mantenimiento de slots
    CUSTOMER = "CUSTOMER"              # Cliente final (Acceso a PWA vía QR)


class TicketStatus(str, Enum):
    """
    Estados del ciclo de vida de los tickets de soporte / sistemas.
    Flujo estricto: PENDIENTE -> EN_PROCESO -> (HOLD) -> FINALIZADO.
    """
    PENDIENTE = "PENDIENTE"    # Ticket creado, en espera de asignación
    EN_PROCESO = "EN_PROCESO"  # Técnico trabajando en la resolución
    HOLD = "HOLD"              # En pausa esperando refacción o aprobación
    FINALIZADO = "FINALIZADO"  # Ticket resuelto y cerrado con validación PIN de Jefe de Sala


class StockLocation(str, Enum):
    """
    Ubicaciones físicas / bodegas de almacenamiento e inventario en la sala.
    """
    WAREHOUSE = "WAREHOUSE"  # Almacén Central / Bodega Principal
    KITCHEN = "KITCHEN"      # Cocina / Estación de Platillos
    BAR = "BAR"              # Barra / Estación de Coctelería y Bebidas


class StockTransactionType(str, Enum):
    """
    Tipos de movimiento o transacción de inventario.
    """
    PURCHASE = "PURCHASE"             # Entrada por compra / factura a proveedor
    ADJUSTMENT = "ADJUSTMENT"         # Ajuste manual por inventario físico / conteo
    PORTIONING = "PORTIONING"         # Conversión / porcionado de insumo macro a micro
    WASTE = "WASTE"                   # Salida por merma / desperdicio / expiración
    SALE_DEDUCTION = "SALE_DEDUCTION" # Descuento automático por comanda POS
    TRANSFER = "TRANSFER"             # Traspaso entre bodegas / estaciones


class OrderStatus(str, Enum):
    """
    Estados operativos del ciclo de vida de una comanda o ticket POS de AyB.
    """
    PENDING = "PENDING"        # Recibida, en espera de asignación/producción
    PREPARING = "PREPARING"    # En preparación en cocina/barra (KDS)
    READY = "READY"            # Preparado y listo para entrega por mesero
    DELIVERED = "DELIVERED"    # Entregado al cliente en mesa/máquina
    CANCELLED = "CANCELLED"    # Cancelado con reversa opcional o merma


class MembershipTier(str, Enum):
    """
    Niveles de membresía del cliente para determinar elegibilidad de cortesías.
    Soporta nomenclatura estándar (CLASSIC, GOLD, PLATINUM, VIP) y en español (PLATA, ORO, PLATINO, PRESTIGE).
    """
    CLASSIC = "CLASSIC"
    PLATA = "PLATA"
    GOLD = "GOLD"
    ORO = "ORO"
    PLATINUM = "PLATINUM"
    PLATINO = "PLATINO"
    VIP = "VIP"
    PRESTIGE = "PRESTIGE"


class IngredientCategory(str, Enum):
    """
    Categorías estandarizadas de insumos y materias primas.
    """
    PROTEINAS = "PROTEINAS"      # Carnes, Pollo, Pescados
    VEGETALES = "VEGETALES"      # Verduras, Frutas frescas
    LACTEOS = "LACTEOS"          # Quesos, Cremas, Mantequillas
    PANADERIA = "PANADERIA"      # Panes, Tortillas, Harinas
    ABARROTES = "ABARROTES"      # Salsas, Aceites, Condimentos, Enlatados
    LICORES = "LICORES"          # Destilados, Vinos, Cervezas base
    MEZCLADORES = "MEZCLADORES"  # Jugos, Jarabes, Refrescos base
    DESECHABLES = "DESECHABLES"  # Empaques, Vasos, Servilletas
    SUBRECETAS = "SUBRECETAS"    # Preparados intermedios / salsas caseras


class PaymentStatus(str, Enum):
    """
    Estados financieros o de pago de la comanda.
    """
    PENDING = "PENDING"                # Cuenta abierta pendiente de cobro en caja
    PAID = "PAID"                      # Liquidada en caja (Efectivo / Tarjeta)
    COMPLIMENTARY = "COMPLIMENTARY"    # Cortesía autorizada sin costo ($0.00)



