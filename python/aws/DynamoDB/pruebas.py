"""
=============================================================================
SMARTRUTA & MOVILIDAD SOSTENIBLE - SUITE DE PRUEBAS EN AWS DYNAMODB (pruebas.py)
=============================================================================

Permite ejecutar las 9 pruebas de forma individual o conjunta mediante CLI:
  python pruebas.py --1        -> Crea 3 registros en cada tabla
  python pruebas.py --2        -> Obtiene 1 registro de cada tabla (get_item)
  python pruebas.py --3        -> Actualiza 1 registro de cada tabla (update_item)
  python pruebas.py --4        -> Elimina 1 registro de cada tabla (delete_item)
  python pruebas.py --5        -> Obtiene todos los registros de cada tabla (scan)
  python pruebas.py --6        -> Filtra registros con scan (usando GSI en la global)
  python pruebas.py --7        -> Eliminacion condicional (usando GSI en la global)
  python pruebas.py --8        -> Consulta con multiples filtros combinados
  python pruebas.py --9        -> Consultas PartiQL en cada tabla
  python pruebas.py --todas    -> Ejecuta todas las pruebas (1 a 9)
=============================================================================
"""

import argparse
import os
import time
from decimal import Decimal
from pathlib import Path

import boto3
from boto3.dynamodb.conditions import Attr, Key
from boto3.dynamodb.types import TypeDeserializer
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# pruebas.py -> DynamoDB -> aws -> python -> Negocio_SBD
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
client = session.client("dynamodb")
deserializer = TypeDeserializer()

# Referencias a las 3 tablas
tabla_mensajes = dynamodb.Table("MENSAJES_RUTA")
tabla_notificaciones = dynamodb.Table("NOTIFICACIONES_USUARIO")
tabla_posiciones = dynamodb.Table("POSICIONES_TIEMPO_REAL")

# Constantes deterministas para los datos de prueba (evitan colision con el seed 1..100)
TEST_ID_RUTA = 999
TEST_ID_USUARIO = 999
TEST_TIMESTAMPS = [
    "2026-11-16T10:00:00Z",
    "2026-11-16T10:01:00Z",
    "2026-11-16T10:02:00Z",
]


# -------------------------------
# FUNCIONES AUXILIARES
# -------------------------------

def deserializar_item(item_dynamodb):
    """Convierte un item en formato JSON de bajo nivel de DynamoDB a dict Python."""
    return {k: deserializer.deserialize(v) for k, v in item_dynamodb.items()}


def scan_completo(tabla, **kwargs):
    """Ejecuta un scan manejando la paginacion con LastEvaluatedKey."""
    items = []
    while True:
        respuesta = tabla.scan(**kwargs)
        items.extend(respuesta.get("Items", []))
        if "LastEvaluatedKey" not in respuesta:
            break
        kwargs["ExclusiveStartKey"] = respuesta["LastEvaluatedKey"]
    return items


