CREATE DATABASE IF NOT EXISTS smartruta_db;
USE smartruta_db;

-- 1. Tabla DIRECCIONES
CREATE TABLE DIRECCIONES (
    id_direccion INT AUTO_INCREMENT PRIMARY KEY,
    codigo_postal VARCHAR(10),
    barrio_zona VARCHAR(100),
    latitud DECIMAL(10,8),
    longitud DECIMAL(11,8)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. Tabla USUARIOS
CREATE TABLE USUARIOS (
    id_usuario INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    contrasena_hash VARCHAR(255) NOT NULL,
    tipo_usuario ENUM('Alumno', 'Profesor', 'Familia', 'Admin') NOT NULL,
    id_direccion INT,
    consentimiento_rgpd BOOLEAN NOT NULL DEFAULT FALSE,
    fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_direccion) REFERENCES DIRECCIONES(id_direccion)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. Tabla VEHICULOS
CREATE TABLE VEHICULOS (
    id_vehiculo INT AUTO_INCREMENT PRIMARY KEY,
    id_propietario INT NOT NULL,
    marca_modelo VARCHAR(100) NOT NULL,
    plazas_totales INT NOT NULL,
    tipo_propulsion ENUM('Electrico', 'Hibrido', 'Gasolina', 'Diesel') NOT NULL,
    matricula_hash VARCHAR(255) NOT NULL,
    FOREIGN KEY (id_propietario) REFERENCES USUARIOS(id_usuario)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. Tabla RUTAS_CARPOOLING
CREATE TABLE RUTAS_CARPOOLING (
    id_ruta INT AUTO_INCREMENT PRIMARY KEY,
    id_conductor INT NOT NULL,
    id_vehiculo INT NOT NULL,
    origen_lat DECIMAL(10,8) NOT NULL,
    origen_lon DECIMAL(11,8) NOT NULL,
    destino_lat DECIMAL(10,8) NOT NULL,
    destino_lon DECIMAL(11,8) NOT NULL,
    hora_salida DATETIME NOT NULL,
    plazas_disponibles INT NOT NULL,
    estado ENUM('Programada', 'En_Curso', 'Completada', 'Cancelada') DEFAULT 'Programada',
    FOREIGN KEY (id_conductor) REFERENCES USUARIOS(id_usuario),
    FOREIGN KEY (id_vehiculo) REFERENCES VEHICULOS(id_vehiculo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. Tabla RESERVAS_CARPOOLING
CREATE TABLE RESERVAS_CARPOOLING (
    id_reserva INT AUTO_INCREMENT PRIMARY KEY,
    id_ruta INT NOT NULL,
    id_pasajero INT NOT NULL,
    punto_recogida_lat DECIMAL(10,8),
    punto_recogida_lon DECIMAL(11,8),
    estado_reserva ENUM('Pendiente', 'Confirmada', 'Rechazada', 'Cancelada') DEFAULT 'Pendiente',
    fecha_reserva DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_ruta) REFERENCES RUTAS_CARPOOLING(id_ruta),
    FOREIGN KEY (id_pasajero) REFERENCES USUARIOS(id_usuario)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 6. Tabla REGISTROS_GPS
CREATE TABLE REGISTROS_GPS (
    id_registro_gps BIGINT AUTO_INCREMENT PRIMARY KEY,
    id_usuario INT NOT NULL,
    id_ruta INT,
    latitud DECIMAL(10,8) NOT NULL,
    longitud DECIMAL(11,8) NOT NULL,
    velocidad_kmh DECIMAL(5,2),
    timestamp_captura DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_usuario) REFERENCES USUARIOS(id_usuario),
    FOREIGN KEY (id_ruta) REFERENCES RUTAS_CARPOOLING(id_ruta)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 7. Tabla HISTORIAL_DESPLAZAMIENTOS
CREATE TABLE HISTORIAL_DESPLAZAMIENTOS (
    id_desplazamiento INT AUTO_INCREMENT PRIMARY KEY,
    id_usuario INT NOT NULL,
    modo_transporte ENUM('A_Pie', 'Bicicleta', 'Autobus', 'Carpooling', 'Coche_Individual') NOT NULL,
    distancia_km DECIMAL(6,2) NOT NULL,
    co2_ahorrado_kg DECIMAL(6,3) DEFAULT 0.000,
    tiempo_minutos INT,
    fecha_desplazamiento DATE NOT NULL,
    FOREIGN KEY (id_usuario) REFERENCES USUARIOS(id_usuario)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 8. Tabla INCIDENCIAS_TRAFICO
CREATE TABLE INCIDENCIAS_TRAFICO (
    id_incidencia INT AUTO_INCREMENT PRIMARY KEY,
    tipo_incidencia ENUM('Retencion', 'Obras', 'Accidente', 'Corte_Vial', 'Otro') NOT NULL,
    latitud DECIMAL(10,8) NOT NULL,
    longitud DECIMAL(11,8) NOT NULL,
    descripcion TEXT,
    nivel_gravedad ENUM('Bajo', 'Medio', 'Alto', 'Critico') DEFAULT 'Bajo',
    fecha_inicio DATETIME DEFAULT CURRENT_TIMESTAMP,
    fuente_dato VARCHAR(50)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 9. Tabla ENCUESTAS_HABITOS
CREATE TABLE ENCUESTAS_HABITOS (
    id_encuesta INT AUTO_INCREMENT PRIMARY KEY,
    titulo VARCHAR(150) NOT NULL,
    descripcion TEXT,
    fecha_inicio DATE NOT NULL,
    fecha_fin DATE NOT NULL,
    activo BOOLEAN DEFAULT TRUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 10. Tabla RESPUESTAS_ENCUESTA
CREATE TABLE RESPUESTAS_ENCUESTA (
    id_respuesta INT AUTO_INCREMENT PRIMARY KEY,
    id_encuesta INT NOT NULL,
    token_usuario_anonimo VARCHAR(255) NOT NULL,
    modo_habitual ENUM('A_Pie', 'Bicicleta', 'Autobus', 'Coche_Privado') NOT NULL,
    tiempo_medio_min INT,
    comentarios_texto_libre TEXT,
    FOREIGN KEY (id_encuesta) REFERENCES ENCUESTAS_HABITOS(id_encuesta)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 11. Tabla REGISTRO_METEOROLOGICO
CREATE TABLE REGISTRO_METEOROLOGICO (
    id_clima INT AUTO_INCREMENT PRIMARY KEY,
    fecha DATE NOT NULL,
    hora TIME NOT NULL,
    temperatura_c DECIMAL(4,1),
    precipitacion_mm DECIMAL(5,2),
    estado_tiempo VARCHAR(50)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;