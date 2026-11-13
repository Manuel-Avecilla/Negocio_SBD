"""
=============================================================================
SMARTRUTA & MOVILIDAD SOSTENIBLE - INFORMES JSON EN AWS RDS
=============================================================================
Script: generate_reports.py
Descripción:
    Se conecta exclusivamente a MariaDB en una instancia RDS de AWS y genera
    tres informes JSON independientes, manteniendo la misma estructura de
    carpetas, nombres de archivos y formato que generate_reports.py local.

    Cada informe ejecuta una consulta básica contra la base de datos de AWS,
    por lo que en total se realizan 3 consultas:

    1. AWS_RDS_sostenibilidad.json:
       - Resumen de sostenibilidad por modo de transporte.
    2. AWS_RDS_carpooling.json:
       - Resumen de rutas de carpooling por estado.
    3. AWS_RDS_desplazamientos.json:
       - Evolución temporal mensual de los desplazamientos.
=============================================================================
"""

import os
import json
import datetime
from decimal import Decimal
from pathlib import Path

import pymysql
import pymysql.cursors
from pymysql.constants import CLIENT
from dotenv import load_dotenv

# generate_reports.py -> RDS -> aws -> python -> Negocio_SBD
BASE_DIR = Path(__file__).resolve().parents[3]
DOCKER_DIR = BASE_DIR / "Docker"
ENV_PATH = DOCKER_DIR / ".env"

load_dotenv(ENV_PATH)

# -------------------------------
# PARAMETROS DE CONFIGURACION
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
    Función de apoyo para json.dumps para transformar tipos de datos no admitidos
    nativamente por la especificación JSON (fechas, horas, Decimales, etc.).
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


# =============================================================================
# 1. INFORME MYSQL: SOSTENIBILIDAD POR MODO DE TRANSPORTE
# =============================================================================
def analizar_sostenibilidad():
    """
    Consulta básica sobre HISTORIAL_DESPLAZAMIENTOS.
    Enfoque: viajes, distancia, CO2 ahorrado y tiempo medio por modo.
    """
    print(" Procesando informe de sostenibilidad...")
    query = """
        SELECT
            h.modo_transporte,
            COUNT(h.id_desplazamiento) AS total_desplazamientos,
            ROUND(SUM(h.distancia_km), 2) AS distancia_total_km,
            ROUND(SUM(h.co2_ahorrado_kg), 3) AS co2_total_ahorrado_kg,
            ROUND(AVG(h.tiempo_minutos), 1) AS tiempo_promedio_minutos
        FROM HISTORIAL_DESPLAZAMIENTOS h
        GROUP BY h.modo_transporte
        ORDER BY total_desplazamientos DESC;
    """
    filas = ejecutar_consulta(query)
    if filas is None:
        return None

    return {
        "metadatos": {
            "motor": "MariaDB (AWS RDS)",
            "fecha_generacion": datetime.datetime.now().isoformat(),
            "enfoque_analitico": "Sostenibilidad por Modo de Transporte",
            "descripcion": (
                "Resumen básico de desplazamientos, distancia acumulada, "
                "CO2 ahorrado y tiempo medio por modo de transporte."
            )
        },
        "resumen_sostenibilidad_por_modo": filas
    }


# =============================================================================
# 2. INFORME POSTGRESS: RUTAS DE CARPOOLING POR ESTADO
# =============================================================================
def analizar_carpooling():
    """
    Consulta básica sobre RUTAS_CARPOOLING y RESERVAS_CARPOOLING.
    Enfoque: rutas ofertadas, plazas disponibles y reservas por estado.
    """
    print(" Procesando informe de carpooling...")
    query = """
        SELECT
            r.estado AS estado_ruta,
            COUNT(DISTINCT r.id_ruta) AS total_rutas,
            SUM(r.plazas_disponibles) AS plazas_disponibles,
            COUNT(res.id_reserva) AS total_reservas
        FROM RUTAS_CARPOOLING r
        LEFT JOIN RESERVAS_CARPOOLING res ON r.id_ruta = res.id_ruta
        GROUP BY r.estado
        ORDER BY total_rutas DESC;
    """
    filas = ejecutar_consulta(query)
    if filas is None:
        return None

    return {
        "metadatos": {
            "motor": "MariaDB (AWS RDS)",
            "fecha_generacion": datetime.datetime.now().isoformat(),
            "enfoque_analitico": "Rutas de Carpooling por Estado",
            "descripcion": (
                "Resumen básico de rutas compartidas, plazas ofertadas "
                "y reservas asociadas según el estado de la ruta."
            )
        },
        "resumen_rutas_carpooling": filas
    }


