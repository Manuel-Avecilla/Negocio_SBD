import os
from pathlib import Path
import pymysql
from pymysql.constants import CLIENT
import psycopg2
from dotenv import load_dotenv

# Cargar .env desde la carpeta docker/
BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / "docker" / ".env"
load_dotenv(dotenv_path=env_path)

# Variables generales
SHARED_PASS = os.getenv("SHARED_PASSWORD", "smartruta_pass_123")
DB_NAME = os.getenv("MYSQL_DATABASE", "smartruta_db")
DB_USER = os.getenv("MYSQL_USER", "smartruta_user")

CONFIG_MYSQL = {
    "host": "localhost",
    "port": 3306,
    "user": DB_USER,
    "password": os.getenv("MYSQL_PASSWORD", SHARED_PASS),
    "database": DB_NAME,
    "client_flag": CLIENT.MULTI_STATEMENTS  # Permite ejecutar el bloque SQL completo
}

CONFIG_POSTGRES = {
    "host": "localhost",
    "port": 5432,
    "user": os.getenv("POSTGRES_USER", DB_USER),
    "password": os.getenv("POSTGRES_PASSWORD", SHARED_PASS),
    "dbname": os.getenv("POSTGRES_DB", DB_NAME)
}

CONFIG_MARIADB = {
    "host": "localhost",
    "port": 3307,
    "user": os.getenv("MARIADB_USER", os.getenv("MYSQL_USER", DB_USER)),
    "password": os.getenv("MARIADB_PASSWORD", os.getenv("MYSQL_PASSWORD", SHARED_PASS)),
    "database": os.getenv("MARIADB_DATABASE", os.getenv("MYSQL_DATABASE", DB_NAME)),
    "client_flag": CLIENT.MULTI_STATEMENTS  # Permite ejecutar el bloque SQL completo
}

# --- DDL SCRIPT PARA MYSQL Y MARIADB ---
SQL_MYSQL_MARIADB = """
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

# --- DDL SCRIPT PARA POSTGRESQL ---
SQL_POSTGRES = """
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'tipo_usuario_enum') THEN
        CREATE TYPE tipo_usuario_enum AS ENUM ('Alumno', 'Profesor', 'Familia', 'Admin');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'tipo_propulsion_enum') THEN
        CREATE TYPE tipo_propulsion_enum AS ENUM ('Electrico', 'Hibrido', 'Gasolina', 'Diesel');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'estado_ruta_enum') THEN
        CREATE TYPE estado_ruta_enum AS ENUM ('Programada', 'En_Curso', 'Completada', 'Cancelada');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'estado_reserva_enum') THEN
        CREATE TYPE estado_reserva_enum AS ENUM ('Pendiente', 'Confirmada', 'Rechazada', 'Cancelada');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'modo_transporte_enum') THEN
        CREATE TYPE modo_transporte_enum AS ENUM ('A_Pie', 'Bicicleta', 'Autobus', 'Carpooling', 'Coche_Individual');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'tipo_incidencia_enum') THEN
        CREATE TYPE tipo_incidencia_enum AS ENUM ('Retencion', 'Obras', 'Accidente', 'Corte_Vial', 'Otro');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'nivel_gravedad_enum') THEN
        CREATE TYPE nivel_gravedad_enum AS ENUM ('Bajo', 'Medio', 'Alto', 'Critico');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'modo_habitual_enum') THEN
        CREATE TYPE modo_habitual_enum AS ENUM ('A_Pie', 'Bicicleta', 'Autobus', 'Coche_Privado');
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS DIRECCIONES (
    id_direccion SERIAL PRIMARY KEY,
    codigo_postal VARCHAR(10),
    barrio_zona VARCHAR(100),
    latitud NUMERIC(10,8),
    longitud NUMERIC(11,8)
);

