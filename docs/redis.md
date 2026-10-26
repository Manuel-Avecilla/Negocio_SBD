# Despliegue y Análisis de Datos: Redis

Guía detallada para el despliegue del contenedor Docker de **Redis**.

---

## 1. Despliegue con Dockerfile

Para compilar y levantar el servicio Redis de forma individual utilizando su propio Dockerfile:

### 1.1. Configuración previa

Accede a la carpeta de configuración y asegúrate de que el volumen persistente esta creado:

```bash
# Crear volumen persistente de Redis
docker volume create redis_data
```

### 1.2. Construir la imagen Docker

Construye la imagen personalizada a partir del archivo [`Docker/redis/Dockerfile`](file:///home/manuel/Escritorio/IABD2026/Negocio_SBD/Docker/redis/Dockerfile):

```bash
docker build -t smartruta-redis ./redis
```

### 1.3. Ejecutar el contenedor

Inicia el contenedor en segundo plano vinculando el puerto host `6379` al puerto interno `6379`, inyectando las variables de entorno de `.env` y asociando el volumen persistente:

```bash
docker run -d \
  -p 6379:6379 \
  --name contenedor-smartruta-redis \
  -v redis_data:/data \
  smartruta-redis
```

> [!NOTE]
> Redis utiliza el puerto estándar `6379` y almacena la información persistente dentro del directorio contenedor `/data`.

### 1.4. Comprobación y Logs

```bash
# Verificar estado del contenedor
docker ps --filter "name=contenedor-smartruta-redis"

# Ver registros de inicialización
docker logs -f contenedor-smartruta-redis
```

---