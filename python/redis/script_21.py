# 21 - Obtén datos de alguna de las bases de datos de la tarea anterior mediante una sql e incluyelos en Redis(1 punto)
"""
Importa datos desde MySQL (una de las bases de datos de la tarea anterior) a Redis.

Flujo del script:
    1. Se conecta a MySQL y ejecuta una consulta SQL con JOIN entre USUARIOS y
       DIRECCIONES.
    2. Guarda cada fila en Redis como un hash independiente.
    3. Guarda además el conjunto completo como JSON (RedisJSON si está
       disponible o como cadena JSON en caso contrario).
    4. Registra una clave de metadatos con información de la importación.

Las claves que genera este script son las que consume posteriormente
script_22.py para realizar el camino inverso Redis -> SQL.
"""

import json
import os
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path

import pymysql
import pymysql.cursors
from pymysql.constants import CLIENT
import redis
from dotenv import load_dotenv
from redis.exceptions import ResponseError


# Cargar .env desde la carpeta Docker/
BASE_DIR = Path(__file__).resolve().parent.parent.parent
env_path = BASE_DIR / "Docker" / ".env"
load_dotenv(dotenv_path=env_path)

# Variables generales
SHARED_DB_USER = os.getenv("SHARED_DB_USER")
SHARED_DB_PASSWORD = os.getenv("SHARED_DB_PASSWORD")

CONFIG_MYSQL = {
    "host": "localhost",
    "port": 3306,
    "user": SHARED_DB_USER,
    "password": SHARED_DB_PASSWORD,
    "database": os.getenv("MYSQL_DB_NAME"),
    "cursorclass": pymysql.cursors.DictCursor,
    "client_flag": CLIENT.MULTI_STATEMENTS  # Permite ejecutar el bloque SQL completo
}

# --- CONFIGURACIÓN DE REDIS (DESTINO DE LOS DATOS) ---
conexionRedis = redis.ConnectionPool(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=int(os.getenv("REDIS_DB", 0)),
    decode_responses=True
)
baseDatosRedis = redis.Redis(connection_pool=conexionRedis)


# --- CLAVES QUE SE CREARÁN EN REDIS ---
PREFIJO_USUARIO = "smartruta:mysql:usuario:"
CLAVE_INDICE_IDS = "smartruta:mysql:usuarios:ids"
CLAVE_JSON = "smartruta:mysql:usuarios_json"
CLAVE_METADATOS = "smartruta:mysql:importacion"


# --- CONSULTA SQL DE ORIGEN ---
SQL_USUARIOS = """
    SELECT
        u.id_usuario,
        u.nombre,
        u.email,
        u.tipo_usuario,
        u.consentimiento_rgpd,
        u.fecha_registro,
        d.codigo_postal,
        d.barrio_zona
    FROM USUARIOS u
    LEFT JOIN DIRECCIONES d ON u.id_direccion = d.id_direccion
    ORDER BY u.id_usuario ASC;
"""


def normalizar_para_json(valor):
    """Convierte tipos de MySQL no serializables a tipos admitidos por JSON."""
    if isinstance(valor, (datetime, date, time)):
        return valor.isoformat()
    if isinstance(valor, Decimal):
        return float(valor)
    if isinstance(valor, (bytes, bytearray)):
        # Las columnas BIT(n) llegan desde pymysql como bytes.
        return int.from_bytes(valor, "big")
    if valor is None or isinstance(valor, (str, int, float, bool)):
        return valor
    # Cualquier otro tipo (timedelta, etc.) se guarda como texto.
    return str(valor)


def convertir_a_texto(valor):
    """Convierte cualquier valor de MySQL al formato de texto que usa Redis."""
    if valor is None:
        return ""
    if isinstance(valor, (datetime, date, time)):
        return valor.isoformat()
    if isinstance(valor, (bytes, bytearray)):
        # Las columnas BIT(n) llegan desde pymysql como bytes (b'\x01' -> "1").
        return str(int.from_bytes(valor, "big"))
    if isinstance(valor, bool):
        return "1" if valor else "0"
    return str(valor)


