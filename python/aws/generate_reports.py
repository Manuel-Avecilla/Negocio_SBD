"""
=============================================================================
SMARTRUTA & MOVILIDAD SOSTENIBLE - INFORME JSON UNIFICADO EN AWS
=============================================================================
Script: generate_reports.py
Descripción:
    Consulta MariaDB en AWS RDS y las tres tablas de Amazon DynamoDB aplicando
    filtros en ambos orígenes, y genera un único informe JSON que reúne la
    información de las dos bases de datos.

    La carpeta de salida sigue el mismo patrón que generate_reports.py local:
        json_reports/Date_YYYY_MM_DD_Hour_HH-MM-SS/AWS_report.json

    El informe es autocontenido: incluye su propia conexión a MariaDB RDS y su
    serializador JSON, sin depender de otros scripts de informes. Toda la
    configuración se lee desde Docker/.env.

    Filtros aplicados (equivalentes a los de pruebas.py --8 de DynamoDB):
        1. RDS - Sostenibilidad: modos Bicicleta, Autobus y Carpooling.
        2. RDS - Carpooling: rutas en estado Programada o En_Curso.
        3. RDS - Desplazamientos: fecha de los últimos 12 meses.
        4. DynamoDB - MENSAJES_RUTA: id_ruta 1..60 y mensajes no leídos.
        5. DynamoDB - NOTIFICACIONES_USUARIO: no leídas de tipo
           reserva_confirmada u recordatorio_salida.
        6. DynamoDB - POSICIONES_TIEMPO_REAL: velocidad 20..110 km/h e
           id_usuario >= 1.
=============================================================================
"""

import datetime
import json
import os
from decimal import Decimal
from pathlib import Path

import boto3
import pymysql
import pymysql.cursors
from boto3.dynamodb.conditions import Attr
from dotenv import load_dotenv
from pymysql.constants import CLIENT

# generate_reports.py -> aws -> python -> Negocio_SBD
BASE_DIR = Path(__file__).resolve().parents[2]
DOCKER_DIR = BASE_DIR / "Docker"
ENV_PATH = DOCKER_DIR / ".env"

load_dotenv(ENV_PATH)

# -------------------------------
# CONEXION A RDS (MARIADB)
# -------------------------------
AWS_RDS_DB_ENDPOINT = os.getenv("AWS_RDS_DB_ENDPOINT")
AWS_RDS_DB_NAME = os.getenv("AWS_RDS_DB_NAME")
SHARED_DB_USER = os.getenv("SHARED_DB_USER")
SHARED_DB_PASSWORD = os.getenv("SHARED_DB_PASSWORD")

CONFIG_RDS_MARIADB = {
    "host": AWS_RDS_DB_ENDPOINT,
    "port": 3306,
    "user": SHARED_DB_USER,
    "password": SHARED_DB_PASSWORD,
    "database": AWS_RDS_DB_NAME,
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
    "client_flag": CLIENT.MULTI_STATEMENTS,
}


