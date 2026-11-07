# Negocio_SBD · SmartRuta & Movilidad Sostenible

Sistema integral de bases de datos y analítica de datos para **SmartRuta & Movilidad Sostenible**.

La infraestructura se despliega con Docker Compose e incluye cuatro motores (**MySQL 8**, **PostgreSQL 15**, **MariaDB** y **Redis**), un visor web (**DbGate**) con todas las conexiones preconfiguradas, volúmenes persistentes y configuración centralizada en un archivo `.env`.

Sobre ella se ejecuta un pipeline en Python que inicializa los esquemas, los puebla con datos sintéticos (`Faker`), genera informes analíticos en JSON y ejecuta las pruebas de Redis.

---

## Índice

1. [Arquitectura](#1-arquitectura)
2. [Requisitos previos](#2-requisitos-previos)
3. [Despliegue con Docker](#3-despliegue-con-docker)
4. [Entorno Python](#4-entorno-python)
5. [Pipeline de datos y reportes](#5-pipeline-de-datos-y-reportes)
6. [Visor de bases de datos (DbGate)](#6-visor-de-bases-de-datos-dbgate)
7. [Scripts de Redis](#7-scripts-de-redis)
8. [Documentación por motor](#8-documentación-por-motor)
9. [Solución de problemas](#9-solución-de-problemas)

---

## 1. Arquitectura

Todos los servicios comparten la red `app-net`, por lo que se resuelven entre sí por el nombre del servicio.

| Servicio   | Contenedor                      | Puerto host → contenedor | Uso                                   |
|------------|---------------------------------|--------------------------|---------------------------------------|
| `mysql`    | `contenedor-smartruta-mysql`    | `3306 → 3306`            | Indicadores de sostenibilidad         |
| `postgres` | `contenedor-smartruta-postgres` | `5432 → 5432`            | Carpooling, usuarios y telemetría GPS |
| `mariadb`  | `contenedor-smartruta-mariadb`  | `3307 → 3306`            | Tendencias, meteorología e incidencias|
| `redis`    | `contenedor-smartruta-redis`    | `6379 → 6379`            | Pruebas clave-valor, JSON e índices   |
| `dbgate`   | `visor-bases-de-datos`          | `8080 → 3000`            | Visor web de todas las bases de datos |

Volúmenes persistentes: `mysql_data`, `postgres_data`, `mariadb_data`, `redis_data` y `dbgate_data`.

> [!NOTE]
> MariaDB escucha internamente en el puerto `3306`. El `3307` es solo el puerto expuesto en tu máquina para no chocar con MySQL.

### Estructura del proyecto

```text
Negocio_SBD/
├── Docker/            # docker-compose.yml, .env.template y Dockerfile de cada motor
├── python/            # Scripts de inicialización, poblado, informes y pruebas
│   └── redis/         # Pruebas y scripts de Redis
├── docs/              # Guía detallada de cada motor
└── json_reports/      # Informes generados (se crea al ejecutar generate_reports.py)
```

---

## 2. Requisitos previos

- [Docker](https://docs.docker.com/get-docker/) y Docker Compose v2 (`docker compose`)
- Python 3.10 o superior
- Puertos libres en el host: `3306`, `3307`, `5432`, `6379` y `8080`

---

## 3. Despliegue con Docker

### 3.1. Configuración del entorno

Desde el directorio `Docker/`, genera el archivo `.env` a partir de la plantilla y edita las credenciales:

```bash
cd Docker/
cp .env.template .env
```

Variables que utiliza el `docker-compose.yml`:

| Variable              | Descripción                                   |
|-----------------------|-----------------------------------------------|
| `MYSQL_ROOT_PASSWORD` | Contraseña root de MySQL y MariaDB            |
| `MYSQL_DATABASE`      | Base de datos inicial de MySQL y MariaDB      |
| `MYSQL_USER`          | Usuario de aplicación de MySQL y MariaDB      |
| `MYSQL_PASSWORD`      | Contraseña del usuario de aplicación          |
| `POSTGRES_DB`         | Base de datos inicial de PostgreSQL           |
| `POSTGRES_USER`       | Usuario de PostgreSQL                         |
| `POSTGRES_PASSWORD`   | Contraseña de PostgreSQL                      |

> [!WARNING]
> No subas el archivo `.env` al repositorio. Contiene credenciales.

### 3.2. Levantar los servicios

Compila las imágenes y arranca los cinco servicios en segundo plano:

```bash
docker compose up -d --build
```

Comprueba que todos están en ejecución:

```bash
docker compose ps
```

### 3.3. Comandos de gestión

```bash
# Ver logs de un servicio (por ejemplo, el visor)
docker compose logs -f dbgate

# Detener los contenedores conservando los datos
docker compose down

# Detener los contenedores y ELIMINAR los volúmenes (borra todos los datos)
docker compose down -v
```

> [!TIP]
> Para construir y levantar cada base de datos de forma independiente con su propio `Dockerfile`, consulta las guías de la carpeta [`docs/`](docs/).

---

## 4. Entorno Python

Desde la raíz del proyecto, prepara el entorno virtual e instala las dependencias:

```bash
cd python

# Crear el entorno virtual
python3 -m venv venv

# Activarlo (Linux/macOS)
source venv/bin/activate

# Actualizar pip e instalar dependencias
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

## 5. Pipeline de datos y reportes

Ejecuta los pasos en este orden, con el entorno virtual activado y desde el directorio `python/`.

### 5.1. Inicialización y poblado

```bash
# 1. Crear el esquema en MySQL, PostgreSQL y MariaDB
python init_db.py

# 2. Poblar con datos sintéticos de prueba
python seed.py
```

### 5.2. Informes analíticos JSON

```bash
# 3. Ejecutar el análisis en los tres motores relacionales
python generate_reports.py
```

Los informes se guardan de forma versionada en la raíz del proyecto, dentro de `json_reports/Date_YYYY_MM_DD_Hour_HH-MM-SS/`:

| Archivo          | Contenido                                                        |
|------------------|------------------------------------------------------------------|
| `mysql.json`     | Indicadores globales de sostenibilidad y distribución modal      |
| `postgress.json` | Red de carpooling, dinámicas de usuarios y telemetría GPS        |
| `mariadb.json`   | Tendencias temporales, condiciones meteorológicas e incidencias  |

---

## 6. Visor de bases de datos (DbGate)

**URL:** [http://localhost:8080](http://localhost:8080)

DbGate se levanta con las cuatro conexiones ya creadas, sin configuración manual:

| Conexión   | Servidor interno | Usuario                    |
|------------|------------------|----------------------------|
| MySQL      | `mysql:3306`     | `root`                     |
| PostgreSQL | `postgres:5432`  | `${POSTGRES_USER}`         |
| MariaDB    | `mariadb:3306`   | `root`                     |
| Redis      | `redis:6379`     | sin autenticación          |

Las conexiones se definen por variables de entorno en el `docker-compose.yml`, por lo que **no se pueden editar desde la interfaz**. Para modificarlas, cambia el compose y reinicia el servicio.

### Particularidades de Redis en el visor

- Redis tiene **16 bases de datos lógicas** (`db0` a `db15`) y DbGate las muestra todas, aunque estén vacías. Los scripts de este proyecto usan **`db0`**.
- Haz doble clic en `db0` para abrir el explorador de claves y pulsa **refrescar** tras ejecutar scripts; el visor no se actualiza solo.
- Las claves se agrupan en carpetas según el separador `:` (por ejemplo, `vehiculo:1` aparece dentro de la carpeta `vehiculo`).
- Las claves de tipo RedisJSON (como `smartruta:rutas_json`) pueden no mostrarse correctamente en el visor. Compruébalas con `redis-cli`:

```bash
docker exec -it contenedor-smartruta-redis redis-cli JSON.GET smartruta:rutas_json
```

---

## 7. Scripts de Redis

Se ejecutan desde el directorio `python/` con el entorno virtual activado.

### Pruebas 1-20

Cubren claves-valor, patrones de búsqueda, filtros, estructuras JSON, listas e índices con RediSearch (búsqueda y *group by*).

```bash
python redis/pruebas_1_20.py
```

> [!WARNING]
> Estas pruebas antes de la ejecución **vacían la base de datos de Redis**. No las lances si tienes datos que quieras conservar.


### Script 21: MySQL → Redis

Ejecuta en MySQL una consulta SQL con `JOIN` entre `USUARIOS` y `DIRECCIONES` y guarda el resultado en Redis (`db0`):

| Clave                           | Contenido                                                    |
|---------------------------------|--------------------------------------------------------------|
| `smartruta:mysql:usuario:<id>`  | Un hash por usuario                                          |
| `smartruta:mysql:usuarios:ids`  | Conjunto con los identificadores importados                  |
| `smartruta:mysql:usuarios_json` | Todos los usuarios en un único JSON (RedisJSON si está disponible) |
| `smartruta:mysql:importacion`   | Metadatos de la importación (consulta, total, fecha)         |

Es idempotente: borra la importación anterior antes de escribir. Requiere haber ejecutado antes `init_db.py` y `seed.py`.

```bash
python redis/script_21.py
```

### Script 22: Redis → PostgreSQL

Lee de Redis los usuarios que dejó el script 21 (los hashes o, si no existen, el JSON completo) y los inserta o actualiza en la tabla `USUARIOS_DESDE_REDIS` de PostgreSQL, que crea si no existe.

```bash
python redis/script_22.py
```

> [!IMPORTANT]
> Ejecuta el script 21 antes que el 22. Si lanzas las pruebas 1-20 entre ambos, los datos del script 21 se borran de Redis y el 22 no encontrará nada que importar.

Para comprobar en qué base de datos están las claves tras una ejecución:

```bash
docker exec -it contenedor-smartruta-redis redis-cli INFO keyspace
```

---

## 8. Documentación por motor

En la carpeta [`docs/`](docs/) está la guía de cada base de datos, junto con la explicación detallada de su análisis e informe:

- [MySQL: despliegue y análisis](docs/mysql.md)
- [PostgreSQL: despliegue y análisis](docs/postgres.md)
- [MariaDB: despliegue y análisis](docs/mariadb.md)
- [Redis: despliegue](docs/redis.md)