# =============================================================================
# 3. INFORME MARIADB: EVOLUCIÓN TEMPORAL MENSUAL
# =============================================================================
def analizar_temporal():
    """
    Consulta básica sobre HISTORIAL_DESPLAZAMIENTOS.
    Enfoque: evolución mensual de viajes, distancia y CO2 ahorrado.
    """
    print(" Procesando informe temporal...")
    query = """
        SELECT
            DATE_FORMAT(h.fecha_desplazamiento, '%Y-%m') AS periodo_mes,
            COUNT(h.id_desplazamiento) AS total_desplazamientos,
            ROUND(SUM(h.distancia_km), 2) AS distancia_total_km,
            ROUND(SUM(h.co2_ahorrado_kg), 3) AS co2_total_ahorrado_kg
        FROM HISTORIAL_DESPLAZAMIENTOS h
        GROUP BY DATE_FORMAT(h.fecha_desplazamiento, '%Y-%m')
        ORDER BY periodo_mes ASC;
    """
    filas = ejecutar_consulta(query)
    if filas is None:
        return None

    return {
        "metadatos": {
            "motor": "MariaDB (AWS RDS)",
            "fecha_generacion": datetime.datetime.now().isoformat(),
            "enfoque_analitico": "Evolución Temporal Mensual de Desplazamientos",
            "descripcion": (
                "Resumen básico mensual de desplazamientos, distancia "
                "acumulada y CO2 ahorrado en la base de datos de AWS."
            )
        },
        "evolucion_temporal_mensual": filas
    }


# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================
def main():
    """
    Orquesta la ejecución de las 3 consultas básicas contra MariaDB en AWS RDS
    y la persistencia de los informes JSON en una carpeta timestamped.
    """
    # 1. Definición de la carpeta de destino: json_reports/Date_YYYY_MM_DD_Hour_HH-MM-SS
    ahora = datetime.datetime.now()
    nombre_carpeta = ahora.strftime("Date_%Y_%m_%d_Hour_%H-%M-%S")
    directorio_salida = BASE_DIR / "json_reports" / nombre_carpeta

    print("=" * 70)
    print(" INICIANDO GENERACIÓN DE INFORMES ANALÍTICOS EN AWS RDS")
    print(f" Directorio de salida: {directorio_salida}")
    print("=" * 70)

    # 2. Ejecutar los tres análisis independientes sobre MariaDB RDS
    tareas = [
        ("Sostenibilidad", "AWS_RDS_sostenibilidad.json", analizar_sostenibilidad),
        ("Carpooling", "AWS_RDS_carpooling.json", analizar_carpooling),
        ("Temporal", "AWS_RDS_desplazamientos.json", analizar_temporal)
    ]

    informes_generados = 0
    directorio_creado = False

    for nombre_informe, archivo_salida, funcion_analisis in tareas:
        print(f"\n Procesando análisis para {nombre_informe}...")
        datos = funcion_analisis()

        if datos is not None:
            # Crear directorio únicamente si hay al menos un informe generado con éxito
            if not directorio_creado:
                directorio_salida.mkdir(parents=True, exist_ok=True)
                directorio_creado = True

            ruta_archivo = directorio_salida / archivo_salida
            try:
                with open(ruta_archivo, "w", encoding="utf-8") as f:
                    json.dump(datos, f, indent=4, ensure_ascii=False, default=serializador_json)
                print(f"Archivo generado: {ruta_archivo}")
                informes_generados += 1
            except Exception as e:
                print(f"Error al guardar archivo JSON para {nombre_informe}: {e}")
        else:
            print(f"No se pudo generar el informe para {nombre_informe}.")

    print("\n" + "=" * 70)
    if informes_generados == len(tareas):
        print(f" Proceso finalizado con éxito. Los 3 informes se han generado en:\n  {directorio_salida}")
    else:
        print(f"Proceso finalizado parcialmente: {informes_generados}/{len(tareas)} informes generados.")
    print("=" * 70)


if __name__ == "__main__":
    main()
