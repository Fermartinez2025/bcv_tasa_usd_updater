from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header 
from datetime import date, timedelta
from dotenv import load_dotenv 
import pandas as pd
import requests
import pyodbc
import os
import smtplib
import logging
import urllib3
import datetime
from requests.adapters import HTTPAdapter, Retry
import sys
from io import BytesIO
import platform

# --- Cargar variables de entorno ---
load_dotenv() 

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ----------------------------- CONSTANTES Y CONFIGURACIÓN -------------------------------- #

# Variables SMTP leídas globalmente para evitar repetición y permitir validación centralizada
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
EMAIL_DESTINO = os.getenv("EMAIL_DESTINO")
try:
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
except ValueError:
    SMTP_PORT = 587
    
# Configuración de Archivos y Logging
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
log_filename = os.path.join(LOG_DIR, datetime.datetime.now().strftime("log_bcv_%Y%m%d.log"))
ESTADO_CORREO = os.path.join(LOG_DIR, "estado_correo.txt")

logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

# ----------------------------- UTILIDADES DE ESTADO -------------------------------- #

def guardar_estado_envio(fecha, tipo):
    """Guarda la fecha y tipo de tasa del último envío de correo."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fecha_str = fecha.strftime("%Y-%m-%d")
    estado = f"{fecha_str}|{tipo}|{timestamp}\n"
    try:
        with open(ESTADO_CORREO, "a", encoding="utf-8") as f:
            f.write(estado)
        logging.debug(f"Estado de envío guardado: {estado.strip()}")
    except Exception as e:
        logging.error(f"No se pudo guardar el estado de envío en {ESTADO_CORREO}: {e}")

def leer_estado_envio(tipo):
    """
    #Lee la fecha del último correo enviado para un tipo de tasa específico.
    #Retorna la fecha más reciente encontrada, o None si no hay registro.
    """
    if not os.path.exists(ESTADO_CORREO):
        return None
    
    ultima_fecha = None
    try:
        with open(ESTADO_CORREO, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        fecha_str, tipo_tasa, _ = line.strip().split('|')
                        if tipo_tasa.upper() == tipo.upper():
                            fecha_leida = datetime.datetime.strptime(fecha_str, "%Y-%m-%d").date()
                            if ultima_fecha is None or fecha_leida > ultima_fecha:
                                ultima_fecha = fecha_leida
                    except ValueError:
                        logging.warning(f"Línea de estado inválida: {line.strip()}")
    except Exception as e:
        logging.error(f"Error leyendo estado de envío: {e}")
        return None
    
    logging.debug(f"Última fecha de envío para {tipo}: {ultima_fecha}")
    return ultima_fecha

def limpiar_estado_antiguo(dias=10):
    """Mantiene solo los registros de estado recientes (últimos 10 días)."""
    if not os.path.exists(ESTADO_CORREO):
        return
    hoy = datetime.date.today()
    nuevas_lineas = []
    try:
        with open(ESTADO_CORREO, "r", encoding='utf-8') as f:
            for linea in f:
                partes = linea.strip().split("|")
                if len(partes) >= 1:
                    try:
                        fecha_registro = datetime.datetime.strptime(partes[0], "%Y-%m-%d").date()
                        if (hoy - fecha_registro).days <= dias:
                            nuevas_lineas.append(linea)
                    except Exception:
                        continue
        with open(ESTADO_CORREO, "w", encoding='utf-8') as f:
            f.writelines(nuevas_lineas)
        logging.info(f"Estado de correo limpiado. Registros de los últimos {dias} días mantenidos.")
    except Exception as e:
        logging.error(f"Error limpiando estado antiguo: {e}")

def truncar_decimal_desde_texto(texto, decimales=4):
    """Trunca un número (formato texto) a n decimales."""
    texto = str(texto).replace(',', '.').strip()
    try:
        if '.' in texto:
            parte_entera, parte_decimal = texto.split('.')
            parte_decimal = (parte_decimal + '0' * decimales)[:decimales]
        else:
            parte_entera = texto
            parte_decimal = '0' * decimales
        return round(float(f"{parte_entera}.{parte_decimal}"), decimales)
    except ValueError:
        return 0.0
# ----------------------------- UTILIDADES DE CONEXIÓN Y DESCARGA -------------------------------- #

def get_db_connection(server_type):
    """Establece y devuelve una conexión a SQL Server."""
    if server_type == 2019:
        SERVER = os.getenv('SQL2019_SERVER')
        USER = os.getenv('SQL2019_USER')
        PASS = os.getenv('SQL2019_PASS')
        DB = os.getenv('SQL2019_DB_TEMP')
        # Usar driver 17 si se está en ambiente moderno (Windows o Linux con driver instalado)
        DRIVER = '{ODBC Driver 17 for SQL Server}' 
        conn_str = f"DRIVER={DRIVER};SERVER={SERVER};DATABASE={DB};UID={USER};PWD={PASS};"
    elif server_type == 2000:
        SERVER = os.getenv('SQL2000_SERVER')
        USER = os.getenv('SQL2000_USER')
        PASS = os.getenv('SQL2000_PASS')
        DB = os.getenv('SQL2000_DB_FINAL')
        PORT = os.getenv('SQL2000_PORT', '1433')
        
        # Corrección SQL 2000: Usar el driver nativo con lógica de plataforma
        if platform.system() == "Windows":
             DRIVER = '{SQL Server}' 
             conn_str = f"DRIVER={DRIVER};SERVER={SERVER},{PORT};DATABASE={DB};UID={USER};PWD={PASS};"
        else:
            
             DRIVER = '{FreeTDS}'
             conn_str = f"DRIVER={DRIVER};SERVER={SERVER};PORT={PORT};DATABASE={DB};UID={USER};PWD={PASS};TDS_Version=7.0;"
    else:
        raise ValueError("Tipo de servidor no válido.")
        
    try:
        conn = pyodbc.connect(conn_str, timeout=15)
        logging.info(f"Conexión a SQL Server {server_type} ({DB}) exitosa.")
        return conn
    except Exception as e:
        logging.error(f"Error al conectar a SQL Server {server_type}: {e}")
        raise ConnectionError(f"Fallo en conexión a SQL {server_type}: {e}")

def es_dia_habil(fecha):
    """Verifica si la fecha es día hábil (no fin de semana o feriado)."""
    if fecha.weekday() >= 5: 
        return False
    try:
        conn = get_db_connection(2019)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM dias_feriados WHERE DIAS = ?", fecha.strftime("%Y-%m-%d"))
        resultado = cursor.fetchone()
        conn.close()
        return resultado[0] == 0
    except Exception as e:
        logging.warning(f"Error al verificar feriados: {e}. Asumiendo día hábil.")
        return True

def generar_nombre_archivo(fecha):
    """Genera el nombre del archivo BCV basado en el trimestre y año."""
    trimestre_actual = (fecha.month - 1) // 3
    letra_trimestre = ['a', 'b', 'c', 'd'][trimestre_actual]
    anio = str(fecha.year)[-2:]
    return f"2_1_2{letra_trimestre}{anio}_smc.xls"

def descargar_archivo():
    """Busca y descarga el archivo BCV en los últimos 5 días hábiles."""
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[500,502,503,504]) 
    session.mount("https://", HTTPAdapter(max_retries=retries))
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/vnd.ms-excel, application/excel, application/x-excel, application/x-msexcel',
    }
    
    hoy = date.today()
    
    for i in range(5): 
        fecha = hoy - timedelta(days=i)
        if not es_dia_habil(fecha):
            logging.debug(f"Saltando {fecha}: No es día hábil.")
            continue
        
        nombre = generar_nombre_archivo(fecha)
        url = f"https://www.bcv.org.ve/sites/default/files/EstadisticasGeneral/{nombre}" 
        logging.info(f"Intentando descargar {nombre} desde {url}...")
        
        try:
            r = session.get(url, verify=False, timeout=15, headers=headers)
            content_type = r.headers.get("Content-Type", "")
            
            logging.debug(f"Respuesta HTTP: {r.status_code}, Content-Type: {content_type}")
            
            # Verificar Magic Number para archivos OLE (.xls)
            if r.status_code == 200 and r.content[:8] == b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1': 
                filepath = os.path.join(LOG_DIR, nombre)
                with open(filepath, "wb") as f:
                    f.write(r.content)
                logging.info(f"Archivo descargado: {filepath}")
                return filepath, fecha
            
            elif r.status_code == 403:
                logging.warning(f"403 Forbidden para {url}. Archivo no disponible o bloqueado.")
            elif r.status_code != 200:
                logging.warning(f"URL devolvió código de error HTTP {r.status_code}.")
            else:
                logging.warning(f"URL devolvió un tipo de contenido inesperado: {content_type}")
                
        except requests.exceptions.RequestException as e:
            logging.warning(f"Error durante la petición para {nombre}: {e}")
            
    raise Exception("No se pudo descargar archivo BCV válido en los últimos 5 días hábiles.")

def extraer_tasa_usd(filepath):
    """
    Extrae la Tasa de Compra (Columna F) y Venta (Columna G) para el USD.
    Retorna: (tasa_compra, tasa_venta, fecha_operacion)
    """
    try:
        logging.info("Iniciando extracción del archivo...")

        with open(filepath, 'rb') as f:
            excel_data = BytesIO(f.read())

        # Intentar primero con pandas (comportamiento original)
        try:
            xls = pd.ExcelFile(excel_data)
            hoja_target = xls.sheet_names[0]
            df = xls.parse(hoja_target, header=None).fillna("")

            tasa_compra_excel = None
            tasa_venta_excel = None
            fecha_operacion = date.today()

            # Búsqueda de la fila del USD y la fecha
            for _, row in df.iterrows():
                if "USD" in str(row[1]).upper() or "USD" in str(row[2]).upper():
                    try:
                        if len(row) < 7:
                            logging.warning("Fila USD encontrada pero incompleta.")
                            continue

                        tasa_compra_excel = truncar_decimal_desde_texto(row[5])
                        tasa_venta_excel = truncar_decimal_desde_texto(row[6])

                        if tasa_compra_excel < 10 or tasa_venta_excel < 10:
                            logging.warning(f"Tasas muy bajas ({tasa_compra_excel}). Índice incorrecto o datos corruptos.")
                            continue

                        # Búsqueda de la fecha de operación (Fila 6 o similar)
                        try:
                            fecha_row = df.iloc[5]
                            if "Fecha Operacion" in str(fecha_row[0]):
                                fecha_str = str(fecha_row[2]).split()[0] if fecha_row[2] and not str(fecha_row[2]).isspace() else str(fecha_row[3]).split()[0]
                                fecha_operacion = datetime.datetime.strptime(fecha_str, "%d/%m/%Y").date()
                        except Exception:
                            pass

                        logging.info(f"Datos BCV encontrados: Compra={tasa_compra_excel}, Venta={tasa_venta_excel}, Fecha={fecha_operacion}")
                        return tasa_compra_excel, tasa_venta_excel, fecha_operacion

                    except Exception as e:
                        logging.error(f"Error al procesar fila USD: {e}")
                        continue

            raise Exception("No se encontraron USD o tasas válidas en el archivo BCV.")

        except Exception as e_pandas:
            # Si falla pandas por problemas con xlrd/versión, intentar con xlrd directamente (fallback)
            logging.warning(f"Pandas falló leyendo Excel: {e_pandas}. Intentando fallback con xlrd.")
            try:
                import xlrd
            except ImportError:
                logging.critical("Pandas falló y 'xlrd' no está disponible para el fallback.")
                raise Exception(f"Fallo al leer Excel con pandas y falta 'xlrd' para fallback: {e_pandas}")

            try:
                # xlrd espera bytes, usamos el contenido leido
                wb = xlrd.open_workbook(file_contents=excel_data.getvalue())
                sheet = wb.sheet_by_index(0)

                tasa_compra_excel = None
                tasa_venta_excel = None
                fecha_operacion = date.today()

                for r in range(sheet.nrows):
                    # Asegurar índices
                    def cell_val(row_idx, col_idx):
                        try:
                            return sheet.cell_value(row_idx, col_idx)
                        except IndexError:
                            return ""

                    c1 = str(cell_val(r, 1)).upper() if sheet.ncols > 1 else ""
                    c2 = str(cell_val(r, 2)).upper() if sheet.ncols > 2 else ""

                    if "USD" in c1 or "USD" in c2:
                        try:
                            compra_raw = cell_val(r, 5)
                            venta_raw = cell_val(r, 6)

                            tasa_compra_excel = truncar_decimal_desde_texto(compra_raw)
                            tasa_venta_excel = truncar_decimal_desde_texto(venta_raw)

                            if tasa_compra_excel < 10 or tasa_venta_excel < 10:
                                logging.warning(f"Tasas muy bajas ({tasa_compra_excel}). Índice incorrecto o datos corruptos.")
                                continue

                            # Buscar fecha en filas superiores (ej. fila 6 -> índice 5)
                            try:
                                for fr in range(min(8, sheet.nrows)):
                                    cell0 = str(cell_val(fr, 0))
                                    if "FECHA" in cell0.upper() or "FECHA OPERACION" in cell0.upper():
                                        # intentar leer fecha de columnas cercanas
                                        posible = str(cell_val(fr, 2)).split()[0] if sheet.ncols > 2 and str(cell_val(fr, 2)).strip() else (str(cell_val(fr,3)).split()[0] if sheet.ncols > 3 else "")
                                        try:
                                            fecha_operacion = datetime.datetime.strptime(posible, "%d/%m/%Y").date()
                                            break
                                        except Exception:
                                            continue
                            except Exception:
                                pass

                            logging.info(f"Datos BCV encontrados (xlrd): Compra={tasa_compra_excel}, Venta={tasa_venta_excel}, Fecha={fecha_operacion}")
                            return tasa_compra_excel, tasa_venta_excel, fecha_operacion

                        except Exception as e:
                            logging.error(f"Error procesando fila USD con xlrd: {e}")
                            continue

                raise Exception("No se encontraron USD o tasas válidas en el archivo BCV (xlrd fallback).")

            except Exception as e_xlrd:
                logging.critical(f"FALLO DE LECTURA DEL ARCHIVO (xlrd): {e_xlrd}")
                raise Exception(f"Fallo al leer o procesar el archivo Excel con xlrd: {e_xlrd}")

    except Exception as e:
        logging.critical(f"FALLO DE LECTURA DEL ARCHIVO: {e}")
        raise Exception(f"Fallo al leer o procesar el archivo Excel: {e}")

# ----------------------------- INSERCIÓN DE DATOS -------------------------------- #

def ejecutar_sp_carga_tasa(periodo, fecha, valor_compra, valor_venta):
    """
    Ejecuta el Stored Procedure en SQL 2000 que maneja la carga y actualización.
    """
    # Parámetros de reintento configurables vía env vars
    max_attempts = int(os.getenv('DB_MAX_ATTEMPTS', '3'))
    backoff_seconds = float(os.getenv('DB_BACKOFF_SECONDS', '1.0'))

    fecha_str = fecha.strftime('%Y-%m-%d') if isinstance(fecha, (datetime.date, datetime.datetime)) else str(fecha)

    last_err = None
    for attempt in range(1, max_attempts + 1):
        conn = None
        try:
            logging.info(f"[DB] Intento {attempt}/{max_attempts}: Ejecutando SP sp_carga_tasa para {periodo} - fecha={fecha_str}")
            conn = get_db_connection(2000)
            cursor = conn.cursor()

            # Ejecutar SP de forma parametrizada e intentar leer código de retorno (si el SP fue actualizado para devolverlo)
            # Usamos un wrapper T-SQL que asigna el retorno a @rc y lo selecciona al final.
            cursor.execute(
                "DECLARE @rc INT; EXEC @rc = [rep_post_dia].[dbo].[sp_carga_tasa] ?, ?, ?, ?; SELECT @rc AS rc;",
                (periodo, fecha_str, float(valor_compra), None if valor_venta is None else float(valor_venta))
            )

            # Intentar leer el código de retorno devuelto por el SELECT @rc
            rc_row = cursor.fetchone()
            # Si fetchone devolvió None, puede que el driver no haya avanzado al SELECT; intentar avanzar
            if rc_row is None:
                try:
                    # avanzar al siguiente resultado y volver a leer
                    while cursor.nextset():
                        rc_row = cursor.fetchone()
                        if rc_row is not None:
                            break
                except Exception:
                    rc_row = None

            # Confirmar commit siempre
            conn.commit()

            db_valor = None
            db_valorVenta = None

            if rc_row is not None and len(rc_row) > 0 and rc_row[0] is not None:
                try:
                    rc = int(rc_row[0])
                except Exception:
                    rc = None

                if rc is not None:
                    if rc == 0:
                        logging.info(f"[DB] SP returned rc=0 (success) for fecha={fecha_str}; no verification SELECT required.")
                        conn.close()
                        return True
                    else:
                        raise Exception(f"SP returned non-zero return code: {rc}")

            # Si no se obtuvo código de retorno, o rc es None, hacer la verificación por SELECT (fallback)...
            verify_cursor = conn.cursor()
            verify_cursor.execute("SELECT [valor], ISNULL([valorVenta], NULL) FROM [dbo].[tasas_dicom] WHERE [fecha] = ?", (fecha_str,))
            row = verify_cursor.fetchone()
            verify_cursor.close()

            if row is None:
                raise Exception(f"Registro para fecha {fecha_str} no encontrado tras ejecución del SP.")

            db_valor = row[0]
            db_valorVenta = row[1] if len(row) > 1 else None

            def close_enough(a, b, tol=0.0006):
                try:
                    return abs(float(a) - float(b)) <= tol
                except Exception:
                    return False

            if periodo == 'manana':
                if close_enough(db_valor, valor_compra):
                    logging.info(f"[DB] Verificación OK (manana): valor en BD={db_valor} coincide con {valor_compra}")
                    conn.close()
                    return True
                else:
                    raise Exception(f"Valor en BD ({db_valor}) no coincide con valor esperado ({valor_compra}).")
            else:
                venta_ok = True if valor_venta is None else close_enough(db_valorVenta, valor_venta)
                compra_ok = close_enough(db_valor, valor_compra)
                if compra_ok and venta_ok:
                    logging.info(f"[DB] Verificación OK: compra={db_valor}, venta={db_valorVenta}")
                    conn.close()
                    return True
                else:
                    raise Exception(f"Mismatch en BD: compra_bd={db_valor} vs espera={valor_compra}, venta_bd={db_valorVenta} vs espera={valor_venta}")

        except Exception as e:
            last_err = e
            logging.warning(f"[DB] Intento {attempt} falló: {e}")
            try:
                if conn:
                    conn.close()
            except Exception:
                pass

            if attempt < max_attempts:
                logging.info(f"Esperando {backoff_seconds} segundos antes del siguiente intento...")
                import time
                time.sleep(backoff_seconds)
            else:
                logging.error(f"[DB] Todos los intentos ({max_attempts}) fallaron. Ultimo error: {last_err}")
                raise Exception(f"Fallo de DB (SP Carga Tasa) tras {max_attempts} intentos: {last_err}")

# ----------------------------- CORREO REAL -------------------------------- #

def enviar_correo(tipo, fecha, valor_compra, valor_venta, contingencia=False):
    
    # Validación de la configuración SMTP (Robustez contra NoneType)
    if not SMTP_SERVER or not SMTP_USER or not SMTP_PASS or not EMAIL_DESTINO:
        logging.error("Error CRÍTICO de CONFIGURACIÓN: Faltan variables SMTP (SERVER, USER, PASS, o DESTINO) en .env.")
        return False
    # Si es contingencia, aclaramos que los valores mostrados son referenciales del día anterior
    nota_contingencia = ""
    if contingencia:
        nota_contingencia = """
        <div style="background-color: #fff3cd; color: #856404; padding: 15px; border: 1px solid #ffeeba; margin-bottom: 20px;">
            <strong>AVISO OPERATIVO:</strong> No se detectó publicación oficial en el portal del BCV para el día de hoy. 
            Se ha aplicado automáticamente la <strong>tasa de cierre del día hábil anterior</strong> para garantizar la continuidad del sistema.
        </div>
        """
    # Formateo robusto de valores (soporta valor_venta = None)
    def _fmt(v):
        try:
            return "{:.4f}".format(0.0 if v is None else float(v))
        except Exception:
            return "N/A"

    valor_compra_display = _fmt(valor_compra)
    venta_display = _fmt(valor_venta)

    # CORRECCIÓN CRÍTICA: Inicializar variables para prevenir NameError/UnboundLocalError
    asunto = "ASUNTO BCV PENDIENTE" 
    cuerpo_html = ""

    # ------------------ CONSTRUCCIÓN DEL CONTENIDO ------------------
    if tipo.upper() == "COMPRA":
        asunto = f"ACTUALIZACIÓN 1/2 BCV: Tasa de COMPRA USD - {fecha.strftime('%d/%m/%Y')} ({valor_compra_display})"
        cuerpo_html = cuerpo_html.replace("<h3>Detalle", f"{nota_contingencia}<h3>Detalle")
        cuerpo_html = f"""
        <html><body>
