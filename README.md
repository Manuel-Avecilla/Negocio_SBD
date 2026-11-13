# Negocio_SBD · SmartRuta & Movilidad Sostenible

Sistema integral de bases de datos y analítica para **SmartRuta & Movilidad Sostenible**.

El proyecto contempla dos entornos de ejecución:

- **Entorno local:** MySQL, PostgreSQL, MariaDB y Redis desplegados con Docker Compose, más un visor web (**DbGate**) con las conexiones preconfiguradas.
- **Entorno AWS:** una instancia **MariaDB en Amazon RDS**, creada y gestionada desde Python con `boto3`, con scripts propios de inicialización, poblado y generación de informes.

Sobre ambos entornos se ejecuta un pipeline en Python que crea los esquemas, los puebla con datos sintéticos mediante `Faker` y genera informes analíticos en JSON. El entorno local incorpora además las prácticas de Redis, incluyendo los flujos SQL → Redis y Redis → SQL.

---

## Índice

1. [Arquitectura](#1-arquitectura)
2. [Estructura del proyecto](#2-estructura-del-proyecto)
3. [Requisitos previos](#3-requisitos-previos)
4. [Configuración del entorno](#4-configuración-del-entorno)
5. [Despliegue local con Docker](#5-despliegue-local-con-docker)
6. [Entorno Python](#6-entorno-python)
7. [Pipeline local de datos y reportes](#7-pipeline-local-de-datos-y-reportes)
8. [Pipeline en AWS RDS](#8-pipeline-en-aws-rds)
9. [Visor de bases de datos (DbGate)](#9-visor-de-bases-de-datos-dbgate)
10. [Scripts de Redis](#10-scripts-de-redis)
11. [Documentación por motor](#11-documentación-por-motor)
12. [Diagrama ER](#12-diagrama-er)

---

## 1. Arquitectura

### 1.1. Servicios locales

Todos los servicios de Docker Compose comparten la red `app-net`, por lo que se resuelven entre sí por el nombre del servicio.

| Servicio   | Contenedor                      | Imagen / origen        | Puerto host → contenedor | Uso                                      |
|------------|---------------------------------|------------------------|--------------------------|------------------------------------------|
| `mysql`    | `contenedor-smartruta-mysql`    | `mysql:latest`         | `3306 → 3306`            | Indicadores de sostenibilidad            |
| `postgres` | `contenedor-smartruta-postgres` | `postgres:15`          | `5432 → 5432`            | Carpooling, usuarios y telemetría GPS    |
| `mariadb`  | `contenedor-smartruta-mariadb`  | `mariadb:latest`       | `3307 → 3306`            | Tendencias, meteorología e incidencias   |
| `redis`    | `contenedor-smartruta-redis`    | `redis:alpine`         | `6379 → 6379`            | Pruebas clave-valor, JSON e índices      |
| `rds-cert` | `rds-cert-init`                 | `curlimages/curl`      | —                        | Descarga el bundle CA de AWS RDS         |
| `dbgate`   | `visor-bases-de-datos`          | `dbgate/dbgate:latest` | `8080 → 3000`            | Visor web de bases de datos              |

Volúmenes persistentes: `mysql_data`, `postgres_data`, `mariadb_data`, `redis_data`, `dbgate_data` y `rds_certs`.

> [!NOTE]
> MariaDB escucha internamente en el puerto `3306`. El puerto `3307` solo se expone en el host para evitar colisiones con MySQL.

### 1.2. AWS RDS

La instancia RDS no se define en `docker-compose.yml`: se crea desde `python/aws/RDS/init_RDS.py` mediante la API de AWS.

| Recurso                  | Valor / comportamiento                                                     |
|--------------------------|----------------------------------------------------------------------------|
| Motor                    | MariaDB                                                                    |
| Clase de instancia       | `db.t4g.micro`                                                             |
| Almacenamiento           | 20 GB                                                                      |
| Acceso público           | `PubliclyAccessible=True`                                                  |
| Usuario maestro          | `SHARED_DB_USER`                                                           |
| Contraseña maestra       | `SHARED_DB_PASSWORD`                                                       |
| Base de datos            | `AWS_RDS_DB_NAME`                                                          |
| Endpoint                 | Se guarda automáticamente en `Docker/.env` como `AWS_RDS_DB_ENDPOINT`      |
| Certificado TLS para DbGate | Se descarga en el volumen `rds_certs` mediante el servicio `rds-cert`  |

---

## 2. Estructura del proyecto

```text
Negocio_SBD/
├── Docker/
│   ├── docker-compose.yml
│   ├── .env.template
│   ├── mysql/
│   ├── postgres/
│   ├── mariadb/
│   └── redis/
├── python/
│   ├── init_db.py                 # Creación de tablas en MySQL, PostgreSQL y MariaDB local
│   ├── seed.py                    # Poblado local con Faker
│   ├── generate_reports.py        # Informes locales en JSON
│   ├── requirements.txt
│   ├── redis/
│   │   ├── conexion.py            # Comprobación de conexión con Redis
│   │   ├── flushdb.py             # Vacía la base de datos Redis db0
│   │   ├── pruebas_1_20.py        # Pruebas de Redis
│   │   ├── script_21.py           # MySQL → Redis
│   │   └── script_22.py           # Redis → PostgreSQL
│   └── aws/
│       └── RDS/
│           ├── init_RDS.py        # Crea/arranca RDS, la base de datos y las tablas
│           ├── seed.py            # Poblado de MariaDB en AWS RDS
│           ├── generate_reports.py # Informes JSON de AWS RDS
│           └── conexion.py        # Script auxiliar de conexión AWS (DynamoDB)
├── docs/
│   ├── mysql.md
│   ├── postgres.md
│   ├── mariadb.md
│   ├── redis.md
│   └── Diagrama ER.png
├── json_reports/                  # Informes generados (ignorado por Git)
└── README.md
```

---

## 3. Requisitos previos

- [Docker](https://docs.docker.com/get-docker/) y Docker Compose v2 (`docker compose`).
- Python 3.10 o superior.
- Puertos libres en el host: `3306`, `3307`, `5432`, `6379` y `8080`.
- Para el flujo AWS:
  - Cuenta de AWS con permisos para crear, describir, arrancar y detener instancias RDS.
  - Credenciales de AWS válidas: access key, secret key y, si son temporales, session token.
  - Región de AWS configurada en `AWS_REGION`.
  - Security group asociado a la instancia que permita conexiones TCP al puerto `3306` desde tu equipo.
- Para las pruebas avanzadas de Redis: soporte de **RediSearch** y **RedisJSON** en el servidor Redis.

---

## 4. Configuración del entorno

Toda la configuración se centraliza en `Docker/.env`. Los scripts que necesitan credenciales o nombres de base de datos cargan ese archivo automáticamente, tanto los locales como los de `python/aws/RDS/`.

### 4.1. Crear el archivo `.env`

```bash
cd Docker/
cp .env.template .env
```

Edita `Docker/.env` con tus credenciales y nombres de base de datos.

### 4.2. Variables de bases de datos locales

| Variable                 | Descripción                                                       |
|--------------------------|-------------------------------------------------------------------|
| `SHARED_DB_USER`         | Usuario común de MySQL, PostgreSQL, MariaDB y usuario maestro RDS |
| `SHARED_DB_PASSWORD`     | Contraseña del usuario común y contraseña maestra RDS             |
| `SHARED_DB_ROOT`         | Usuario root de referencia para los motores locales               |
| `SHARED_DB_ROOT_PASSWORD`| Contraseña root usada por MySQL y MariaDB en Docker Compose       |
| `MYSQL_DB_NAME`          | Nombre de la base de datos MySQL local                            |
| `POSTGRES_DB_NAME`       | Nombre de la base de datos PostgreSQL local                       |
| `MARIADB_DB_NAME`        | Nombre de la base de datos MariaDB local                          |

### 4.3. Variables de AWS y RDS

| Variable                  | Descripción                                                                 |
|---------------------------|-----------------------------------------------------------------------------|
| `AWS_ACCESS_KEY`          | Access key de AWS                                                           |
| `AWS_SECRET_KEY`          | Secret key de AWS                                                           |
| `AWS_SESSION_TOKEN`       | Token de sesión para credenciales temporales; puede quedar vacío            |
| `AWS_REGION`              | Región de AWS, por ejemplo `us-east-1`                                      |
| `AWS_RDS_DB_INSTANCE_ID`  | Identificador de la instancia RDS                                           |
| `AWS_RDS_DB_NAME`         | Base de datos que se crea y utiliza dentro de la instancia RDS              |
| `AWS_RDS_DB_ENDPOINT`     | Endpoint de la instancia RDS; `init_RDS.py` lo actualiza automáticamente    |

> [!IMPORTANT]
> `init_RDS.py` utiliza `SHARED_DB_USER` y `SHARED_DB_PASSWORD` como credenciales maestras de RDS. Si la instancia ya existe, estos valores deben coincidir con los definidos en el momento de su creación.

### 4.4. Variables opcionales de Redis

Los scripts `script_21.py` y `script_22.py` permiten sobrescribir la conexión de Redis:

| Variable      | Valor por defecto | Descripción                    |
|---------------|-------------------|--------------------------------|
| `REDIS_HOST`  | `localhost`       | Host de Redis                  |
| `REDIS_PORT`  | `6379`            | Puerto de Redis                |
| `REDIS_DB`    | `0`               | Base de datos lógica de Redis  |

> [!WARNING]
> No subas el archivo `Docker/.env` al repositorio. Contiene credenciales.

---

## 5. Despliegue local con Docker

### 5.1. Levantar los servicios

Desde el directorio `Docker/`:

```bash
docker compose up -d --build
```

Comprueba que todos los contenedores están en ejecución:

```bash
docker compose ps
```

Si solo necesitas las bases de datos locales y Redis:

```bash
docker compose up -d --build mysql postgres mariadb redis
```

> [!NOTE]
> Los Dockerfiles no ejecutan los archivos `init.sql`: la creación real de tablas se realiza con `python/init_db.py`. El servicio `rds-cert` es de un solo uso y descarga el certificado CA necesario para que DbGate se conecte a RDS por TLS.

### 5.2. Comandos de gestión

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

## 6. Entorno Python

Desde la raíz del proyecto:

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

Dependencias principales declaradas en `python/requirements.txt`:

- `Faker`
- `pymysql`
- `psycopg2-binary`
- `python-dotenv`
- `redis`
- `boto3`
- `mysql-connector-python`

Los comandos de las siguientes secciones deben ejecutarse con el entorno virtual activado.

---

## 7. Pipeline local de datos y reportes

Ejecuta los pasos en este orden, desde el directorio `python/`.

### 7.1. Inicialización del esquema

```bash
python init_db.py
```

Crea las tablas en las tres bases de datos relacionales locales:

- MySQL en `localhost:3306`.
- PostgreSQL en `localhost:5432`.
- MariaDB en `localhost:3307`.

El script utiliza `CREATE TABLE IF NOT EXISTS`, por lo que puede ejecutarse de nuevo sin recrear las tablas existentes.

### 7.2. Poblado con datos sintéticos

```bash
python seed.py
```

Genera e inserta datos con `Faker` en MySQL, PostgreSQL y MariaDB. Los volúmenes utilizados son:

| Tabla                        | Registros |
|------------------------------|-----------|
| `DIRECCIONES`                | 50        |
| `USUARIOS`                   | 100       |
| `VEHICULOS`                  | 40        |
| `RUTAS_CARPOOLING`           | 60        |
| `RESERVAS_CARPOOLING`        | 80        |
| `REGISTROS_GPS`              | 200       |
| `HISTORIAL_DESPLAZAMIENTOS`  | 120       |
| `INCIDENCIAS_TRAFICO`        | 30        |
| `ENCUESTAS_HABITOS`          | 5         |
| `RESPUESTAS_ENCUESTA`        | 50        |
| `REGISTRO_METEOROLOGICO`     | 40        |

> [!WARNING]
> El script no vacía las tablas antes de insertar. Si lo ejecutas varias veces sobre una base ya poblada pueden aparecer duplicados o errores de claves únicas y foráneas.

### 7.3. Informes analíticos locales

```bash
python generate_reports.py
```

El script consulta MySQL, PostgreSQL y MariaDB y genera tres informes JSON en:

```text
json_reports/Date_YYYY_MM_DD_Hour_HH-MM-SS/
```

| Archivo          | Contenido                                                              |
|------------------|------------------------------------------------------------------------|
| `mysql.json`     | Indicadores globales de sostenibilidad y distribución modal            |
| `postgress.json` | Red de carpooling, dinámicas de usuarios y telemetría GPS              |
| `mariadb.json`   | Tendencias temporales, condiciones meteorológicas e incidencias        |

Cada informe incluye un bloque `metadatos` con el motor, la fecha de generación y el enfoque analítico, además de las secciones de resultados correspondientes.

---

## 8. Pipeline en AWS RDS

El flujo de AWS RDS es independiente del pipeline local y se ejecuta con los scripts de `python/aws/RDS/`. Todos ellos leen la configuración desde `Docker/.env` y escriben los informes en la misma carpeta raíz `json_reports/`.

### 8.1. Preparación

Antes de ejecutar los scripts, comprueba que `Docker/.env` contiene:

- `AWS_ACCESS_KEY`
- `AWS_SECRET_KEY`
- `AWS_SESSION_TOKEN`, si usas credenciales temporales
- `AWS_REGION`
- `AWS_RDS_DB_INSTANCE_ID`
- `AWS_RDS_DB_NAME`
- `SHARED_DB_USER`
- `SHARED_DB_PASSWORD`

`AWS_RDS_DB_ENDPOINT` puede estar vacío o ser un marcador de posición: `init_RDS.py` lo actualiza con el endpoint real.

### 8.2. Inicialización de la instancia y de las tablas

Desde la raíz del proyecto, con el entorno virtual activado:

```bash
python python/aws/RDS/init_RDS.py
```

El script realiza las siguientes operaciones:

1. Comprueba si la instancia RDS existe.
2. Si no existe, la crea con MariaDB, clase `db.t4g.micro`, 20 GB y acceso público.
3. Si existe pero está detenida, la arranca.
4. Espera a que el estado sea `available`.
5. Crea la base de datos `AWS_RDS_DB_NAME` si no existe.
6. Crea las 11 tablas del esquema con `CREATE TABLE IF NOT EXISTS`.
7. Guarda el endpoint en `Docker/.env` como `AWS_RDS_DB_ENDPOINT`.
8. Ejecuta el servicio `rds-cert` para descargar el bundle de certificados CA de RDS.

> [!NOTE]
> La creación y el arranque de una instancia RDS pueden tardar varios minutos. El script espera hasta 30 minutos mediante polling.

> [!IMPORTANT]
> `init_RDS.py` no crea VPC, subnet group ni security group: utiliza la configuración por defecto de la cuenta de AWS. Debes asegurarte de que la instancia queda accesible por el puerto `3306` desde tu equipo. Además, Docker debe estar disponible porque el script ejecuta `docker compose run` para descargar el certificado de RDS.

### 8.3. Poblado de MariaDB en RDS

```bash
python python/aws/RDS/seed.py
```

Inserta en MariaDB RDS los mismos volúmenes de datos sintéticos que el poblado local, pero utilizando una única conexión y un único `commit` final. Debe ejecutarse después de `init_RDS.py`.

> [!WARNING]
> Al igual que el seed local, este script no limpia las tablas. Repetirlo sobre una base ya poblada puede provocar duplicados o errores de integridad referencial.

### 8.4. Informes analíticos de AWS RDS

```bash
python python/aws/RDS/generate_reports.py
```

Genera tres informes independientes en:

```text
json_reports/Date_YYYY_MM_DD_Hour_HH-MM-SS/
```

| Archivo                            | Contenido                                                        |
|------------------------------------|------------------------------------------------------------------|
| `AWS_RDS_sostenibilidad.json`      | Resumen de sostenibilidad por modo de transporte                 |
| `AWS_RDS_carpooling.json`          | Resumen de rutas de carpooling por estado                        |
| `AWS_RDS_desplazamientos.json`     | Evolución temporal mensual de los desplazamientos                |

Cada informe ejecuta una consulta básica contra MariaDB RDS, por lo que el flujo completo realiza tres consultas en total. El formato JSON mantiene el bloque `metadatos` y una sección de resultados por informe.

### 8.5. Orden recomendado del flujo AWS

```bash
# 1. Crear/arrancar la instancia, la base de datos y las tablas
python python/aws/RDS/init_RDS.py

# 2. Poblar MariaDB RDS
python python/aws/RDS/seed.py

# 3. Generar los informes JSON
python python/aws/RDS/generate_reports.py
```

---

## 9. Visor de bases de datos (DbGate)

**URL:** [http://localhost:8080](http://localhost:8080)

DbGate se levanta con las conexiones preconfiguradas desde `docker-compose.yml`:

| Conexión   | Servidor                       | Usuario              | Observaciones                                      |
|------------|--------------------------------|----------------------|----------------------------------------------------|
| MySQL      | `mysql:3306`                   | `SHARED_DB_USER`     | Base creada con `MYSQL_DB_NAME`                    |
| PostgreSQL | `postgres:5432`                | `SHARED_DB_USER`     | Base creada con `POSTGRES_DB_NAME`                 |
| MariaDB    | `mariadb:3306`                 | `SHARED_DB_USER`     | Base creada con `MARIADB_DB_NAME`                  |
| Redis      | `redis:6379`                   | Sin autenticación    | Los scripts usan `db0`                             |
| AWS RDS    | `AWS_RDS_DB_ENDPOINT:3306`     | `SHARED_DB_USER`     | Base fijada mediante `DATABASE_rds`                |

Las conexiones locales no fijan una base de datos concreta en el compose; DbGate muestra las bases disponibles en cada servidor. La conexión de AWS RDS sí utiliza `DATABASE_rds=AWS_RDS_DB_NAME`.

La conexión de AWS RDS utiliza TLS:

- `USE_SSL_rds=1`
- `SSL_CA_FILE_rds=/certs/rds-ca.pem`
- `SSL_REJECT_UNAUTHORIZED_rds=1`

El certificado se obtiene con el servicio `rds-cert` y se monta en DbGate desde el volumen `rds_certs`.

Las conexiones se definen por variables de entorno en el `docker-compose.yml`, por lo que **no se pueden editar desde la interfaz**. Para modificarlas, cambia el compose y reinicia el servicio.

### Particularidades de Redis en el visor

- Redis tiene **16 bases de datos lógicas** (`db0` a `db15`) y DbGate las muestra todas, aunque estén vacías. Los scripts de este proyecto usan **`db0`**.
- Haz doble clic en `db0` para abrir el explorador de claves y pulsa **refrescar** tras ejecutar scripts; el visor no se actualiza solo.
- Las claves se agrupan en carpetas según el separador `:` (por ejemplo, `vehiculo:1` aparece dentro de la carpeta `vehiculo`).
- Las claves de tipo RedisJSON (como `smartruta:mysql:usuarios_json`) pueden no mostrarse correctamente en el visor. Compruébalas con `redis-cli`:

```bash
docker exec -it contenedor-smartruta-redis redis-cli JSON.GET smartruta:mysql:usuarios_json
```

---

## 10. Scripts de Redis

Se ejecutan desde el directorio `python/` con el entorno virtual activado y los servicios locales levantados.

### 10.1. Comprobación de conexión

```bash
python redis/conexion.py
```

Comprueba que Redis responde en `localhost:6379`.

### 10.2. Pruebas 1-20

Cubren claves-valor, patrones de búsqueda, filtros, estructuras JSON, listas e índices con RediSearch (búsqueda y *group by*).

```bash
python redis/pruebas_1_20.py
```

> [!WARNING]
> El script vacía la base de datos Redis `db0` al comenzar. No lo ejecutes si tienes datos que quieras conservar.

### 10.3. Script 21: MySQL → Redis

Ejecuta en MySQL una consulta SQL con `JOIN` entre `USUARIOS` y `DIRECCIONES` y guarda el resultado en Redis (`db0`):

| Clave                           | Contenido                                                          |
|---------------------------------|--------------------------------------------------------------------|
| `smartruta:mysql:usuario:<id>`  | Un hash por usuario                                                |
| `smartruta:mysql:usuarios:ids`  | Conjunto con los identificadores importados                        |
| `smartruta:mysql:usuarios_json` | Todos los usuarios en un único JSON (RedisJSON si está disponible) |
| `smartruta:mysql:importacion`   | Metadatos de la importación (consulta, total, fecha)               |

Es idempotente: borra la importación anterior antes de escribir. Requiere haber ejecutado antes `init_db.py` y `seed.py`.

```bash
python redis/script_21.py
```

### 10.4. Script 22: Redis → PostgreSQL

Lee de Redis los usuarios que dejó el script 21 (los hashes o, si no existen, el JSON completo) y los inserta o actualiza en la tabla `USUARIOS_DESDE_REDIS` de PostgreSQL, que crea si no existe.

```bash
python redis/script_22.py
```

> [!IMPORTANT]
> Ejecuta el script 21 antes que el 22. Si lanzas las pruebas 1-20 entre ambos, los datos del script 21 se borran de Redis y el 22 no encontrará nada que importar.

### 10.5. Vaciar Redis

Para vaciar manualmente la base de datos `db0`:

```bash
python redis/flushdb.py
```

> [!WARNING]
> Este comando elimina todas las claves de Redis `db0`. Úsalo solo cuando quieras reiniciar las prácticas.

Para comprobar en qué base de datos están las claves tras una ejecución:

```bash
docker exec -it contenedor-smartruta-redis redis-cli INFO keyspace
```

---

## 11. Documentación por motor

En la carpeta [`docs/`](docs/) está la guía de cada base de datos, junto con la explicación detallada de su análisis e informe:

- [MySQL: despliegue y análisis](docs/mysql.md)
- [PostgreSQL: despliegue y análisis](docs/postgres.md)
- [MariaDB: despliegue y análisis](docs/mariadb.md)
- [Redis: despliegue](docs/redis.md)

---

## 12. Diagrama ER

![Diagrama entidad-relación](docs/Diagrama%20ER.png)