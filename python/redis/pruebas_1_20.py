import json
import redis
from redis.commands.search.field import TextField, NumericField, TagField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.query import Query
from redis.commands.search.aggregation import AggregateRequest
import redis.commands.search.reducers as reducers


conexionRedis = redis.ConnectionPool(host='localhost', port=6379, db=0, decode_responses=True)
baseDatosRedis = redis.Redis(connection_pool=conexionRedis)




# 1- Crear registros clave-valor(0.25 puntos)
def add_data():
    datos = {
        "vehiculo:1": "activo",
        "vehiculo:2": "activo",
        "vehiculo:3": "inactivo",
        "vehiculo:10": "activo",
        "vehiculo:A1": "disponible",
        "vehiculo:B1": "mantenimiento",
        "contador:viaje:1": "10",
        "contador:viaje:2": "25",
        "contador:viaje:3": "15",
        "usuario:admin": "superusuario",
        "ciudad:sede": "Madrid"
    }
    for clave, valor in datos.items():
        baseDatosRedis.set(clave, valor)
        
    print("Registros clave-valor creados correctamente:")
    
    for clave, valor in datos.items():
        print(f"  {clave} => {valor}")
        
    return datos


# 2 - Obtener y mostrar el número de claves registradas (0.25 puntos)
def get_num_key():
    num_claves = baseDatosRedis.dbsize()
    print(f"Número total de claves registradas: {num_claves}")
    return num_claves


# 3 - Obtener y mostrar un registro en base a una clave (0.25 puntos)
def get_data(key: str):
    valor = baseDatosRedis.get(key)
    print(f"Registro obtenido -> Clave: '{key}' | Valor: '{valor}'")
    return valor


# 4 - Actualizar el valor de una clave y mostrar el nuevo valor(0.25 puntos)
def update_data(key: str, new_value: str):
    
    baseDatosRedis.set(key, new_value)
    
    valor_actualizado = baseDatosRedis.get(key)
    
    print(f"Clave '{key}' actualizada con éxito -> Nuevo valor: '{valor_actualizado}'")
    
    return valor_actualizado


# 5 - Eliminar una clave-valor y mostrar la clave y el valor eliminado(0.25 puntos)
def delete_data(key: str):
    valor_eliminado = baseDatosRedis.get(key)
    
    if valor_eliminado is not None:
        baseDatosRedis.delete(key)
        print(f"Clave eliminada: '{key}' | Valor que tenía: '{valor_eliminado}'")
    else:
        print(f"La clave '{key}' no existe en Redis.")
    
    return valor_eliminado


# 6 - Obtener y mostrar todas las claves guardadas (0.25 puntos)
def get_all_keys():
    claves = baseDatosRedis.keys("*")
    
    print(f"Total claves encontradas ({len(claves)}):")
    
    for clave in claves:
        print(f"  - {clave}")
    
    return claves


# 7 - Obtener y mostrar todos los valores guardados(0.25 puntos)
def get_all_values():
    
    claves = baseDatosRedis.keys("*")
    
    print(f"Todos los valores guardados ({len(claves)} registros):")
    
    valores = {}
    
    for clave in claves:
        
        tipo = baseDatosRedis.type(clave)
        
        match (tipo):
            case "string": 
                val = baseDatosRedis.get(clave)
            
            case "list":
                val = baseDatosRedis.lrange(clave, 0, -1)
            
            case "hash":
                val = baseDatosRedis.hgetall(clave)
            
            case "ReJSON-RL":
                val = baseDatosRedis.json().get(clave)
            
            case _:
                val = f"<{tipo}>"

        valores[clave] = val
        
        print(f"  Clave: {clave} ({tipo}) => {val}")
        
    return valores

# 8,9,10 - Obtener y mostrar varios registros con una clave con un patrón:
def get_keys_pattern(pattern: str):
        
    claves = baseDatosRedis.keys(pattern)
    
    print(f"\nRegistros coincidentes con patrón '*' ('{pattern}'):")
    
    registros = {}
    
    for clave in claves:
        
        if baseDatosRedis.type(clave) == "string":
            
            registros[clave] = baseDatosRedis.get(clave)
            
            print(f"  {clave} => {registros[clave]}")
    
    return registros

