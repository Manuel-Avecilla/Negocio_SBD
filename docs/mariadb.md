# Despliegue y Análisis de Datos: MariaDB

Guía detallada para el despliegue del contenedor Docker de **MariaDB** y especificación del informe analítico [`mariadb.json`](file:///home/manuel/Escritorio/IABD2026/Negocio_SBD/json_info).

---

## 1. Despliegue con Dockerfile

Para compilar y levantar el servicio MariaDB de forma individual utilizando su propio Dockerfile y variables de entorno centralizadas:

### 1.1. Configuración previa

Accede a la carpeta de configuración y asegúrate de que el archivo `.env` está preparado y el volumen persistente creado:

```bash
cd Docker/

# Copiar plantilla si aún no existe el archivo .env
cp .env.template .env

# Crear volumen persistente de MariaDB
docker volume create mariadb_data
```

### 1.2. Construir la imagen Docker

Construye la imagen personalizada a partir del archivo [`Docker/mariadb/Dockerfile`](file:///home/manuel/Escritorio/IABD2026/Negocio_SBD/Docker/mariadb/Dockerfile):

```bash
docker build -t smartruta-mariadb ./mariadb
```

### 1.3. Ejecutar el contenedor

Inicia el contenedor en segundo plano vinculando el puerto host `3307` al puerto interno `3306`, inyectando las variables de entorno de `.env` y asociando el volumen persistente:

```bash
docker run -d \
  -p 3307:3306 \
  --name contenedor-smartruta-mariadb \
  --env-file .env \
  -v mariadb_data:/var/lib/mysql \
  smartruta-mariadb
```

> [!NOTE]
> MariaDB utiliza el puerto host `3307` para evitar colisiones con el puerto estándar `3306` asignado a MySQL.

### 1.4. Comprobación y Logs

```bash
# Verificar estado del contenedor
docker ps --filter "name=contenedor-smartruta-mariadb"

# Ver registros de inicialización
docker logs -f contenedor-smartruta-mariadb
```

---

## 2. Informe Analítico: `mariadb.json`

### 2.1. Enfoque del Análisis
**Evolución Temporal, Condiciones Operativas y Encuestas Ciudadanas.**

MariaDB se ha seleccionado para estudiar la **dimensión temporal y el contexto operacional** de SmartRuta. Analiza cómo evolucionan los hábitos de transporte a lo largo de los meses, cómo inciden las variables externas (incidencias de tráfico e inclemencias meteorológicas) en la movilidad, y qué percepción de tiempos y modos reportan los usuarios en las encuestas anónimas.

### 2.2. Secciones del Informe y Justificación

| Bloque en el JSON | Tablas Involucradas | Justificación Analítica |
| :--- | :--- | :--- |
| **`evolucion_temporal_mensual`** | `HISTORIAL_DESPLAZAMIENTOS` $\bowtie$ `USUARIOS` | Desglose mensual de desplazamientos, distancia total acumulada, CO₂ ahorrado y tiempo medio por modo de transporte. Permite observar estacionalidad y tendencias de adopción a lo largo del año. |
| **`impacto_incidencias_viales`** | `INCIDENCIAS_TRAFICO` | Conteo y clasificación de incidencias viales por tipología (`Retencion`, `Obras`, `Accidente`, `Corte_Vial`, `Otro`) y gravedad (`Bajo`, `Medio`, `Alto`, `Critico`), contabilizando además el número de fuentes informantes. Evalúa puntos críticos de congestión y riesgo vial en la red. |
| **`percepcion_ciudadana_encuestas`** | `ENCUESTAS_HABITOS` $\bowtie$ `RESPUESTAS_ENCUESTA` | Muestra la distribución del modo de transporte habitual elegido por los encuestados y analiza la percepción de tiempo empleado (tiempo promedio estimado, mínimo y máximo en minutos). Permite contrastar la percepción subjetiva frente a los datos reales registrados. |
| **`registro_condiciones_meteorologicas`** | `REGISTRO_METEOROLOGICO` | Estadísticas climáticas agrupadas por estado del tiempo (`Soleado`, `Lluvioso`, `Nublado`, `Viento`): temperaturas medias, mínimas y máximas, junto con el volumen de precipitaciones acumuladas. Proporciona el contexto meteorológico que influye directamente en la elección modal (ej. lluvia desincentivando bicicleta). |

### 2.3. Estructura de Salida Ejemplo

```json
{
  "metadatos": {
    "motor": "MariaDB",
    "fecha_generacion": "2026-10-24T16:30:45.123456",
    "enfoque_analitico": "Evolución Temporal, Condiciones Operativas y Encuestas Ciudadanas",
    "descripcion": "Tendencias mensuales de movilidad, afecciones viales por incidencias..."
  },
  "evolucion_temporal_mensual": [
    {
      "periodo_mes": "2026-03",
      "modo_transporte": "Autobus",
      "total_viajes": 14,
      "distancia_total_km": 289.4,
      "co2_ahorrado_kg": 34.12,
      "tiempo_promedio_min": 42.1
    }
  ],
  "impacto_incidencias_viales": [ ... ],
  "percepcion_ciudadana_encuestas": [ ... ],
  "registro_condiciones_meteorologicas": [ ... ]
}
```
