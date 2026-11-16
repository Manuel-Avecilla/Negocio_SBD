"""
=============================================================================
SMARTRUTA & MOVILIDAD SOSTENIBLE - LIMPIEZA DE DATOS EN AWS DYNAMODB (flushdb.py)
=============================================================================

Elimina todos los registros (items) de las tablas de DynamoDB sin borrar la
estructura ni los indices (LSI/GSI) de las tablas:
- MENSAJES_RUTA            (PK: id_ruta, SK: marca_tiempo)
- NOTIFICACIONES_USUARIO   (PK: id_usuario, SK: marca_tiempo)
- POSICIONES_TIEMPO_REAL   (PK: id_ruta, SK: marca_tiempo)
=============================================================================
"""

import os
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# flushdb.py -> DynamoDB -> aws -> python -> Negocio_SBD
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

# Definicion de tablas y sus claves primarias (HASH y RANGE)
TABLAS_CLAVES = {
    "MENSAJES_RUTA": ["id_ruta", "marca_tiempo"],
    "NOTIFICACIONES_USUARIO": ["id_usuario", "marca_tiempo"],
    "POSICIONES_TIEMPO_REAL": ["id_ruta", "marca_tiempo"],
}


# -------------------------------
# FUNCIONES DE LIMPIEZA
# -------------------------------

def vaciar_tabla(nombre_tabla, claves):
    """Escanea todos los items de la tabla (solo claves) y los elimina en bloque."""
    tabla = dynamodb.Table(nombre_tabla)

    try:
        # Proyectamos unicamente las claves primarias para minimizar consumo de lectura
        nombres_atributos = {f"#k{i}": clave for i, clave in enumerate(claves)}
        proyeccion = ", ".join(nombres_atributos.keys())

        total_eliminados = 0
        parametros_scan = {
            "ProjectionExpression": proyeccion,
            "ExpressionAttributeNames": nombres_atributos,
        }

        with tabla.batch_writer() as batch:
            while True:
                respuesta = tabla.scan(**parametros_scan)
                items = respuesta.get("Items", [])

                for item in items:
                    clave_item = {clave: item[clave] for clave in claves}
                    batch.delete_item(Key=clave_item)
                    total_eliminados += 1

                if "LastEvaluatedKey" not in respuesta:
                    break
                parametros_scan["ExclusiveStartKey"] = respuesta["LastEvaluatedKey"]

        print(f"{nombre_tabla}: {total_eliminados} registros eliminados")

    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            print(f"{nombre_tabla}: la tabla no existe en DynamoDB, se omite.")
        else:
            raise


def limpiar_base_de_datos():
    print("Eliminando todos los registros de las tablas en DynamoDB...")

    try:
        for nombre_tabla, claves in TABLAS_CLAVES.items():
            vaciar_tabla(nombre_tabla, claves)
        print("Limpieza completada con exito en DynamoDB.")
    except Exception as e:
        print(f"Error durante la limpieza de DynamoDB: {e}")
        raise


if __name__ == "__main__":
    limpiar_base_de_datos()