# 8 - Obtener y mostrar varios registros con una clave con un patrón en común usando * (0.5 puntos)
def get_keys_pattern_asterisk(pattern: str = "vehiculo:*"):
    
    print(f"\nRegistros coincidentes con patrón '*' ('{pattern}'):")
    
    return get_keys_pattern(pattern)

# 9 - Obtener y mostrar varios registros con una clave con un patrón en común usando [] (0.5 puntos)
def get_keys_pattern_brackets(pattern: str = "vehiculo:[1-3]"):

    print(f"\nRegistros coincidentes con patrón '[]' ('{pattern}'):")
    
    return get_keys_pattern(pattern)


# 10 - Obtener y mostrar varios registros con una clave con un patrón en común usando ? (0.5 puntos)
def get_keys_pattern_question(pattern: str = "vehiculo:?"):
    
    print(f"\nRegistros coincidentes con patrón '?' ('{pattern}'):")
    
    return get_keys_pattern(pattern)


# 11 - Obtener y mostrar varios registros y filtrarlos por un valor en concreto. (0.5 puntos)
def filter_by_value(target_value: str = "activo", pattern: str = "vehiculo:*"):
    claves = baseDatosRedis.keys(pattern)
    
    print(f"\nRegistros con patrón '{pattern}' filtrados por valor '{target_value}':")
    
    filtrados = {}
    
    for clave in claves:
        
        if baseDatosRedis.type(clave) == "string":
            
            valor = baseDatosRedis.get(clave)
            
            if valor == target_value:
                filtrados[clave] = valor
                print(f"  {clave} => {valor}")
    
    return filtrados


# 12 - Actualizar una serie de registros en base a un filtro (por ejemplo aumentar su valor en 1 )(0.5 puntos)
def update_by_filter(pattern: str = "contador:viaje:*", increment: int = 1):
    
    claves = baseDatosRedis.keys(pattern)
    
    print(f"\nActualizando registros con patrón '{pattern}' (incrementando en {increment}):")
    
    actualizados = {}
    
    for clave in claves:
        
        if baseDatosRedis.type(clave) == "string":
            
            valor_antiguo = baseDatosRedis.get(clave)
            
            try:
                
                nuevo_valor = baseDatosRedis.incrby(clave, increment)
                
                actualizados[clave] = nuevo_valor
                
                print(f"  {clave}: {valor_antiguo} -> {nuevo_valor}")
                
            except Exception:
                
                print(f"El valor no es un numero entero")

    return actualizados


# 13 - Eliminar una serie de registros en base a un filtro (0.5 puntos)
def delete_by_filter(pattern: str = "vehiculo:*", filter_value: str = "inactivo"):
    
    claves = baseDatosRedis.keys(pattern)
    
    print(f"\nEliminando registros con patrón '{pattern}' cuyo valor sea '{filter_value}':")
    
    eliminados = {}
    
    for clave in claves:
        
        if baseDatosRedis.type(clave) == "string":
            
            valor = baseDatosRedis.get(clave)
            
            if valor == filter_value:
                
                baseDatosRedis.delete(clave)
                
                eliminados[clave] = valor
                
                print(f"  Eliminado -> Clave: {clave} | Valor: {valor}")
    
    return eliminados


# 14 - Crear una estructura en JSON de array de los datos que vayais a almacenar(0.5 puntos)
def create_json_structure(key: str = "smartruta:rutas_json"):
    
    rutas_array = [
        {"id_ruta": 101, "ciudad": "Madrid", "tipo_transporte": "autobus", "distancia_km": 15.5, "activo": True},
        {"id_ruta": 102, "ciudad": "Barcelona", "tipo_transporte": "metro", "distancia_km": 8.2, "activo": True},
        {"id_ruta": 103, "ciudad": "Valencia", "tipo_transporte": "bicicleta", "distancia_km": 4.0, "activo": False},
        {"id_ruta": 104, "ciudad": "Madrid", "tipo_transporte": "patinete", "distancia_km": 2.5, "activo": True},
        {"id_ruta": 105, "ciudad": "Sevilla", "tipo_transporte": "autobus", "distancia_km": 12.0, "activo": False}
    ]
    
    try:
        baseDatosRedis.json().set(key, "$", rutas_array)
        
        print(f"Estructura JSON (array) almacenada con RedisJSON en la clave '{key}'")
    
    except Exception:
        
        baseDatosRedis.set(key, json.dumps(rutas_array))
        
        print(f"Estructura JSON (array) almacenada como JSON string en la clave '{key}'")
    
    print(json.dumps(rutas_array, indent=2, ensure_ascii=False))
    
    return rutas_array


