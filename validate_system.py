
import os
import sys
import logging
import datetime
from dotenv import load_dotenv
import pyodbc
import requests
import pandas as pd
import xlrd

# Configurar logging para validación
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def validate():
    logging.info("=== VALIDACIÓN DEL SISTEMA BCV TASA USD UPDATER ===")
    
    # 1. Cargar .env
    if not os.path.exists(".env"):
        logging.error("Archivo .env no encontrado.")
    else:
        load_dotenv()
        logging.info("Archivo .env cargado.")

    # 2. Validar Variables de Entorno Críticas
    critical_vars = [
        "SQL2019_SERVER", "SQL2019_USER", "SQL2019_PASS", "SQL2019_DB_TEMP",
        "SQL2000_SERVER", "SQL2000_USER", "SQL2000_PASS", "SQL2000_DB_FINAL",
        "SMTP_SERVER", "SMTP_USER", "SMTP_PASS", "EMAIL_DESTINO"
    ]
    missing = [v for v in critical_vars if not os.getenv(v)]
    if missing:
        logging.error(f"Faltan variables de entorno: {', '.join(missing)}")
    else:
        logging.info("Variables de entorno críticas presentes.")

    # 3. Validar Conexión SQL 2019 (Holidays)
    try:
        DRIVER = '{ODBC Driver 17 for SQL Server}'
        conn_str = f"DRIVER={DRIVER};SERVER={os.getenv('SQL2019_SERVER')};DATABASE={os.getenv('SQL2019_DB_TEMP')};UID={os.getenv('SQL2019_USER')};PWD={os.getenv('SQL2019_PASS')};"
        conn = pyodbc.connect(conn_str, timeout=5)
        logging.info("Conexión a SQL 2019 (Holidays) exitosa.")
        conn.close()
    except Exception as e:
        logging.error(f"Error conectando a SQL 2019: {e}")

    # 4. Validar Conexión SQL 2000 (Final)
    try:
        DRIVER = '{SQL Server}'
        conn_str = f"DRIVER={DRIVER};SERVER={os.getenv('SQL2000_SERVER')};DATABASE={os.getenv('SQL2000_DB_FINAL')};UID={os.getenv('SQL2000_USER')};PWD={os.getenv('SQL2000_PASS')};"
        conn = pyodbc.connect(conn_str, timeout=5)
        logging.info("Conexión a SQL 2000 (Final) exitosa.")
        conn.close()
    except Exception as e:
        logging.error(f"Error conectando a SQL 2000: {e}")

    # 5. Validar Acceso Web BCV
    try:
        r = requests.get("https://www.bcv.org.ve/", verify=False, timeout=5)
        logging.info(f"Acceso al portal BCV: {r.status_code}")
    except Exception as e:
        logging.error(f"Error accediendo al portal BCV: {e}")

    # 6. Validar Instalación de Paquetes
    try:
        logging.info(f"Versión de Pandas: {pd.__version__}")
        logging.info(f"Versión de xlrd: {xlrd.__version__}")
    except Exception as e:
        logging.error(f"Error validando paquetes: {e}")

    logging.info("=== FIN DE VALIDACIÓN ===")

if __name__ == "__main__":
    validate()
