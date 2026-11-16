import os
import subprocess
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv, set_key

# ------------------------------------------------------------------------------------------------
# Crear las tablas de DynamoDB si no existen
# ------------------------------------------------------------------------------------------------

# init_DynamoDB.py -> DynamoDB -> aws -> python -> Negocio_SBD
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

dynamodb = session.client("dynamodb")

ENDPOINT_DYNAMODB = dynamodb.meta.endpoint_url

# ------------------------------------------------------------------------------------------------
# DEFINICION DE TABLAS
# ------------------------------------------------------------------------------------------------
# DynamoDB complementa a MariaDB (RDS): el modelo relacional guarda los datos maestros
# (usuarios, vehiculos, rutas, reservas...) y DynamoDB guarda los datos de alto volumen,
# escritura continua y vida corta que no necesitan JOINs.
#
# En DynamoDB solo se declaran en AttributeDefinitions los atributos que forman parte
# de alguna clave (tabla base, LSI o GSI); el resto de atributos son libres.

TABLAS_DYNAMODB = [
    {
        # 1. TABLA SIN INDICE LOCAL NI GLOBAL
        # Chat entre el conductor y los pasajeros de una ruta de carpooling.
        # Consulta tipica: "ultimos mensajes de la ruta X" -> Query por id_ruta, orden por marca_tiempo.
        # Otros atributos libres: id_usuario_emisor (N), texto (S), leido (BOOL)
        "TableName": "MENSAJES_RUTA",
        "KeySchema": [
            {"AttributeName": "id_ruta", "KeyType": "HASH"},
            {"AttributeName": "marca_tiempo", "KeyType": "RANGE"},  # ISO 8601 UTC
        ],
        "AttributeDefinitions": [
            {"AttributeName": "id_ruta", "AttributeType": "N"},
            {"AttributeName": "marca_tiempo", "AttributeType": "S"},
        ],
        "ttl_attribute": None,
    },
    {
        # 2. TABLA CON INDICE SECUNDARIO LOCAL (LSI)
        # Notificaciones push/in-app de cada usuario (reserva confirmada, ruta cancelada, etc.).
        # Consulta base: "notificaciones del usuario X ordenadas por fecha".
        # Consulta con LSI: "notificaciones del usuario X filtradas por tipo".
        # Otros atributos libres: mensaje (S), leida (BOOL), id_ruta (N, opcional), expira_en (N)
        "TableName": "NOTIFICACIONES_USUARIO",
        "KeySchema": [
            {"AttributeName": "id_usuario", "KeyType": "HASH"},
            {"AttributeName": "marca_tiempo", "KeyType": "RANGE"},  # ISO 8601 UTC
        ],
        "AttributeDefinitions": [
            {"AttributeName": "id_usuario", "AttributeType": "N"},
            {"AttributeName": "marca_tiempo", "AttributeType": "S"},
            {"AttributeName": "tipo", "AttributeType": "S"},
        ],
        "LocalSecondaryIndexes": [
            {
                "IndexName": "LSI_usuario_tipo",
                "KeySchema": [
                    {"AttributeName": "id_usuario", "KeyType": "HASH"},
                    {"AttributeName": "tipo", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
        "ttl_attribute": "expira_en",
    },
    {
        # 3. TABLA CON INDICE SECUNDARIO GLOBAL (GSI)
        # Posicion en directo de los vehiculos durante una ruta en curso.
        # Consulta base: "ultima posicion de la ruta X" -> Query por id_ruta.
        # Consulta con GSI: "ultimas posiciones registradas por el usuario Y" -> Query por id_usuario.
        # Otros atributos libres: latitud (N), longitud (N), velocidad_kmh (N), expira_en (N)
        "TableName": "POSICIONES_TIEMPO_REAL",
        "KeySchema": [
            {"AttributeName": "id_ruta", "KeyType": "HASH"},
            {"AttributeName": "marca_tiempo", "KeyType": "RANGE"},  # ISO 8601 UTC
        ],
        "AttributeDefinitions": [
            {"AttributeName": "id_ruta", "AttributeType": "N"},
            {"AttributeName": "marca_tiempo", "AttributeType": "S"},
            {"AttributeName": "id_usuario", "AttributeType": "N"},
        ],
        "GlobalSecondaryIndexes": [
            {
                "IndexName": "GSI_usuario_tiempo",
                "KeySchema": [
                    {"AttributeName": "id_usuario", "KeyType": "HASH"},
                    {"AttributeName": "marca_tiempo", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
        "ttl_attribute": "expira_en",
    },
]


# -------------------------------
# CREAR TABLAS
# -------------------------------

def tabla_existe(nombre):
    """Devuelve True si la tabla ya existe en DynamoDB."""
    try:
        dynamodb.describe_table(TableName=nombre)
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            return False
        raise


def activar_ttl(nombre, atributo):
    """Activa el TTL en la tabla si todavia no esta activado."""
    estado = dynamodb.describe_time_to_live(TableName=nombre)["TimeToLiveDescription"]
    if estado.get("TimeToLiveStatus") in ("ENABLED", "ENABLING"):
        print(f"  TTL ya activado en '{nombre}' (atributo '{estado.get('AttributeName')}').")
        return

    dynamodb.update_time_to_live(
        TableName=nombre,
        TimeToLiveSpecification={"Enabled": True, "AttributeName": atributo},
    )
    print(f"  TTL activado en '{nombre}' (atributo '{atributo}').")


def crear_tabla(definicion):
    """Crea la tabla con sus indices si no existe (o espera a que este activa si ya existe)."""
    nombre = definicion["TableName"]

    if tabla_existe(nombre):
        print(f"La tabla '{nombre}' ya existe.")
    else:
        print(f"Creando tabla '{nombre}'...")
        parametros_creacion = {
            "TableName": nombre,
            "KeySchema": definicion["KeySchema"],
            "AttributeDefinitions": definicion["AttributeDefinitions"],
            "BillingMode": "PAY_PER_REQUEST",  # bajo demanda: sin capacidad que configurar
        }

        if definicion.get("LocalSecondaryIndexes"):
            parametros_creacion["LocalSecondaryIndexes"] = definicion["LocalSecondaryIndexes"]

        if definicion.get("GlobalSecondaryIndexes"):
            parametros_creacion["GlobalSecondaryIndexes"] = definicion["GlobalSecondaryIndexes"]

        dynamodb.create_table(**parametros_creacion)

    # Si estaba en CREATING, espera hasta que este activa
    waiter = dynamodb.get_waiter("table_exists")
    waiter.wait(TableName=nombre)
    print(f"  La tabla '{nombre}' esta activa.")

    if definicion.get("ttl_attribute"):
        try:
            activar_ttl(nombre, definicion["ttl_attribute"])
        except ClientError as e:
            print(f"  No se pudo activar el TTL en '{nombre}': {e}")


def inicializar_tablas_dynamodb():
    """Crea las tablas del proyecto en DynamoDB."""
    print("Creando tablas en DynamoDB...")

    try:
        for definicion in TABLAS_DYNAMODB:
            crear_tabla(definicion)
        print("Tablas de DynamoDB disponibles.")
    except Exception as e:
        print(f"Error al inicializar las tablas en DynamoDB: {e}")
        raise


inicializar_tablas_dynamodb()

# ------------------------------------------------------------------------------------------------
# Comprobacion final
# ------------------------------------------------------------------------------------------------

print("Tablas actuales en DynamoDB:", dynamodb.list_tables()["TableNames"])

# ------------------------------------------------------------------------------------------------
# Actualizar la conexion del visor DynamoDB Admin
# ------------------------------------------------------------------------------------------------

def crear_conexion_dynamodb_admin(endpoint):
    # Guardar en .env (ruta absoluta)
    set_key(str(ENV_PATH), "AWS_DYNAMODB_ENDPOINT", endpoint)

    # Recrear el contenedor desde la carpeta donde está el compose y el .env, para que
    # coja el endpoint y las credenciales temporales (AWS_SESSION_TOKEN) actualizadas.
    subprocess.run(
        ["docker", "compose", "up", "-d", "--force-recreate", "--no-deps", "dynamodb-admin"],
        cwd=DOCKER_DIR,
        check=True,
    )


crear_conexion_dynamodb_admin(ENDPOINT_DYNAMODB)