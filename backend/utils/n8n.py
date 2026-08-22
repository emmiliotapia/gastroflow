"""
Servicio de Integración y Webhooks con n8n y notify.sh (`n8n.py`)
==================================================================
Este módulo maneja el envío asíncrono y no bloqueante de alertas hacia
los 4 canales segregados:
- runners: Solicitudes de recargas y órdenes listas para entrega.
- sistemas: Reportes de fallas técnicas en slots y solicitudes de mantenimiento.
- meseros: Avisos de despacho de comandas listas desde cocina/barra.
- alertas: Notificaciones de stock mínimo y sugerencias de compras.
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

# Variables de entorno para URLs de webhooks
N8N_WEBHOOK_ORDERS = os.getenv("N8N_WEBHOOK_ORDERS", "https://n8n.smartopsia.com/webhook/ordenes-nuevas")
N8N_WEBHOOK_TICKETS = os.getenv("N8N_WEBHOOK_TICKETS", "https://n8n.smartopsia.com/webhook/tickets-sistemas")
N8N_WEBHOOK_ALERTS = os.getenv("N8N_WEBHOOK_ALERTS", "https://n8n.smartopsia.com/webhook/alertas-inventario")
N8N_WEBHOOK_RUNNERS = os.getenv("N8N_WEBHOOK_RUNNERS", "https://n8n.smartopsia.com/webhook/alerta-runner")
N8N_WEBHOOK_MESEROS = os.getenv("N8N_WEBHOOK_MESEROS", "https://n8n.smartopsia.com/webhook/alerta-meseros")


def _execute_notify_script(channel: str, title: str, message: str, payload: dict):
    """
    Invoca notify.sh si está disponible en el entorno y ejecuta el envío HTTP a n8n.
    """
    # 1. Enviar HTTP Webhook
    url_map = {
        "runners": N8N_WEBHOOK_RUNNERS,
        "sistemas": N8N_WEBHOOK_TICKETS,
        "meseros": N8N_WEBHOOK_MESEROS,
        "alertas": N8N_WEBHOOK_ALERTS
    }
    target_url = url_map.get(channel, N8N_WEBHOOK_RUNNERS)
    
    try:
        body = {
            "channel": channel,
            "title": title,
            "message": message,
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
            logger.info(f"[NOTIFY] Webhook canal '{channel}' enviado a {target_url}. Status: {status}")
    except Exception as e:
        logger.warning(f"[NOTIFY] Alerta HTTP a {target_url} omitida/error: {str(e)}")

    # 2. Ejecutar notify.sh si existe
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
    """Dispara el webhook de comanda nueva."""
    try:
        total = float(order_data.get('total_amount', 0))
    except (ValueError, TypeError):
        total = 0.0

    executor.submit(
        _execute_notify_script,
        "runners",
        f"Nueva Comanda #{order_data.get('order_number')}",
        f"Comanda registrada con total ${total:.2f}",
        order_data
    )



def trigger_order_ready_notification(order_data: dict):
    """
    Notifica a meseros y runners que una orden ha sido marcada como READY
    en Cocina o Barra y está lista para su entrega en sala.
    """
    order_num = order_data.get("order_number", "COM-XXXX")
    machine = order_data.get("machine_code") or order_data.get("machine_id") or "SALA / BARRA"
    
    title = f"🔔 ¡ORDEN LISTA! #{order_num}"
    msg = f"La comanda #{order_num} para la máquina {machine} está LISTA para recoger y entregar."
    
    executor.submit(_execute_notify_script, "meseros", title, msg, order_data)
    executor.submit(_execute_notify_script, "runners", title, msg, order_data)


def trigger_runner_recharge_alert(machine_id: str, amount: Optional[str] = None, notes: Optional[str] = None, user_name: Optional[str] = None):
    """
    Dispara una alerta prioritaria de solicitud de recarga hacia el canal de Runners.
    """
    title = f"⚡ SOLICITUD DE RECARGA: {machine_id}"
    msg = f"Mesero/Operador {user_name or 'Staff'} solicita recarga para {machine_id}."
    if amount:
        msg += f" Monto: ${amount}"
    if notes:
        msg += f" ({notes})"

    payload = {
        "event": "recharge_request",
        "machine_id": machine_id,
        "amount": amount,
        "notes": notes,
        "requested_by": user_name
    }
    executor.submit(_execute_notify_script, "runners", title, msg, payload)


def trigger_system_failure_alert(machine_id: str, description: str, user_name: Optional[str] = None, ticket_folio: Optional[str] = None):
    """
    Dispara una alerta de falla técnica hacia el canal de Sistemas y Mantenimiento.
    """
    title = f"🚨 REPORTE DE FALLA: {machine_id} ({ticket_folio or 'TKT'})"
    msg = f"Reporte técnico por {user_name or 'Staff'}: {description}"

    payload = {
        "event": "technical_failure",
        "machine_id": machine_id,
        "ticket_folio": ticket_folio,
        "description": description,
        "reported_by": user_name
    }
    executor.submit(_execute_notify_script, "sistemas", title, msg, payload)


def trigger_ticket_webhook(ticket_data: dict):
    """Dispara el webhook general de tickets."""
    executor.submit(
        _execute_notify_script,
        "sistemas",
        f"Ticket {ticket_data.get('folio', 'TKT')}",
        ticket_data.get("description", "Actualización de ticket"),
        ticket_data
    )


def trigger_stock_webhook(alert_data: dict):
    """Dispara el webhook de alertas de inventario mínimo."""
    executor.submit(
        _execute_notify_script,
        "alertas",
        "⚠️ ALERTA DE STOCK MÍNIMO",
        f"Insumo {alert_data.get('name', 'N/A')} bajo de stock de seguridad.",
        alert_data
    )


def trigger_runner_alert_webhook(machine_id: str, action: str):
    """Compatibilidad con flujos anteriores de alerta-runner."""
    executor.submit(
        _execute_notify_script,
        "runners",
        f"Alerta de Servicio: {action.upper()}",
        f"Acción solicitada '{action}' en máquina {machine_id}",
        {"machine_id": machine_id, "action": action}
    )


