#!/usr/bin/env bash
# ==============================================================================
# notify.sh - Despachador de Alertas y Notificaciones Segregadas
# GastroFlow (ERP Modular)
# Canales soportados: runners | meseros | kds | sistemas | alertas
# Uso: ./notify.sh <canal> <asunto/titulo> <mensaje> [json_payload_opcional]
# ==============================================================================

CHANNEL="${1:-runners}"
TITLE="${2:-Alerta Casino Prestige}"
MESSAGE="${3:-Sin detalle de mensaje}"
PAYLOAD="${4:-{}}"

NTFY_TOPIC_PREFIX="${NTFY_TOPIC_PREFIX:-prestige-}"
NTFY_SERVER="${NTFY_SERVER:-https://ntfy.smartopsia.com}"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")


echo "[$(date '+%Y-%m-%d %H:%M:%S')] [NOTIFY] Canal: [$CHANNEL] | Asunto: $TITLE"
echo "  -> Mensaje: $MESSAGE"

# Mapear canal a Webhook de n8n, Topic de ntfy y Tags
case "$CHANNEL" in
  runners)
    WEBHOOK_URL="${N8N_WEBHOOK_RUNNERS:-https://n8n.smartopsia.com/webhook/alerta-runner}"
    NTFY_TOPIC="${NTFY_TOPIC_PREFIX}runners"
    NTFY_TAGS="rotating_light,moneybag,zap,runner"
    NTFY_PRIORITY="5"
    ;;
  meseros)
    WEBHOOK_URL="${N8N_WEBHOOK_MESEROS:-https://n8n.smartopsia.com/webhook/alerta-meseros}"
    NTFY_TOPIC="${NTFY_TOPIC_PREFIX}meseros"
    NTFY_TAGS="rotating_light,bell,waiter,plate"
    NTFY_PRIORITY="5"
    ;;
  kds|cocina|barra)
    WEBHOOK_URL="${N8N_WEBHOOK_ORDERS:-https://n8n.smartopsia.com/webhook/ordenes-nuevas}"
    NTFY_TOPIC="${NTFY_TOPIC_PREFIX}kds"
    NTFY_TAGS="rotating_light,fire,cooking,fork_and_knife"
    NTFY_PRIORITY="5"
    ;;
  sistemas|mantenimiento)
    WEBHOOK_URL="${N8N_WEBHOOK_TICKETS:-https://n8n.smartopsia.com/webhook/tickets-sistemas}"
    NTFY_TOPIC="${NTFY_TOPIC_PREFIX}sistemas"
    NTFY_TAGS="rotating_light,warning,tools,red_circle"
    NTFY_PRIORITY="5"
    ;;
  alertas|stock)
    WEBHOOK_URL="${N8N_WEBHOOK_ALERTS:-https://n8n.smartopsia.com/webhook/alertas-inventario}"
    NTFY_TOPIC="${NTFY_TOPIC_PREFIX}alertas"
    NTFY_TAGS="package,warning,chart_with_downwards_trend"
    NTFY_PRIORITY="4"
    ;;
  *)
    WEBHOOK_URL="${N8N_WEBHOOK_DEFAULT:-https://n8n.smartopsia.com/webhook/alerta-runner}"
    NTFY_TOPIC="${NTFY_TOPIC_PREFIX}${CHANNEL}"
    NTFY_TAGS="rotating_light,bell"
    NTFY_PRIORITY="5"
    ;;
esac


# 1. Enviar a n8n Webhook
if command -v curl &> /dev/null; then
  curl -s -X POST "$WEBHOOK_URL" \
    -H "Content-Type: application/json" \
    -d "{\"channel\":\"$CHANNEL\",\"title\":\"$TITLE\",\"message\":\"$MESSAGE\",\"timestamp\":\"$TIMESTAMP\",\"extra\":$PAYLOAD}" \
    --max-time 4 > /dev/null 2>&1 &
fi

# 2. Enviar a ntfy (Push Notification instantánea)
if command -v curl &> /dev/null; then
  curl -s -X POST "${NTFY_SERVER}" \
    -H "Content-Type: application/json" \
    -d "{\"topic\":\"$NTFY_TOPIC\",\"title\":\"$TITLE\",\"message\":\"$MESSAGE\",\"priority\":$NTFY_PRIORITY,\"tags\":[\"$NTFY_TAGS\"]}" \
    --max-time 4 > /dev/null 2>&1 &
fi


exit 0