CREATE TABLE IF NOT EXISTS USUARIOS (
    id_usuario SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    contrasena_hash VARCHAR(255) NOT NULL,
    tipo_usuario tipo_usuario_enum NOT NULL,
    id_direccion INT REFERENCES DIRECCIONES(id_direccion),
    consentimiento_rgpd BOOLEAN NOT NULL DEFAULT FALSE,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS VEHICULOS (
    id_vehiculo SERIAL PRIMARY KEY,
    id_propietario INT NOT NULL REFERENCES USUARIOS(id_usuario),
    marca_modelo VARCHAR(100) NOT NULL,
    plazas_totales INT NOT NULL,
    tipo_propulsion tipo_propulsion_enum NOT NULL,
    matricula_hash VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS RUTAS_CARPOOLING (
    id_ruta SERIAL PRIMARY KEY,
    id_conductor INT NOT NULL REFERENCES USUARIOS(id_usuario),
    id_vehiculo INT NOT NULL REFERENCES VEHICULOS(id_vehiculo),
    origen_lat NUMERIC(10,8) NOT NULL,
    origen_lon NUMERIC(11,8) NOT NULL,
    destino_lat NUMERIC(10,8) NOT NULL,
    destino_lon NUMERIC(11,8) NOT NULL,
    hora_salida TIMESTAMP NOT NULL,
    plazas_disponibles INT NOT NULL,
    estado estado_ruta_enum DEFAULT 'Programada'
);

CREATE TABLE IF NOT EXISTS RESERVAS_CARPOOLING (
    id_reserva SERIAL PRIMARY KEY,
    id_ruta INT NOT NULL REFERENCES RUTAS_CARPOOLING(id_ruta),
    id_pasajero INT NOT NULL REFERENCES USUARIOS(id_usuario),
    punto_recogida_lat NUMERIC(10,8),
    punto_recogida_lon NUMERIC(11,8),
    estado_reserva estado_reserva_enum DEFAULT 'Pendiente',
    fecha_reserva TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS REGISTROS_GPS (
    id_registro_gps BIGSERIAL PRIMARY KEY,
    id_usuario INT NOT NULL REFERENCES USUARIOS(id_usuario),
    id_ruta INT REFERENCES RUTAS_CARPOOLING(id_ruta),
    latitud NUMERIC(10,8) NOT NULL,
    longitud NUMERIC(11,8) NOT NULL,
    velocidad_kmh NUMERIC(5,2),
    timestamp_captura TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS HISTORIAL_DESPLAZAMIENTOS (
    id_desplazamiento SERIAL PRIMARY KEY,
    id_usuario INT NOT NULL REFERENCES USUARIOS(id_usuario),
    modo_transporte modo_transporte_enum NOT NULL,
    distancia_km NUMERIC(6,2) NOT NULL,
    co2_ahorrado_kg NUMERIC(6,3) DEFAULT 0.000,
    tiempo_minutos INT,
    fecha_desplazamiento DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS INCIDENCIAS_TRAFICO (
    id_incidencia SERIAL PRIMARY KEY,
    tipo_incidencia tipo_incidencia_enum NOT NULL,
    latitud NUMERIC(10,8) NOT NULL,
    longitud NUMERIC(11,8) NOT NULL,
    descripcion TEXT,
    nivel_gravedad nivel_gravedad_enum DEFAULT 'Bajo',
    fecha_inicio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fuente_dato VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS ENCUESTAS_HABITOS (
    id_encuesta SERIAL PRIMARY KEY,
    titulo VARCHAR(150) NOT NULL,
    descripcion TEXT,
    fecha_inicio DATE NOT NULL,
    fecha_fin DATE NOT NULL,
    activo BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS RESPUESTAS_ENCUESTA (
    id_respuesta SERIAL PRIMARY KEY,
    id_encuesta INT NOT NULL REFERENCES ENCUESTAS_HABITOS(id_encuesta),
    token_usuario_anonimo VARCHAR(255) NOT NULL,
    modo_habitual modo_habitual_enum NOT NULL,
    tiempo_medio_min INT,
    comentarios_texto_libre TEXT
);

CREATE TABLE IF NOT EXISTS REGISTRO_METEOROLOGICO (
    id_clima SERIAL PRIMARY KEY,
    fecha DATE NOT NULL,
    hora TIME NOT NULL,
    temperatura_c NUMERIC(4,1),
    precipitacion_mm NUMERIC(5,2),
    estado_tiempo VARCHAR(50)
);
"""

def ejecutar_ddl(conn, sql_script, nombre_bd):
    """Ejecuta un script DDL dentro de la conexión indicada."""
    try:
        cursor = conn.cursor()
        cursor.execute(sql_script)
        conn.commit()
        cursor.close()
        print(f" Esquema creado con éxito en {nombre_bd}.")
    except Exception as e:
        print(f" Error creando esquema en {nombre_bd}: {e}")

def inicializar_tablas():
    print(" Creando tablas en MySQL, PostgreSQL y MariaDB desde Python...")

    # 1. MySQL
    try:
        conn_mysql = pymysql.connect(**CONFIG_MYSQL)
        ejecutar_ddl(conn_mysql, SQL_MYSQL_MARIADB, "MySQL")
        conn_mysql.close()
    except Exception as e:
        print(f" Error al conectar con MySQL: {e}")

    # 2. PostgreSQL
    try:
        conn_postgres = psycopg2.connect(**CONFIG_POSTGRES)
        ejecutar_ddl(conn_postgres, SQL_POSTGRES, "PostgreSQL")
        conn_postgres.close()
    except Exception as e:
        print(f" Error al conectar con PostgreSQL: {e}")

    # 3. MariaDB
    try:
        conn_mariadb = pymysql.connect(**CONFIG_MARIADB)
        ejecutar_ddl(conn_mariadb, SQL_MYSQL_MARIADB, "MariaDB")
        conn_mariadb.close()
    except Exception as e:
        print(f" Error al conectar con MariaDB: {e}")

if __name__ == "__main__":
    inicializar_tablas()