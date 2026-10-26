# Negocio_SBD · SmartRuta & Movilidad Sostenible

Sistema integral de base de datos relacional y analítica de datos para **SmartRuta & Movilidad Sostenible**. La infraestructura se despliega en contenedores Docker independientes con tres motores de bases de datos (**MySQL 8**, **PostgreSQL 15** y **MariaDB**), configuración centralizada mediante variables de entorno (`.env`), volúmenes persistentes y un pipeline en Python para la inicialización del esquema, poblado de datos sintéticos mediante `Faker` y generación de informes analíticos en formato JSON.

---

## 1. Despliegue de Base de Datos con Docker

### 1.1. Configuración Inicial del Entorno

Accede al directorio de Docker y genera el archivo de configuración a partir de la plantilla:

```bash
cd Docker/
cp .env.template .env
```

### 1.2. Despliegue Unificado con Docker Compose

Para compilar las imágenes y levantar simultáneamente los tres motores de bases de datos en segundo plano:

```bash
docker compose up -d --build
```

**Comandos de gestión:**

```bash
# Detener los contenedores conservando los datos persistentes
docker compose down

# Detener los contenedores y eliminar volúmenes persistentes
docker compose down -v
```

> [!TIP]
> Para construir y levantar cada base de datos de manera independiente utilizando su propio `Dockerfile`, consulta las guías específicas en la carpeta [`docs/`](docs/).

---

## 2. Configuración del Entorno Python

Para preparar el entorno de ejecución de los scripts de inicialización, poblado y analítica:

```bash
cd ../python

# Crear el entorno virtual
python3 -m venv venv

# Activar el entorno virtual
source venv/bin/activate

# Actualizar el gestor de paquetes e instalar dependencias
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

## 3. Pipeline de Datos y Reportes

### Inicialización y Poblado de Datos

```bash
# Crear esquema en los tres motores
python init_db.py

# Poblar con datos de prueba sintéticos
python seed.py
```

### Generación de Informes Analíticos JSON

```bash
# Ejecutar análisis en MySQL, PostgreSQL y MariaDB
python generate_reports.py
```

Los informes resultantes se guardan de forma versionada en la raíz del proyecto dentro de `json_reports/Date_YYYY_MM_DD_Hour_HH-MM-SS/`:
* `mysql.json`: Indicadores globales de sostenibilidad y distribución modal.
* `postgress.json`: Red de carpooling, dinámicas de usuarios y telemetría GPS.
* `mariadb.json`: Tendencias temporales, condiciones meteorológicas e incidencias viales.

---

## 4. Documentación Detallada por Motor

En la carpeta [`docs/`](docs/) se encuentra la guía específica de cada base de datos junto a la explicación detallada de su análisis e informe:

* [MySQL - Despliegue y Análisis](docs/mysql.md)
* [PostgreSQL - Despliegue y Análisis](docs/postgres.md)
* [MariaDB - Despliegue y Análisis](docs/mariadb.md)
* [Redis - Despliegue](docs/redis.md)
