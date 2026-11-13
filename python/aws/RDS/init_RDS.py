import os
import subprocess
import time
import urllib.request

import boto3
import pymysql
from pymysql.constants import CLIENT
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
        
        rds.create_db_instance(
            DBInstanceIdentifier=AWS_RDS_DB_INSTANCE_ID,
            AllocatedStorage=AWS_RDS_DB_ALLOCATED_STORAGE,
            DBInstanceClass=AWS_RDS_DB_INSTANCE_CLASS,
            Engine=AWS_RDS_DB_ENGINE,
            MasterUsername=os.getenv("SHARED_DB_USER"),
            MasterUserPassword=os.getenv("SHARED_DB_PASSWORD"),
            PubliclyAccessible=True
        )
        print("Creando instancia RDS...")
        
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


ENDPOINT_AWS = create_rds_instance()

# ------------------------------------------------------------------------------------------------
# Crear las TABLAS en la base de datos RDS (si no existen)
# ------------------------------------------------------------------------------------------------

SHARED_DB_USER = os.getenv("SHARED_DB_USER")
SHARED_DB_PASSWORD = os.getenv("SHARED_DB_PASSWORD")

# --- DDL SCRIPT PARA MARIADB EN RDS ---
SQL_MARIADB_RDS = """
CREATE TABLE IF NOT EXISTS DIRECCIONES (
    id_direccion INT AUTO_INCREMENT PRIMARY KEY,
    codigo_postal VARCHAR(10),
    barrio_zona VARCHAR(100),
    latitud DECIMAL(10,8),
    longitud DECIMAL(11,8)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS USUARIOS (
    id_usuario INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    contrasena_hash VARCHAR(255) NOT NULL,
    tipo_usuario ENUM('Alumno', 'Profesor', 'Familia', 'Admin') NOT NULL,
    id_direccion INT,
    consentimiento_rgpd BOOLEAN NOT NULL DEFAULT FALSE,
    fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_direccion) REFERENCES DIRECCIONES(id_direccion)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS VEHICULOS (
    id_vehiculo INT AUTO_INCREMENT PRIMARY KEY,
    id_propietario INT NOT NULL,
    marca_modelo VARCHAR(100) NOT NULL,
    plazas_totales INT NOT NULL,
    tipo_propulsion ENUM('Electrico', 'Hibrido', 'Gasolina', 'Diesel') NOT NULL,
    matricula_hash VARCHAR(255) NOT NULL,
    FOREIGN KEY (id_propietario) REFERENCES USUARIOS(id_usuario)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS RUTAS_CARPOOLING (
    id_ruta INT AUTO_INCREMENT PRIMARY KEY,
    id_conductor INT NOT NULL,
    id_vehiculo INT NOT NULL,
    origen_lat DECIMAL(10,8) NOT NULL,
    origen_lon DECIMAL(11,8) NOT NULL,
    destino_lat DECIMAL(10,8) NOT NULL,
    destino_lon DECIMAL(11,8) NOT NULL,
    hora_salida DATETIME NOT NULL,
    plazas_disponibles INT NOT NULL,
    estado ENUM('Programada', 'En_Curso', 'Completada', 'Cancelada') DEFAULT 'Programada',
    FOREIGN KEY (id_conductor) REFERENCES USUARIOS(id_usuario),
    FOREIGN KEY (id_vehiculo) REFERENCES VEHICULOS(id_vehiculo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS RESERVAS_CARPOOLING (
    id_reserva INT AUTO_INCREMENT PRIMARY KEY,
    id_ruta INT NOT NULL,
    id_pasajero INT NOT NULL,
    punto_recogida_lat DECIMAL(10,8),
    punto_recogida_lon DECIMAL(11,8),
    estado_reserva ENUM('Pendiente', 'Confirmada', 'Rechazada', 'Cancelada') DEFAULT 'Pendiente',
    fecha_reserva DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_ruta) REFERENCES RUTAS_CARPOOLING(id_ruta),
    FOREIGN KEY (id_pasajero) REFERENCES USUARIOS(id_usuario)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS REGISTROS_GPS (
    id_registro_gps BIGINT AUTO_INCREMENT PRIMARY KEY,
    id_usuario INT NOT NULL,
    id_ruta INT,
    latitud DECIMAL(10,8) NOT NULL,
    longitud DECIMAL(11,8) NOT NULL,
    velocidad_kmh DECIMAL(5,2),
    timestamp_captura DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_usuario) REFERENCES USUARIOS(id_usuario),
    FOREIGN KEY (id_ruta) REFERENCES RUTAS_CARPOOLING(id_ruta)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS HISTORIAL_DESPLAZAMIENTOS (
    id_desplazamiento INT AUTO_INCREMENT PRIMARY KEY,
    id_usuario INT NOT NULL,
    modo_transporte ENUM('A_Pie', 'Bicicleta', 'Autobus', 'Carpooling', 'Coche_Individual') NOT NULL,
    distancia_km DECIMAL(6,2) NOT NULL,
    co2_ahorrado_kg DECIMAL(6,3) DEFAULT 0.000,
    tiempo_minutos INT,
    fecha_desplazamiento DATE NOT NULL,
    FOREIGN KEY (id_usuario) REFERENCES USUARIOS(id_usuario)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS INCIDENCIAS_TRAFICO (
    id_incidencia INT AUTO_INCREMENT PRIMARY KEY,
    tipo_incidencia ENUM('Retencion', 'Obras', 'Accidente', 'Corte_Vial', 'Otro') NOT NULL,
    latitud DECIMAL(10,8) NOT NULL,
    longitud DECIMAL(11,8) NOT NULL,
    descripcion TEXT,
    nivel_gravedad ENUM('Bajo', 'Medio', 'Alto', 'Critico') DEFAULT 'Bajo',
    fecha_inicio DATETIME DEFAULT CURRENT_TIMESTAMP,
    fuente_dato VARCHAR(50)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ENCUESTAS_HABITOS (
    id_encuesta INT AUTO_INCREMENT PRIMARY KEY,
    titulo VARCHAR(150) NOT NULL,
    descripcion TEXT,
    fecha_inicio DATE NOT NULL,
    fecha_fin DATE NOT NULL,
    activo BOOLEAN DEFAULT TRUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS RESPUESTAS_ENCUESTA (
    id_respuesta INT AUTO_INCREMENT PRIMARY KEY,
    id_encuesta INT NOT NULL,
    token_usuario_anonimo VARCHAR(255) NOT NULL,
    modo_habitual ENUM('A_Pie', 'Bicicleta', 'Autobus', 'Coche_Privado') NOT NULL,
    tiempo_medio_min INT,
    comentarios_texto_libre TEXT,
    FOREIGN KEY (id_encuesta) REFERENCES ENCUESTAS_HABITOS(id_encuesta)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS REGISTRO_METEOROLOGICO (
    id_clima INT AUTO_INCREMENT PRIMARY KEY,
    fecha DATE NOT NULL,
    hora TIME NOT NULL,
    temperatura_c DECIMAL(4,1),
    precipitacion_mm DECIMAL(5,2),
    estado_tiempo VARCHAR(50)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""


def get_rds_db_config(database=None):
    """Construye la configuracion de conexion a MariaDB en RDS."""
    config = {
        "host": ENDPOINT_AWS,
        "port": 3306,
        "user": SHARED_DB_USER,
        "password": SHARED_DB_PASSWORD,
        "charset": "utf8mb4",
        "client_flag": CLIENT.MULTI_STATEMENTS,
    }
    if database:
        config["database"] = database
    return config


def crear_base_datos_rds():
    """Crea la base de datos en RDS si no existe y devuelve su nombre."""
    db_name = os.getenv("AWS_RDS_DB_NAME")
    if not db_name:
        raise ValueError("La variable de entorno AWS_RDS_DB_NAME no esta definida.")

    conn = pymysql.connect(**get_rds_db_config())
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{db_name.replace('`', '``')}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        conn.commit()
        print(f"Base de datos '{db_name}' disponible en RDS MariaDB.")
    finally:
        conn.close()

    return db_name


def ejecutar_ddl_rds(conn, sql_script, nombre_bd):
    """Ejecuta un script DDL dentro de la conexion indicada."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql_script)
            # Con MULTI_STATEMENTS hay que consumir todos los result sets.
            while cursor.nextset():
                pass
        conn.commit()
        print(f"Esquema creado con exito en {nombre_bd}.")
    except Exception as e:
        conn.rollback()
        print(f"Error creando esquema en {nombre_bd}: {e}")


def inicializar_tablas_rds():
    """Crea las tablas del proyecto en la instancia MariaDB de RDS."""
    print("Creando tablas en MariaDB (AWS RDS)...")

    try:
        db_name = crear_base_datos_rds()
        conn = pymysql.connect(**get_rds_db_config(db_name))
        try:
            ejecutar_ddl_rds(conn, SQL_MARIADB_RDS, "MariaDB RDS")
        finally:
            conn.close()
    except Exception as e:
        print(f"Error al inicializar las tablas en MariaDB RDS: {e}")


inicializar_tablas_rds()



# ------------------------------------------------------------------------------------------------
# Actualizar la conexion del visor DBgate
# ------------------------------------------------------------------------------------------------

def crear_conexion_dbgate(endpoint):
    # Guardar en .env (ruta absoluta)
    set_key(str(ENV_PATH), "AWS_RDS_DB_ENDPOINT", endpoint)

    # Ejecutar docker compose desde la carpeta donde está el compose y el .env
    subprocess.run(
        ["docker", "compose", "run", "--rm", "--no-deps", "rds-cert"],
        cwd=DOCKER_DIR,
        check=True,
    )

crear_conexion_dbgate(ENDPOINT_AWS)