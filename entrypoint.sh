#!/bin/bash

# Define el período. Usa 'general' como fallback si la variable PERIODO no se pasa.
PERIODO=${PERIODO:-general}
# El archivo de log usará el PERIODO (manana, tarde, general) para diferenciar las ejecuciones
LOG_FILE="/app/logs/cron_${PERIODO}.log"

# Asegura que el directorio de logs exista y sea escribible
mkdir -p /app/logs
chmod 777 /app/logs

echo "======================================================================" >> "$LOG_FILE"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Iniciando ejecución (${PERIODO})." >> "$LOG_FILE"

# Ejecuta el script principal de Python. 
# ¡IMPORTANTE! Se ejecuta main.py.
python3 /app/main.py >> "$LOG_FILE" 2>&1

EXIT_CODE=$?
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Ejecución finalizada (${PERIODO}). Código de salida: ${EXIT_CODE}" >> "$LOG_FILE"
echo "======================================================================" >> "$LOG_FILE"

exit $EXIT_CODE