# 15 - Realizar un filtro por cada atributo de la estructura JSON anterior (0.5 puntos)
def filter_json_attributes(key: str = "smartruta:rutas_json"):
    try:
        datos = baseDatosRedis.json().get(key)
        
    except Exception:
        
        raw = baseDatosRedis.get(key)
        datos = json.loads(raw) if raw else []

    if not isinstance(datos, list):
        datos = []

    print("\n--- Filtro por cada atributo de la estructura JSON ---")
    f_id = [item for item in datos if item.get("id_ruta", 0) > 102]
    print(f"1. Filtro por 'id_ruta > 102': {f_id}")

    f_ciudad = [item for item in datos if item.get("ciudad") == "Madrid"]
    print(f"2. Filtro por 'ciudad == Madrid': {f_ciudad}")

    f_tipo = [item for item in datos if item.get("tipo_transporte") == "autobus"]
    print(f"3. Filtro por 'tipo_transporte == autobus': {f_tipo}")

    f_dist = [item for item in datos if item.get("distancia_km", 0) >= 10.0]
    print(f"4. Filtro por 'distancia_km >= 10.0': {f_dist}")

    f_activo = [item for item in datos if item.get("activo") is True]
    print(f"5. Filtro por 'activo == True': {f_activo}")

    return {
        "por_id_ruta": f_id,
        "por_ciudad": f_ciudad,
        "por_tipo_transporte": f_tipo,
        "por_distancia_km": f_dist,
        "por_activo": f_activo
    }


# 16 - Crear una lista en Redis (0.25 puntos)
def create_redis_list(list_key: str = "smartruta:viajes_lista"):
    
    baseDatosRedis.delete(list_key)
    
    elementos = [
        "viaje:001:completado:Madrid",
        "viaje:002:en_curso:Madrid",
        "viaje:003:cancelado:Barcelona",
        "viaje:004:completado:Valencia",
        "viaje:005:en_curso:Sevilla"
    ]
    
    baseDatosRedis.rpush(list_key, *elementos)
    
    total = baseDatosRedis.llen(list_key)
    
    contenido = baseDatosRedis.lrange(list_key, 0, -1)
    
    print(f"Lista '{list_key}' creada con {total} elementos:")
    
    for idx, elem in enumerate(contenido):
        print(f"  [{idx}] {elem}")
        
    return contenido


# 17 - Obtener elementos de una lista con un filtro en concreto(0.5 puntos)
def filter_redis_list(list_key: str = "smartruta:viajes_lista", filter_term: str = "completado"):
    
    elementos = baseDatosRedis.lrange(list_key, 0, -1)
    
    filtrados = [elem for elem in elementos if filter_term in elem]
    
    print(f"Elementos de la lista '{list_key}' que contienen '{filter_term}':")
    
    for elem in filtrados:
        print(f"  - {elem}")
        
    return filtrados


# 18 - Crea datos con índices, definiendo un esquema de al menos tres campos (0.5 puntos)
INDEX_NAME = "idx:vehiculos"
DOC_PREFIX = "vehiculo_idx:"