def obtener_datos_mysql():
    """Ejecuta la consulta SQL y devuelve las filas como una lista de diccionarios."""
    print("Conectando a MySQL (puerto "
          f"{CONFIG_MYSQL['port']}) para obtener los datos de origen...")

    conexion = pymysql.connect(**CONFIG_MYSQL)

    try:
        with conexion.cursor() as cursor:
            cursor.execute(SQL_USUARIOS)
            registros = cursor.fetchall()

        print(f"Consulta ejecutada correctamente. Registros obtenidos: {len(registros)}")
        return registros

    finally:
        conexion.close()


def limpiar_importacion_anterior():
    """Elimina los datos de una ejecución previa para que la importación sea idempotente."""
    claves_hashes = list(baseDatosRedis.scan_iter(match=f"{PREFIJO_USUARIO}*"))

    if claves_hashes:
        baseDatosRedis.delete(*claves_hashes)

    baseDatosRedis.delete(CLAVE_INDICE_IDS, CLAVE_JSON, CLAVE_METADATOS)


def guardar_en_redis(registros):
    """Guarda los registros de MySQL en Redis usando hashes, índice y JSON."""
    limpiar_importacion_anterior()

    registros_json = []

    for registro in registros:
        id_usuario = registro.get("id_usuario")
        clave_hash = f"{PREFIJO_USUARIO}{id_usuario}"

        campos = {
            campo: convertir_a_texto(valor)
            for campo, valor in registro.items()
        }

        baseDatosRedis.hset(clave_hash, mapping=campos)
        baseDatosRedis.sadd(CLAVE_INDICE_IDS, str(id_usuario))

        registros_json.append({
            campo: normalizar_para_json(valor)
            for campo, valor in registro.items()
        })

    # Se intenta usar RedisJSON; si el módulo no está instalado Redis responde
    # con un error de comando desconocido (ResponseError) y se guarda como una
    # cadena JSON convencional, manteniendo el mismo nombre de clave. Se captura
    # solo ese error para no ocultar fallos reales (conexión, serialización...).
    try:
        baseDatosRedis.json().set(CLAVE_JSON, "$", registros_json)
        formato_json = "RedisJSON"
    except ResponseError:
        baseDatosRedis.set(
            CLAVE_JSON,
            json.dumps(registros_json, ensure_ascii=False, default=str)
        )
        formato_json = "cadena JSON"

    baseDatosRedis.hset(
        CLAVE_METADATOS,
        mapping={
            "origen": "MySQL",
            "tabla": "USUARIOS + DIRECCIONES",
            "consulta_sql": " ".join(SQL_USUARIOS.split()),
            "total_registros": str(len(registros)),
            "formato_json": formato_json,
            "prefijo_hashes": PREFIJO_USUARIO,
            "clave_indice": CLAVE_INDICE_IDS,
            "clave_json": CLAVE_JSON,
            "fecha_importacion": datetime.now().isoformat(timespec="seconds")
        }
    )

    return len(registros), formato_json


def main():
    print("=" * 70)
    print("21 - IMPORTACIÓN DE DATOS SQL (MySQL) A REDIS")
    print("=" * 70)

    try:
        registros = obtener_datos_mysql()
    except Exception as error:
        print(f"ERROR al obtener datos de MySQL: {error}")
        print("Comprueba que el contenedor de MySQL esté levantado y que las "
              "credenciales del archivo Docker/.env sean correctas.")
        return

    if not registros:
        print("No se han encontrado registros en la tabla USUARIOS. "
              "Ejecuta antes init_db.py y seed.py.")
        return

    try:
        total, formato_json = guardar_en_redis(registros)
    except Exception as error:
        print(f"ERROR al escribir los datos en Redis: {error}")
        print("Comprueba que el contenedor de Redis esté levantado en el "
              "puerto configurado.")
        return

    print("\nDatos almacenados en Redis:")
    print(f"  - Hashes individuales: {total} claves con prefijo '{PREFIJO_USUARIO}'")
    print(f"  - Índice de identificadores: {CLAVE_INDICE_IDS}")
    print(f"  - Documento JSON completo ({formato_json}): {CLAVE_JSON}")
    print(f"  - Metadatos de la importación: {CLAVE_METADATOS}")

    print("\nMuestra de los primeros registros:")
    for registro in registros[:5]:
        print(f"  - ID {registro['id_usuario']} | {registro['nombre']} | "
              f"{registro['email']} | {registro['tipo_usuario']}")

    print(f"\nImportación completada: {total} registros de MySQL guardados en Redis.")
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    finally:
        # Se cierra la conexión con Redis también en las salidas anticipadas.
        baseDatosRedis.close()