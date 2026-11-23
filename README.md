# Negocio_SBD · SmartRuta & Movilidad Sostenible

Sistema integral de bases de datos y analítica para **SmartRuta & Movilidad Sostenible**.

El proyecto contempla dos entornos de ejecución:

- **Entorno local:** MySQL, PostgreSQL, MariaDB y Redis desplegados con Docker Compose, más un visor web (**DbGate**) con las conexiones preconfiguradas.
- **Entorno AWS:** una instancia **MariaDB en Amazon RDS** y tres tablas en **Amazon DynamoDB**, creadas y gestionadas desde Python con `boto3`, con scripts propios de inicialización, poblado y pruebas.

Sobre ambos entornos se ejecuta un pipeline en Python que crea los esquemas, los puebla con datos sintéticos mediante `Faker` y genera informes analíticos en JSON. El entorno local incorpora además las prácticas de Redis, incluyendo los flujos SQL → Redis y Redis → SQL, y el entorno AWS incluye una suite de pruebas sobre DynamoDB.

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
9. [Pipeline en AWS DynamoDB](#9-pipeline-en-aws-dynamodb)
10. [Visores de bases de datos](#10-visores-de-bases-de-datos)
11. [Scripts de Redis](#11-scripts-de-redis)
12. [Documentación por motor](#12-documentación-por-motor)
13. [Diagrama ER](#13-diagrama-er)

---

## 1. Arquitectura

### 1.1. Servicios locales

Todos los servicios de Docker Compose comparten la red `app-net`, por lo que se resuelven entre sí por el nombre del servicio.

| Servicio         | Contenedor                      | Imagen / origen                   | Puerto host → contenedor | Uso                                    |
|------------------|---------------------------------|-----------------------------------|--------------------------|----------------------------------------|
| `mysql`          | `contenedor-smartruta-mysql`    | `mysql:latest`                    | `3306 → 3306`            | Indicadores de sostenibilidad          |
| `postgres`       | `contenedor-smartruta-postgres` | `postgres:15`                     | `5432 → 5432`            | Carpooling, usuarios y telemetría GPS  |
| `mariadb`        | `contenedor-smartruta-mariadb`  | `mariadb:latest`                  | `3307 → 3306`            | Tendencias, meteorología e incidencias |
| `redis`          | `contenedor-smartruta-redis`    | `redis:alpine`                    | `6379 → 6379`            | Pruebas clave-valor, JSON e índices    |
| `rds-cert`       | `rds-cert-init`                 | `curlimages/curl`                 | —                        | Descarga el bundle CA de AWS RDS       |
| `dbgate`         | `visor-bases-de-datos`          | `dbgate/dbgate:latest`            | `8080 → 3000`            | Visor web de bases de datos            |
| `dynamodb-admin` | `visor-dynamodb`                | `aaronshaf/dynamodb-admin:latest` | `8001 → 8001`            | Visor web de DynamoDB en AWS           |

Volúmenes persistentes: `mysql_data`, `postgres_data`, `mariadb_data`, `redis_data`, `dbgate_data` y `rds_certs`.

> [!NOTE]
> MariaDB escucha internamente en el puerto `3306`. El puerto `3307` solo se expone en el host para evitar colisiones con MySQL.

> [!NOTE]
> `dynamodb-admin` no almacena datos localmente: se conecta a la cuenta de AWS usando `AWS_DYNAMODB_ENDPOINT` y las credenciales de `Docker/.env`. `init_DynamoDB.py` actualiza ese endpoint y vuelve a crear el contenedor automáticamente.

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

### 1.3. AWS DynamoDB

DynamoDB complementa a MariaDB en RDS: el modelo relacional conserva los datos maestros (usuarios, vehículos, rutas, reservas...), mientras que DynamoDB guarda los datos de alto volumen, escritura continua y vida corta que no necesitan `JOIN`. Las claves `id_ruta` e `id_usuario` usan los mismos rangos que el seed de RDS, por lo que los ítems pueden relacionarse lógicamente con esas tablas.

| Tabla                    | Clave de partición (HASH) | Clave de ordenación (RANGE) | Índice secundario                  | TTL         | Uso                                        |
|--------------------------|---------------------------|-----------------------------|------------------------------------|-------------|--------------------------------------------|
| `MENSAJES_RUTA`          | `id_ruta` (N)             | `marca_tiempo` (S)          | —                                  | —           | Chat conductor-pasajeros de una ruta       |
| `NOTIFICACIONES_USUARIO` | `id_usuario` (N)          | `marca_tiempo` (S)          | LSI `LSI_usuario_tipo` (por `tipo`) | `expira_en` | Notificaciones push/in-app de cada usuario |
| `POSICIONES_TIEMPO_REAL` | `id_ruta` (N)             | `marca_tiempo` (S)          | GSI `GSI_usuario_tiempo`           | `expira_en` | Posiciones GPS en directo durante una ruta |

Las tres tablas se crean en modo `PAY_PER_REQUEST` (bajo demanda, sin capacidad que configurar). Solo se declaran como `AttributeDefinitions` los atributos que forman parte de una clave; el resto son libres. Las marcas de tiempo se guardan como ISO 8601 UTC para que sean ordenables como texto. `init_DynamoDB.py` guarda el endpoint del servicio en `Docker/.env` como `AWS_DYNAMODB_ENDPOINT`.

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
│       ├── RDS/
│       │   ├── init_RDS.py         # Crea/arranca RDS, la base de datos y las tablas
│       │   ├── seed.py             # Poblado de MariaDB en AWS RDS
│       │   ├── generate_reports.py # Informes JSON de AWS RDS
│       │   └── conexion.py         # Script auxiliar de conexión con AWS RDS
│       └── DynamoDB/
│           ├── init_DynamoDB.py    # Crea las 3 tablas, índices y TTL; actualiza el visor
│           ├── seed.py             # Poblado de las 3 tablas con datos sintéticos
│           ├── conexion.py         # Lista las tablas disponibles en DynamoDB
│           ├── pruebas.py          # Suite de 9 pruebas (CLI --1..--9 / --todas)
│           └── flushdb.py          # Elimina todos los ítems sin borrar las tablas
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
- Puertos libres en el host: `3306`, `3307`, `5432`, `6379`, `8080` y `8001`.
- Para el flujo AWS:
  - Cuenta de AWS con permisos para crear, describir, arrancar y detener instancias RDS.
  - Permisos sobre DynamoDB para crear y describir tablas, activar TTL, listar tablas y operar con ítems (`BatchWriteItem`, `GetItem`, `UpdateItem`, `DeleteItem`, `Scan`, `Query` y `ExecuteStatement` para PartiQL).
  - Credenciales de AWS válidas: access key, secret key y, si son temporales, session token.
  - Región de AWS configurada en `AWS_REGION`.
  - Security group asociado a la instancia que permita conexiones TCP al puerto `3306` desde tu equipo.
  - Docker disponible para levantar los visores (`dbgate` y `dynamodb-admin`).
- Para las pruebas avanzadas de Redis: soporte de **RediSearch** y **RedisJSON** en el servidor Redis.

---

## 4. Configuración del entorno

Toda la configuración se centraliza en `Docker/.env`. Los scripts que necesitan credenciales o nombres de base de datos cargan ese archivo automáticamente, tanto los locales como los de `python/aws/`.

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

### 4.3. Variables de AWS (RDS y DynamoDB)

| Variable                  | Descripción                                                                                   |
|---------------------------|-----------------------------------------------------------------------------------------------|
| `AWS_ACCESS_KEY`          | Access key de AWS                                                                             |
| `AWS_SECRET_KEY`          | Secret key de AWS                                                                             |
| `AWS_SESSION_TOKEN`       | Token de sesión para credenciales temporales; puede quedar vacío                              |
| `AWS_REGION`              | Región de AWS, por ejemplo `us-east-1`                                                        |
| `AWS_RDS_DB_INSTANCE_ID`  | Identificador de la instancia RDS                                                             |
| `AWS_RDS_DB_NAME`         | Base de datos que se crea y utiliza dentro de la instancia RDS                                |
| `AWS_RDS_DB_ENDPOINT`     | Endpoint de la instancia RDS; `init_RDS.py` lo actualiza automáticamente                      |
| `AWS_DYNAMODB_ENDPOINT`   | Endpoint del servicio DynamoDB; `init_DynamoDB.py` lo actualiza y lo usa el visor             |

> [!NOTE]
> `AWS_DYNAMODB_ENDPOINT` puede estar vacío o ser un marcador de posición en `.env`: `init_DynamoDB.py` lo sustituye por el endpoint real de la región configurada. No es necesaria una instancia local de DynamoDB.

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

El visor de DynamoDB (`dynamodb-admin`) se levanta con el resto de servicios en el puerto `8001`. Necesita `AWS_DYNAMODB_ENDPOINT` en `Docker/.env`; `init_DynamoDB.py` lo actualiza y fuerza su recreación para que coja el endpoint y un posible `AWS_SESSION_TOKEN` nuevo.

> [!NOTE]
> Los Dockerfiles no ejecutan los archivos `init.sql`: la creación real de tablas se realiza con `python/init_db.py`. El servicio `rds-cert` es de un solo uso y descarga el certificado CA necesario para que DbGate se conecte a RDS por TLS.

### 5.2. Comandos de gestión

```bash
# Ver logs de un servicio (por ejemplo, el visor DbGate)
docker compose logs -f dbgate

# Ver logs del visor de DynamoDB
docker compose logs -f dynamodb-admin

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

## 9. Pipeline en AWS DynamoDB

El flujo de DynamoDB usa el servicio administrado de AWS: no hay ningún motor local que levantar. Se ejecuta con los scripts de `python/aws/DynamoDB/`, todos leen la configuración desde `Docker/.env` y trabajan sobre las mismas credenciales y región que el pipeline de RDS. DynamoDB complementa al modelo relacional guardando mensajes, notificaciones y posiciones en tiempo real.

### 9.1. Preparación

Comprueba que `Docker/.env` contiene `AWS_ACCESS_KEY`, `AWS_SECRET_KEY`, `AWS_SESSION_TOKEN` (si usas credenciales temporales) y `AWS_REGION`. `AWS_DYNAMODB_ENDPOINT` puede estar vacío o ser un marcador de posición: `init_DynamoDB.py` lo actualiza con el endpoint real de la región.

### 9.2. Inicialización de las tablas

Desde la raíz del proyecto, con el entorno virtual activado:

```bash
python python/aws/DynamoDB/init_DynamoDB.py
```

El script realiza las siguientes operaciones:

1. Crea una sesión de `boto3` con las credenciales y la región de `.env`.
2. Crea las tres tablas si no existen, en modo `PAY_PER_REQUEST` (sin capacidad aprovisionada).
3. Define `MENSAJES_RUTA` sin índices secundarios, `NOTIFICACIONES_USUARIO` con el LSI `LSI_usuario_tipo` y `POSICIONES_TIEMPO_REAL` con el GSI `GSI_usuario_tiempo`.
4. Espera a que cada tabla esté activa mediante el *waiter* `table_exists`.
5. Activa el TTL sobre `expira_en` en las dos tablas que lo usan, si no estaba activado.
6. Guarda el endpoint del cliente en `Docker/.env` como `AWS_DYNAMODB_ENDPOINT`.
7. Recrea el contenedor `dynamodb-admin` con `docker compose up -d --force-recreate --no-deps` para que coja el endpoint y las credenciales actualizados.

> [!NOTE]
> La definición de cada tabla está en `TABLAS_DYNAMODB`. Solo se declaran en `AttributeDefinitions` los atributos que son clave de la tabla, del LSI o del GSI; el resto de atributos son libres.

> [!IMPORTANT]
> El script necesita Docker disponible porque ejecuta un comando `docker compose` desde el directorio `Docker/`. Requiere permisos de AWS para crear tablas, describirlas y modificar su configuración de TTL.

### 9.3. Poblado con datos sintéticos

```bash
python python/aws/DynamoDB/seed.py
```

Genera 50 ítems por tabla con `Faker` en español (`es_ES`):

| Tabla                    | Registros                    | Detalle                                                            |
|--------------------------|------------------------------|--------------------------------------------------------------------|
| `MENSAJES_RUTA`          | 50                           | Mensajes de chat con texto, emisor y estado `leido`                 |
| `NOTIFICACIONES_USUARIO` | 50                           | Cinco tipos de notificación con TTL de 7 a 30 días                 |
| `POSICIONES_TIEMPO_REAL` | 50 (5 rutas × 10 posiciones) | Latitud, longitud y velocidad, una posición cada 30 s, TTL de 24 h |

Los ids de ruta (`1`-`60`) y usuario (`1`-`100`) coinciden con los rangos del seed de RDS. Las escrituras se agrupan con `batch_writer` y `overwrite_by_pkeys`, los decimales se guardan como `Decimal` (DynamoDB no admite `float`) y las marcas de tiempo como ISO 8601 UTC. Debe ejecutarse después de `init_DynamoDB.py`.

> [!WARNING]
> El script no vacía las tablas antes de insertar: como las marcas de tiempo son aleatorias, repetirlo crea ítems nuevos. Ejecuta `flushdb.py` antes si quieres partir de cero.

### 9.4. Comprobación de conexión

```bash
python python/aws/DynamoDB/conexion.py
```

Imprime la respuesta de `list_tables()` con las tablas disponibles en la cuenta y región configuradas.

### 9.5. Suite de pruebas

`pruebas.py` permite lanzar cada prueba por separado o todas en orden. Usa ids deterministas (`999` para ruta y usuario) y tres marcas de tiempo fijas para no colisionar con los datos del seed.

| Comando                     | Prueba                                                                 |
|-----------------------------|------------------------------------------------------------------------|
| `python pruebas.py --1`     | Crea tres registros en cada tabla (`put_item`)                          |
| `python pruebas.py --2`     | Obtiene un registro de cada tabla (`get_item`)                          |
| `python pruebas.py --3`     | Actualiza un registro de cada tabla (`update_item`)                     |
| `python pruebas.py --4`     | Elimina un registro de cada tabla (`delete_item`)                       |
| `python pruebas.py --5`     | Obtiene todos los registros de cada tabla con `scan` paginado            |
| `python pruebas.py --6`     | Filtra con `scan` y usa el GSI en `POSICIONES_TIEMPO_REAL`               |
| `python pruebas.py --7`     | Eliminación condicional; localiza el ítem mediante el GSI               |
| `python pruebas.py --8`     | Combina varios filtros con `Attr` en cada tabla                         |
| `python pruebas.py --9`     | Consultas PartiQL, incluidas las del LSI y el GSI                       |
| `python pruebas.py --todas` | Ejecuta las nueve pruebas del 1 al 9                                    |

Ejecútalo desde `python/aws/DynamoDB/` o con la ruta completa desde la raíz:

```bash
python python/aws/DynamoDB/pruebas.py --todas
```

> [!IMPORTANT]
> Las pruebas 2 a 7 dependen de los registros que crea la prueba 1; si ejecutas `--todas`, se crean primero. Las pruebas 4 y 7 eliminan registros y la suite no limpia los datos al terminar: usa `flushdb.py` para reiniciar el estado. Sin argumentos, el script ejecuta también todas las pruebas.

### 9.6. Limpieza de datos

```bash
python python/aws/DynamoDB/flushdb.py
```

Elimina todos los ítems de las tres tablas mediante `scan` y `batch_writer`, pero conserva las tablas, sus índices y la configuración de TTL. Omite las tablas que no existan.

> [!WARNING]
> Esta limpieza es definitiva para los datos. Solo afecta a los ítems: para borrar también las tablas hay que hacerlo desde la consola o la API de AWS.

### 9.7. Orden recomendado del flujo DynamoDB

```bash
# 1. Crear las tablas, los índices y el TTL; actualizar el visor
python python/aws/DynamoDB/init_DynamoDB.py

# 2. Poblar las tres tablas
python python/aws/DynamoDB/seed.py

# 3. Comprobar conexión
python python/aws/DynamoDB/conexion.py

# 4. Ejecutar las pruebas (opcional)
python python/aws/DynamoDB/pruebas.py --todas

# 5. Vaciar los ítems cuando ya no se necesiten (opcional)
python python/aws/DynamoDB/flushdb.py
```

---

## 10. Visores de bases de datos

### 10.1. DbGate

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

### 10.2. Particularidades de Redis en el visor

- Redis tiene **16 bases de datos lógicas** (`db0` a `db15`) y DbGate las muestra todas, aunque estén vacías. Los scripts de este proyecto usan **`db0`**.
- Haz doble clic en `db0` para abrir el explorador de claves y pulsa **refrescar** tras ejecutar scripts; el visor no se actualiza solo.
- Las claves se agrupan en carpetas según el separador `:` (por ejemplo, `vehiculo:1` aparece dentro de la carpeta `vehiculo`).
- Las claves de tipo RedisJSON (como `smartruta:mysql:usuarios_json`) pueden no mostrarse correctamente en el visor. Compruébalas con `redis-cli`:

```bash
docker exec -it contenedor-smartruta-redis redis-cli JSON.GET smartruta:mysql:usuarios_json
```

### 10.3. DynamoDB Admin

**URL:** [http://localhost:8001](http://localhost:8001)

Es el visor web de DynamoDB (`aaronshaf/dynamodb-admin:latest`). Se conecta directamente al servicio de AWS con la región y las credenciales de `Docker/.env`, y usa `DYNAMO_ENDPOINT=${AWS_DYNAMODB_ENDPOINT}`. Muestra las tres tablas, sus índices LSI/GSI y los ítems almacenados.

`init_DynamoDB.py` escribe el endpoint real en `.env` y fuerza la recreación de este contenedor, por lo que conviene ejecutarlo antes de abrir el visor. Tras `seed.py`, `pruebas.py` o `flushdb.py`, actualiza la página para ver los cambios.

> [!NOTE]
> A diferencia de DbGate, este visor no necesita un archivo de certificados: la conexión a DynamoDB se realiza con la SDK de AWS sobre HTTPS.

---

## 11. Scripts de Redis

Se ejecutan desde el directorio `python/` con el entorno virtual activado y los servicios locales levantados.

### 11.1. Comprobación de conexión

```bash
python redis/conexion.py
```

Comprueba que Redis responde en `localhost:6379`.

### 11.2. Pruebas 1-20

Cubren claves-valor, patrones de búsqueda, filtros, estructuras JSON, listas e índices con RediSearch (búsqueda y *group by*).

```bash
python redis/pruebas_1_20.py
```

> [!WARNING]
> El script vacía la base de datos Redis `db0` al comenzar. No lo ejecutes si tienes datos que quieras conservar.

### 11.3. Script 21: MySQL → Redis

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

### 11.4. Script 22: Redis → PostgreSQL

Lee de Redis los usuarios que dejó el script 21 (los hashes o, si no existen, el JSON completo) y los inserta o actualiza en la tabla `USUARIOS_DESDE_REDIS` de PostgreSQL, que crea si no existe.

```bash
python redis/script_22.py
```

> [!IMPORTANT]
> Ejecuta el script 21 antes que el 22. Si lanzas las pruebas 1-20 entre ambos, los datos del script 21 se borran de Redis y el 22 no encontrará nada que importar.

### 11.5. Vaciar Redis

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

## 12. Documentación por motor

En la carpeta [`docs/`](docs/) está la guía de cada base de datos, junto con la explicación detallada de su análisis e informe:

- [MySQL: despliegue y análisis](docs/mysql.md)
- [PostgreSQL: despliegue y análisis](docs/postgres.md)
- [MariaDB: despliegue y análisis](docs/mariadb.md)
- [Redis: despliegue](docs/redis.md)

No hay una guía específica para DynamoDB: su documentación está en la [sección 9](#9-pipeline-en-aws-dynamodb). El [diagrama ER](#13-diagrama-er) cubre únicamente el modelo relacional local.

---

## 13. Diagrama ER

![Diagrama entidad-relación](docs/Diagrama%20ER.png)