def create_indexed_data():
    docs = [
        {"doc_id": f"{DOC_PREFIX}1", "modelo": "Tesla Model 3", "autonomia_km": 450, "categoria": "electrico"},
        {"doc_id": f"{DOC_PREFIX}2", "modelo": "Nissan Leaf", "autonomia_km": 270, "categoria": "electrico"},
        {"doc_id": f"{DOC_PREFIX}3", "modelo": "Toyota Prius", "autonomia_km": 800, "categoria": "hibrido"},
        {"doc_id": f"{DOC_PREFIX}4", "modelo": "Renault Zoe", "autonomia_km": 300, "categoria": "electrico"},
        {"doc_id": f"{DOC_PREFIX}5", "modelo": "Hyundai Ioniq", "autonomia_km": 520, "categoria": "hibrido"}
    ]

    schema = (
        TextField("modelo"),
        NumericField("autonomia_km"),
        TagField("categoria")
    )
    definition = IndexDefinition(prefix=[DOC_PREFIX], index_type=IndexType.HASH)

    try:
        baseDatosRedis.ft(INDEX_NAME).dropindex(delete_documents=False)
    except Exception:
        pass

    try:
        
        baseDatosRedis.ft(INDEX_NAME).create_index(schema, definition=definition)
        
        print(f"Índice '{INDEX_NAME}' creado en RediSearch con esquema: modelo (TEXT), autonomia_km (NUMERIC), categoria (TAG).")
        
    except Exception as e:
        print(f"Aviso RediSearch: {e} (se mantendrán también índices secundarios en Hashes/Sets).")

    for doc in docs:
        doc_id = doc["doc_id"]
        campos = {k: str(v) for k, v in doc.items() if k != "doc_id"}
        
        baseDatosRedis.hset(doc_id, mapping=campos)
        
        baseDatosRedis.sadd(f"idx_manual:categoria:{campos['categoria']}", doc_id)
        
        print(f"  Documento insertado: {doc_id} => {campos}")
        
    return docs


# 19 - Realiza una búsqueda con índices en base a un campo(0.5 puntos)
def search_indexed_data(category: str = "electrico"):
    
    print(f"\n--- Búsqueda con índices para campo 'categoria' = '{category}' ---")
    
    try:
        q = Query(f"@categoria:{{{category}}}")
        
        res = baseDatosRedis.ft(INDEX_NAME).search(q)
        
        print(f"Resultados encontrados con RediSearch ({res.total}):")
        
        resultados = []
        
        for doc in res.docs:
            
            print(f"  ID: {doc.id} | Modelo: {doc.modelo} | Autonomía: {doc.autonomia_km} km | Categoría: {doc.categoria}")
            
            resultados.append(doc)
            
        return resultados
    
    except Exception as e:
        print(f"Búsqueda mediante índices secundarios (RediSearch no disponible: {e}):")
        
        doc_ids = baseDatosRedis.smembers(f"idx_manual:categoria:{category}")
        
        resultados = []
        
        for doc_id in doc_ids:
            
            datos = baseDatosRedis.hgetall(doc_id)
            
            resultados.append((doc_id, datos))
            
            print(f"  ID: {doc_id} => {datos}")
        
        return resultados


# 20 - Realiza un group  by usando los índices(0.5 puntos)
def group_by_indexed_data():
    print("\n--- Group By usando índices (agrupación por 'categoria') ---")
    try:
        req = (
            AggregateRequest("*")
            .group_by("@categoria", reducers.count().alias("cantidad"), reducers.avg("@autonomia_km").alias("promedio_autonomia"))
        )
        
        res = baseDatosRedis.ft(INDEX_NAME).aggregate(req)
        
        print("Resultados de agregación y Group By con RediSearch:")
        
        for row in res.rows:
            
            fila_dict = {row[i]: row[i + 1] for i in range(0, len(row), 2)}
            
            print(f"  Categoría: {fila_dict.get('categoria')} | Cantidad: {fila_dict.get('cantidad')} | Autonomía media: {float(fila_dict.get('promedio_autonomia', 0)):.2f} km")
            
        return res
    
    except Exception as e:
        
        print(f"Group By mediante índices secundarios (RediSearch no disponible: {e}):")
        
        categorias = ["electrico", "hibrido"]
        
        res_dict = {}
        
        for cat in categorias:
            
            doc_ids = baseDatosRedis.smembers(f"idx_manual:categoria:{cat}")
            
            cant = len(doc_ids)
            
            autonomias = []
            
            for did in doc_ids:
                
                h = baseDatosRedis.hgetall(did)
                
                if "autonomia_km" in h:
                    
                    autonomias.append(float(h["autonomia_km"]))
            
            avg_aut = sum(autonomias) / cant if cant > 0 else 0
            
            res_dict[cat] = {"cantidad": cant, "promedio_autonomia": avg_aut}
            
            print(f"  Categoría: {cat} | Cantidad: {cant} | Autonomía media: {avg_aut:.2f} km")
        
        return res_dict


