# 22 - Obtén datos de la base de datos de Redis e incluyelos en de alguna de las bases de datos de la tarea anterior (1 puntos)
"""
Importa a PostgreSQL los datos que script_21.py dejó previamente en Redis.

Flujo del script:
    1. Lee de Redis los hashes con prefijo 'smartruta:mysql:usuario:'.
       Si no existen, intenta leer la clave JSON completa
       'smartruta:mysql:usuarios_json'.
    2. Crea la tabla USUARIOS_DESDE_REDIS en PostgreSQL si no existe.
    3. Inserta o actualiza los registros leídos de Redis en dicha tabla.

De este modo se completa el camino inverso SQL -> Redis -> SQL.
"""

import json
import os
from datetime import date, datetime
from pathlib import Path

import psycopg2
import redis
from dotenv import load_dotenv
from redis.exceptions import ResponseError


# --- LOCALIZACIÓN DEL PROYECTO Y CARGA DE VARIABLES DE ENTORNO ---
# Este script está en python/redis/, por lo que la raíz queda tres niveles arriba.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env_path = BASE_DIR / "Docker" / ".env"
if not env_path.exists():
    env_path = BASE_DIR / "docker" / ".env"

load_dotenv(dotenv_path=env_path)

SHARED_PASS = os.getenv("SHARED_PASSWORD", "smartruta_pass_123")
DB_NAME_DEFAULT = os.getenv("MYSQL_DATABASE", "smartruta_db")
DB_USER_DEFAULT = os.getenv("MYSQL_USER", "smartruta_user")


# --- CONFIGURACIÓN DE REDIS (ORIGEN DE LOS DATOS) ---
conexionRedis = redis.ConnectionPool(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=int(os.getenv("REDIS_DB", 0)),
    decode_responses=True
)
baseDatosRedis = redis.Redis(connection_pool=conexionRedis)


# --- CONFIGURACIÓN DE PostgreSQL (DESTINO DE LOS DATOS) ---
CONFIG_POSTGRES = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", 5432)),
    "user": os.getenv("POSTGRES_USER", DB_USER_DEFAULT),
    "password": os.getenv("POSTGRES_PASSWORD", SHARED_PASS),
    "dbname": os.getenv("POSTGRES_DB", DB_NAME_DEFAULT)
}


# --- CLAVES DE REDIS QUE SE VAN A LEER ---
PREFIJO_USUARIO = "smartruta:mysql:usuario:"
CLAVE_JSON = "smartruta:mysql:usuarios_json"
CLAVE_METADATOS = "smartruta:mysql:importacion"


# --- SQL DE DESTINO ---
SQL_CREAR_TABLA = """
    CREATE TABLE IF NOT EXISTS USUARIOS_DESDE_REDIS (
        id_usuario INTEGER PRIMARY KEY,
        nombre VARCHAR(100) NOT NULL,
        email VARCHAR(150),
        tipo_usuario VARCHAR(50),
        consentimiento_rgpd BOOLEAN DEFAULT FALSE,
        fecha_registro TIMESTAMP,
        codigo_postal VARCHAR(10),
        barrio_zona VARCHAR(100),
        fecha_importacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
"""

SQL_INSERTAR_O_ACTUALIZAR = """
    INSERT INTO USUARIOS_DESDE_REDIS (
        id_usuario,
        nombre,
        email,
        tipo_usuario,
        consentimiento_rgpd,
        fecha_registro,
        codigo_postal,
        barrio_zona,
        fecha_importacion
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
    ON CONFLICT (id_usuario) DO UPDATE SET
        nombre = EXCLUDED.nombre,
        email = EXCLUDED.email,
        tipo_usuario = EXCLUDED.tipo_usuario,
        consentimiento_rgpd = EXCLUDED.consentimiento_rgpd,
        fecha_registro = EXCLUDED.fecha_registro,
        codigo_postal = EXCLUDED.codigo_postal,
        barrio_zona = EXCLUDED.barrio_zona,
        fecha_importacion = CURRENT_TIMESTAMP;
"""


def convertir_a_texto(valor):
    """Normaliza los valores recuperados de Redis para tratarlos como texto."""
    if valor is None:
        return ""
    if isinstance(valor, bool):
        return "1" if valor else "0"
    return str(valor)


def ordenar_clave(clave):
    """Ordena las claves por el identificador numérico final cuando sea posible."""
    sufijo = clave.rsplit(":", 1)[-1]
    try:
        return (0, int(sufijo))
    except ValueError:
        return (1, sufijo)


def obtener_desde_hashes():
    """Lee de Redis todos los hashes individuales creados por script_21.py."""
    claves = sorted(
        baseDatosRedis.scan_iter(match=f"{PREFIJO_USUARIO}*"),
        key=ordenar_clave
    )

    registros = []

    for clave in claves:
        if baseDatosRedis.type(clave) == "hash":
            registros.append(baseDatosRedis.hgetall(clave))

    return registros


def obtener_desde_json():
    """Lee la clave JSON completa como alternativa si no hay hashes individuales."""
    if not baseDatosRedis.exists(CLAVE_JSON):
        return []

    # Si la clave es una cadena normal (o RedisJSON no está disponible), Redis
    # responde con ResponseError y se lee como texto. Otros errores se propagan.
    try:
        datos = baseDatosRedis.json().get(CLAVE_JSON)
    except ResponseError:
        contenido = baseDatosRedis.get(CLAVE_JSON)
        datos = json.loads(contenido) if contenido else []

    if isinstance(datos, dict):
        datos = [datos]

    if not isinstance(datos, list):
        return []

    return [
        {campo: convertir_a_texto(valor) for campo, valor in registro.items()}
        for registro in datos
        if isinstance(registro, dict)
    ]


