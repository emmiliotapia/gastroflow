"""
Servicio de Integración, Webhooks con n8n y Notificaciones Push vía ntfy.sh (`n8n.py`)
======================================================================================
Este módulo maneja el envío asíncrono y no bloqueante de alertas hacia
los canales segregados de operación:
- meseros: Llamados de clientes desde máquinas y avisos de órdenes listas en cocina/barra.
- runners: Solicitudes de recargas de créditos en slots y cobros.
- kds: Nuevas comandas y pedidos enviados a cocina y barra.
- sistemas: Reportes de fallas técnicas en slots y tickets de mantenimiento.
- alertas: Notificaciones de stock mínimo e inventarios críticos.
"""

import json
import logging
import os
import subprocess
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Optional

logger = logging.getLogger("n8n_integration")

# Pool de hilos para no bloquear el bucle de eventos de FastAPI
executor = ThreadPoolExecutor(max_workers=5)

# Variables de entorno para URLs de webhooks de n8n
N8N_WEBHOOK_ORDERS = os.getenv("N8N_WEBHOOK_ORDERS", "https://n8n.smartopsia.com/webhook/ordenes-nuevas")
N8N_WEBHOOK_TICKETS = os.getenv("N8N_WEBHOOK_TICKETS", "https://n8n.smartopsia.com/webhook/tickets-sistemas")
N8N_WEBHOOK_ALERTS = os.getenv("N8N_WEBHOOK_ALERTS", "https://n8n.smartopsia.com/webhook/alertas-inventario")
N8N_WEBHOOK_RUNNERS = os.getenv("N8N_WEBHOOK_RUNNERS", "https://n8n.smartopsia.com/webhook/alerta-runner")
N8N_WEBHOOK_MESEROS = os.getenv("N8N_WEBHOOK_MESEROS", "https://n8n.smartopsia.com/webhook/alerta-meseros")

# Configuración del Servidor Privado de ntfy (Push Notifications a Celulares y Relojes)
NTFY_SERVER = os.getenv("NTFY_SERVER", "https://ntfy.smartopsia.com")
NTFY_TOPIC_PREFIX = os.getenv("NTFY_TOPIC_PREFIX", "prestige-")



def _execute_notify_script(channel: str, title: str, message: str, payload: dict, priority: str = "4", tags: str = "bell"):
    """
    Despacha la alerta en paralelo hacia:
    1. Webhook de n8n (para automatizaciones, logs y bots de Telegram/WhatsApp).
    2. ntfy.sh (para notificaciones push inmediatas en teléfonos de meseros, runners y técnicos).
    3. notify.sh script bash local si está presente.
    """
    # 1. Enviar HTTP Webhook a n8n
    url_map = {
        "runners": N8N_WEBHOOK_RUNNERS,
        "meseros": N8N_WEBHOOK_MESEROS,
        "kds": N8N_WEBHOOK_ORDERS,
        "cocina": N8N_WEBHOOK_ORDERS,
        "sistemas": N8N_WEBHOOK_TICKETS,
        "alertas": N8N_WEBHOOK_ALERTS
    }
    target_url = url_map.get(channel, N8N_WEBHOOK_RUNNERS)
    
    try:
        body = {
            "channel": channel,
            "title": title,
            "message": message,
            "priority": priority,
            "tags": tags,
            "timestamp": datetime.now().isoformat(),
            "data": payload
        }
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            target_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=4) as response:
            status = response.getcode()
            logger.info(f"[NOTIFY:n8n] Webhook canal '{channel}' enviado a {target_url}. Status: {status}")
    except Exception as e:
        logger.warning(f"[NOTIFY:n8n] Alerta HTTP a {target_url} omitida/error: {str(e)}")

    # 2. Enviar HTTP Push a ntfy.sh
    try:
        topic_name = f"{NTFY_TOPIC_PREFIX}{channel}"
        ntfy_url = f"{NTFY_SERVER}/{topic_name}"
        msg_bytes = message.encode("utf-8")
        
        req_ntfy = urllib.request.Request(
            ntfy_url,
            data=msg_bytes,
            headers={
                "Title": title.encode("utf-8").decode("latin-1", "ignore"),
                "Priority": priority,
                "Tags": tags
            },
            method="POST"
        )
        with urllib.request.urlopen(req_ntfy, timeout=4) as resp_ntfy:
            logger.info(f"[NOTIFY:ntfy.sh] Push enviado al topic '{topic_name}'. Status: {resp_ntfy.getcode()}")
    except Exception as e:
        logger.warning(f"[NOTIFY:ntfy.sh] Alerta push a ntfy.sh omitida/error: {str(e)}")

    # 3. Invocar notify.sh si existe en el host
    script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "notify.sh"))
    if os.path.exists(script_path) and os.name != 'nt':
        try:
            subprocess.run(
                ["bash", script_path, channel, title, message, json.dumps(payload)],
                capture_output=True,
                timeout=5
            )
        except Exception as e:
            logger.debug(f"notify.sh subprocess error: {str(e)}")