<p>Estimado(a) equipo,</p>
<p>Se informa que el proceso de actualización matutino de la Tasa de Referencia del BCV ha concluido satisfactoriamente. Los datos han sido cargados en la base de datos DESARROLLO.</p>

<h3>Detalle de Tasa (Operación {fecha.strftime('%d/%m/%Y')})</h3>
<table border="1" cellpadding="5" cellspacing="0" style="width:50%; border-collapse: collapse;">
    <thead>
        <tr style="background-color: #f2f2f2;">
            <th>Indicador</th>
            <th>Monto (Bs./USD)</th>
            <th>Referencia Horaria</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><strong>Tasa de Compra (USD/ME)</strong></td>
            <td><strong>{valor_compra_display}</strong></td>
            <td>Referencia para la Apertura</td>
        </tr>
    </tbody>
</table>

<p style="margin-top: 20px;">
    <strong>Nota Operativa:</strong> Este valor corresponde a la Tasa de Venta publicada al cierre del día hábil anterior. La Tasa de Venta definitiva del día ({venta_display}) será actualizada y notificada en el proceso vespertino.
</p>

<p>Atentamente,</p>
<p>Sistema de Notificación Automática Tranred.</p>
</body></html>
"""
    elif tipo.upper() == "VENTA":
        asunto = f"PROCESO FINALIZADO BCV: Tasas {fecha.strftime('%d/%m/%Y')} | C:{valor_compra_display} V:{venta_display}"
        cuerpo_html = cuerpo_html.replace("<h3>Detalle", f"{nota_contingencia}<h3>Detalle")
        cuerpo_html = f"""
        <html><body>
