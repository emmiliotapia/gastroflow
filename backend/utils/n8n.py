"""
Servicio de Integración y Webhooks con n8n (`n8n.py`)
======================================================
Este módulo maneja el envío asíncrono y no bloqueante de payloads
hacia los webhooks de n8n para el flujo de alertas y escalación.
"""

import json
import os
import urllib.request
from concurrent.futures import ThreadPoolExecutor
import logging

logger = logging.getLogger("n8n_integration")

# Pool de hilos para no bloquear el bucle de eventos de FastAPI con llamadas HTTP
executor = ThreadPoolExecutor(max_workers=5)

# Cargar URLs de webhooks desde el entorno
N8N_WEBHOOK_ORDERS = os.getenv("N8N_WEBHOOK_ORDERS", "")
N8N_WEBHOOK_TICKETS = os.getenv("N8N_WEBHOOK_TICKETS", "")
N8N_WEBHOOK_ALERTS = os.getenv("N8N_WEBHOOK_ALERTS", "")


def _send_post_request(url: str, payload: dict):
    """
    Función interna bloqueante ejecutada en el pool de hilos.
    """
    if not url:
        logger.warning("Intento de enviar webhook n8n pero la URL no está configurada.")
        return

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            status = response.getcode()
            logger.info(f"Webhook enviado a {url} exitosamente. Código: {status}")
    except Exception as e:
        logger.error(f"Error al enviar webhook a {url}: {str(e)}")


def trigger_order_webhook(order_data: dict):
    """
    Dispara el webhook de comanda nueva hacia n8n.
    """
    if N8N_WEBHOOK_ORDERS:
        executor.submit(_send_post_request, N8N_WEBHOOK_ORDERS, order_data)


def trigger_ticket_webhook(ticket_data: dict):
    """
    Dispara el webhook de creación o actualización de ticket.
    """
    if N8N_WEBHOOK_TICKETS:
        executor.submit(_send_post_request, N8N_WEBHOOK_TICKETS, ticket_data)


def trigger_stock_webhook(alert_data: dict):
    """
    Dispara el webhook de alertas de inventario mínimo o insumos sugeridos.
    """
    if N8N_WEBHOOK_ALERTS:
        executor.submit(_send_post_request, N8N_WEBHOOK_ALERTS, alert_data)
