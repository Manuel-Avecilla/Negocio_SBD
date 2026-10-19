# Negocio_SBD

Proyecto de base de datos relacional para **SmartRuta & Movilidad Sostenible** desplegado en contenedores Docker (MySQL, PostgreSQL y MariaDB) con configuración centralizada mediante `.env` y volúmenes persistentes independientes.

---

## 1. Configuración Previa

```bash
cd Docker/
```

### Copiar la plantilla de variables de entorno
```bash
cp .env.template .env
```

### Crear los volúmenes persistentes en Docker
```bash
docker volume create mysql_data
docker volume create postgres_data
docker volume create mariadb_data
```

---

## 1. MySQL (`contenedor-smartruta-mysql`)

### Construir la imagen
```bash
docker build -t smartruta-mysql ./mysql
```

### Ejecutar el contenedor
```bash
docker run -d \
  -p 3306:3306 \
  --name contenedor-smartruta-mysql \
  --env-file .env \
  -v mysql_data:/var/lib/mysql \
  smartruta-mysql
```

---

## 2. PostgreSQL (`contenedor-smartruta-postgres`)

### Construir la imagen
```bash
docker build -t smartruta-postgres ./postgres
```

### Ejecutar el contenedor
```bash
docker run -d \
  -p 5432:5432 \
  --name contenedor-smartruta-postgres \
  --env-file .env \
  -v postgres_data:/var/lib/postgresql/data \
  smartruta-postgres
```

---

## 3. MariaDB (`contenedor-smartruta-mariadb`)

### Construir la imagen
```bash
docker build -t smartruta-mariadb ./mariadb
```

### Ejecutar el contenedor
```bash
docker run -d \
  -p 3307:3306 \
  --name contenedor-smartruta-mariadb \
  --env-file .env \
  -v mariadb_data:/var/lib/mysql \
  smartruta-mariadb
```

---

Docker Compose

```bash
docker compose up -d --build
```

```bash
docker compose down
```

Eliminar volúmenes persistentes (si es necesario)

```bash
docker compose down -v
```

---

Python

```bash
cd python
```

```bash
python3 -m venv venv
```

```bash
source venv/bin/activate
```

```bash
python -m pip install --upgrade pip
```

```bash
pip install -r requirements.txt
```