"""
=============================================================================
SMARTRUTA & MOVILIDAD SOSTENIBLE - ANÁLISIS DE DATOS E INFORMES JSON
=============================================================================
Script: generate_reports.py
Descripción:
    Se conecta a las 3 bases de datos del sistema (MySQL, PostgreSQL y MariaDB),
    ejecuta consultas analíticas avanzadas con JOINs y agregaciones que explotan
    los datos generados y genera tres informes JSON complementarios e independientes
    en el directorio raíz json_info/Date_YYYY_MM_DD_Hour_HH-MM-SS/.

Enfoques de los informes:
    1. MySQL (mysql.json):
       - Sostenibilidad Global, Impacto Ambiental y Distribución Modal.
       - KPIs generales de movilidad, huella de carbono por modo y perfil de usuario,
         distribución del parque vehicular y compromiso ecológico por barrio/zona.
    2. PostgreSQL (postgress.json):
       - Red de Carpooling, Eficiencia Operativa y Dinámica de Usuarios.
       - Conversión y estado de rutas compartidas, ranking de conductores líderes,
         comportamiento de pasajeros y telemetría de velocidades GPS.
    3. MariaDB (mariadb.json):
       - Tendencias Temporales, Factores Externos (Clima/Incidencias) y Encuestas.
       - Evolución mensual de desplazamientos, distribución de incidencias de tráfico,
         percepción de hábitos de movilidad en encuestas y condiciones meteorológicas.
=============================================================================
"""

import os
import json
import datetime
from decimal import Decimal
from pathlib import Path
import pymysql
import pymysql.cursors
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv


# --- LOCALIZACIÓN Y CARGA DE VARIABLES DE ENTORNO ---
BASE_DIR = Path(__file__).resolve().parent.parent

# Soporte para directorio Docker tanto en mayúscula como minúscula
env_path = BASE_DIR / "Docker" / ".env"
if not env_path.exists():
    env_path = BASE_DIR / "docker" / ".env"

load_dotenv(dotenv_path=env_path)

# Variables generales / compartidas con valores por defecto
SHARED_PASS = os.getenv("SHARED_PASSWORD", "smartruta_pass_123")
DB_NAME_DEFAULT = os.getenv("MYSQL_DATABASE", "smartruta_db")
DB_USER_DEFAULT = os.getenv("MYSQL_USER", "smartruta_user")

# Configuración de conexiones
CONFIG_MYSQL = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", 3306)),
    "user": os.getenv("MYSQL_USER", DB_USER_DEFAULT),
    "password": os.getenv("MYSQL_PASSWORD", SHARED_PASS),
    "database": os.getenv("MYSQL_DATABASE", DB_NAME_DEFAULT),
    "cursorclass": pymysql.cursors.DictCursor
}

CONFIG_POSTGRES = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", 5432)),
    "user": os.getenv("POSTGRES_USER", DB_USER_DEFAULT),
    "password": os.getenv("POSTGRES_PASSWORD", SHARED_PASS),
    "dbname": os.getenv("POSTGRES_DB", DB_NAME_DEFAULT)
}