# ================================================================================================
# PRUEBA 1: Crear tres registros en cada tabla
# ================================================================================================
def prueba_1_crear_registros():
    print("\n" + "=" * 80)
    print("PRUEBA 1: Crear tres registros en cada tabla")
    print("=" * 80)

    expira_en = int(time.time()) + 86400

    # 1. MENSAJES_RUTA (sin indices)
    mensajes = [
        {
            "id_ruta": TEST_ID_RUTA,
            "marca_tiempo": TEST_TIMESTAMPS[0],
            "id_usuario_emisor": TEST_ID_USUARIO,
            "texto": "Hola, salgo en 5 minutos hacia el punto de encuentro.",
            "leido": False,
        },
        {
            "id_ruta": TEST_ID_RUTA,
            "marca_tiempo": TEST_TIMESTAMPS[1],
            "id_usuario_emisor": 102,
            "texto": "Perfecto, ya estoy esperando en la parada.",
            "leido": True,
        },
        {
            "id_ruta": TEST_ID_RUTA,
            "marca_tiempo": TEST_TIMESTAMPS[2],
            "id_usuario_emisor": TEST_ID_USUARIO,
            "texto": "Llegando ahora mismo.",
            "leido": False,
        },
    ]
    for msg in mensajes:
        tabla_mensajes.put_item(Item=msg)
    print(f"[MENSAJES_RUTA] Insertados {len(mensajes)} registros (id_ruta={TEST_ID_RUTA}).")

    # 2. NOTIFICACIONES_USUARIO (con LSI_usuario_tipo)
    notificaciones = [
        {
            "id_usuario": TEST_ID_USUARIO,
            "marca_tiempo": TEST_TIMESTAMPS[0],
            "tipo": "reserva_confirmada",
            "mensaje": "Tu reserva para la ruta 999 ha sido confirmada.",
            "leida": False,
            "id_ruta": TEST_ID_RUTA,
            "expira_en": expira_en,
        },
        {
            "id_usuario": TEST_ID_USUARIO,
            "marca_tiempo": TEST_TIMESTAMPS[1],
            "tipo": "recordatorio_salida",
            "mensaje": "Tu viaje comienza en 15 minutos.",
            "leida": True,
            "id_ruta": TEST_ID_RUTA,
            "expira_en": expira_en,
        },
        {
            "id_usuario": TEST_ID_USUARIO,
            "marca_tiempo": TEST_TIMESTAMPS[2],
            "tipo": "incidencia_trafico",
            "mensaje": "Retenciones leves en la avenida principal.",
            "leida": False,
            "expira_en": expira_en,
        },
    ]
    for notif in notificaciones:
        tabla_notificaciones.put_item(Item=notif)
    print(f"[NOTIFICACIONES_USUARIO] Insertados {len(notificaciones)} registros (id_usuario={TEST_ID_USUARIO}).")

    # 3. POSICIONES_TIEMPO_REAL (con GSI_usuario_tiempo)
    posiciones = [
        {
            "id_ruta": TEST_ID_RUTA,
            "marca_tiempo": TEST_TIMESTAMPS[0],
            "id_usuario": TEST_ID_USUARIO,
            "latitud": Decimal("37.389092"),
            "longitud": Decimal("-5.984459"),
            "velocidad_kmh": Decimal("45.50"),
            "expira_en": expira_en,
        },
        {
            "id_ruta": TEST_ID_RUTA,
            "marca_tiempo": TEST_TIMESTAMPS[1],
            "id_usuario": TEST_ID_USUARIO,
            "latitud": Decimal("37.390120"),
            "longitud": Decimal("-5.983100"),
            "velocidad_kmh": Decimal("62.00"),
            "expira_en": expira_en,
        },
        {
            "id_ruta": TEST_ID_RUTA,
            "marca_tiempo": TEST_TIMESTAMPS[2],
            "id_usuario": TEST_ID_USUARIO,
            "latitud": Decimal("37.391500"),
            "longitud": Decimal("-5.981950"),
            "velocidad_kmh": Decimal("80.25"),
            "expira_en": expira_en,
        },
    ]
    for pos in posiciones:
        tabla_posiciones.put_item(Item=pos)
    print(f"[POSICIONES_TIEMPO_REAL] Insertados {len(posiciones)} registros (id_ruta={TEST_ID_RUTA}).")


