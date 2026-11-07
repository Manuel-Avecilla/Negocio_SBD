import redis

conexionRedis = redis.ConnectionPool(host='localhost', port=6379, db=0, decode_responses=True)
baseDatosRedis = redis.Redis(connection_pool=conexionRedis)

# Vaciar la base de datos
baseDatosRedis.flushdb()
print("Base de datos REDIS vaciada correctamente.")