def trigger_order_webhook(order_data: dict):
    """
    Notifica al canal KDS (Cocina y Barra) que ha entrado una nueva comanda.
    """
    order_num = order_data.get("order_number", "COM-XXXX")
    machine = order_data.get("machine_code") or order_data.get("machine_id") or "000"
    items_count = len(order_data.get("items", []))
    
    try:
        total = float(order_data.get('total_amount', 0))
    except (ValueError, TypeError):
        total = 0.0

    title = f"🍽️ ¡NUEVA COMANDA! #{order_num} (Máq. {machine})"
    msg = f"Nueva comanda recibida para Máquina {machine} con {items_count} artículo(s). Total: ${total:.2f}"

    executor.submit(
        _execute_notify_script,
        "kds",
        title,
        msg,
        order_data,
        "4",
        "fire,cooking,fork_and_knife"
    )


def trigger_order_ready_notification(order_data: dict):
    """
    Notifica a meseros y runners que una orden ha sido marcada como READY o finalizada
    en Cocina o Barra para que acudan de inmediato a recogerla y entregarla al cliente.
    """
    order_num = order_data.get("order_number", "COM-XXXX")
    machine = order_data.get("machine_code") or order_data.get("machine_id") or "SALA / BARRA"
    
    items_summary = ", ".join([f"{it.get('quantity', 1)}x {it.get('product_name', 'Item')}" for it in order_data.get('items', [])]) or "Platillos listos"

    title = f"🔔 ¡ORDEN LISTA PARA ENTREGA! #{order_num}"
    msg = f"Comanda #{order_num} lista en barra/cocina para MÁQUINA {machine}.\nDetalle: {items_summary}"
    
    executor.submit(_execute_notify_script, "meseros", title, msg, order_data, "5", "bell,plate,runner")
    executor.submit(_execute_notify_script, "runners", title, msg, order_data, "4", "runner,bell")


def trigger_waiter_call_alert(machine_id: str, notes: Optional[str] = None, user_name: Optional[str] = None):
    """
    Dispara una alerta prioritaria al canal de Meseros cuando el cliente presiona 'Llamar Mesero'.
    """
    title = f"🛎️ CLIENTE LLAMA A MESERO: MÁQUINA {machine_id}"
    msg = f"El cliente en la Máquina {machine_id} solicita atención personalizada de un mesero en sala."
    if notes:
        msg += f" (Nota: {notes})"

    payload = {
        "event": "waiter_call",
        "machine_id": machine_id,
        "notes": notes,
        "requested_by": user_name or "Cliente QR"
    }
    executor.submit(_execute_notify_script, "meseros", title, msg, payload, "5", "bell,warning,raising_hand")


def trigger_runner_recharge_alert(machine_id: str, amount: Optional[str] = None, notes: Optional[str] = None, user_name: Optional[str] = None):
    """
    Dispara una alerta prioritaria de solicitud de recarga hacia el canal de Runners.
    """
    title = f"⚡ SOLICITUD DE RECARGA: MÁQUINA {machine_id}"
    msg = f"Cliente en Máquina {machine_id} solicita recarga de créditos / saldo."
    if amount:
        msg += f" Monto sugerido: ${amount}"
    if notes:
        msg += f" ({notes})"

    payload = {
        "event": "recharge_request",
        "machine_id": machine_id,
        "amount": amount,
        "notes": notes,
        "requested_by": user_name or "Cliente QR"
    }
    executor.submit(_execute_notify_script, "runners", title, msg, payload, "4", "moneybag,runner,zap")


def trigger_system_failure_alert(machine_id: str, description: str, user_name: Optional[str] = None, ticket_folio: Optional[str] = None):
    """
    Dispara una alerta de falla técnica hacia el canal de Sistemas y Mantenimiento.
    """
    title = f"🚨 FALLA TÉCNICA EN SLOT: MÁQUINA {machine_id}"
    msg = f"Reporte de falla ({ticket_folio or 'TKT-NUEVO'}): {description}"

    payload = {
        "event": "technical_failure",
        "machine_id": machine_id,
        "ticket_folio": ticket_folio,
        "description": description,
        "reported_by": user_name or "Cliente QR"
    }
    executor.submit(_execute_notify_script, "sistemas", title, msg, payload, "5", "warning,tools,red_circle")


def trigger_ticket_webhook(ticket_data: dict):
    """Dispara el webhook general de tickets."""
    executor.submit(
        _execute_notify_script,
        "sistemas",
        f"Ticket {ticket_data.get('folio', 'TKT')}",
        ticket_data.get("description", "Actualización de ticket"),
        ticket_data,
        "4",
        "tools,clipboard"
    )


def trigger_stock_webhook(alert_data: dict):
    """Dispara el webhook de alertas de inventario mínimo."""
    executor.submit(
        _execute_notify_script,
        "alertas",
        "⚠️ ALERTA DE STOCK MÍNIMO",
        f"Insumo {alert_data.get('name', 'N/A')} bajo de stock de seguridad.",
        alert_data,
        "3",
        "package,chart_with_downwards_trend"
    )


def trigger_runner_alert_webhook(machine_id: str, action: str):
    """Compatibilidad con flujos de servicio rápido."""
    if action == "mesero":
        trigger_waiter_call_alert(machine_id=machine_id)
    elif action == "recarga":
        trigger_runner_recharge_alert(machine_id=machine_id)
    elif action == "falla":
        trigger_system_failure_alert(machine_id=machine_id, description="Falla reportada desde terminal")
    else:
        executor.submit(
            _execute_notify_script,
            "runners",
            f"Alerta de Servicio: {action.upper()}",
            f"Acción solicitada '{action}' en máquina {machine_id}",
            {"machine_id": machine_id, "action": action},
            "4",
            "bell"
        )