if __name__ == "__main__":
    
    # Vaciar la base de datos antes de iniciar las pruebas
    baseDatosRedis.flushdb()
    
    print("=" * 60)
    print("EJECUCIÓN DE PRUEBAS REDIS 1 - 20 (SMARTRUTA & SBD)")
    print("=" * 60)

    # 1. Crear registros
    print("\n>>> 1. Crear registros clave-valor")
    add_data()

    # 2. Número de claves
    print("\n>>> 2. Número de claves registradas")
    get_num_key()

    # 3. Obtener registro por clave
    print("\n>>> 3. Obtener un registro por clave ('vehiculo:1')")
    get_data("vehiculo:1")

    # 4. Actualizar valor y mostrarlo
    print("\n>>> 4. Actualizar clave ('vehiculo:1' -> 'en_mantenimiento')")
    update_data("vehiculo:1", "en_mantenimiento")

    # 5. Eliminar clave y mostrar clave y valor eliminado
    print("\n>>> 5. Eliminar una clave ('vehiculo:B1')")
    delete_data("vehiculo:B1")

    # 6. Mostrar todas las claves
    print("\n>>> 6. Obtener todas las claves guardadas")
    get_all_keys()

    # 7. Mostrar todos los valores
    print("\n>>> 7. Obtener todos los valores guardados")
    get_all_values()

    # 8. Patrón *
    print("\n>>> 8. Búsqueda con patrón '*' ('vehiculo:*')")
    get_keys_pattern_asterisk("vehiculo:*")

    # 9. Patrón []
    print("\n>>> 9. Búsqueda con patrón '[]' ('vehiculo:[1-3]')")
    get_keys_pattern_brackets("vehiculo:[1-3]")

    # 10. Patrón ?
    print("\n>>> 10. Búsqueda con patrón '?' ('vehiculo:?')")
    get_keys_pattern_question("vehiculo:?")

    # 11. Filtrar por valor concreto
    print("\n>>> 11. Filtrar registros por valor concreto ('activo')")
    filter_by_value(target_value="activo", pattern="vehiculo:*")

    # 12. Actualizar registros en base a filtro
    print("\n>>> 12. Actualizar registros en base a filtro (aumentar contadores en +1)")
    update_by_filter(pattern="contador:viaje:*", increment=1)

    # 13. Eliminar registros en base a filtro
    print("\n>>> 13. Eliminar registros en base a filtro (vehículos inactivos)")
    delete_by_filter(pattern="vehiculo:*", filter_value="inactivo")

    # 14. Crear estructura JSON array
    print("\n>>> 14. Crear estructura JSON de array")
    create_json_structure()

    # 15. Filtrar por cada atributo JSON
    print("\n>>> 15. Filtrar por cada atributo de la estructura JSON")
    filter_json_attributes()

    # 16. Crear lista en Redis
    print("\n>>> 16. Crear una lista en Redis")
    create_redis_list()

    # 17. Filtrar elementos de una lista
    print("\n>>> 17. Filtrar elementos de la lista ('completado')")
    filter_redis_list(filter_term="completado")

    # 18. Crear datos con índices y esquema de al menos 3 campos
    print("\n>>> 18. Crear datos con índices y esquema de 3 campos")
    create_indexed_data()

    # 19. Búsqueda con índices
    print("\n>>> 19. Búsqueda con índices por campo 'categoria' = 'electrico'")
    search_indexed_data("electrico")

    # 20. Group By usando índices
    print("\n>>> 20. Group By usando índices")
    group_by_indexed_data()

    print("\n" + "=" * 60)
    print("FIN DE LAS PRUEBAS 1 - 20")
    print("=" * 60)
    
    # Vaciar la base de datos después de finalizar las pruebas
    baseDatosRedis.flushdb()
    
    # Cerrar la conexión a Redis
    baseDatosRedis.close()
    