def obtener_datos_redis():
    """Obtiene los registros de Redis y devuelve también la fuente utilizada."""
    registros = obtener_desde_hashes()

    if registros:
        return registros, f"hashes con prefijo '{PREFIJO_USUARIO}'"

    registros = obtener_desde_json()

    if registros:
        return registros, f"clave JSON '{CLAVE_JSON}'"

    return [], "sin datos"


def obtener_metadatos_redis():
    """Recupera, si existe, la información de la importación realizada en script_21.py."""
    if baseDatosRedis.exists(CLAVE_METADATOS):
        return baseDatosRedis.hgetall(CLAVE_METADATOS)
    return {}


def interpretar_booleano(valor):
    """Convierte los distintos formatos de Redis en un booleano de PostgreSQL."""
    return str(valor).strip().lower() in ("1", "true", "t", "yes", "si", "sí")


def interpretar_fecha(valor):
    """Convierte el texto ISO de Redis en un datetime para PostgreSQL."""
    if not valor:
        return None

    if isinstance(valor, datetime):
        return valor

    if isinstance(valor, date):
        return datetime.combine(valor, datetime.min.time())

    texto = str(valor).strip().replace("Z", "+00:00")

    try:
        return datetime.fromisoformat(texto)
    except ValueError:
        return None


def convertir_registro(registro):
    """Transforma un registro de Redis en una tupla preparada para el INSERT."""
    id_usuario = registro.get("id_usuario")

    if id_usuario is None or str(id_usuario).strip() == "":
        return None

    try:
        id_usuario = int(id_usuario)
    except (TypeError, ValueError):
        print(f"Aviso: se omite un registro con id_usuario no válido: {id_usuario}")
        return None

    nombre = convertir_a_texto(registro.get("nombre")).strip() or "Sin nombre"
    email = convertir_a_texto(registro.get("email")).strip() or None
    tipo_usuario = convertir_a_texto(registro.get("tipo_usuario")).strip() or None
    codigo_postal = convertir_a_texto(registro.get("codigo_postal")).strip() or None
    barrio_zona = convertir_a_texto(registro.get("barrio_zona")).strip() or None

    return (
        id_usuario,
        nombre,
        email,
        tipo_usuario,
        interpretar_booleano(registro.get("consentimiento_rgpd")),
        interpretar_fecha(registro.get("fecha_registro")),
        codigo_postal,
        barrio_zona
    )


def guardar_en_postgres(registros):
    """Crea la tabla de destino e inserta o actualiza los registros de Redis."""
    filas = []

    for registro in registros:
        fila = convertir_registro(registro)
        if fila is not None:
            filas.append(fila)

    if not filas:
        print("No hay registros válidos que insertar en PostgreSQL.")
        return 0

    print(f"Conectando a PostgreSQL (puerto {CONFIG_POSTGRES['port']})...")
    conexion = psycopg2.connect(**CONFIG_POSTGRES)

    try:
        with conexion.cursor() as cursor:
            cursor.execute(SQL_CREAR_TABLA)
            cursor.executemany(SQL_INSERTAR_O_ACTUALIZAR, filas)

        conexion.commit()
        print(f"Se han insertado o actualizado {len(filas)} registros en la tabla "
              "USUARIOS_DESDE_REDIS.")
        return len(filas)

    except Exception:
        conexion.rollback()
        raise

    finally:
        conexion.close()


def main():
    print("=" * 70)
    print("22 - IMPORTACIÓN DE DATOS REDIS A SQL (PostgreSQL)")
    print("=" * 70)

    try:
        registros, fuente = obtener_datos_redis()

        if not registros:
            print("No se han encontrado datos de usuarios en Redis.")
            print("Ejecuta primero 'python redis/script_21.py' para cargar en Redis "
                  "los datos procedentes de MySQL.")
            return

        metadatos = obtener_metadatos_redis()

        print(f"Origen en Redis: {fuente}")
        print(f"Registros leídos de Redis: {len(registros)}")

        if metadatos:
            print("Metadatos de la importación original:")
            print(f"  - Origen SQL: {metadatos.get('origen', 'no disponible')}")
            print(f"  - Tabla: {metadatos.get('tabla', 'no disponible')}")
            print(f"  - Fecha: {metadatos.get('fecha_importacion', 'no disponible')}")

        print("\nMuestra de los primeros registros leídos:")
        for registro in registros[:5]:
            print(f"  - ID {registro.get('id_usuario')} | "
                  f"{registro.get('nombre')} | {registro.get('email')} | "
                  f"{registro.get('tipo_usuario')}")

        print("\nGuardando los datos en PostgreSQL...")
        total = guardar_en_postgres(registros)

        print(f"\nImportación completada: {total} registros de Redis guardados en "
              "PostgreSQL (tabla USUARIOS_DESDE_REDIS).")

    except Exception as error:
        print(f"ERROR durante la importación de Redis a PostgreSQL: {error}")
        print("Comprueba que Redis y PostgreSQL estén levantados y que las "
              "credenciales del archivo Docker/.env sean correctas.")

    finally:
        baseDatosRedis.close()
        print("=" * 70)


if __name__ == "__main__":
    main()