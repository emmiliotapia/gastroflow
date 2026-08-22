#!/usr/bin/env bash
# ==============================================================================
# notify.sh - Despachador de Alertas y Notificaciones Segregadas
# Casino Intelligent Hub (ERP Modular)
# Canales soportados: runners | sistemas | meseros | alertas
# Uso: ./notify.sh <canal> <asunto/titulo> <mensaje> [json_payload_opcional]
# ==============================================================================

CHANNEL="${1:-runners}"
TITLE="${2:-Alerta Casino Prestige}"
MESSAGE="${3:-Sin detalle de mensaje}"
PAYLOAD="${4:-{}}"

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

echo "[$(date '+%Y-%m-%d %H:%M:%S')] [NOTIFY] Canal: [$CHANNEL] | Asunto: $TITLE"
echo "  -> Mensaje: $MESSAGE"

# Definir URLs de destino según canal (por defecto o sobreescritas por entorno)
case "$CHANNEL" in
  runners)
    WEBHOOK_URL="${N8N_WEBHOOK_RUNNERS:-https://n8n.smartopsia.com/webhook/alerta-runner}"
    ;;
  sistemas|mantenimiento)
    WEBHOOK_URL="${N8N_WEBHOOK_TICKETS:-https://n8n.smartopsia.com/webhook/tickets-sistemas}"
    ;;
  meseros)
    WEBHOOK_URL="${N8N_WEBHOOK_MESEROS:-https://n8n.smartopsia.com/webhook/alerta-meseros}"
    ;;
  alertas|stock)
    WEBHOOK_URL="${N8N_WEBHOOK_ALERTS:-https://n8n.smartopsia.com/webhook/alertas-inventario}"
    ;;
  *)
    WEBHOOK_URL="${N8N_WEBHOOK_DEFAULT:-https://n8n.smartopsia.com/webhook/alerta-runner}"
    ;;
esac

# Enviar via curl si curl está disponible
if command -v curl &> /dev/null; then
  curl -s -X POST "$WEBHOOK_URL" \
    -H "Content-Type: application/json" \
    -d "{\"channel\":\"$CHANNEL\",\"title\":\"$TITLE\",\"message\":\"$MESSAGE\",\"timestamp\":\"$TIMESTAMP\",\"extra\":$PAYLOAD}" \
    --max-time 4 > /dev/null 2>&1 &
fi

exit 0
