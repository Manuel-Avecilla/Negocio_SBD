# Despliegue y Análisis de Datos: PostgreSQL

Guía detallada para el despliegue del contenedor Docker de **PostgreSQL** y especificación del informe analítico [`postgress.json`](file:///home/manuel/Escritorio/IABD2026/Negocio_SBD/json_info).

---

## 1. Despliegue con Dockerfile

Para compilar y levantar el servicio PostgreSQL de forma individual utilizando su propio Dockerfile y variables de entorno centralizadas:

### 1.1. Configuración previa

Accede a la carpeta de configuración y asegúrate de que el archivo `.env` está preparado y el volumen persistente creado:

```bash
cd Docker/

# Copiar plantilla si aún no existe el archivo .env
cp .env.template .env

# Crear volumen persistente de PostgreSQL
docker volume create postgres_data
```

### 1.2. Construir la imagen Docker

Construye la imagen personalizada a partir del archivo [`Docker/postgres/Dockerfile`](file:///home/manuel/Escritorio/IABD2026/Negocio_SBD/Docker/postgres/Dockerfile):

```bash
docker build -t smartruta-postgres ./postgres
```

### 1.3. Ejecutar el contenedor

Inicia el contenedor en segundo plano vinculando el puerto `5432`, inyectando las variables de entorno de `.env` y asociando el volumen persistente:

```bash
docker run -d \
  -p 5432:5432 \
  --name contenedor-smartruta-postgres \
  --env-file .env \
  -v postgres_data:/var/lib/postgresql/data \
  smartruta-postgres
```

### 1.4. Comprobación y Logs

```bash
# Verificar estado del contenedor
docker ps --filter "name=contenedor-smartruta-postgres"

# Ver registros de inicialización
docker logs -f contenedor-smartruta-postgres
```

---

## 2. Informe Analítico: `postgress.json`

### 2.1. Enfoque del Análisis
**Red de Carpooling, Dinámica de Usuarios y Eficiencia Operativa.**

PostgreSQL se ha seleccionado para analizar el **comportamiento de la red de viajes compartidos (carpooling)** y las relaciones entre entidades. Aprovecha la capacidad analítica relacional para cruzar la oferta de plazas de los conductores con la demanda real de los pasajeros, examinar tasas de conversión de reservas y medir el desempeño cinemático/GPS de las rutas.

### 2.2. Secciones del Informe y Justificación

| Bloque en el JSON | Tablas Involucradas | Justificación Analítica |
| :--- | :--- | :--- |
| **`eficiencia_rutas_y_vehiculos`** | `RUTAS_CARPOOLING` $\bowtie$ `VEHICULOS` $\bowtie_{left}$ `RESERVAS_CARPOOLING` | Evalúa la salud operativa del servicio según el estado de la ruta (`Programada`, `En_Curso`, `Completada`, `Cancelada`) y el tipo de propulsión del vehículo. Mide el balance oferta-demanda comparando plazas disponibles frente a solicitudes totales, confirmadas, pendientes, canceladas y rechazadas. |
| **`ranking_top_10_conductores`** | `USUARIOS` (conductor) $\bowtie$ `RUTAS_CARPOOLING` $\bowtie_{left}$ `RESERVAS_CARPOOLING` | Identifica a los conductores líderes por número de rutas publicadas, capacidad de plazas ofrecida y volumen de reservas confirmadas logradas. Permite reconocer a los usuarios más comprometidos y diseñar esquemas de fidelización. |
| **`comportamiento_demanda_pasajeros`** | `RESERVAS_CARPOOLING` $\bowtie$ `USUARIOS` (pasajero) $\bowtie$ `RUTAS_CARPOOLING` | Analiza el comportamiento de los pasajeros desglosado por tipo de usuario (`Alumno`, `Profesor`, `Familia`) y estado de la reserva. Permite entender qué segmentos de la comunidad educativa utilizan con mayor éxito el servicio y cuáles experimentan fricción en la asignación de plazas. |
| **`monitoreo_velocidades_gps`** | `REGISTROS_GPS` $\bowtie$ `RUTAS_CARPOOLING` | Analiza la telemetría recopilada en los trayectos según el estado de la ruta, calculando muestras de posicionamiento, usuarios rastreados y velocidades medias y máximas registradas (km/h) para auditoría de seguridad vial. |

### 2.3. Estructura de Salida Ejemplo

```json
{
  "metadatos": {
    "motor": "PostgreSQL",
    "fecha_generacion": "2026-10-24T16:30:45.123456",
    "enfoque_analitico": "Red de Carpooling, Dinámica de Usuarios y Eficiencia Operativa",
    "descripcion": "Evaluación del servicio de viajes compartidos: balance oferta-demanda..."
  },
  "eficiencia_rutas_y_vehiculos": [
    {
      "estado_ruta": "Programada",
      "tipo_propulsion": "Electrico",
      "total_rutas_ofertadas": 15,
      "plazas_totales_disponibles": 38,
      "total_solicitudes_reserva": 24,
      "reservas_confirmadas": 16,
      "reservas_pendientes": 5,
      "reservas_canceladas": 2,
      "reservas_rechazadas": 1
    }
  ],
  "ranking_top_10_conductores": [ ... ],
  "comportamiento_demanda_pasajeros": [ ... ],
  "monitoreo_velocidades_gps": [ ... ]
}
```
