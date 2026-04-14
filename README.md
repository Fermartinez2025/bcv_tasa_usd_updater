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

*   **🔍 Scraping Inteligente**: Extracción dinámica desde archivos Excel (`.xls`) oficiales del BCV con lógica de búsqueda dinámica de celdas y fallback técnico (`xlrd`).
*   **✅ Validación por Fecha Valor**: El sistema valida que la **"Fecha Valor"** sea vigente:
    *   **Mañana**: Debe ser estrictamente la fecha de hoy.
    *   **Tarde**: Debe ser el **próximo día hábil** (regla de anticipo comercial).
*   **🛡️ Protección de Integridad (Tarde)**: En la ejecución vespertina, el sistema **preserva el valor de compra** (valor) que ya existe en la base de datos y solo actualiza el **valor de venta**, garantizando consistencia.
*   **⏳ Contingencia Inteligente**: Si el BCV no publica a tiempo:
    *   Extrae automáticamente la última tasa registrada en la BD (evitando ceros).
    *   En la tarde, espera pacientemente una actualización oficial hasta las **21:00** antes de aplicar el respaldo.
*   **📧 Notificaciones Premium**: Reportes HTML detallados indicando si la tasa es Oficial o de Contingencia.

---

##  Estructura del Proyecto
... (omitiendo para brevedad en el diff) ...

---

##  Flujo de Operación

1.  **Mantenimiento**: Limpieza automática de logs superiores a 15 días.
2.  **Validación Temporal**: Verificación de fin de semana y feriados en base de datos.
3.  **Ingesta de Datos**: Descarga de reportes desde el portal `bcv.org.ve`.
4.  **Auditoría de Vigencia**: 
    *   Detecta automáticamente el periodo (`manana`/`tarde`).
    *   Calcula el próximo día hábil si es el cierre vespertino.
    *   Compara la **Fecha Valor** del Excel contra la fecha esperada según el periodo.
5.  **Persistencia y Blindaje**: 
    *   Consulta la BD para rescatar valores previos si es necesario proteger la tasa de compra.
    *   Ejecución del SP `sp_carga_tasa` con los valores finales validados.
6.  **Cierre y Notificación**: Generación y envío del reporte HTML detallado.

---

##  Tecnologías

*   **Language**: Python 3.10+
*   **Data Analysis**: Pandas (con fallback xlrd)
*   **Connection**: PyODBC / FreeTDS
*   **DevOps**: Docker & Bash

---

> [!NOTE]
> **Soporte Técnico**: Este proyecto es mantenido por el equipo de **Desarrollo de Aplicaciones - TRANRED**. Para incidencias, contactar al administrador del sistema.

---
© 2026 TRANRED - Todos los derechos reservados.
"# bcv_tasa_usd_updater" 