# ================================================================================================
# PRUEBA 2: Obtener un registro de cada tabla
# ================================================================================================
def prueba_2_obtener_un_registro():
    print("\n" + "=" * 80)
    print("PRUEBA 2: Obtener un registro de cada tabla (get_item)")
    print("=" * 80)

    r1 = tabla_mensajes.get_item(
        Key={"id_ruta": TEST_ID_RUTA, "marca_tiempo": TEST_TIMESTAMPS[0]}
    )
    print("[MENSAJES_RUTA]:", r1.get("Item", "No encontrado (ejecuta --1 primero)"))

    r2 = tabla_notificaciones.get_item(
        Key={"id_usuario": TEST_ID_USUARIO, "marca_tiempo": TEST_TIMESTAMPS[0]}
    )
    print("[NOTIFICACIONES_USUARIO]:", r2.get("Item", "No encontrado (ejecuta --1 primero)"))

    r3 = tabla_posiciones.get_item(
        Key={"id_ruta": TEST_ID_RUTA, "marca_tiempo": TEST_TIMESTAMPS[0]}
    )
    print("[POSICIONES_TIEMPO_REAL]:", r3.get("Item", "No encontrado (ejecuta --1 primero)"))


# ================================================================================================
# PRUEBA 3: Actualizar un registro de cada tabla
# ================================================================================================
def prueba_3_actualizar_un_registro():
    print("\n" + "=" * 80)
    print("PRUEBA 3: Actualizar un registro de cada tabla (update_item)")
    print("=" * 80)

    u1 = tabla_mensajes.update_item(
        Key={"id_ruta": TEST_ID_RUTA, "marca_tiempo": TEST_TIMESTAMPS[0]},
        UpdateExpression="SET leido = :l, texto = :t",
        ExpressionAttributeValues={
            ":l": True,
            ":t": "Mensaje actualizado durante la prueba 3.",
        },
        ReturnValues="ALL_NEW",
    )
    print("[MENSAJES_RUTA] Actualizado:", u1.get("Attributes"))

    u2 = tabla_notificaciones.update_item(
        Key={"id_usuario": TEST_ID_USUARIO, "marca_tiempo": TEST_TIMESTAMPS[0]},
        UpdateExpression="SET leida = :l, mensaje = :m",
        ExpressionAttributeValues={
            ":l": True,
            ":m": "Notificacion marcada como leida en prueba 3.",
        },
        ReturnValues="ALL_NEW",
    )
    print("[NOTIFICACIONES_USUARIO] Actualizado:", u2.get("Attributes"))

    u3 = tabla_posiciones.update_item(
        Key={"id_ruta": TEST_ID_RUTA, "marca_tiempo": TEST_TIMESTAMPS[0]},
        UpdateExpression="SET velocidad_kmh = :v",
        ExpressionAttributeValues={":v": Decimal("95.75")},
        ReturnValues="ALL_NEW",
    )
    print("[POSICIONES_TIEMPO_REAL] Actualizado:", u3.get("Attributes"))


# ================================================================================================
# PRUEBA 4: Eliminar un registro de cada tabla
# ================================================================================================
def prueba_4_eliminar_un_registro():
    print("\n" + "=" * 80)
    print("PRUEBA 4: Eliminar un registro de cada tabla (delete_item)")
    print("=" * 80)

    d1 = tabla_mensajes.delete_item(
        Key={"id_ruta": TEST_ID_RUTA, "marca_tiempo": TEST_TIMESTAMPS[2]},
        ReturnValues="ALL_OLD",
    )
    print("[MENSAJES_RUTA] Eliminado:", d1.get("Attributes", "No existia el registro"))

    d2 = tabla_notificaciones.delete_item(
        Key={"id_usuario": TEST_ID_USUARIO, "marca_tiempo": TEST_TIMESTAMPS[2]},
        ReturnValues="ALL_OLD",
    )
    print("[NOTIFICACIONES_USUARIO] Eliminado:", d2.get("Attributes", "No existia el registro"))

    d3 = tabla_posiciones.delete_item(
        Key={"id_ruta": TEST_ID_RUTA, "marca_tiempo": TEST_TIMESTAMPS[2]},
        ReturnValues="ALL_OLD",
    )
    print("[POSICIONES_TIEMPO_REAL] Eliminado:", d3.get("Attributes", "No existia el registro"))


