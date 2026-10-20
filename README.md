# 🍽️ GastroFlow OS
> **Plataforma Integral de Software, Operaciones y Equipamiento para Restaurantes, Bares y Dark Kitchens.**

GastroFlow OS conecta todos los puntos clave de un negocio gastronómico: desde que el cliente escanea el código QR en mesa, el mesero toma la orden en su celular, la cocina recibe la comanda digitalmente, hasta el cobro en caja y el control exacto de recetas e inventarios.

---

## 🎯 ¿Qué soluciona para el Restaurante?

* **Rotación de Mesas un 30% más rápida:** Los comensales consultan la carta con fotos y piden sin esperas.
* **Cero Errores y Letra Ilegible:** Reemplaza los papelitos por pantallas de cocina (KDS) con semáforo de tiempos.
* **Menos Tiempos Muertos:** Avisos instantáneos al teléfono del mesero cuando los platillos están listos en cocina o barra.
* **Cuentas Claras y Arqueos Sin Descuadres:** División de cuentas, propinas y cierres de turno protegidos por PIN.
* **Control de Costos y Recetas:** Conoce el costo real de cada platillo y deduce automáticamente insumos del almacén al vender.

---

## 🧩 Módulos y Soluciones Disponibles

| Módulo | Tipo | ¿Para qué sirve? | Demo Interactiva |
| :--- | :--- | :--- | :--- |
| **Menú Digital & Pedidos QR** | Autoservicio | Carta en alta definición con filtros de alérgenos y pedidos desde mesa sin apps. | [`frontend/cliente.html`](frontend/cliente.html) |
| **Comandero Móvil Meseros** | Sala | Funciona en cualquier celular o tablet para levantar comandas a pie de mesa. | [`frontend/pos.html`](frontend/pos.html) |
| **Pantalla KDS Cocina & Barra** | Cocina | Cola en vivo en orden de llegada (FIFO), semáforo de demora y timbre acústico. | [`frontend/kds.html`](frontend/kds.html) |
| **Terminal de Cobro y Caja** | Administración | Cobro multiformato (Efectivo/Tarjeta), cuentas divididas y arqueo de turno. | [`frontend/cashier.html`](frontend/cashier.html) |
| **Escandallos y Recetas** | Rentabilidad | Digitaliza fichas técnicas, calcula márgenes y descuenta ingredientes. | [`frontend/catalogo.html`](frontend/catalogo.html) |
| **Avisos al Personal** | Comunicación | Alertas al celular del mesero para retiro de platos listos y llamados de mesa. | [`frontend/alerts.html`](frontend/alerts.html) |
| **Portal Central / Catálogo** | Visión General | Catálogo interactivo con cotizador de software y equipos en tiempo real. | [`frontend/index.html`](frontend/index.html) |

---

## 📦 Estaciones Físicas y Equipamiento Recomendado para Cotizar

GastroFlow es 100% compatible con equipos estándares de mercado para que no dependas de hardware propietario:

1. **Estación de Cocina (KDS):**
   * Tablet de 10" o pantalla táctil + soporte metálico articulado de pared/mesa + cargador continuo de uso rudo.
2. **Estación de Barra:**
   * Tablet o monitor con filtro exclusivo para bebidas y cócteles.
3. **Punto de Caja / Cobros:**
   * Impresora térmica rápida de 80mm (red/USB).
   * Cajón de dinero con apertura electrónica automática.
   * Terminal o tablet POS para cobro.
4. **Comanderos Móviles:**
   * Smartphones de uso rudo o tablets compactas de 7" para meseros.
5. **Mesas y Terrazas:**
   * Displays acrílicos o madera grabados con código QR y número de mesa personalizado.

---

## 🚀 Despliegue Rápido con Docker

El sistema está empaquetado para levantarse en minutos en cualquier servidor local o VPS en la nube:

```bash
# 1. Clonar el repositorio
git clone https://github.com/emmiliotapia/gastroflow.git
cd gastroflow

# 2. Configurar variables de entorno
cp .env.example .env

# 3. Iniciar servicios en segundo plano
docker compose up -d --build
```

### Puertos del Sistema:
* **Catálogo & Demos Web:** `http://localhost:8002` (o `8000`)
* **API REST & WebSockets:** `http://localhost:8002/docs`
* **Base de Datos:** PostgreSQL con soporte vectorial en puerto `5441` (interno `5432`)

---

## 🛠️ Pruebas de Integración y Calidad

Para verificar que todos los flujos de comandas, cocina, cortesías y cobros funcionan correctamente:

```bash
python test_integration.py
```

---

## 📄 Licencia y Contacto
Desarrollado para optimizar operaciones en el sector gastronómico.
Para soporte, demostraciones o consultoría de implantación: contacto@smartopsia.com
