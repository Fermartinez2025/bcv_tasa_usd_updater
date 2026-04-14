FROM python:3.10-slim

# Establecer directorio de trabajo
WORKDIR /app

# Establecer zona horaria
ENV TZ=America/Caracas

# Variables de entorno para la instalación no interactiva
ENV DEBIAN_FRONTEND=noninteractive
ENV ACCEPT_EULA=Y

# ==============================================================================
# FASE 1: Instalación de dependencias del sistema
# ==============================================================================
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Zona horaria
    tzdata \
    # Compiladores (necesarios para algunos paquetes Python)
    gcc \
    g++ \
    # Herramientas de red y seguridad
    gnupg2 \
    curl \
    ca-certificates \
    apt-transport-https \
    lsb-release \
    # ODBC base
    unixodbc \
    unixodbc-dev \
    # FreeTDS para SQL Server antiguo (2000/2005)
    freetds-dev \
    freetds-bin \
    tdsodbc \
    # PostgreSQL (si lo necesitas en el futuro)
    libpq-dev \
    # Limpieza
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

# ==============================================================================
# FASE 2: Instalación de Microsoft ODBC Driver 17 (para SQL Server 2019+)
# ==============================================================================
RUN curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && curl -fsSL https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends \
        msodbcsql17 \
        mssql-tools \
    && echo 'export PATH="$PATH:/opt/mssql-tools/bin"' >> ~/.bashrc \
    && rm -rf /var/lib/apt/lists/*

# ==============================================================================
# FASE 3: Configuración de FreeTDS
# ==============================================================================

# Configurar FreeTDS en odbcinst.ini
RUN echo "[FreeTDS]" > /etc/odbcinst.ini && \
    echo "Description = FreeTDS Driver for SQL Server" >> /etc/odbcinst.ini && \
    echo "Driver = /usr/lib/x86_64-linux-gnu/odbc/libtdsodbc.so" >> /etc/odbcinst.ini && \
    echo "Setup = /usr/lib/x86_64-linux-gnu/odbc/libtdsS.so" >> /etc/odbcinst.ini && \
    echo "UsageCount = 1" >> /etc/odbcinst.ini && \
    echo "FileUsage = 1" >> /etc/odbcinst.ini && \
    echo "" >> /etc/odbcinst.ini && \
    echo "[ODBC Driver 17 for SQL Server]" >> /etc/odbcinst.ini && \
    echo "Description = Microsoft ODBC Driver 17 for SQL Server" >> /etc/odbcinst.ini && \
    echo "Driver = /opt/microsoft/msodbcsql17/lib64/libmsodbcsql-17.10.so.6.1" >> /etc/odbcinst.ini && \
    echo "UsageCount = 1" >> /etc/odbcinst.ini

# Configurar FreeTDS global (freetds.conf)
RUN echo "[global]" > /etc/freetds/freetds.conf && \
    echo "    tds version = 7.1" >> /etc/freetds/freetds.conf && \
    echo "    client charset = UTF-8" >> /etc/freetds/freetds.conf && \
    echo "    port = 1433" >> /etc/freetds/freetds.conf && \
    echo "    dump file = /tmp/freetds.log" >> /etc/freetds/freetds.conf && \
    echo "    text size = 64512" >> /etc/freetds/freetds.conf && \
    echo "" >> /etc/freetds/freetds.conf

# ==============================================================================
# FASE 4: Copiar archivos y dependencias Python
# ==============================================================================

# Copiar requirements.txt primero (mejor cache de Docker)
COPY requirements.txt /app/

# Instalar dependencias Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar el resto de la aplicación
COPY . /app

# ==============================================================================
# FASE 5: Crear directorios y permisos
# ==============================================================================

# Crear directorio de logs si no existe
RUN mkdir -p /app/logs && \
    chmod 755 /app/logs

# Dar permisos de ejecución al entrypoint
RUN chmod +x /app/entrypoint.sh

# ==============================================================================
# FASE 6: Script de verificación (OPCIONAL - para debugging)
# ==============================================================================

# Crear script de verificación de drivers
RUN echo '#!/bin/bash' > /app/verify_drivers.sh && \
    echo 'echo "=== Verificación de Drivers ODBC ===" ' >> /app/verify_drivers.sh && \
    echo 'echo "" ' >> /app/verify_drivers.sh && \
    echo 'echo "Drivers instalados en odbcinst.ini:" ' >> /app/verify_drivers.sh && \
    echo 'cat /etc/odbcinst.ini' >> /app/verify_drivers.sh && \
    echo 'echo "" ' >> /app/verify_drivers.sh && \
    echo 'echo "=== Verificación con odbcinst ===" ' >> /app/verify_drivers.sh && \
    echo 'odbcinst -q -d' >> /app/verify_drivers.sh && \
    echo 'echo "" ' >> /app/verify_drivers.sh && \
    echo 'echo "=== Verificación desde Python ===" ' >> /app/verify_drivers.sh && \
    echo 'python3 -c "import pyodbc; print(\"Drivers:\"); [print(f\"  - {d}\") for d in pyodbc.drivers()]"' >> /app/verify_drivers.sh && \
    chmod +x /app/verify_drivers.sh

# ==============================================================================
# FASE 7: Healthcheck (OPCIONAL)
# ==============================================================================

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "import pyodbc; pyodbc.drivers()" || exit 1

# ==============================================================================
# ENTRYPOINT
# ==============================================================================

ENTRYPOINT ["/app/entrypoint.sh"]