# ================================================================================================
# PRUEBA 5: Obtener todos los registros de cada tabla
# ================================================================================================
def prueba_5_obtener_todos():
    print("\n" + "=" * 80)
    print("PRUEBA 5: Obtener todos los registros de cada tabla (scan completo)")
    print("=" * 80)

    for nombre, tabla in [
        ("MENSAJES_RUTA", tabla_mensajes),
        ("NOTIFICACIONES_USUARIO", tabla_notificaciones),
        ("POSICIONES_TIEMPO_REAL", tabla_posiciones),
    ]:
        items = scan_completo(tabla)
        print(f"[{nombre}] Total de registros: {len(items)}")
        for item in items[:3]:
            print("   ->", item)


# ================================================================================================
# PRUEBA 6: Obtener un conjunto de registros de un filtrado de cada tabla usando scan.
#           En la global utilizar el indice global para ello.
# ================================================================================================
def prueba_6_scan_filtrado():
    print("\n" + "=" * 80)
    print("PRUEBA 6: Filtrado con scan en cada tabla (usando GSI en POSICIONES_TIEMPO_REAL)")
    print("=" * 80)

    # 1. MENSAJES_RUTA: scan con filtro sobre mensajes no leidos
    res_msg = scan_completo(
        tabla_mensajes,
        FilterExpression=Attr("leido").eq(False),
    )
    print(f"[MENSAJES_RUTA] Mensajes con leido=False: {len(res_msg)}")
    for item in res_msg[:3]:
        print("   ->", item)

    # 2. NOTIFICACIONES_USUARIO: scan con filtro sobre tipo de notificacion
    res_notif = scan_completo(
        tabla_notificaciones,
        FilterExpression=Attr("tipo").eq("reserva_confirmada"),
    )
    print(f"[NOTIFICACIONES_USUARIO] Notificaciones tipo='reserva_confirmada': {len(res_notif)}")
    for item in res_notif[:3]:
        print("   ->", item)

    # 3. POSICIONES_TIEMPO_REAL: scan utilizando explicitamente el indice global GSI_usuario_tiempo
    res_pos = scan_completo(
        tabla_posiciones,
        IndexName="GSI_usuario_tiempo",
        FilterExpression=Attr("velocidad_kmh").gt(Decimal("50.0")),
    )
    print(f"[POSICIONES_TIEMPO_REAL - GSI_usuario_tiempo] Posiciones con velocidad > 50 km/h: {len(res_pos)}")
    for item in res_pos[:3]:
        print("   ->", item)


