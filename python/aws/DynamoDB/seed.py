"""
=============================================================================
SMARTRUTA & MOVILIDAD SOSTENIBLE - POBLADO DE DATOS EN AWS DYNAMODB (seed.py)
=============================================================================

PROVIDERS / MÉTODOS DE FAKER UTILIZADOS EN ESTE SCRIPT:
1.  Provider Lorem:          fake.sentence()                -> Textos de mensajes y notificaciones
2.  Provider Date/Time:      fake.date_time_this_year(), fake.date_time_between() -> Marcas de tiempo
3.  Provider Geo:            fake.latitude(), fake.longitude()   -> Punto de partida de las rutas en directo
4.  Provider Python / Bool:  fake.boolean()                 -> Estado leido / no leido

TABLAS QUE SE POBLAN (50 registros por tabla):
- MENSAJES_RUTA            (50 registros - sin índices)
- NOTIFICACIONES_USUARIO   (50 registros - con LSI_usuario_tipo)
- POSICIONES_TIEMPO_REAL   (50 registros: 5 rutas x 10 posiciones - con GSI_usuario_tiempo)

Los ids (id_ruta 1-60, id_usuario 1-100) usan los mismos rangos que el seed de RDS.
=============================================================================
"""

import os
import random
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import boto3
from dotenv import load_dotenv
from faker import Faker

# Inicializar Faker en español
fake = Faker("es_ES")

# seed.py -> DynamoDB -> aws -> python -> Negocio_SBD
BASE_DIR = Path(__file__).resolve().parents[3]
DOCKER_DIR = BASE_DIR / "Docker"
ENV_PATH = DOCKER_DIR / ".env"

load_dotenv(ENV_PATH)

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

# Rangos de ids de la base de datos relacional (ver seed.py de RDS)
NUM_USUARIOS = 100
NUM_RUTAS = 60
REGISTROS_POR_TABLA = 50

SEGUNDOS_DIA = 24 * 60 * 60


# -------------------------------
# FUNCIONES AUXILIARES
# -------------------------------

def iso_utc(fecha):
    """Convierte un datetime a ISO 8601 UTC (ordenable como texto)."""
    return fecha.strftime("%Y-%m-%dT%H:%M:%SZ")


def decimal(valor, decimales):
    """DynamoDB no admite float: los numeros decimales se guardan como Decimal."""
    return Decimal(str(round(valor, decimales)))


def insertar_items(nombre_tabla, items, claves):
    """
    Inserta los items en bloque con batch_writer (agrupa de 25 en 25 y reintenta
    los pendientes). 'claves' evita errores si dos items repiten la misma clave.
    """
    tabla = dynamodb.Table(nombre_tabla)
    with tabla.batch_writer(overwrite_by_pkeys=claves) as batch:
        for item in items:
            batch.put_item(Item=item)
    print(f"{nombre_tabla}: {len(items)} registros enviados")