CONFIG_MARIADB = {
    "host": os.getenv("MARIADB_HOST", "localhost"),
    "port": int(os.getenv("MARIADB_PORT", 3307)),
    "user": os.getenv("MARIADB_USER", os.getenv("MYSQL_USER", DB_USER_DEFAULT)),
    "password": os.getenv("MARIADB_PASSWORD", os.getenv("MYSQL_PASSWORD", SHARED_PASS)),
    "database": os.getenv("MARIADB_DATABASE", os.getenv("MYSQL_DATABASE", DB_NAME_DEFAULT)),
    "cursorclass": pymysql.cursors.DictCursor
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


# =============================================================================
# 1. ANÁLISIS MYSQL: SOSTENIBILIDAD, HUELLA DE CARBONO Y DISTRIBUCIÓN MODAL
# =============================================================================
def analizar_mysql():
    """
    Ejecuta el análisis sobre la base de datos MySQL.
    Enfoque: Visión global de sostenibilidad, ahorro de emisiones CO2,
    distribución del parque de vehículos sostenibles y comportamiento por barrios.
    """
    print(" Conectando a MySQL (puerto 3306)...")
    conn = None
    try:
        conn = pymysql.connect(**CONFIG_MYSQL)
        with conn.cursor() as cursor:
            # Consulta 1: Indicadores macro de sostenibilidad y desplazamientos
            query_kpis = """
                SELECT 
                    COUNT(DISTINCT h.id_usuario) AS usuarios_activos_desplazamientos,
                    COUNT(h.id_desplazamiento) AS total_desplazamientos,
                    ROUND(SUM(h.distancia_km), 2) AS distancia_total_km,
                    ROUND(AVG(h.distancia_km), 2) AS distancia_media_km,
                    ROUND(SUM(h.co2_ahorrado_kg), 3) AS co2_total_ahorrado_kg,
                    ROUND(AVG(h.co2_ahorrado_kg), 3) AS co2_promedio_por_viaje_kg,
                    ROUND(AVG(h.tiempo_minutos), 1) AS tiempo_promedio_minutos
                FROM HISTORIAL_DESPLAZAMIENTOS h;
            """
            cursor.execute(query_kpis)
            kpis_generales = cursor.fetchone()

            # Consulta 2: Desempeño ecológico y adopción modal por perfil de usuario
            query_modal = """
                SELECT 
                    h.modo_transporte,
                    u.tipo_usuario,
                    COUNT(h.id_desplazamiento) AS total_viajes,
                    ROUND(SUM(h.distancia_km), 2) AS distancia_acumulada_km,
                    ROUND(SUM(h.co2_ahorrado_kg), 3) AS co2_ahorrado_kg,
                    ROUND(AVG(h.co2_ahorrado_kg), 3) AS promedio_co2_ahorrado_kg,
                    ROUND(AVG(h.tiempo_minutos), 1) AS tiempo_medio_minutos
                FROM HISTORIAL_DESPLAZAMIENTOS h
                JOIN USUARIOS u ON h.id_usuario = u.id_usuario
                GROUP BY h.modo_transporte, u.tipo_usuario
                ORDER BY total_viajes DESC;
            """
            cursor.execute(query_modal)
            desglose_modal_usuario = cursor.fetchall()

            # Consulta 3: Distribución del parque vehicular según tipo de propulsión y propietario
            query_vehiculos = """
                SELECT 
                    v.tipo_propulsion,
                    u.tipo_usuario AS perfil_propietario,
                    COUNT(v.id_vehiculo) AS total_vehiculos,
                    SUM(v.plazas_totales) AS plazas_totales_disponibles,
                    ROUND(AVG(v.plazas_totales), 1) AS promedio_plazas_por_vehiculo
                FROM VEHICULOS v
                JOIN USUARIOS u ON v.id_propietario = u.id_usuario
                GROUP BY v.tipo_propulsion, u.tipo_usuario
                ORDER BY total_vehiculos DESC;
            """
            cursor.execute(query_vehiculos)
            distribucion_vehiculos = cursor.fetchall()

            # Consulta 4: Compromiso ecológico y actividad por zona geográfica (Barrio / Código Postal)
            query_zonas = """
                SELECT 
                    d.barrio_zona,
                    d.codigo_postal,
                    COUNT(DISTINCT u.id_usuario) AS residentes_registrados,
                    COUNT(h.id_desplazamiento) AS desplazamientos_registrados,
                    ROUND(SUM(h.distancia_km), 2) AS km_totales_recorridos,
                    ROUND(SUM(h.co2_ahorrado_kg), 3) AS co2_total_ahorrado_kg
                FROM DIRECCIONES d
                JOIN USUARIOS u ON d.id_direccion = u.id_direccion
                JOIN HISTORIAL_DESPLAZAMIENTOS h ON u.id_usuario = h.id_usuario
                GROUP BY d.barrio_zona, d.codigo_postal
                ORDER BY co2_total_ahorrado_kg DESC
                LIMIT 10;
            """
            cursor.execute(query_zonas)
            top_zonas_sostenibles = cursor.fetchall()

            informe = {
                "metadatos": {
                    "motor": "MySQL",
                    "fecha_generacion": datetime.datetime.now().isoformat(),
                    "enfoque_analitico": "Sostenibilidad Global, Impacto Ambiental y Distribución Modal",
                    "descripcion": (
                        "Indicadores clave de movilidad ecológica, ahorro acumulado de emisiones CO2, "
                        "patrones de desplazamiento por rol de usuario y análisis geográfico por zonas."
                    )
                },
                "resumen_ejecutivo_sostenibilidad": kpis_generales,
                "adopcion_modal_por_perfil_usuario": desglose_modal_usuario,
                "distribucion_parque_vehicular": distribucion_vehiculos,
                "top_10_zonas_mayor_impacto_ecologico": top_zonas_sostenibles
            }
            return informe

    except Exception as e:
        print(f"Error al consultar MySQL: {e}")
        return None
    finally:
        if conn:
            conn.close()


# =============================================================================
# 2. ANÁLISIS POSTGRESQL: RED DE CARPOOLING, EFICIENCIA Y DINÁMICA DE USUARIOS
# =============================================================================
def analizar_postgres():
    """
    Ejecuta el análisis sobre la base de datos PostgreSQL.
    Enfoque: Eficiencia de la red de viajes compartidos (carpooling),
    tasas de ocupación y éxito en reservas, ranking de conductores y telemetría GPS.
    """
    print(" Conectando a PostgreSQL (puerto 5432)...")
    conn = None
    try:
        conn = psycopg2.connect(**CONFIG_POSTGRES)
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            # Consulta 1: Rendimiento y conversión de rutas según estado y tecnología vehicular
            query_rutas = """
                SELECT 
                    r.estado AS estado_ruta,
                    v.tipo_propulsion,
                    COUNT(DISTINCT r.id_ruta) AS total_rutas_ofertadas,
                    SUM(r.plazas_disponibles) AS plazas_totales_disponibles,
                    COUNT(res.id_reserva) AS total_solicitudes_reserva,
                    COUNT(CASE WHEN res.estado_reserva = 'Confirmada' THEN 1 END) AS reservas_confirmadas,
                    COUNT(CASE WHEN res.estado_reserva = 'Pendiente' THEN 1 END) AS reservas_pendientes,
                    COUNT(CASE WHEN res.estado_reserva = 'Cancelada' THEN 1 END) AS reservas_canceladas,
                    COUNT(CASE WHEN res.estado_reserva = 'Rechazada' THEN 1 END) AS reservas_rechazadas
                FROM RUTAS_CARPOOLING r
                JOIN VEHICULOS v ON r.id_vehiculo = v.id_vehiculo
                LEFT JOIN RESERVAS_CARPOOLING res ON r.id_ruta = res.id_ruta
                GROUP BY r.estado, v.tipo_propulsion
                ORDER BY total_rutas_ofertadas DESC;
            """
            cursor.execute(query_rutas)
            rendimiento_rutas = [dict(r) for r in cursor.fetchall()]

            # Consulta 2: Ranking de conductores más activos y fiables
            query_conductores = """
                SELECT 
                    u.id_usuario AS id_conductor,
                    u.nombre AS nombre_conductor,
                    u.tipo_usuario AS perfil_usuario,
                    COUNT(DISTINCT r.id_ruta) AS total_rutas_publicadas,
                    SUM(r.plazas_disponibles) AS plazas_ofertadas_acumuladas,
                    COUNT(res.id_reserva) AS total_reservas_recibidas,
                    COUNT(CASE WHEN res.estado_reserva = 'Confirmada' THEN 1 END) AS reservas_confirmadas
                FROM USUARIOS u
                JOIN RUTAS_CARPOOLING r ON u.id_usuario = r.id_conductor
                LEFT JOIN RESERVAS_CARPOOLING res ON r.id_ruta = res.id_ruta
                GROUP BY u.id_usuario, u.nombre, u.tipo_usuario
                ORDER BY total_rutas_publicadas DESC, reservas_confirmadas DESC
                LIMIT 10;
            """
            cursor.execute(query_conductores)
            top_conductores = [dict(r) for r in cursor.fetchall()]

            # Consulta 3: Demanda y comportamiento de pasajeros por categoría
            query_pasajeros = """
                SELECT 
                    u.tipo_usuario AS perfil_pasajero,
                    res.estado_reserva,
                    COUNT(res.id_reserva) AS total_solicitudes,
                    COUNT(DISTINCT res.id_pasajero) AS pasajeros_unicos,
                    COUNT(DISTINCT res.id_ruta) AS rutas_distintas_solicitadas
                FROM RESERVAS_CARPOOLING res
                JOIN USUARIOS u ON res.id_pasajero = u.id_usuario
                JOIN RUTAS_CARPOOLING r ON res.id_ruta = r.id_ruta
                GROUP BY u.tipo_usuario, res.estado_reserva
                ORDER BY perfil_pasajero, total_solicitudes DESC;
            """
            cursor.execute(query_pasajeros)
            demanda_pasajeros = [dict(r) for r in cursor.fetchall()]

            # Consulta 4: Telemetría GPS y análisis de velocidades operativas
            query_gps = """
                SELECT 
                    r.estado AS estado_ruta,
                    COUNT(g.id_registro_gps) AS total_muestras_gps,
                    COUNT(DISTINCT g.id_usuario) AS usuarios_rastreados,
                    ROUND(CAST(AVG(g.velocidad_kmh) AS NUMERIC), 2) AS velocidad_media_kmh,
                    ROUND(CAST(MAX(g.velocidad_kmh) AS NUMERIC), 2) AS velocidad_maxima_kmh
                FROM REGISTROS_GPS g
                JOIN RUTAS_CARPOOLING r ON g.id_ruta = r.id_ruta
                GROUP BY r.estado
                ORDER BY total_muestras_gps DESC;
            """
            cursor.execute(query_gps)
            telemetria_gps = [dict(r) for r in cursor.fetchall()]

            informe = {
                "metadatos": {
                    "motor": "PostgreSQL",
                    "fecha_generacion": datetime.datetime.now().isoformat(),
                    "enfoque_analitico": "Red de Carpooling, Dinámica de Usuarios y Eficiencia Operativa",
                    "descripcion": (
                        "Evaluación del servicio de viajes compartidos: balance oferta-demanda, "
                        "tasas de éxito de reservas, ranking de conductores líderes y telemetría de rutas."
                    )
                },
                "eficiencia_rutas_y_vehiculos": rendimiento_rutas,
                "ranking_top_10_conductores": top_conductores,
                "comportamiento_demanda_pasajeros": demanda_pasajeros,
                "monitoreo_velocidades_gps": telemetria_gps
            }
            return informe

    except Exception as e:
        print(f"Error al consultar PostgreSQL: {e}")
        return None
    finally:
        if conn:
            conn.close()


# =============================================================================
# 3. ANÁLISIS MARIADB: TENDENCIAS TEMPORALES, FACTORES EXTERNOS Y ENCUESTAS
# =============================================================================
def analizar_mariadb():
    """
    Ejecuta el análisis sobre la base de datos MariaDB.
    Enfoque: Dinámica temporal de desplazamientos, incidencias de tráfico,
    percepción ciudadana en encuestas de hábitos y registros meteorológicos.
    """
    print(" Conectando a MariaDB (puerto 3307)...")
    conn = None
    try:
        conn = pymysql.connect(**CONFIG_MARIADB)
        with conn.cursor() as cursor:
            # Consulta 1: Evolución mensual de desplazamientos y emisiones evitadas
            query_temporal = """
                SELECT 
                    DATE_FORMAT(h.fecha_desplazamiento, '%Y-%m') AS periodo_mes,
                    h.modo_transporte,
                    COUNT(h.id_desplazamiento) AS total_viajes,
                    ROUND(SUM(h.distancia_km), 2) AS distancia_total_km,
                    ROUND(SUM(h.co2_ahorrado_kg), 3) AS co2_ahorrado_kg,
                    ROUND(AVG(h.tiempo_minutos), 1) AS tiempo_promedio_min
                FROM HISTORIAL_DESPLAZAMIENTOS h
                JOIN USUARIOS u ON h.id_usuario = u.id_usuario
                GROUP BY DATE_FORMAT(h.fecha_desplazamiento, '%Y-%m'), h.modo_transporte
                ORDER BY periodo_mes ASC, total_viajes DESC;
            """
            cursor.execute(query_temporal)
            tendencias_mensuales = cursor.fetchall()

            # Consulta 2: Severidad y tipos de incidencias en la infraestructura vial
            query_incidencias = """
                SELECT 
                    i.tipo_incidencia,
                    i.nivel_gravedad,
                    COUNT(i.id_incidencia) AS total_incidencias,
                    COUNT(DISTINCT i.fuente_dato) AS fuentes_reporte_distintas
                FROM INCIDENCIAS_TRAFICO i
                GROUP BY i.tipo_incidencia, i.nivel_gravedad
                ORDER BY total_incidencias DESC;
            """
            cursor.execute(query_incidencias)
            analisis_incidencias = cursor.fetchall()

            # Consulta 3: Resultados de encuestas de movilidad y percepción de tiempos
            query_encuestas = """
                SELECT 
                    e.id_encuesta,
                    e.titulo AS titulo_encuesta,
                    r.modo_habitual,
                    COUNT(r.id_respuesta) AS total_respuestas,
                    ROUND(AVG(r.tiempo_medio_min), 1) AS tiempo_medio_estimado_min,
                    MIN(r.tiempo_medio_min) AS tiempo_minimo_min,
                    MAX(r.tiempo_medio_min) AS tiempo_maximo_min
                FROM ENCUESTAS_HABITOS e
                JOIN RESPUESTAS_ENCUESTA r ON e.id_encuesta = r.id_encuesta
                GROUP BY e.id_encuesta, e.titulo, r.modo_habitual
                ORDER BY e.id_encuesta ASC, total_respuestas DESC;
            """
            cursor.execute(query_encuestas)
            resultados_encuestas = cursor.fetchall()

            # Consulta 4: Caracterización de condiciones meteorológicas
            query_clima = """
                SELECT 
                    m.estado_tiempo,
                    COUNT(m.id_clima) AS total_registros_clima,
                    ROUND(AVG(m.temperatura_c), 1) AS temperatura_media_c,
                    ROUND(MIN(m.temperatura_c), 1) AS temperatura_minima_c,
                    ROUND(MAX(m.temperatura_c), 1) AS temperatura_maxima_c,
                    ROUND(AVG(m.precipitacion_mm), 2) AS precipitacion_media_mm,
                    ROUND(SUM(m.precipitacion_mm), 2) AS precipitacion_total_mm
                FROM REGISTRO_METEOROLOGICO m
                GROUP BY m.estado_tiempo
                ORDER BY total_registros_clima DESC;
            """
            cursor.execute(query_clima)
            condiciones_clima = cursor.fetchall()

            informe = {
                "metadatos": {
                    "motor": "MariaDB",
                    "fecha_generacion": datetime.datetime.now().isoformat(),
                    "enfoque_analitico": "Evolución Temporal, Condiciones Operativas y Encuestas Ciudadanas",
                    "descripcion": (
                        "Tendencias mensuales de movilidad, afecciones viales por incidencias, "
                        "hábitos declarados en encuestas y análisis de variables meteorológicas."
                    )
                },
                "evolucion_temporal_mensual": tendencias_mensuales,
                "impacto_incidencias_viales": analisis_incidencias,
                "percepcion_ciudadana_encuestas": resultados_encuestas,
                "registro_condiciones_meteorologicas": condiciones_clima
            }
            return informe

    except Exception as e:
        print(f"Error al consultar MariaDB: {e}")
        return None
    finally:
        if conn:
            conn.close()


# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================
def main():
    """
    Orquesta la ejecución de los análisis en las tres bases de datos
    y la persistencia en formato JSON dentro de una carpeta timestamped.
    """
    # 1. Definición de la carpeta de destino: json_info/Date_YYYY_MM_DD_Hour_HH-MM-SS
    ahora = datetime.datetime.now()
    nombre_carpeta = ahora.strftime("Date_%Y_%m_%d_Hour_%H-%M-%S")
    directorio_salida = BASE_DIR / "json_reports" / nombre_carpeta

    print("=" * 70)
    print(" INICIANDO GENERACIÓN DE INFORMES ANALÍTICOS")
    print(f" Directorio de salida: {directorio_salida}")
    print("=" * 70)

    # 2. Ejecutar análisis independientes
    tareas = [
        ("MySQL", "mysql.json", analizar_mysql),
        ("PostgreSQL", "postgress.json", analizar_postgres),
        ("MariaDB", "mariadb.json", analizar_mariadb)
    ]

    informes_generados = 0
    directorio_creado = False

    for nombre_motor, archivo_salida, funcion_analisis in tareas:
        print(f"\n Procesando análisis para {nombre_motor}...")
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
                print(f"Error al guardar archivo JSON para {nombre_motor}: {e}")
        else:
            print(f"No se pudo generar el informe para {nombre_motor}.")

    print("\n" + "=" * 70)
    if informes_generados == len(tareas):
        print(f" Proceso finalizado con éxito. Los 3 informes se han generado en:\n  {directorio_salida}")
    else:
        print(f"Proceso finalizado parcialmente: {informes_generados}/{len(tareas)} informes generados.")
    print("=" * 70)


if __name__ == "__main__":
    main()
