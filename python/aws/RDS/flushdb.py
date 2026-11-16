"""
=============================================================================
SMARTRUTA & MOVILIDAD SOSTENIBLE - VACIADO DE LA BASE DE DATOS EN AWS RDS
=============================================================================
Vacía TODAS las tablas de la base de datos (conserva el esquema) y reinicia
los AUTO_INCREMENT, de forma que seed.py pueda volver a ejecutarse y las
claves foráneas (ids 1..N) sigan siendo válidas.

Uso:
    python flushdb.py
=============================================================================
"""

import os
from pathlib import Path

import pymysql
from dotenv import load_dotenv

# flushdb.py -> RDS -> aws -> python -> Negocio_SBD
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
}


def obtener_conexion():
    """Establece conexión con MariaDB en la instancia RDS de AWS."""
    if not AWS_RDS_DB_ENDPOINT:
        print(" Error: la variable AWS_RDS_DB_ENDPOINT no está definida en el .env.")
        exit(1)

    if not AWS_RDS_DB_NAME:
        print(" Error: la variable AWS_RDS_DB_NAME no está definida en el .env.")
        exit(1)

    try:
        conn = pymysql.connect(**CONFIG_RDS_MARIADB)
        print(" Conexión exitosa a MariaDB en AWS RDS.")
        return conn
    except Exception as e:
        print(f" Error conectando a MariaDB en AWS RDS: {e}")
        exit(1)


def listar_tablas(conexion):
    """Devuelve todas las tablas base de la BD (excluye vistas)."""
    with conexion.cursor() as cursor:
        cursor.execute("SHOW FULL TABLES WHERE Table_type = 'BASE TABLE'")
        return [fila[0] for fila in cursor.fetchall()]


def vaciar_base_de_datos():
    conn = obtener_conexion()

    try:
        tablas = listar_tablas(conn)

        if not tablas:
            print(" La base de datos no contiene tablas. Nada que vaciar.")
            return

        print(f" Vaciando {len(tablas)} tablas en MariaDB RDS...")

        with conn.cursor() as cursor:
            # Desactivar FKs para poder truncar en cualquier orden
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
            try:
                for tabla in tablas:
                    # TRUNCATE vacía la tabla y reinicia el AUTO_INCREMENT a 1
                    cursor.execute(f"TRUNCATE TABLE `{tabla}`")
                    print(f"Vaciando tabla: {tabla} ...")
            finally:
                # Reactivar siempre las FKs, aunque falle algún TRUNCATE
                cursor.execute("SET FOREIGN_KEY_CHECKS = 1")

        # TRUNCATE hace commit implícito, pero lo dejamos explícito por claridad
        conn.commit()
        print(f" Base de datos '{AWS_RDS_DB_NAME}' vaciada con éxito ({len(tablas)} tablas).")

    except Exception as e:
        print(f" Error durante el vaciado de MariaDB RDS: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    vaciar_base_de_datos()