def poblar_base_de_datos():
    print("Generando datos sintéticos e insertando en DynamoDB...")

    try:
        ahora = datetime.now(timezone.utc)
        ahora_epoch = int(time.time())

        # 1. MENSAJES_RUTA (50 registros - Tabla base sin LSI ni GSI)
        datos_mensajes = [
            {
                "id_ruta": random.randint(1, NUM_RUTAS),                                # PK -> RUTAS_CARPOOLING
                "marca_tiempo": iso_utc(fake.date_time_this_year(tzinfo=timezone.utc)), # SK - Provider: Date/Time
                "id_usuario_emisor": random.randint(1, NUM_USUARIOS),                   # -> USUARIOS
                "texto": fake.sentence(nb_words=10),                                    # Provider: Lorem
                "leido": fake.boolean(chance_of_getting_true=70),                       # Provider: Python/Bool
            }
            for _ in range(REGISTROS_POR_TABLA)
        ]
        insertar_items("MENSAJES_RUTA", datos_mensajes, ["id_ruta", "marca_tiempo"])

        # 2. NOTIFICACIONES_USUARIO (50 registros - Tabla con LSI_usuario_tipo)
        tipos_notificacion = [
            "reserva_confirmada",
            "reserva_rechazada",
            "ruta_cancelada",
            "incidencia_trafico",
            "recordatorio_salida",
        ]
        datos_notificaciones = []
        for _ in range(REGISTROS_POR_TABLA):
            tipo = random.choice(tipos_notificacion)
            notificacion = {
                "id_usuario": random.randint(1, NUM_USUARIOS),                          # PK (base y LSI) -> USUARIOS
                "marca_tiempo": iso_utc(fake.date_time_this_year(tzinfo=timezone.utc)), # SK (base) - Provider: Date/Time
                "tipo": tipo,                                                           # SK (LSI_usuario_tipo) - siempre String
                "mensaje": fake.sentence(nb_words=8),                                   # Provider: Lorem
                "leida": fake.boolean(chance_of_getting_true=60),                       # Provider: Python/Bool
                # TTL: se calcula desde AHORA (si fuera una fecha pasada, DynamoDB la borraria enseguida)
                "expira_en": ahora_epoch + random.randint(7, 30) * SEGUNDOS_DIA,
            }
            # Las incidencias de trafico no estan ligadas a una ruta concreta
            if tipo != "incidencia_trafico":
                notificacion["id_ruta"] = random.randint(1, NUM_RUTAS)
            datos_notificaciones.append(notificacion)
        insertar_items("NOTIFICACIONES_USUARIO", datos_notificaciones, ["id_usuario", "marca_tiempo"])

        # 3. POSICIONES_TIEMPO_REAL (5 rutas x 10 posiciones = 50 registros - Tabla con GSI_usuario_tiempo)
        num_rutas_activas = 5
        puntos_por_ruta = REGISTROS_POR_TABLA // num_rutas_activas  # 10 posiciones por ruta
        segundos_entre_puntos = 30

        rutas_en_curso = random.sample(range(1, NUM_RUTAS + 1), num_rutas_activas)
        conductores_activos = random.sample(range(1, NUM_USUARIOS + 1), num_rutas_activas)

        datos_posiciones = []
        for id_ruta, id_conductor in zip(rutas_en_curso, conductores_activos):
            latitud = float(fake.latitude())    # Provider: Geo
            longitud = float(fake.longitude())  # Provider: Geo
            # Cada ruta avanza en una direccion fija con un poco de ruido
            avance_lat = random.uniform(-0.0004, 0.0004)
            avance_lon = random.uniform(-0.0004, 0.0004)

            for i in range(puntos_por_ruta):
                latitud += avance_lat + random.uniform(-0.0001, 0.0001)
                longitud += avance_lon + random.uniform(-0.0001, 0.0001)
                momento = ahora - timedelta(seconds=(puntos_por_ruta - i) * segundos_entre_puntos)

                datos_posiciones.append({
                    "id_ruta": id_ruta,                                        # PK (base) -> RUTAS_CARPOOLING
                    "marca_tiempo": iso_utc(momento),                          # SK (base y GSI_usuario_tiempo)
                    "id_usuario": id_conductor,                                # PK (GSI_usuario_tiempo) -> USUARIOS
                    "latitud": decimal(latitud, 6),
                    "longitud": decimal(longitud, 6),
                    "velocidad_kmh": decimal(random.uniform(10.0, 120.0), 2),
                    "expira_en": ahora_epoch + SEGUNDOS_DIA,                   # TTL: 24 h desde ahora
                })
        insertar_items("POSICIONES_TIEMPO_REAL", datos_posiciones, ["id_ruta", "marca_tiempo"])

        print("Poblado completado con éxito en DynamoDB.")

    except Exception as e:
        print(f"Error durante el poblado de DynamoDB: {e}")
        raise


if __name__ == "__main__":
    poblar_base_de_datos()