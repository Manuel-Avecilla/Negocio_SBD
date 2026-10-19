"""
=============================================================================
SMARTRUTA & MOVILIDAD SOSTENIBLE - SCRIPT DE POBLADO DE DATOS (seed.py)
=============================================================================

10 PROVIDERS / MÉTODOS DE FAKER UTILIZADOS EN ESTE SCRIPT:
1.  Provider Person:         fake.name()                    -> Nombres de usuarios
2.  Provider Internet:       fake.email()                   -> Correos electrónicos
3.  Provider Address:        fake.postcode(), fake.street_name() -> Direcciones y barrios
4.  Provider Geo:            fake.latitude(), fake.longitude()   -> Coordenadas GPS
5.  Provider Automotive:     fake.license_plate()          -> Matrículas de vehículos
6.  Provider Date/Time:      fake.date_time_this_year(), fake.time(), fake.date_this_year() -> Fechas y timestamps
7.  Provider Lorem:          fake.sentence(), fake.text()   -> Comentarios e incidencias
8.  Provider Misc / UUID:    fake.uuid4()                   -> Hashes y tokens anónimos
9.  Provider Python / Bool:  fake.boolean()                 -> Consentimientos RGPD y estados booleanos
10. Provider Company:        fake.company()                 -> Modelos/Marcas de transporte y fuentes
=============================================================================
"""

import os
import random
import datetime
import pymysql
import psycopg2
from faker import Faker

from pathlib import Path
from dotenv import load_dotenv

# Obtener la ruta absoluta de la carpeta raíz del proyecto y localizar docker/.env
BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / "docker" / ".env"

# Cargar explícitamente el archivo .env desde la carpeta docker
load_dotenv(dotenv_path=env_path)

# Inicializar Faker en español
fake = Faker('es_ES')

# Variables generales / compartidas
SHARED_PASS = os.getenv("SHARED_PASSWORD", "smartruta_pass_123")
DB_NAME_DEFAULT = os.getenv("MYSQL_DATABASE", "smartruta_db")
DB_USER_DEFAULT = os.getenv("MYSQL_USER", "smartruta_user")

# Configuración individual por motor
CONFIG_MYSQL = {
    "host": "localhost",
    "port": 3306,
    "user": os.getenv("MYSQL_USER", DB_USER_DEFAULT),
    "password": os.getenv("MYSQL_PASSWORD", SHARED_PASS),
    "database": os.getenv("MYSQL_DATABASE", DB_NAME_DEFAULT)
}

CONFIG_POSTGRES = {
    "host": "localhost",
    "port": 5432,
    "user": os.getenv("POSTGRES_USER", DB_USER_DEFAULT),
    "password": os.getenv("POSTGRES_PASSWORD", SHARED_PASS),
    "dbname": os.getenv("POSTGRES_DB", DB_NAME_DEFAULT)
}

CONFIG_MARIADB = {
    "host": "localhost",
    "port": 3307,
    "user": os.getenv("MARIADB_USER", os.getenv("MYSQL_USER", DB_USER_DEFAULT)),
    "password": os.getenv("MARIADB_PASSWORD", os.getenv("MYSQL_PASSWORD", SHARED_PASS)),
    "database": os.getenv("MARIADB_DATABASE", os.getenv("MYSQL_DATABASE", DB_NAME_DEFAULT))
}

def obtener_conexiones():
    """Establece conexión con las 3 bases de datos."""
    try:
        conn_mysql = pymysql.connect(**CONFIG_MYSQL)
        conn_postgres = psycopg2.connect(**CONFIG_POSTGRES)
        conn_mariadb = pymysql.connect(**CONFIG_MARIADB)
        print(" Conexión exitosa a MySQL, PostgreSQL y MariaDB.")
        return conn_mysql, conn_postgres, conn_mariadb
    except Exception as e:
        print(f" Error conectando a las bases de datos: {e}")
        exit(1)

def ejecutar_insert_global(conexiones, query, datos_lista):
    """Ejecuta un INSERT parametrizado con executemany en las 3 bases de datos."""
    for conn in conexiones:
        cursor = conn.cursor()
        cursor.executemany(query, datos_lista)
        cursor.close()

