import os
import subprocess
import time
import urllib.request

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv, set_key
from pathlib import Path

# ------------------------------------------------------------------------------------------------
# Crear la instancia RDS (MariaDB) si no existe, o arrancarla si está detenida
# ------------------------------------------------------------------------------------------------

# init_RDS.py -> RDS -> aws -> python -> Negocio_SBD
BASE_DIR = Path(__file__).resolve().parents[3]
DOCKER_DIR = BASE_DIR / "Docker"
ENV_PATH = DOCKER_DIR / ".env"

load_dotenv(ENV_PATH)

# -------------------------------
# PARAMETROS DE CONFIGURACION
# -------------------------------
AWS_RDS_DB_INSTANCE_ID = os.getenv("AWS_RDS_DB_INSTANCE_ID")
AWS_RDS_DB_INSTANCE_CLASS = "db.t4g.micro"
AWS_RDS_DB_ENGINE = "mariadb"
AWS_RDS_DB_ALLOCATED_STORAGE = 20

# Parametros de espera (polling) para estados transitorios
POLL_INTERVAL_SECONDS = 15
POLL_MAX_ATTEMPTS = 120  # 15 s * 120 = 30 min

# -------------------------------
# CREAR RDS (MariaDB)
# -------------------------------

session = boto3.session.Session(
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("AWS_SECRET_KEY"),
    aws_session_token=os.getenv("AWS_SESSION_TOKEN"),
    region_name=os.getenv("AWS_REGION"))

rds = session.client('rds')


def get_instance_status():
    """Devuelve el estado actual de la instancia RDS (available, stopped, ...)."""
    info = rds.describe_db_instances(DBInstanceIdentifier=AWS_RDS_DB_INSTANCE_ID)
    return info['DBInstances'][0]['DBInstanceStatus']


def wait_for_status(target_status):
    """
    Espera haciendo polling hasta que la instancia alcance 'target_status'.
    Boto3 no ofrece un waiter para el estado 'stopped', por eso se hace a mano.
    Devuelve True si se alcanza el estado, False si se agotan los intentos.
    """
    for _ in range(POLL_MAX_ATTEMPTS):
        status = get_instance_status()
        if status == target_status:
            return True
        print(f"Estado actual: '{status}'. Esperando a '{target_status}'...")
        time.sleep(POLL_INTERVAL_SECONDS)
    return False


def create_rds_instance():
    
    try:
        print("Comprobando si la instancia RDS ya existe...")
        info = rds.describe_db_instances(DBInstanceIdentifier=AWS_RDS_DB_INSTANCE_ID)
        status = info['DBInstances'][0]['DBInstanceStatus']
        print(f"La instancia '{AWS_RDS_DB_INSTANCE_ID}' ya existe (estado: {status}).")
    except ClientError as e:
        print("Creando instancia RDS...")

        rds.create_db_instance(
            DBInstanceIdentifier=AWS_RDS_DB_INSTANCE_ID,
            AllocatedStorage=AWS_RDS_DB_ALLOCATED_STORAGE,
            DBInstanceClass=AWS_RDS_DB_INSTANCE_CLASS,
            Engine=AWS_RDS_DB_ENGINE,
            MasterUsername=os.getenv("AWS_RDS_DB_USER"),
            MasterUserPassword=os.getenv("AWS_RDS_DB_PASSWORD"),
            PubliclyAccessible=True
        )

        print("Usamos los waiters para esperar a que la instancia esté disponible")
        
        waiter = rds.get_waiter('db_instance_available')
        waiter.wait(DBInstanceIdentifier=AWS_RDS_DB_INSTANCE_ID)
        
        print("La instancia RDS está disponible")
    else:
        # La instancia ya existe: si no está disponible, la dejamos operativa
        if status == 'stopping':
            print("La instancia se está deteniendo. Esperando a que termine para poder iniciarla...")
            wait_for_status('stopped')
            status = get_instance_status()

        if status == 'stopped':
            print("La instancia está detenida. Iniciándola...")
            rds.start_db_instance(DBInstanceIdentifier=AWS_RDS_DB_INSTANCE_ID)
            status = 'starting'

        if status != 'available':
            # Cubre 'starting', 'configuring-enhanced-monitoring', 'backing-up', etc.
            print("Usamos los waiters para esperar a que la instancia esté disponible")

            waiter = rds.get_waiter('db_instance_available')
            waiter.wait(DBInstanceIdentifier=AWS_RDS_DB_INSTANCE_ID)

            print("La instancia RDS está disponible")

    info = rds.describe_db_instances(DBInstanceIdentifier=AWS_RDS_DB_INSTANCE_ID)
    endpoint = info['DBInstances'][0]['Endpoint']['Address']
    return endpoint


def crear_conexion_dbgate(endpoint):
    # Guardar en .env (ruta absoluta)
    set_key(str(ENV_PATH), "AWS_RDS_DB_ENDPOINT", endpoint)

    # Ejecutar docker compose desde la carpeta donde está el compose y el .env
    subprocess.run(
        ["docker", "compose", "up", "-d", "--no-deps", "--force-recreate", "dbgate"],
        cwd=DOCKER_DIR,
        check=True,
    )

endpoint = create_rds_instance()
crear_conexion_dbgate(endpoint)

# ------------------------------------------------------------------------------------------------
# Crear las TABLAS en la base de datos RDS (si no existen)
# ------------------------------------------------------------------------------------------------