<p>Estimado(a) equipo,</p>
<p>El proceso vespertino de tasas de referencia BCV para el día **{fecha.strftime('%d/%m/%Y')}** ha finalizado con éxito. Las tasas han sido actualizadas y transferidas a la base de datos de DESARROLLO.</p>

<h3>Resumen Final de Tasas USD</h3>
<table border="1" cellpadding="5" cellspacing="0" style="width:50%; border-collapse: collapse;">
    <thead>
        <tr style="background-color: #f2f2f2;">
            <th>Tipo de Tasa</th>
            <th>Monto (Bs./USD)</th>
            <th>Transferencia a DB Final</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><strong>Tasa de Compra</strong></td>
            <td>{valor_compra_display}</td>
            <td>Completada</td>
        </tr>
        <tr>
            <td><strong>Tasa de Venta</strong></td>
            <td><strong>{venta_display}</strong></td>
            <td>Completada</td>
        </tr>
    </tbody>
</table>

<p style="margin-top: 20px;">
    <strong>Acción:</strong> No se requiere intervención. La data está disponible en el sistema.
</p>

<p>Atentamente,</p>
<p>Sistema de Notificación Automática Tranred.</p>
</body></html>
"""
    else:
        # En caso de que el valor de 'tipo' en procesar_logica_periodo sea inesperado.
        logging.error(f"Tipo de ejecución de correo no reconocido: {tipo}")
        return False
        
    # ------------------ CONFIGURACIÓN Y ENVÍO DEL CORREO ------------------
    msg = MIMEMultipart('alternative')
    msg['Subject'] = Header(asunto, 'utf-8') 
    msg['From'] = SMTP_USER
    msg['To'] = EMAIL_DESTINO
    
    part = MIMEText(cuerpo_html, 'html', 'utf-8')
    msg.attach(part)
    
    try:
        logging.info(f"Conectando a SMTP en puerto {SMTP_PORT}...")
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(SMTP_USER, SMTP_PASS)
        
        server.sendmail(SMTP_USER, EMAIL_DESTINO, msg.as_string()) 
        
        server.quit()
        logging.info(f"Correo enviado exitosamente - {asunto}")
        return True
    
    except smtplib.SMTPAuthenticationError:
        logging.error("Error CRÍTICO de AUTENTICACIÓN (535).")
        logging.error("ℹ️ Acción Requerida: La contraseña debe ser una Contraseña de Aplicación (App Password) de Office 365.")
        return False
    except Exception as e:
        logging.error(f"Error enviando correo: {e}")
        return False
        
# ----------------------------- CORREO DE FALLO (ANTES DE MAIN) -------------------------------- #

def enviar_correo_fallo(asunto, cuerpo_error):
    """Función auxiliar para enviar correos de fallo."""
    
    # Validación de la configuración SMTP 
    if not SMTP_SERVER or not SMTP_USER or not SMTP_PASS or not EMAIL_DESTINO:
        logging.error("Error CRÍTICO de CONFIGURACIÓN: Faltan variables SMTP (SERVER, USER, PASS, o DESTINO) en .env.")
        return False
        
    msg = MIMEMultipart('alternative')
    msg['From'] = SMTP_USER
    msg['To'] = EMAIL_DESTINO
    msg['Subject'] = Header(asunto, 'utf-8') 
    
    cuerpo_html = f"""
    <html><body>
    <p>ATENCIÓN, ha ocurrido un fallo crítico en el proceso de tasas BCV.</p>
    <p><b>Error Detallado:</b> {cuerpo_error}</p>
    </body></html>
    """
    
    part = MIMEText(cuerpo_html, 'html', 'utf-8')
    msg.attach(part)
    
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        
        # CAMBIO CLAVE: Usar sendmail
        server.sendmail(SMTP_USER, EMAIL_DESTINO, msg.as_string()) 
        
        server.quit()
        logging.info(f"Notificación de fallo enviada: {asunto}")
        return True
    except smtplib.SMTPAuthenticationError:
        return False

# ----------------------------- LÓGICA DE PROCESAMIENTO (ANTES DE MAIN) -------------------------------- #

def procesar_logica_periodo(valor_compra, valor_venta, fecha_tasa, es_contingencia=False):
    """
    Nota: Importante: Maneja la lógica de inserción y notificación basada en el período.
    Solo realiza la actualización si la fecha de operación coincide con la fecha actual.

    Coordina la ejecución del SP y el envío del correo.
    Si es_contingencia=True, el SP buscará el valor anterior automáticamente.
    """
    # Normalizar tipo (acepta datetime, date o str). None significa fecha no detectada.
    hoy = datetime.date.today()
    periodo = os.getenv("PERIODO", "manana").lower()
    tipo = 'COMPRA' if periodo == 'manana' else 'VENTA'

    # --- LÓGICA DE CONTINGENCIA ---
    # Si la fecha del archivo no es la de hoy, o no hay valores
    if fecha_tasa != hoy or valor_compra == 0:
        logging.warning(f"⚠️ Contingencia activada: No se encontró publicación oficial para {hoy}. Aplicando tasa del día anterior.")
        # Enviamos 0 para que el SP busque el respaldo en la BD
        valor_compra = 0
        valor_venta = 0
        fecha_tasa = hoy 
    
    # Verificar si ya se envió para evitar duplicidad
    if leer_estado_envio(tipo) and leer_estado_envio(tipo) >= hoy:
        logging.info(f"Tasa de {tipo} para {hoy} ya fue procesada anteriormente. Omitiendo.")
        return

    # Ejecutar SP (el SP hará el trabajo de buscar la tasa de ayer al recibir 0)
    try:
        ejecutar_sp_carga_tasa(periodo, hoy, valor_compra, valor_venta)
        
        # Opcional: Podrías querer avisar en el correo que es una tasa de contingencia
        es_contingencia = (valor_compra == 0)
        if enviar_correo(tipo, hoy, valor_compra, valor_venta, contingencia=es_contingencia):
            guardar_estado_envio(hoy, tipo)
        if es_contingencia:
            logging.info("Notificación de contingencia enviada satisfactoriamente.")    
    except Exception as e:
        logging.error(f"Error crítico en el proceso: {e}")
        enviar_correo_fallo("FALLO CRITICO - Carga de Tasa", str(e)) 


# ----------------------------- BACKFILL ( Agregado Cambio de alcance) -------------------------------- #

def backfill_tasa_si_no_actualizada(fecha=None, force=False):
    """
    Si no hay tasa para `fecha` en la BD final, copia la última tasa anterior y llama al SP.
    Retorna True si aplicó backfill, False si no fue necesario o falló.
    """
    fecha = fecha or datetime.date.today()
    fecha_str = fecha.strftime("%Y-%m-%d")

    # Permitir forzar ejecución fuera de horario con env var o flag
    if not force and os.getenv("FORCE_BACKFILL") not in ("1", "true", "True"):
        # caller debe asegurarse de invocar a la hora deseada (23:59) o pasar force=True
        logging.info("Backfill no ejecutado: force no activado.")
        return False

    try:
        conn = get_db_connection(2000)
        cur = conn.cursor()

        # 1) Verificar si ya existe la tasa para la fecha objetivo
        cur.execute("SELECT TOP 1 valor, ISNULL(valorVenta, NULL) FROM dbo.tasas_dicom WHERE fecha = ?", (fecha_str,))
        existente = cur.fetchone()
        if existente:
            logging.info("Backfill: tasa ya presente para %s, nada por hacer.", fecha_str)
            conn.close()
            return False

        # 2) Obtener la tasa más reciente anterior a la fecha
        cur.execute("SELECT TOP 1 valor, ISNULL(valorVenta, NULL) FROM dbo.tasas_dicom WHERE fecha < ? ORDER BY fecha DESC", (fecha_str,))
        row = cur.fetchone()
        conn.close()

        if not row:
            logging.warning("Backfill: no se encontró tasa anterior para %s.", fecha_str)
            return False

        valor_compra_prev, valor_venta_prev = row[0], row[1]
        logging.info("Backfill: aplicando tasa anterior para %s -> compra=%s venta=%s", fecha_str, valor_compra_prev, valor_venta_prev)

        periodo_backfill = os.getenv("PERIODO_BACKFILL", "tarde").lower()
        # Reusar la función que ejecuta el SP para mantener consistencia y logging
        ejecutar_sp_carga_tasa(periodo_backfill, fecha, valor_compra_prev, valor_venta_prev)
        logging.info("Backfill: SP ejecutado para fecha %s", fecha_str)
        return True

    except Exception as e:
        logging.error("Backfill: error al intentar aplicar tasa anterior para %s: %s", fecha_str, e)
        return False

# ----------------------------- MAIN EXECUTION -------------------------------- #

def main():
    archivo_path = None
    try:
        logging.info("Iniciando proceso BCV...")
        limpiar_estado_antiguo()
        
        # soporte para invocación manual de backfill
        if "--backfill-now" in sys.argv or os.getenv("FORCE_BACKFILL") in ("1", "true", "True"):
            logging.info("Modo backfill detectado (--backfill-now o FORCE_BACKFILL). Ejecutando backfill y saliendo.")
            backfill_tasa_si_no_actualizada(force=True)
            return

        periodo = os.getenv("PERIODO", "manana").lower()
        logging.info(f"Modo de ejecución detectado: {periodo.upper()}")
        
        # 1. Descargar el archivo
        try:
            archivo_path, fecha_intento = descargar_archivo() 
        except Exception as e:
            logging.critical(f"FALLO CRÍTICO DE DESCARGA: {e}")
            enviar_correo_fallo("FALLO CRITICO: Descarga BCV", f"Fallo al descargar el archivo: {e}")
            raise 
            
        # 2. Extraer las tasas del Excel
        valor_compra, valor_venta, fecha_tasa = extraer_tasa_usd(archivo_path)
        
        # 3. Procesar e insertar en base de datos y notificar
        procesar_logica_periodo(valor_compra, valor_venta, fecha_tasa) # CORRECCIÓN 1
        
        logging.info("Proceso completado correctamente.")
        
    except Exception as e:
        logging.error(f"Error crítico en la ejecución principal: {e}")
        if 'archivo_path' in locals() and archivo_path:
            enviar_correo_fallo("FALLO GENERAL: Proceso BCV", f"Error en extracción o DB: {e}") # CORRECCIÓN 1
        
    finally:
        # Limpieza del archivo temporal
        if 'archivo_path' in locals() and archivo_path and os.path.exists(archivo_path):
            try:
                os.remove(archivo_path)
                logging.info(f"Archivo temporal {os.path.basename(archivo_path)} eliminado.")
            except Exception as e:
                logging.error(f"Error al intentar eliminar el archivo temporal: {e}")
        
        # --- Simulando el flujo en bloque main ---
        try:
            filepath, fecha_archivo = descargar_archivo()
            tasa_c, tasa_v, fecha_op = extraer_tasa_usd(filepath)
            
            # Si todo va bien, procesamos normal
            procesar_logica_periodo(tasa_c, tasa_v, fecha_op)

        except Exception as e:
            logging.error(f"No se pudo obtener la tasa del BCV: {e}")
            # SI FALLA TODO, forzamos el llamado al SP con ceros para cumplir el alcance
            logging.info("Iniciando carga automática por falta de publicación oficial...")
            procesar_logica_periodo(0, 0, datetime.date.today())
if __name__ == "__main__":
    logging.info("=== INICIANDO PROCESO DE ACTUALIZACIÓN DE TASAS BCV ===")
    
    try:
        # 1. Limpieza de logs antiguos
        limpiar_estado_antiguo(dias=15)
        
        try:
            # 2. Intentar flujo normal: Descarga y Extracción
            filepath, fecha_archivo = descargar_archivo()
            tasa_compra, tasa_venta, fecha_operacion = extraer_tasa_usd(filepath)
            
            logging.info(f"Datos oficiales obtenidos exitosamente para la fecha: {fecha_operacion}")
            procesar_logica_periodo(tasa_compra, tasa_venta, fecha_operacion)

        except Exception as e_bcv:
            # 3. FALLBACK: Si falla la descarga o el archivo no tiene la fecha de hoy
            logging.error(f"No se pudo obtener la tasa oficial del BCV: {e_bcv}")
            logging.warning("Iniciando MODO CONTINGENCIA: Aplicando regla de tasa del día anterior.")
            
            # Llamamos a la lógica con valores 0 para activar el fallback en el Stored Procedure
            # Usamos la fecha de hoy porque es la que necesitamos cubrir
            procesar_logica_periodo(0, 0, date.today(), es_contingencia=True)

    except Exception as e_critico:
        # 4. Error catastrófico (Base de datos caída o error de red total)
        error_msg = f"Fallo crítico en el script: {str(e_critico)}"
        logging.critical(error_msg)
        enviar_correo_fallo("CRÍTICO: Fallo Total Proceso Tasas", error_msg)
    
    logging.info("=== FIN DEL PROCESO ===")