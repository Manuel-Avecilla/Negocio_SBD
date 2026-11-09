import os
import subprocess
import urllib.request

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv, set_key
from pathlib import Path

# crearRDS.py -> RDS -> aws -> python -> Negocio_SBD
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

# -------------------------------
# CREAR RDS (MariaDB)
# -------------------------------

session = boto3.session.Session(
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("AWS_SECRET_KEY"),
    aws_session_token=os.getenv("AWS_SESSION_TOKEN"),
    region_name=os.getenv("AWS_REGION"))

rds = session.client('rds')

def create_rds_instance():
    
    try:
        print("Comprobando si la instancia RDS ya existe...")
        info = rds.describe_db_instances(DBInstanceIdentifier=AWS_RDS_DB_INSTANCE_ID)
        print(f"La instancia '{AWS_RDS_DB_INSTANCE_ID}' ya existe.")
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