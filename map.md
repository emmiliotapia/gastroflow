# Topología del VPS y Puertos (`map.md`)

## Entorno de Producción VPS (`smartops`)
- **Directorio Raíz en VPS:** `/opt/smartops/casino-erp`
- **Red Aislada Docker:** `casino_net` (Subred bridge independiente)

---

## Mapeo de Puertos y Servicios (Anti-Colisión)

| Servicio | Puerto Host VPS | Puerto Contenedor | Descripción / Endpoints |
|---|---|---|---|
| **FastAPI Core Backend** | `8001` | `8000` | API REST (`http://localhost:8001/docs`, `/health`) |
| **PostgreSQL + pgvector** | `5434` | `5432` | BD Híbrida Vectorial/Relacional (`casino_erp_db`) |
| **PWA Frontend** | `3000` | `80` | Interfaces cliente/KDS (Nginx estático) |
| **n8n Webhooks** | `5678` | `5678` | Sistema de Automatizaciones Externas |

---

## Enrutamiento Nginx Proxy Manager (NPM)

Todos los subdominios apuntan al contenedor backend en el puerto **`8001`**. FastAPI detecta automáticamente el subdominio y sirve el layout correspondiente directamente en la raíz `/`:

---

### 1. Hub Central / Launchpad (`erp.smartopsia.com` o `casino.smartopsia.com`)
* **Dominio:** `erp.smartopsia.com` *(o `smartopsia.com`)*
* **Forward Host / IP:** `172.17.0.1` *(o IP del host)*
* **Forward Port:** `8001`
* **SSL:** Let's Encrypt + Force SSL + HTTP/2 Support.
* **Websockets Support:** ✅ Habilitado.
* **Comportamiento:** Carga el **Launchpad Principal (`index.html`)** con accesos directos a todos los módulos y la documentación Swagger `/docs`.

---

### 2. Comandero Móvil Meseros (`pos.smartopsia.com`)
* **Dominio:** `pos.smartopsia.com`
* **Forward Host / IP:** `172.17.0.1`
* **Forward Port:** `8001`
* **SSL:** Let's Encrypt + Force SSL.
* **Websockets Support:** ✅ Habilitado *(para alertas `ORDER_READY`)*.
* **Comportamiento:** Al entrar a `https://pos.smartopsia.com/` abre directamente la **PWA de Meseros (`pos.html`)** con el selector de socios VIP, menú lateral y botones de asistencia.

---

### 3. Pantalla de Cocina y Barra (`kds.smartopsia.com`)
* **Dominio:** `kds.smartopsia.com`
* **Forward Host / IP:** `172.17.0.1`
* **Forward Port:** `8001`
* **SSL:** Let's Encrypt + Force SSL.
* **Websockets Support:** ✅ Habilitado *(indispensable para la cola FIFO en vivo)*.
* **Comportamiento:** Al entrar a `https://kds.smartopsia.com/` abre la **Pantalla KDS (`kds.html`)** con selector de estación y timbres sonoros.

---

### 4. Terminal de Caja y Barra (`caja.smartopsia.com` o `cashier.smartopsia.com`)
* **Dominio:** `caja.smartopsia.com` *(y alias `cashier.smartopsia.com`)*
* **Forward Host / IP:** `172.17.0.1`
* **Forward Port:** `8001`
* **SSL:** Let's Encrypt + Force SSL.
* **Websockets Support:** ✅ Habilitado.
* **Comportamiento:** Al entrar a `https://caja.smartopsia.com/` abre el **POS de Caja (`cashier.html`)** con cuentas abiertas en FIFO y cobro con PIN.

---

### 5. Catálogo & Fichas Técnicas (`cocina.smartopsia.com` o `catalogo.smartopsia.com`)
* **Dominio:** `cocina.smartopsia.com` *(o `catalogo.smartopsia.com`)*
* **Forward Host / IP:** `172.17.0.1`
* **Forward Port:** `8001`
* **SSL:** Let's Encrypt + Force SSL.
* **Websockets Support:** ✅ Habilitado.
* **Comportamiento:** Al entrar a `https://cocina.smartopsia.com/` abre el **Gestor de Fichas Técnicas, Mermas y Costeo (`catalogo.html`)**.


---

## Matriz de Convivencia Aislada en VPS

Este proyecto se ejecuta en un sandbox completamente aislado dentro del VPS sin colisionar ni compartir volúmenes o puertos con los servicios existentes:

| Servicio VPS Existent | Dominio / Puerto | Estado de Convivencia |
|---|---|---|
| **n8n Workflow Engine** | `localhost:5678` | Aislado - Integración vía Webhooks HTTP `/api/v1/webhooks` |
| **WAHA WhatsApp API** | `localhost:3000/3001` | Aislado - Sin colisión de contenedores |
| **RustDesk Server** | Puertos nativos RustDesk | Aislado - Sin impacto |
| **Time Prestige** | `time-prestige.smartopsia.com` | Aislado - Redes Docker separadas |
| **Prestige Ops** | `prestige-ops.smartopsia.com` | Aislado - Redes Docker separadas |

---

## Repositorio Git Oficial & Comandos de Despliegue

- **URL Remota:** `git@github.com:emmiliotapia/PRESTIGE.git`
- **Comando de Despliegue Remoto por SSH:**
  ```bash
  ssh root@smartops "cd /opt/smartops/casino-erp && ./deploy.sh"
  ```
