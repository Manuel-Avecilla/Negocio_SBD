# Dockerfile
FROM mysql:latest

# Argumentos que se reciben durante el build o desde docker-compose
ARG MYSQL_ROOT_PASSWORD
ARG MYSQL_DATABASE
ARG MYSQL_USER
ARG MYSQL_PASSWORD

# Asignación a variables de entorno del contenedor
ENV MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD}
ENV MYSQL_DATABASE=${MYSQL_DATABASE}
ENV MYSQL_USER=${MYSQL_USER}
ENV MYSQL_PASSWORD=${MYSQL_PASSWORD}

# COPY ./init.sql /docker-entrypoint-initdb.d/

# Creamos un volumen para los datos
VOLUME ["/var/lib/mysql"]

EXPOSE 3306