def poblar_bases_de_datos():
    conn_mysql, conn_postgres, conn_mariadb = obtener_conexiones()
    conexiones = [conn_mysql, conn_postgres, conn_mariadb]

    print(" Generando datos sintéticos e insertando...")

    # 1. DIRECCIONES (50 registros)
    datos_direcciones = [
        (
            fake.postcode(),                       # Provider 3: Address
            fake.street_name(),                    # Provider 3: Address
            float(fake.latitude()),                # Provider 4: Geo
            float(fake.longitude())                # Provider 4: Geo
        )
        for _ in range(50)
    ]
    query_direcciones = """
        INSERT INTO DIRECCIONES (codigo_postal, barrio_zona, latitud, longitud)
        VALUES (%s, %s, %s, %s)
    """
    ejecutar_insert_global(conexiones, query_direcciones, datos_direcciones)

    # 2. USUARIOS (100 registros)
    tipos_usuario = ['Alumno', 'Profesor', 'Familia', 'Admin']
    datos_usuarios = [
        (
            fake.name(),                           # Provider 1: Person
            fake.unique.email(),                   # Provider 2: Internet
            fake.uuid4(),                          # Provider 8: Misc/UUID (hash)
            random.choice(tipos_usuario),
            random.randint(1, 50),                 # Foreign Key a DIRECCIONES
            fake.boolean(chance_of_getting_true=80),# Provider 9: Python/Bool
            fake.date_time_this_year()            # Provider 6: Date/Time
        )
        for _ in range(100)
    ]
    query_usuarios = """
        INSERT INTO USUARIOS (nombre, email, contrasena_hash, tipo_usuario, id_direccion, consentimiento_rgpd, fecha_registro)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    ejecutar_insert_global(conexiones, query_usuarios, datos_usuarios)

    # 3. VEHICULOS (40 registros)
    propulsiones = ['Electrico', 'Hibrido', 'Gasolina', 'Diesel']
    datos_vehiculos = [
        (
            random.randint(1, 100),                # FK a USUARIOS
            f"{fake.company()} Model-{random.choice(['X', 'Y', 'Z', 'Eco'])}", # Provider 10: Company
            random.randint(2, 7),
            random.choice(propulsiones),
            fake.license_plate()                  # Provider 5: Automotive
        )
        for _ in range(40)
    ]
    query_vehiculos = """
        INSERT INTO VEHICULOS (id_propietario, marca_modelo, plazas_totales, tipo_propulsion, matricula_hash)
        VALUES (%s, %s, %s, %s, %s)
    """
    ejecutar_insert_global(conexiones, query_vehiculos, datos_vehiculos)

    # 4. RUTAS_CARPOOLING (60 registros)
    estados_ruta = ['Programada', 'En_Curso', 'Completada', 'Cancelada']
    datos_rutas = [
        (
            random.randint(1, 100),                # Conductor
            random.randint(1, 40),                 # Vehículo
            float(fake.latitude()),
            float(fake.longitude()),
            float(fake.latitude()),
            float(fake.longitude()),
            fake.date_time_this_year(),
            random.randint(1, 4),
            random.choice(estados_ruta)
        )
        for _ in range(60)
    ]
    query_rutas = """
        INSERT INTO RUTAS_CARPOOLING 
        (id_conductor, id_vehiculo, origen_lat, origen_lon, destino_lat, destino_lon, hora_salida, plazas_disponibles, estado)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    ejecutar_insert_global(conexiones, query_rutas, datos_rutas)

    # 5. RESERVAS_CARPOOLING (80 registros)
    estados_reserva = ['Pendiente', 'Confirmada', 'Rechazada', 'Cancelada']
    datos_reservas = [
        (
            random.randint(1, 60),                 # FK Ruta
            random.randint(1, 100),                # FK Pasajero
            float(fake.latitude()),
            float(fake.longitude()),
            random.choice(estados_reserva),
            fake.date_time_this_year()
        )
        for _ in range(80)
    ]
    query_reservas = """
        INSERT INTO RESERVAS_CARPOOLING 
        (id_ruta, id_pasajero, punto_recogida_lat, punto_recogida_lon, estado_reserva, fecha_reserva)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    ejecutar_insert_global(conexiones, query_reservas, datos_reservas)

    # 6. REGISTROS_GPS (200 registros)
    datos_gps = [
        (
            random.randint(1, 100),
            random.randint(1, 60),
            float(fake.latitude()),
            float(fake.longitude()),
            round(random.uniform(10.0, 120.0), 2),
            fake.date_time_this_year()
        )
        for _ in range(200)
    ]
    query_gps = """
        INSERT INTO REGISTROS_GPS (id_usuario, id_ruta, latitud, longitud, velocidad_kmh, timestamp_captura)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    ejecutar_insert_global(conexiones, query_gps, datos_gps)

    # 7. HISTORIAL_DESPLAZAMIENTOS (120 registros)
    modos_transporte = ['A_Pie', 'Bicicleta', 'Autobus', 'Carpooling', 'Coche_Individual']
    datos_historial = [
        (
            random.randint(1, 100),
            random.choice(modos_transporte),
            round(random.uniform(1.0, 45.0), 2),
            round(random.uniform(0.1, 5.5), 3),
            random.randint(5, 90),
            fake.date_this_year()
        )
        for _ in range(120)
    ]
    query_historial = """
        INSERT INTO HISTORIAL_DESPLAZAMIENTOS 
        (id_usuario, modo_transporte, distancia_km, co2_ahorrado_kg, tiempo_minutos, fecha_desplazamiento)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    ejecutar_insert_global(conexiones, query_historial, datos_historial)

    # 8. INCIDENCIAS_TRAFICO (30 registros)
    tipos_incidencia = ['Retencion', 'Obras', 'Accidente', 'Corte_Vial', 'Otro']
    gravedades = ['Bajo', 'Medio', 'Alto', 'Critico']
    datos_incidencias = [
        (
            random.choice(tipos_incidencia),
            float(fake.latitude()),
            float(fake.longitude()),
            fake.sentence(nb_words=8),             # Provider 7: Lorem
            random.choice(gravedades),
            fake.date_time_this_year(),
            fake.company()
        )
        for _ in range(30)
    ]
    query_incidencias = """
        INSERT INTO INCIDENCIAS_TRAFICO 
        (tipo_incidencia, latitud, longitud, descripcion, nivel_gravedad, fecha_inicio, fuente_dato)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    ejecutar_insert_global(conexiones, query_incidencias, datos_incidencias)

    # 9. ENCUESTAS_HABITOS (5 registros)
    datos_encuestas = [
        (
            f"Encuesta Mobility {2026} - Q{i+1}",
            fake.text(max_nb_chars=100),           # Provider 7: Lorem
            fake.date_this_year(),
            fake.date_this_year(),
            True
        )
        for i in range(5)
    ]
    query_encuestas = """
        INSERT INTO ENCUESTAS_HABITOS (titulo, descripcion, fecha_inicio, fecha_fin, activo)
        VALUES (%s, %s, %s, %s, %s)
    """
    ejecutar_insert_global(conexiones, query_encuestas, datos_encuestas)

    # 10. RESPUESTAS_ENCUESTA (50 registros)
    modos_habituales = ['A_Pie', 'Bicicleta', 'Autobus', 'Coche_Privado']
    datos_respuestas = [
        (
            random.randint(1, 5),
            fake.uuid4(),                          # Provider 8: UUID token anónimo
            random.choice(modos_habituales),
            random.randint(10, 60),
            fake.sentence()
        )
        for _ in range(50)
    ]
    query_respuestas = """
        INSERT INTO RESPUESTAS_ENCUESTA 
        (id_encuesta, token_usuario_anonimo, modo_habitual, tiempo_medio_min, comentarios_texto_libre)
        VALUES (%s, %s, %s, %s, %s)
    """
    ejecutar_insert_global(conexiones, query_respuestas, datos_respuestas)

    # 11. REGISTRO_METEOROLOGICO (40 registros)
    datos_clima = [
        (
            fake.date_this_year(),
            fake.time(),                           # Provider 6: Date/Time
            round(random.uniform(5.0, 38.0), 1),
            round(random.uniform(0.0, 25.0), 2),
            random.choice(['Soleado', 'Lluvioso', 'Nublado', 'Viento'])
        )
        for _ in range(40)
    ]
    query_clima = """
        INSERT INTO REGISTRO_METEOROLOGICO (fecha, hora, temperatura_c, precipitacion_mm, estado_tiempo)
        VALUES (%s, %s, %s, %s, %s)
    """
    ejecutar_insert_global(conexiones, query_clima, datos_clima)

    # Commit final y simultáneo para consolidar los cambios en las 3 BDs
    print(" Realizando COMMIT final en MySQL, PostgreSQL y MariaDB...")
    conn_mysql.commit()
    conn_postgres.commit()
    conn_mariadb.commit()

    # Cierre de conexiones
    conn_mysql.close()
    conn_postgres.close()
    conn_mariadb.close()

    print(" Poblado completado con éxito en los tres motores de bases de datos.")

if __name__ == "__main__":
    poblar_bases_de_datos()