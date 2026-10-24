# Despliegue y Análisis de Datos: MySQL

Guía detallada para el despliegue del contenedor Docker de **MySQL** y especificación del informe analítico [`mysql.json`](file:///home/manuel/Escritorio/IABD2026/Negocio_SBD/json_info).

---

## 1. Despliegue con Dockerfile

Para compilar y levantar el servicio MySQL de forma individual utilizando su propio Dockerfile y variables de entorno centralizadas:

### 1.1. Configuración previa

Accede a la carpeta de configuración y asegúrate de que el archivo `.env` está preparado y el volumen persistente creado:

```bash
cd Docker/

# Copiar plantilla si aún no existe el archivo .env
cp .env.template .env

# Crear volumen persistente de MySQL
docker volume create mysql_data
```

### 1.2. Construir la imagen Docker

Construye la imagen personalizada a partir del archivo [`Docker/mysql/Dockerfile`](file:///home/manuel/Escritorio/IABD2026/Negocio_SBD/Docker/mysql/Dockerfile):

```bash
docker build -t smartruta-mysql ./mysql
```

### 1.3. Ejecutar el contenedor

Inicia el contenedor en segundo plano vinculando el puerto `3306`, inyectando las variables de entorno de `.env` y asociando el volumen persistente:

```bash
docker run -d \
  -p 3306:3306 \
  --name contenedor-smartruta-mysql \
  --env-file .env \
  -v mysql_data:/var/lib/mysql \
  smartruta-mysql
```

### 1.4. Comprobación y Logs

```bash
# Verificar estado del contenedor
docker ps --filter "name=contenedor-smartruta-mysql"

# Ver registros de inicialización
docker logs -f contenedor-smartruta-mysql
```

---

## 2. Informe Analítico: `mysql.json`

### 2.1. Enfoque del Análisis
**Sostenibilidad Global, Impacto Ambiental y Distribución Modal.**

MySQL se ha seleccionado para proporcionar la **visión macro ejecutiva** del proyecto. Permite cuantificar el impacto ecológico directo del proyecto SmartRuta, responder a preguntas sobre ahorro de huella de carbono, evaluar la penetración de medios de transporte no contaminantes y analizar el compromiso ciudadano distribuido por zonas geográficas.

### 2.2. Secciones del Informe y Justificación

| Bloque en el JSON | Tablas Involucradas | Justificación Analítica |
| :--- | :--- | :--- |
| **`resumen_ejecutivo_sostenibilidad`** | `HISTORIAL_DESPLAZAMIENTOS` | KPIs de alto nivel: recuento de usuarios activos, total de desplazamientos, distancia total acumulada (km), distancia media, total de CO₂ ahorrado (kg) y tiempo medio de viaje. Permite medir el impacto global del sistema en una sola vista. |
| **`adopcion_modal_por_perfil_usuario`** | `HISTORIAL_DESPLAZAMIENTOS` $\bowtie$ `USUARIOS` | Desglose por modo (`A_Pie`, `Bicicleta`, `Autobus`, `Carpooling`, `Coche_Individual`) y tipo de usuario (`Alumno`, `Profesor`, `Familia`, `Admin`). Identifica qué perfil aporta mayor reducción de emisiones y cuáles requieren incentivos de movilidad sostenible. |
| **`distribucion_parque_vehicular`** | `VEHICULOS` $\bowtie$ `USUARIOS` | Clasificación de vehículos por tipo de propulsión (`Electrico`, `Hibrido`, `Gasolina`, `Diesel`) y rol del propietario, calculando total de vehículos y plazas ofertadas. Determina la capacidad del parque móvil limpio disponible para el carpooling. |
| **`top_10_zonas_mayor_impacto_ecologico`** | `DIRECCIONES` $\bowtie$ `USUARIOS` $\bowtie$ `HISTORIAL_DESPLAZAMIENTOS` | Ranking de los 10 barrios con mayor ahorro acumulado de emisiones y distancia recorrida, junto al número de residentes y viajes. Facilita la planificación de infraestructuras y rutas en los vecindarios clave. |

### 2.3. Estructura de Salida Ejemplo

```json
{
  "metadatos": {
    "motor": "MySQL",
    "fecha_generacion": "2026-10-24T16:30:45.123456",
    "enfoque_analitico": "Sostenibilidad Global, Impacto Ambiental y Distribución Modal",
    "descripcion": "Indicadores clave de movilidad ecológica, ahorro acumulado de emisiones CO2..."
  },
  "resumen_ejecutivo_sostenibilidad": {
    "usuarios_activos_desplazamientos": 48,
    "total_desplazamientos": 120,
    "distancia_total_km": 2745.32,
    "distancia_media_km": 22.88,
    "co2_total_ahorrado_kg": 328.412,
    "co2_promedio_por_viaje_kg": 2.737,
    "tiempo_promedio_minutos": 47.3
  },
  "adopcion_modal_por_perfil_usuario": [
    {
      "modo_transporte": "Bicicleta",
      "tipo_usuario": "Alumno",
      "total_viajes": 18,
      "distancia_acumulada_km": 395.2,
      "co2_ahorrado_kg": 62.15,
      "promedio_co2_ahorrado_kg": 3.453,
      "tiempo_medio_minutos": 38.5
    }
  ],
  "distribucion_parque_vehicular": [ ... ],
  "top_10_zonas_mayor_impacto_ecologico": [ ... ]
}
```