# ================================================================================================
# PRUEBA 7: Realizar una eliminacion condicional de cada tabla.
#           En la global utilizar el indice global para ello.
# ================================================================================================
def prueba_7_eliminacion_condicional():
    print("\n" + "=" * 80)
    print("PRUEBA 7: Eliminacion condicional en cada tabla (usando GSI en la global)")
    print("=" * 80)

    # 1. MENSAJES_RUTA: eliminar solo si el mensaje ya ha sido leido (leido == True)
    try:
        del_msg = tabla_mensajes.delete_item(
            Key={"id_ruta": TEST_ID_RUTA, "marca_tiempo": TEST_TIMESTAMPS[1]},
            ConditionExpression=Attr("leido").eq(True),
            ReturnValues="ALL_OLD",
        )
        print("[MENSAJES_RUTA] Eliminacion condicional exitosa:", del_msg.get("Attributes", "No existia"))
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            print("[MENSAJES_RUTA] No se elimino: no cumplia la condicion (leido == True).")
        else:
            raise

    # 2. NOTIFICACIONES_USUARIO: eliminar solo si la notificacion esta leida (leida == True)
    try:
        del_notif = tabla_notificaciones.delete_item(
            Key={"id_usuario": TEST_ID_USUARIO, "marca_tiempo": TEST_TIMESTAMPS[1]},
            ConditionExpression=Attr("leida").eq(True),
            ReturnValues="ALL_OLD",
        )
        print("[NOTIFICACIONES_USUARIO] Eliminacion condicional exitosa:", del_notif.get("Attributes", "No existia"))
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            print("[NOTIFICACIONES_USUARIO] No se elimino: no cumplia la condicion (leida == True).")
        else:
            raise

    # 3. POSICIONES_TIEMPO_REAL:
    # DynamoDB requiere la clave primaria base en delete_item, por lo que primero consultamos
    # el Indice Global (GSI_usuario_tiempo) por id_usuario para localizar el registro a borrar.
    consulta_gsi = tabla_posiciones.query(
        IndexName="GSI_usuario_tiempo",
        KeyConditionExpression=Key("id_usuario").eq(TEST_ID_USUARIO),
        Limit=1,
    )
    items_gsi = consulta_gsi.get("Items", [])

    if not items_gsi:
        print("[POSICIONES_TIEMPO_REAL - GSI_usuario_tiempo] No hay registros para id_usuario=999 (ejecuta --1 primero).")
    else:
        objetivo = items_gsi[0]
        try:
            del_pos = tabla_posiciones.delete_item(
                Key={
                    "id_ruta": objetivo["id_ruta"],
                    "marca_tiempo": objetivo["marca_tiempo"],
                },
                ConditionExpression=Attr("velocidad_kmh").gt(Decimal("10.0")),
                ReturnValues="ALL_OLD",
            )
            print(
                "[POSICIONES_TIEMPO_REAL - GSI_usuario_tiempo] Eliminacion condicional exitosa:",
                del_pos.get("Attributes"),
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                print("[POSICIONES_TIEMPO_REAL] No se elimino: velocidad_kmh <= 10.0.")
            else:
                raise


# ================================================================================================
# PRUEBA 8: Obtener un conjunto de datos a traves de varios filtros aplicado en cada tabla.
# ================================================================================================
def prueba_8_multiples_filtros():
    print("\n" + "=" * 80)
    print("PRUEBA 8: Consulta con multiples filtros aplicados en cada tabla")
    print("=" * 80)

    # 1. MENSAJES_RUTA: id_ruta entre 1 y 999 AND leido == False
    f_msg = scan_completo(
        tabla_mensajes,
        FilterExpression=Attr("id_ruta").between(1, TEST_ID_RUTA) & Attr("leido").eq(False),
    )
    print(f"[MENSAJES_RUTA] Filtros (id_ruta 1..999 AND leido=False): {len(f_msg)} resultados")
    for item in f_msg[:3]:
        print("   ->", item)

    # 2. NOTIFICACIONES_USUARIO: leida == False AND (tipo == 'reserva_confirmada' OR tipo == 'recordatorio_salida')
    f_notif = scan_completo(
        tabla_notificaciones,
        FilterExpression=Attr("leida").eq(False)
        & (Attr("tipo").eq("reserva_confirmada") | Attr("tipo").eq("recordatorio_salida")),
    )
    print(f"[NOTIFICACIONES_USUARIO] Filtros (leida=False AND tipo en confirmada/recordatorio): {len(f_notif)} resultados")
    for item in f_notif[:3]:
        print("   ->", item)

    # 3. POSICIONES_TIEMPO_REAL: velocidad_kmh entre 20 y 110 AND id_usuario >= 1
    f_pos = scan_completo(
        tabla_posiciones,
        FilterExpression=Attr("velocidad_kmh").between(Decimal("20.0"), Decimal("110.0"))
        & Attr("id_usuario").gte(1),
    )
    print(f"[POSICIONES_TIEMPO_REAL] Filtros (velocidad 20..110 AND id_usuario >= 1): {len(f_pos)} resultados")
    for item in f_pos[:3]:
        print("   ->", item)


# ================================================================================================
# PRUEBA 9: Utilizar PartiQL statement en cada tabla
# ================================================================================================
def prueba_9_partiql():
    print("\n" + "=" * 80)
    print("PRUEBA 9: Consultas PartiQL en cada tabla")
    print("=" * 80)

    # 1. PartiQL en MENSAJES_RUTA
    resp_msg = client.execute_statement(
        Statement='SELECT id_ruta, marca_tiempo, texto, leido FROM "MENSAJES_RUTA" WHERE "id_ruta" = ?',
        Parameters=[{"N": str(TEST_ID_RUTA)}],
    )
    items_msg = [deserializar_item(i) for i in resp_msg.get("Items", [])]
    print(f"[PartiQL - MENSAJES_RUTA] {len(items_msg)} registros encontrados:")
    for item in items_msg:
        print("   ->", item)

    # 2. PartiQL en NOTIFICACIONES_USUARIO (consultando su indice local LSI_usuario_tipo)
    resp_notif = client.execute_statement(
        Statement='SELECT id_usuario, tipo, marca_tiempo, mensaje FROM "NOTIFICACIONES_USUARIO"."LSI_usuario_tipo" WHERE "id_usuario" = ?',
        Parameters=[{"N": str(TEST_ID_USUARIO)}],
    )
    items_notif = [deserializar_item(i) for i in resp_notif.get("Items", [])]
    print(f"[PartiQL - NOTIFICACIONES_USUARIO (LSI)] {len(items_notif)} registros encontrados:")
    for item in items_notif:
        print("   ->", item)

    # 3. PartiQL en POSICIONES_TIEMPO_REAL (consultando su indice global GSI_usuario_tiempo)
    resp_pos = client.execute_statement(
        Statement='SELECT id_usuario, id_ruta, marca_tiempo, velocidad_kmh FROM "POSICIONES_TIEMPO_REAL"."GSI_usuario_tiempo" WHERE "id_usuario" = ?',
        Parameters=[{"N": str(TEST_ID_USUARIO)}],
    )
    items_pos = [deserializar_item(i) for i in resp_pos.get("Items", [])]
    print(f"[PartiQL - POSICIONES_TIEMPO_REAL (GSI)] {len(items_pos)} registros encontrados:")
    for item in items_pos:
        print("   ->", item)


# -------------------------------
# SELECTOR CLI DE PRUEBAS
# -------------------------------

PRUEBAS_DISPONIBLES = {
    1: ("Crear tres registros en cada tabla", prueba_1_crear_registros),
    2: ("Obtener un registro de cada tabla", prueba_2_obtener_un_registro),
    3: ("Actualizar un registro de cada tabla", prueba_3_actualizar_un_registro),
    4: ("Eliminar un registro de cada tabla", prueba_4_eliminar_un_registro),
    5: ("Obtener todos los registros de cada tabla", prueba_5_obtener_todos),
    6: ("Filtrar registros usando scan (con GSI en la global)", prueba_6_scan_filtrado),
    7: ("Eliminacion condicional en cada tabla (con GSI en la global)", prueba_7_eliminacion_condicional),
    8: ("Obtener datos mediante varios filtros combinados", prueba_8_multiples_filtros),
    9: ("Utilizar PartiQL statement en cada tabla", prueba_9_partiql),
}


def parsear_argumentos():
    parser = argparse.ArgumentParser(
        description="Ejecuta pruebas individuales (--1 .. --9) o completas (--todas) sobre DynamoDB."
    )
    for num, (descripcion, _) in PRUEBAS_DISPONIBLES.items():
        parser.add_argument(
            f"--{num}",
            dest="pruebas",
            action="append_const",
            const=num,
            help=f"Prueba {num}: {descripcion}",
        )
    parser.add_argument(
        "--todas",
        action="store_true",
        help="Ejecuta todas las pruebas del 1 al 9 en orden.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parsear_argumentos()

    if args.todas or not args.pruebas:
        seleccion = list(PRUEBAS_DISPONIBLES.keys())
    else:
        seleccion = args.pruebas

    for num_prueba in seleccion:
        _, funcion_prueba = PRUEBAS_DISPONIBLES[num_prueba]
        funcion_prueba()