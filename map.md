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

Para exponer la API y las interfaces PWA hacia internet de forma segura con TLS/SSL:

### Proxy Host 1: Core API & Backend (`erp.smartopsia.com`)
- **Domain Names:** `erp.smartopsia.com`
- **Scheme:** `http`
- **Forward Host / IP:** `172.17.0.1` *(IP del docker0 bridge en host)* o `localhost`
- **Forward Port:** `8001`
- **Opciones Avanzadas:**
  - ✅ **Websockets Support:** Habilitado (requerido para KDS y notificaciones en tiempo real).
  - ✅ **Block Common Exploits:** Habilitado.
- **SSL / Certificado:**
  - SSL Certificate: Request a new Let's Encrypt Certificate.
  - ✅ **Force SSL:** Habilitado.
  - ✅ **HTTP/2 Support:** Habilitado.

### Proxy Host 2: Comandero POS (`pos.smartopsia.com`)
- **Domain Names:** `pos.smartopsia.com`
- **Scheme:** `http`
- **Forward Host / IP:** `172.17.0.1`
- **Forward Port:** `8001`
- **Opciones Avanzadas (Custom Nginx Configuration):**
  ```nginx
  location / {
      # Mapea la raíz al catálogo sin fricciones de clientes
      rewrite ^/$ /frontend/catalogo.html break;
      proxy_pass http://172.17.0.1:8001;
      proxy_set_header Host $host;
      proxy_set_header X-Real-IP $remote_addr;
      proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
      proxy_set_header X-Forwarded-Proto $scheme;
  }
  location /frontend/ {
      proxy_pass http://172.17.0.1:8001/frontend/;
  }
  location /api/ {
      proxy_pass http://172.17.0.1:8001/api/;
  }
  location /login {
      proxy_pass http://172.17.0.1:8001/login;
  }
  ```
- **Rutas de Acceso en Producción:**
  - **Catálogo de Clientes:** `https://pos.smartopsia.com/` (Redirección automática)
  - **Comandero Meseros:** `https://pos.smartopsia.com/frontend/pos.html`
  - **Portal de Caja:** `https://pos.smartopsia.com/frontend/cashier.html`
  - **Portal Staff y Técnicos:** `https://pos.smartopsia.com/frontend/staff.html`
  - **Cocina KDS:** `https://pos.smartopsia.com/frontend/kds.html`
- **SSL / Certificado:** Let's Encrypt + Force SSL habilitado.



### Proxy Host 3: Pantalla KDS (`kds.smartopsia.com`)
- **Domain Names:** `kds.smartopsia.com`
- **Scheme:** `http`
- **Forward Host / IP:** `172.17.0.1`
- **Forward Port:** `8001`
- **Opciones Avanzadas (Custom Nginx Configuration):**
  ```nginx
  location / {
      rewrite ^/$ /frontend/kds.html break;
      proxy_pass http://172.17.0.1:8001;
      proxy_set_header Host $host;
      proxy_set_header X-Real-IP $remote_addr;
      proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
      proxy_set_header X-Forwarded-Proto $scheme;
  }
  location /frontend/ {
      proxy_pass http://172.17.0.1:8001/frontend/;
  }
  location /api/ {
      proxy_pass http://172.17.0.1:8001/api/;
  }
  location /login {
      proxy_pass http://172.17.0.1:8001/login;
  }
  location /ws/ {
      proxy_pass http://172.17.0.1:8001/ws/;
      proxy_http_version 1.1;
      proxy_set_header Upgrade $http_upgrade;
      proxy_set_header Connection "Upgrade";
      proxy_set_header Host $host;
  }
  ```
- **SSL / Certificado:** Let's Encrypt + Force SSL + Websockets Support habilitado.

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
