FROM mariadb:latest

# Argumentos recibidos durante el build
ARG MYSQL_ROOT_PASSWORD
ARG MYSQL_DATABASE
ARG MYSQL_USER
ARG MYSQL_PASSWORD

# Asignación a las variables de entorno oficiales de MariaDB
ENV MARIADB_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD}
ENV MARIADB_DATABASE=${MYSQL_DATABASE}
ENV MARIADB_USER=${MYSQL_USER}
ENV MARIADB_PASSWORD=${MYSQL_PASSWORD}

# Copiamos el script SQL de inicialización
# COPY ./init.sql /docker-entrypoint-initdb.d/

# Volumen persistente para los datos de MariaDB
VOLUME ["/var/lib/mysql"]

EXPOSE 3306