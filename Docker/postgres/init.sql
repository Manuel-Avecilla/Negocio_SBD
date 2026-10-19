-- Creación de tipos ENUM personalizados en PostgreSQL
CREATE TYPE tipo_usuario_enum AS ENUM ('Alumno', 'Profesor', 'Familia', 'Admin');
CREATE TYPE tipo_propulsion_enum AS ENUM ('Electrico', 'Hibrido', 'Gasolina', 'Diesel');
CREATE TYPE estado_ruta_enum AS ENUM ('Programada', 'En_Curso', 'Completada', 'Cancelada');
CREATE TYPE estado_reserva_enum AS ENUM ('Pendiente', 'Confirmada', 'Rechazada', 'Cancelada');
CREATE TYPE modo_transporte_enum AS ENUM ('A_Pie', 'Bicicleta', 'Autobus', 'Carpooling', 'Coche_Individual');
CREATE TYPE tipo_incidencia_enum AS ENUM ('Retencion', 'Obras', 'Accidente', 'Corte_Vial', 'Otro');
CREATE TYPE nivel_gravedad_enum AS ENUM ('Bajo', 'Medio', 'Alto', 'Critico');
CREATE TYPE modo_habitual_enum AS ENUM ('A_Pie', 'Bicicleta', 'Autobus', 'Coche_Privado');

-- 1. Tabla DIRECCIONES
CREATE TABLE DIRECCIONES (
    id_direccion SERIAL PRIMARY KEY,
    codigo_postal VARCHAR(10),
    barrio_zona VARCHAR(100),
    latitud NUMERIC(10,8),
    longitud NUMERIC(11,8)
);

-- 2. Tabla USUARIOS
CREATE TABLE USUARIOS (
    id_usuario SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    contrasena_hash VARCHAR(255) NOT NULL,
    tipo_usuario tipo_usuario_enum NOT NULL,
    id_direccion INT REFERENCES DIRECCIONES(id_direccion),
    consentimiento_rgpd BOOLEAN NOT NULL DEFAULT FALSE,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Tabla VEHICULOS
CREATE TABLE VEHICULOS (
    id_vehiculo SERIAL PRIMARY KEY,
    id_propietario INT NOT NULL REFERENCES USUARIOS(id_usuario),
    marca_modelo VARCHAR(100) NOT NULL,
    plazas_totales INT NOT NULL,
    tipo_propulsion tipo_propulsion_enum NOT NULL,
    matricula_hash VARCHAR(255) NOT NULL
);

-- 4. Tabla RUTAS_CARPOOLING
CREATE TABLE RUTAS_CARPOOLING (
    id_ruta SERIAL PRIMARY KEY,
    id_conductor INT NOT NULL REFERENCES USUARIOS(id_usuario),
    id_vehiculo INT NOT NULL REFERENCES VEHICULOS(id_vehiculo),
    origen_lat NUMERIC(10,8) NOT NULL,
    origen_lon NUMERIC(11,8) NOT NULL,
    destino_lat NUMERIC(10,8) NOT NULL,
    destino_lon NUMERIC(11,8) NOT NULL,
    hora_salida TIMESTAMP NOT NULL,
    plazas_disponibles INT NOT NULL,
    estado estado_ruta_enum DEFAULT 'Programada'
);

-- 5. Tabla RESERVAS_CARPOOLING
CREATE TABLE RESERVAS_CARPOOLING (
    id_reserva SERIAL PRIMARY KEY,
    id_ruta INT NOT NULL REFERENCES RUTAS_CARPOOLING(id_ruta),
    id_pasajero INT NOT NULL REFERENCES USUARIOS(id_usuario),
    punto_recogida_lat NUMERIC(10,8),
    punto_recogida_lon NUMERIC(11,8),
    estado_reserva estado_reserva_enum DEFAULT 'Pendiente',
    fecha_reserva TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. Tabla REGISTROS_GPS
CREATE TABLE REGISTROS_GPS (
    id_registro_gps BIGSERIAL PRIMARY KEY,
    id_usuario INT NOT NULL REFERENCES USUARIOS(id_usuario),
    id_ruta INT REFERENCES RUTAS_CARPOOLING(id_ruta),
    latitud NUMERIC(10,8) NOT NULL,
    longitud NUMERIC(11,8) NOT NULL,
    velocidad_kmh NUMERIC(5,2),
    timestamp_captura TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. Tabla HISTORIAL_DESPLAZAMIENTOS
CREATE TABLE HISTORIAL_DESPLAZAMIENTOS (
    id_desplazamiento SERIAL PRIMARY KEY,
    id_usuario INT NOT NULL REFERENCES USUARIOS(id_usuario),
    modo_transporte modo_transporte_enum NOT NULL,
    distancia_km NUMERIC(6,2) NOT NULL,
    co2_ahorrado_kg NUMERIC(6,3) DEFAULT 0.000,
    tiempo_minutos INT,
    fecha_desplazamiento DATE NOT NULL
);

-- 8. Tabla INCIDENCIAS_TRAFICO
CREATE TABLE INCIDENCIAS_TRAFICO (
    id_incidencia SERIAL PRIMARY KEY,
    tipo_incidencia tipo_incidencia_enum NOT NULL,
    latitud NUMERIC(10,8) NOT NULL,
    longitud NUMERIC(11,8) NOT NULL,
    descripcion TEXT,
    nivel_gravedad nivel_gravedad_enum DEFAULT 'Bajo',
    fecha_inicio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fuente_dato VARCHAR(50)
);

-- 9. Tabla ENCUESTAS_HABITOS
CREATE TABLE ENCUESTAS_HABITOS (
    id_encuesta SERIAL PRIMARY KEY,
    titulo VARCHAR(150) NOT NULL,
    descripcion TEXT,
    fecha_inicio DATE NOT NULL,
    fecha_fin DATE NOT NULL,
    activo BOOLEAN DEFAULT TRUE
);

-- 10. Tabla RESPUESTAS_ENCUESTA
CREATE TABLE RESPUESTAS_ENCUESTA (
    id_respuesta SERIAL PRIMARY KEY,
    id_encuesta INT NOT NULL REFERENCES ENCUESTAS_HABITOS(id_encuesta),
    token_usuario_anonimo VARCHAR(255) NOT NULL,
    modo_habitual modo_habitual_enum NOT NULL,
    tiempo_medio_min INT,
    comentarios_texto_libre TEXT
);

-- 11. Tabla REGISTRO_METEOROLOGICO
CREATE TABLE REGISTRO_METEOROLOGICO (
    id_clima SERIAL PRIMARY KEY,
    fecha DATE NOT NULL,
    hora TIME NOT NULL,
    temperatura_c NUMERIC(4,1),
    precipitacion_mm NUMERIC(5,2),
    estado_tiempo VARCHAR(50)
);