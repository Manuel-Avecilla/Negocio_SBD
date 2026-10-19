FROM postgres:15

# Argumentos recibidos durante el build o runtime
ARG POSTGRES_DB
ARG POSTGRES_USER
ARG POSTGRES_PASSWORD

# Asignación a las variables de entorno oficiales de PostgreSQL
ENV POSTGRES_DB=${POSTGRES_DB}
ENV POSTGRES_USER=${POSTGRES_USER}
ENV POSTGRES_PASSWORD=${POSTGRES_PASSWORD}

# Script SQL de inicialización que se ejecuta al arrancar el contenedor por primera vez
# COPY ./init.sql /docker-entrypoint-initdb.d/

# Volumen persistente para los datos de PostgreSQL
VOLUME ["/var/lib/postgresql/data"]

EXPOSE 5432