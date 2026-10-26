FROM redis:alpine

# Declarar el directorio de datos como volumen
VOLUME ["/data"]

# Expone el puerto predeterminado de Redis
EXPOSE 6379

# Inicia el servidor de Redis con persistencia de datos activada
CMD ["redis-server", "--appendonly", "yes"]