def serializador_json(obj):
    """
    Transforma tipos no admitidos nativamente por JSON (fechas, Decimales,
    conjuntos, etc.) antes de escribir el informe.
    """
    if isinstance(obj, (datetime.datetime, datetime.date, datetime.time)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    if isinstance(obj, set):
        return list(obj)
    raise TypeError(f"Tipo no serializable a JSON: {type(obj).__name__}")


def ejecutar_consulta(query):
    """
    Abre una conexión con MariaDB en AWS RDS, ejecuta una consulta y devuelve
    todas las filas como una lista de diccionarios.
    """
    if not AWS_RDS_DB_ENDPOINT:
        print(" Error: la variable AWS_RDS_DB_ENDPOINT no está definida en el .env.")
        return None

    if not AWS_RDS_DB_NAME:
        print(" Error: la variable AWS_RDS_DB_NAME no está definida en el .env.")
        return None

    conn = None
    try:
        print(" Conectando a MariaDB en AWS RDS...")
        conn = pymysql.connect(**CONFIG_RDS_MARIADB)
        with conn.cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchall()
    except Exception as e:
        print(f"Error al consultar MariaDB en AWS RDS: {e}")
        return None
    finally:
        if conn:
            conn.close()


# -------------------------------
# CONEXION A DYNAMODB
# -------------------------------
session = boto3.session.Session(
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("AWS_SECRET_KEY"),
    aws_session_token=os.getenv("AWS_SESSION_TOKEN"),
    region_name=os.getenv("AWS_REGION"),
)

dynamodb = session.resource("dynamodb")

tabla_mensajes = dynamodb.Table("MENSAJES_RUTA")
tabla_notificaciones = dynamodb.Table("NOTIFICACIONES_USUARIO")
tabla_posiciones = dynamodb.Table("POSICIONES_TIEMPO_REAL")

# -------------------------------
# FILTROS DYNAMODB
# -------------------------------
FILTRO_MENSAJES = Attr("id_ruta").between(1, 60) & Attr("leido").eq(False)
FILTRO_NOTIFICACIONES = Attr("leida").eq(False) & (
    Attr("tipo").eq("reserva_confirmada") | Attr("tipo").eq("recordatorio_salida")
)
FILTRO_POSICIONES = Attr("velocidad_kmh").between(
    Decimal("20.0"), Decimal("110.0")
) & Attr("id_usuario").gte(1)

DESCRIPCION_FILTRO_MENSAJES = "id_ruta entre 1 y 60 AND leido = False"
DESCRIPCION_FILTRO_NOTIFICACIONES = (
    "leida = False AND tipo IN ('reserva_confirmada', 'recordatorio_salida')"
)
DESCRIPCION_FILTRO_POSICIONES = (
    "velocidad_kmh entre 20.0 y 110.0 AND id_usuario >= 1"
)


# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================
def scan_completo(tabla, **kwargs):
    """Ejecuta un scan manejando la paginación con LastEvaluatedKey."""
    items = []
    while True:
        respuesta = tabla.scan(**kwargs)
        items.extend(respuesta.get("Items", []))
        if "LastEvaluatedKey" not in respuesta:
            break
        kwargs["ExclusiveStartKey"] = respuesta["LastEvaluatedKey"]
    return items


def metadatos_rds(enfoque, descripcion, filtro):
    """Construye el bloque de metadatos común de los informes RDS."""
    return {
        "motor": "MariaDB (AWS RDS)",
        "fecha_generacion": datetime.datetime.now().isoformat(),
        "enfoque_analitico": enfoque,
        "descripcion": descripcion,
        "filtros_aplicados": filtro,
    }


def metadatos_dynamodb(tabla, enfoque, descripcion, filtro):
    """Construye el bloque de metadatos común de los informes DynamoDB."""
    return {
        "motor": "Amazon DynamoDB",
        "tabla": tabla,
        "fecha_generacion": datetime.datetime.now().isoformat(),
        "enfoque_analitico": enfoque,
        "descripcion": descripcion,
        "filtros_aplicados": filtro,
    }


def resumen_por_clave(items, clave):
    """Devuelve un conteo de ítems agrupado por el valor de una clave."""
    conteo = {}
    for item in items:
        valor = str(item.get(clave))
        conteo[valor] = conteo.get(valor, 0) + 1
    return dict(sorted(conteo.items(), key=lambda entry: (-entry[1], entry[0])))


# =============================================================================
# 1. INFORME RDS: SOSTENIBILIDAD POR MODO DE TRANSPORTE (FILTRADO)
# =============================================================================
def analizar_sostenibilidad_rds():
    """Resumen de sostenibilidad limitado a modos de transporte sostenibles."""
    print(" Procesando informe RDS de sostenibilidad filtrado...")
    query = """
        SELECT
            h.modo_transporte,
            COUNT(h.id_desplazamiento) AS total_desplazamientos,
            ROUND(SUM(h.distancia_km), 2) AS distancia_total_km,
            ROUND(SUM(h.co2_ahorrado_kg), 3) AS co2_total_ahorrado_kg,
            ROUND(AVG(h.tiempo_minutos), 1) AS tiempo_promedio_minutos
        FROM HISTORIAL_DESPLAZAMIENTOS h
        WHERE h.modo_transporte IN ('Bicicleta', 'Autobus', 'Carpooling')
        GROUP BY h.modo_transporte
        ORDER BY total_desplazamientos DESC;
    """
    filas = ejecutar_consulta(query)
    if filas is None:
        return None

    return {
        "metadatos": metadatos_rds(
            "Sostenibilidad por Modo de Transporte (filtrado)",
            "Viajes, distancia, CO2 ahorrado y tiempo medio de los modos "
            "Bicicleta, Autobus y Carpooling.",
            "modo_transporte IN ('Bicicleta', 'Autobus', 'Carpooling')",
        ),
        "resumen_sostenibilidad_por_modo": filas,
    }


# =============================================================================
# 2. INFORME RDS: RUTAS DE CARPOOLING ACTIVAS
# =============================================================================
def analizar_carpooling_rds():
    """Resumen de carpooling limitado a rutas Programada o En_Curso."""
    print(" Procesando informe RDS de carpooling filtrado...")
    query = """
        SELECT
            r.estado AS estado_ruta,
            COUNT(DISTINCT r.id_ruta) AS total_rutas,
            SUM(r.plazas_disponibles) AS plazas_disponibles,
            COUNT(res.id_reserva) AS total_reservas
        FROM RUTAS_CARPOOLING r
        LEFT JOIN RESERVAS_CARPOOLING res ON r.id_ruta = res.id_ruta
        WHERE r.estado IN ('Programada', 'En_Curso')
        GROUP BY r.estado
        ORDER BY total_rutas DESC;
    """
    filas = ejecutar_consulta(query)
    if filas is None:
        return None

    return {
        "metadatos": metadatos_rds(
            "Rutas de Carpooling por Estado (filtrado)",
            "Rutas activas, plazas ofertadas y reservas asociadas.",
            "estado IN ('Programada', 'En_Curso')",
        ),
        "resumen_rutas_carpooling": filas,
    }


# =============================================================================
# 3. INFORME RDS: EVOLUCIÓN TEMPORAL RECIENTE
# =============================================================================
def analizar_desplazamientos_rds():
    """Evolución mensual de los desplazamientos de los últimos 12 meses."""
    print(" Procesando informe RDS de desplazamientos filtrado...")
    query = """
        SELECT
            DATE_FORMAT(h.fecha_desplazamiento, '%Y-%m') AS periodo_mes,
            COUNT(h.id_desplazamiento) AS total_desplazamientos,
            ROUND(SUM(h.distancia_km), 2) AS distancia_total_km,
            ROUND(SUM(h.co2_ahorrado_kg), 3) AS co2_total_ahorrado_kg
        FROM HISTORIAL_DESPLAZAMIENTOS h
        WHERE h.fecha_desplazamiento >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)
        GROUP BY DATE_FORMAT(h.fecha_desplazamiento, '%Y-%m')
        ORDER BY periodo_mes ASC;
    """
    filas = ejecutar_consulta(query)
    if filas is None:
        return None

    return {
        "metadatos": metadatos_rds(
            "Evolución Temporal Mensual de Desplazamientos (filtrado)",
            "Viajes, distancia y CO2 ahorrado de los últimos 12 meses.",
            "fecha_desplazamiento >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)",
        ),
        "evolucion_temporal_mensual": filas,
    }


# =============================================================================
# 4. INFORME DYNAMODB: MENSAJES DE RUTA NO LEÍDOS
# =============================================================================
def analizar_mensajes_dynamodb():
    """Mensajes no leídos de rutas 1..60."""
    print(" Procesando informe DynamoDB de mensajes filtrado...")
    try:
        mensajes = scan_completo(
            tabla_mensajes,
            FilterExpression=FILTRO_MENSAJES,
        )
    except Exception as e:
        print(f"Error al consultar MENSAJES_RUTA en DynamoDB: {e}")
        return None

    return {
        "metadatos": metadatos_dynamodb(
            "MENSAJES_RUTA",
            "Mensajes de chat pendientes de lectura",
            "Mensajes no leídos emitidos en rutas con id entre 1 y 60.",
            DESCRIPCION_FILTRO_MENSAJES,
        ),
        "total_mensajes_filtrados": len(mensajes),
        "resumen_por_ruta": resumen_por_clave(mensajes, "id_ruta"),
        "mensajes": mensajes,
    }


# =============================================================================
# 5. INFORME DYNAMODB: NOTIFICACIONES PENDIENTES RELEVANTES
# =============================================================================
def analizar_notificaciones_dynamodb():
    """Notificaciones no leídas de reserva confirmada o recordatorio de salida."""
    print(" Procesando informe DynamoDB de notificaciones filtrado...")
    try:
        notificaciones = scan_completo(
            tabla_notificaciones,
            FilterExpression=FILTRO_NOTIFICACIONES,
        )
    except Exception as e:
        print(f"Error al consultar NOTIFICACIONES_USUARIO en DynamoDB: {e}")
        return None

    return {
        "metadatos": metadatos_dynamodb(
            "NOTIFICACIONES_USUARIO",
            "Notificaciones pendientes de lectura",
            "Avisos no leídos de reserva confirmada o recordatorio de salida.",
            DESCRIPCION_FILTRO_NOTIFICACIONES,
        ),
        "total_notificaciones_filtradas": len(notificaciones),
        "resumen_por_tipo": resumen_por_clave(notificaciones, "tipo"),
        "notificaciones": notificaciones,
    }


# =============================================================================
# 6. INFORME DYNAMODB: POSICIONES EN RANGO DE VELOCIDAD
# =============================================================================
def resumen_velocidades(posiciones):
    """Calcula estadísticas básicas de velocidad sobre las posiciones filtradas."""
    velocidades = [
        item["velocidad_kmh"]
        for item in posiciones
        if isinstance(item.get("velocidad_kmh"), Decimal)
    ]
    if not velocidades:
        return {
            "velocidad_media_kmh": None,
            "velocidad_minima_kmh": None,
            "velocidad_maxima_kmh": None,
        }

    total = sum(velocidades)
    return {
        "velocidad_media_kmh": round(total / Decimal(len(velocidades)), 2),
        "velocidad_minima_kmh": min(velocidades),
        "velocidad_maxima_kmh": max(velocidades),
    }


def analizar_posiciones_dynamodb():
    """Posiciones de tiempo real con velocidad entre 20 y 110 km/h."""
    print(" Procesando informe DynamoDB de posiciones filtrado...")
    try:
        posiciones = scan_completo(
            tabla_posiciones,
            FilterExpression=FILTRO_POSICIONES,
        )
    except Exception as e:
        print(f"Error al consultar POSICIONES_TIEMPO_REAL en DynamoDB: {e}")
        return None

    return {
        "metadatos": metadatos_dynamodb(
            "POSICIONES_TIEMPO_REAL",
            "Telemetría de posiciones en movimiento",
            "Posiciones con velocidad entre 20 y 110 km/h de usuarios con id >= 1.",
            DESCRIPCION_FILTRO_POSICIONES,
        ),
        "total_posiciones_filtradas": len(posiciones),
        "estadisticas_velocidad": resumen_velocidades(posiciones),
        "posiciones": posiciones,
    }


# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================
def main():
    """Genera un único JSON con la información filtrada de RDS y DynamoDB."""
    ahora = datetime.datetime.now()
    nombre_carpeta = ahora.strftime("Date_%Y_%m_%d_Hour_%H-%M-%S")
    directorio_salida = BASE_DIR / "json_reports" / nombre_carpeta

    print("=" * 70)
    print(" INICIANDO INFORME JSON UNIFICADO DE AWS (RDS + DYNAMODB)")
    print(f" Directorio de salida: {directorio_salida}")
    print("=" * 70)

    informe = {
        "metadatos": {
            "generado_por": "python/aws/generate_reports.py",
            "fecha_generacion": ahora.isoformat(),
            "fuentes": ["MariaDB (AWS RDS)", "Amazon DynamoDB"],
            "archivo": "AWS_report.json",
        },
        "aws_rds": {},
        "aws_dynamodb": {},
        "errores": [],
    }

    tareas = [
        ("aws_rds", "sostenibilidad", "RDS/Sostenibilidad", analizar_sostenibilidad_rds),
        ("aws_rds", "carpooling", "RDS/Carpooling", analizar_carpooling_rds),
        ("aws_rds", "desplazamientos", "RDS/Desplazamientos", analizar_desplazamientos_rds),
        ("aws_dynamodb", "mensajes_ruta", "DynamoDB/MENSAJES_RUTA", analizar_mensajes_dynamodb),
        (
            "aws_dynamodb",
            "notificaciones_usuario",
            "DynamoDB/NOTIFICACIONES_USUARIO",
            analizar_notificaciones_dynamodb,
        ),
        (
            "aws_dynamodb",
            "posiciones_tiempo_real",
            "DynamoDB/POSICIONES_TIEMPO_REAL",
            analizar_posiciones_dynamodb,
        ),
    ]

    for seccion, clave, nombre, funcion_analisis in tareas:
        print(f"\n Procesando análisis para {nombre}...")
        datos = funcion_analisis()
        informe[seccion][clave] = datos
        if datos is None:
            informe["errores"].append(f"No se pudo generar el informe {nombre}.")

    hay_datos = any(
        dato is not None
        for seccion in ("aws_rds", "aws_dynamodb")
        for dato in informe[seccion].values()
    )

    if not hay_datos:
        print("\nNo se pudo generar el informe: ninguna fuente devolvió datos.")
        return

    directorio_salida.mkdir(parents=True, exist_ok=True)
    ruta_archivo = directorio_salida / "AWS_report.json"

    try:
        with open(ruta_archivo, "w", encoding="utf-8") as f:
            json.dump(
                informe,
                f,
                indent=4,
                ensure_ascii=False,
                default=serializador_json,
            )
    except Exception as e:
        print(f"Error al guardar el archivo JSON unificado: {e}")
        return

    print("\n" + "=" * 70)
    print(f"Informe unificado generado: {ruta_archivo}")
    if informe["errores"]:
        print(f"Se generó parcialmente. Incidencias: {len(informe['errores'])}")
        for error in informe["errores"]:
            print(f"  - {error}")
    else:
        print("Proceso finalizado con éxito: las 6 secciones se generaron correctamente.")
    print("=" * 70)


if __name__ == "__main__":
    main()
