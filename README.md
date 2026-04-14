#  BCV Tasa USD Updater

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![SQL Server](https://img.shields.io/badge/SQL_Server-2000%20%7C%202019-red?style=for-the-badge&logo=microsoft-sql-server&logoColor=white)](https://www.microsoft.com/en-us/sql-server/)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

**BCV Tasa USD Updater** es una solución robusta y automatizada diseñada para la extracción, validación y sincronización de las tasas de cambio oficiales del **Banco Central de Venezuela (BCV)**. Este sistema garantiza que los entornos financieros de **TRANRED** cuenten con datos precisos y actualizados en tiempo real hacia servidores SQL Server (2000 y 2019).

---

##  Descripción General

El sistema automatiza el ciclo de vida completo de la información cambiaria: descarga el reporte estadístico oficial, extrae los valores de compra/venta mediante scraping inteligente, valida la vigencia de la información y notifica los resultados a través de reportes corporativos en HTML.

###  Características Principales

*   **🔍 Scraping Inteligente**: Extracción dinámica desde archivos Excel (`.xls`) oficiales del BCV con lógica de reintentos y fallback técnico (`xlrd`).
*   ** Validación de Fecha Crítica**: El sistema solo procesa la información si la **"Fecha Operación"** dentro del archivo coincide con el día actual, evitando registros anacrónicos.
*   ** Continuidad (Contingencia)**: Si el BCV no publica la tasa a tiempo, el sistema aplica automáticamente un **Backfill** basado en la última tasa de cierre disponible.
*   ** Notificaciones Premium**: Envío de reportes estructurados en HTML vía SMTP (Office 365 / Outlook) con estados detallados de la operación.
*   ** Compatibilidad Híbrida**: Conexión nativa a **SQL Server 2019** y soporte heredado para **SQL Server 2000** mediante drivers especializados.
*   ** Calendario Bancario**: Integración con tablas de feriados internos para evitar ejecuciones en días no laborables.

---

##  Estructura del Proyecto

```text
.
├── main.py                # Núcleo del sistema y lógica de procesamiento.
├── .env                   # Configuración de credenciales y parámetros (No versionado).
├── Dockerfile             # Configuración para despliegue en contenedores.
├── entrypoint.sh          # Script de orquestación para entornos Linux/Docker.
├── requirements.txt       # Dependencias del ecosistema Python.
├── sql/                   # Procedimientos almacenados y scripts de DB.
├── logs/                  # Registro histórico de ejecuciones y estados de correo.
└── bcv_tasa_usd_updater/  # Documentación técnica extendida.
```

---

##  Configuración del Entorno (.env)

Cree un archivo `.env` en la raíz del proyecto con la siguiente estructura:

###  Configuración de Correo (SMTP)
| Variable | Descripción | Ejemplo |
| :--- | :--- | :--- |
| `SMTP_SERVER` | Servidor SMTP corporativo | `smtp.office365.com` |
| `SMTP_PORT` | Puerto de conexión (TLS) | `587` |
| `SMTP_USER` | Usuario/Correo remitente | `alertas@tranred.com` |
| `SMTP_PASS` | **Password de Aplicación** | `xxxx-xxxx-xxxx-xxxx` |
| `EMAIL_DESTINO` | Destinatario principal | `finanzas@tranred.com` |

###  Bases de Datos
| Variable | Descripción |
| :--- | :--- |
| `SQL2019_SERVER` | Host/IP del servidor SQL Server 2019 (Validaciones) |
| `SQL2000_SERVER` | Host/IP del servidor SQL Server 2000 (Producción) |
| `SQL2000_DB_FINAL`| Nombre de la BD destino (`tasas_dicom`) |

###  Lógica de Operación
| Variable | Descripción | Valores |
| :--- | :--- | :--- |
| `PERIODO` | Indica el bloque de ejecución | `manana` (Compra) / `tarde` (Cierre) |
| `FORCE_BACKFILL`| Fuerza la aplicación de la tasa anterior | `true` / `false` |
| `DB_MAX_ATTEMPTS`| Máximo de reintentos de conexión a DB | `3` |

---

##  Instalación y Despliegue

### 💻 Ejecución Local (Desarrollo)

1.  **Entorno Virtual**:
    ```bash
    python -m venv .venv
    # Windows:
    .\.venv\Scripts\activate
    # Linux:
    source .venv/bin/activate
    ```
2.  **Dependencias**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Ejecutar**:
    ```bash
    python main.py
    ```

###  Ejecución con Docker

1.  **Construcción**:
    ```bash
    docker build -t bcv-updater .
    ```
2.  **Despliegue**:
    ```bash
    docker run --env-file .env -v $(pwd)/logs:/app/logs bcv-updater
    ```

---

##  Flujo de Operación

1.  **Mantenimiento**: Limpieza automática de logs superiores a 15 días.
2.  **Validación Temporal**: Verificación de fin de semana y feriados en base de datos.
3.  **Ingesta de Datos**: Descarga de reportes desde el portal `bcv.org.ve`.
4.  **Auditoría de Contenido**: El parser verifica que la fecha interna del Excel corresponda a la fecha de ejecución.
5.  **Persistencia**: Ejecución del SP `sp_carga_tasa` con reintentos automáticos.
6.  **Cierre y Notificación**: Generación y envío del reporte HTML detallado.

---

##  Tecnologías

*   **Language**: Python 3.10+
*   **Data Analysis**: Pandas (con fallback xlrd)
*   **Connection**: PyODBC / FreeTDS
*   **DevOps**: Docker & Bash

---

> [!NOTE]
> **Soporte Técnico**: Este proyecto es mantenido por el equipo de **IT - TRANRED**. Para incidencias, contactar al administrador del sistema.

---
© 2026 TRANRED - Todos los derechos reservados.
"# bcv_tasa_usd_updater" 
