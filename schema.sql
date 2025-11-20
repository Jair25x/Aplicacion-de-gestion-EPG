-- ============================
-- TABLA: facultad
-- ============================
DROP TABLE IF EXISTS facultad;

CREATE TABLE facultad (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nombre TEXT NOT NULL,      -- Ej: "Facultad de Ciencias y Humanidades"
  codigo TEXT,               -- Opcional
  observaciones TEXT,        -- Comentarios internos, notas generales
  activo INTEGER NOT NULL DEFAULT 1
);

-- ============================
-- TABLA: programa_academico
-- ============================
DROP TABLE IF EXISTS programa_academico;

CREATE TABLE programa_academico (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  facultad_id INTEGER NOT NULL,

  -- Tipo de programa (para SUNEDU: Maestría / Doctorado / Pregrado)
  tipo TEXT NOT NULL,                -- "DOCTORADO" | "MAESTRIA" | "PREGRADO"

  nombre_corto TEXT NOT NULL,        -- Ej: "Doctorado en Ciencias de la Educación 15va Promoción"
  mencion TEXT,                      -- opcional
  promocion TEXT,                    -- opcional

  -- Modalidad oficial del programa
  modalidad TEXT,                    -- "PRESENCIAL" | "DISTANCIA" | "MIXTA" | etc.

  observaciones TEXT,                -- Notas sobre el programa (promoción, cambios, etc.)
  activo INTEGER NOT NULL DEFAULT 1,

  FOREIGN KEY (facultad_id) REFERENCES facultad(id)
);

-- ============================
-- TABLA: periodo (mes/año)
-- ============================
DROP TABLE IF EXISTS periodo;

CREATE TABLE periodo (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  anio INTEGER NOT NULL,
  mes INTEGER NOT NULL,              -- 1-12
  etiqueta TEXT NOT NULL,            -- "Noviembre 2025"

  -- periodo académico (para agrupar meses)
  -- Ej: '2025-III' para set/oct/nov/dic 2025
  periodo_academico TEXT,

  observaciones TEXT,                -- Notas sobre el período (ej. "mes de regularización", etc.)

  UNIQUE (anio, mes)
);

-- ============================
-- TABLA: docente
-- ============================
DROP TABLE IF EXISTS docente;

CREATE TABLE docente (
  id INTEGER PRIMARY KEY AUTOINCREMENT,

  -- Nombres normalizados (para el reporte SUNEDU)
  apellido_paterno TEXT,
  apellido_materno TEXT,
  nombres TEXT,

  -- Nombre completo para mostrar rápido en la app
  nombre_completo TEXT NOT NULL,

  -- Datos básicos
  especialidad TEXT,
  dni TEXT UNIQUE,                   -- N° DE DNI / CARNET DE EXTRANJERÍA
  pais_nacionalidad TEXT,            -- PAÍS (NACIONALIDAD)
  direccion TEXT,
  correo TEXT,
  telefono TEXT,

  -- Situación en la universidad
  fecha_ingreso_universidad TEXT,   -- YYYY-MM-DD

  -- ¿ERA DOCENTE UNIVERSITARIO A LA ENTRADA EN VIGENCIA DE LA LEY 30220?
  era_docente_antes_ley_30220 INTEGER NOT NULL DEFAULT 0,

  -- Categoría y régimen (SUNEDU)
  categoria_docente TEXT,
  regimen_dedicacion TEXT,

  -- Condición como docente investigador
  es_docente_investigador INTEGER NOT NULL DEFAULT 0,
  registrado_en_dina INTEGER NOT NULL DEFAULT 0,

  -- Niveles en los que el docente PUEDE dictar
  puede_pregrado INTEGER NOT NULL DEFAULT 0,
  puede_maestria INTEGER NOT NULL DEFAULT 0,
  puede_doctorado INTEGER NOT NULL DEFAULT 0,

  -- Grados / títulos principales (para ficha rápida)
  titulo_profesional TEXT,
  titulo_fecha TEXT,
  titulo_universidad TEXT,

  grado_magister TEXT,
  magister_fecha TEXT,
  magister_universidad TEXT,

  grado_doctor TEXT,
  doctor_fecha TEXT,
  doctor_universidad TEXT,

  -- Universidad de procedencia principal
  universidad_procedencia TEXT,

  -- Para SUNEDU: mayor grado y mención
  mayor_grado_academico TEXT,
  mayor_grado_mencion TEXT,

  antecedentes TEXT,                -- Info más formal (antecedentes)
  observaciones TEXT,               -- Comentarios internos y operativos
  tipo_docente TEXT,                -- "LOCAL", "ORDINARIZADO", etc.

  tiene_cv INTEGER NOT NULL DEFAULT 0,
  link_cv TEXT,
  fecha_recepcion_cv TEXT,

  activo INTEGER NOT NULL DEFAULT 1,

  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now'))
);

-- ============================
-- TABLA: docente_grado_academico
-- ============================
DROP TABLE IF EXISTS docente_grado_academico;

CREATE TABLE docente_grado_academico (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  docente_id INTEGER NOT NULL,
  tipo TEXT NOT NULL,               -- "TITULO_PROFESIONAL" | "MAGISTER" | "DOCTORADO" | ...

  denominacion TEXT NOT NULL,       -- Ej: "Maestría en Ciencias..."
  universidad TEXT NOT NULL,
  fecha_expedicion TEXT,
  es_mayor_grado INTEGER NOT NULL DEFAULT 0,
  observaciones TEXT,               -- Comentarios sobre el grado

  FOREIGN KEY (docente_id) REFERENCES docente(id)
);

-- =========================================
-- TABLA: programa_periodo
-- =========================================
DROP TABLE IF EXISTS programa_periodo;

CREATE TABLE programa_periodo (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  programa_id INTEGER NOT NULL,
  periodo_id INTEGER NOT NULL,

  matriculados INTEGER NOT NULL,
  observaciones TEXT,

  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now')),

  UNIQUE (programa_id, periodo_id),
  FOREIGN KEY (programa_id) REFERENCES programa_academico(id),
  FOREIGN KEY (periodo_id) REFERENCES periodo(id)
);

-- ============================
-- TABLA: curso_programado
-- ============================
DROP TABLE IF EXISTS curso_programado;

CREATE TABLE curso_programado (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  periodo_id INTEGER NOT NULL,
  programa_id INTEGER NOT NULL,
  docente_id INTEGER,

  ciclo TEXT,
  asignatura TEXT NOT NULL,

  fechas_texto TEXT NOT NULL,
  fecha_inicio TEXT,
  fecha_fin TEXT,

  modalidad_dictado TEXT NOT NULL DEFAULT 'PRESENCIAL',

  horas_texto TEXT,

  remuneracion_monto REAL,
  remuneracion_texto TEXT,
  poi TEXT,
  dni_docente TEXT,

  tipo_docente_mes TEXT,
  estado_programacion TEXT DEFAULT 'PROPUESTO',

  observaciones TEXT,               -- Ya la tenías

  codigo TEXT,
  categoria TEXT,
  sem1 TEXT,
  sem2 TEXT,

  -- 🔹 NUEVO: soporte para cursos fusionados
  fusion_grupo TEXT,                -- Identificador común para los cursos fusionados
  fusion_principal INTEGER NOT NULL DEFAULT 1, -- 1 si este curso es el "base" para cartas/reportes

  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now')),

  FOREIGN KEY (periodo_id) REFERENCES periodo(id),
  FOREIGN KEY (programa_id) REFERENCES programa_academico(id),
  FOREIGN KEY (docente_id) REFERENCES docente(id)
);

-- ============================
-- TABLA: docente_propuesto
-- ============================
DROP TABLE IF EXISTS docente_propuesto;

CREATE TABLE docente_propuesto (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  docente_id INTEGER NOT NULL,
  periodo_id INTEGER NOT NULL,
  estado TEXT NOT NULL DEFAULT 'PROPUESTO',
  observaciones TEXT,               -- antes 'notas', ahora homogeneizado

  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now')),

  UNIQUE (docente_id, periodo_id),
  FOREIGN KEY (docente_id) REFERENCES docente(id),
  FOREIGN KEY (periodo_id) REFERENCES periodo(id)
);

-- ============================
-- TABLA: docente_carga_academica
-- ============================
DROP TABLE IF EXISTS docente_carga_academica;

CREATE TABLE docente_carga_academica (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  docente_id INTEGER NOT NULL,

  -- PERIODO ACADÉMICO (SUNEDU) – texto, pero ahora consistente con periodo.periodo_academico
  periodo_academico TEXT NOT NULL,   -- Ej: '2025-III'

  nivel_pregrado INTEGER NOT NULL DEFAULT 0,
  nivel_maestria INTEGER NOT NULL DEFAULT 0,
  nivel_doctorado INTEGER NOT NULL DEFAULT 0,

  horas_clase INTEGER NOT NULL DEFAULT 0,
  horas_otras_actividades INTEGER NOT NULL DEFAULT 0,
  horas_total INTEGER NOT NULL DEFAULT 0,

  observaciones TEXT,
  filial TEXT,

  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now')),

  UNIQUE (docente_id, periodo_academico),
  FOREIGN KEY (docente_id) REFERENCES docente(id)
);

-- ============================
-- TABLA: docente_sugerido_curso
-- ============================
DROP TABLE IF EXISTS docente_sugerido_curso;

CREATE TABLE docente_sugerido_curso (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  docente_id INTEGER NOT NULL,
  curso_id INTEGER NOT NULL,   -- referencia a curso_programado.id

  -- Estado de la sugerencia:
  --  SUGERIDO: sugerencia activa
  --  DESCARTADO: se evaluó pero se descartó
  --  ASIGNADO: terminó siendo el docente del curso
  estado TEXT NOT NULL DEFAULT 'SUGERIDO',

  motivo TEXT,                 -- Ej: "Especialista en metodología", "Experiencia previa en el programa", etc.
  origen TEXT,                 -- Ej: "COORDINACIÓN", "DIRECCIÓN", "SISTEMA"

  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now')),

  UNIQUE (docente_id, curso_id),
  FOREIGN KEY (docente_id) REFERENCES docente(id),
  FOREIGN KEY (curso_id) REFERENCES curso_programado(id)
);

-- =====================================================
-- NUEVO: CONFIGURACIÓN DE SÍLABOS POR PROGRAMA
-- =====================================================
DROP TABLE IF EXISTS silabo_programa_config;

CREATE TABLE silabo_programa_config (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  programa_id INTEGER NOT NULL UNIQUE,   -- FK a programa_academico.id

  -- Nombre del programa para mostrar en el sílabo (encabezado)
  nombre_programa TEXT NOT NULL,         -- Ej: "DOCTORADO EN ADMINISTRACIÓN"

  -- Plantilla específica de Word para este programa
  plantilla_archivo TEXT,                -- Ej: "doctorado_administracion_silabo.docx"

  -- Datos generales típicos del programa
  numero_creditos INTEGER NOT NULL DEFAULT 4,
  horas_teoricas INTEGER NOT NULL DEFAULT 40,
  horas_practicas INTEGER NOT NULL DEFAULT 48,

  -- Modalidad predominante (puede sobreescribirse por curso)
  modalidad_default TEXT,                -- "PRESENCIAL" | "A DISTANCIA" | "MIXTA"

  -- Horario tipo (si aplica)
  horario_texto TEXT,                    -- Ej: "vie. 17:00 a 22:00; sáb. 8:00 a 13:00..."

  -- Fechas del semestre (texto libre)
  inicio_semestre TEXT,                  -- Ej: "1 de agosto de 2025"
  fin_semestre TEXT,                     -- Ej: "31 de diciembre de 2025"

  -- Sección 3: perfil del egresado
  perfil_egresado TEXT NOT NULL,         -- Texto largo

  -- Tabla 1: competencias y resultados de aprendizaje (puede ir como bloque de texto)
  resultados_aprendizaje TEXT,

  observaciones TEXT,

  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now')),

  FOREIGN KEY (programa_id) REFERENCES programa_academico(id)
);

-- =====================================================
-- NUEVO: SUMILLAS BASE POR CURSO (POR PROGRAMA)
-- =====================================================
DROP TABLE IF EXISTS silabo_curso_base;

CREATE TABLE silabo_curso_base (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  programa_id INTEGER NOT NULL,         -- FK a programa_academico.id
  codigo TEXT NOT NULL,                 -- Ej: "DM02"
  asignatura TEXT NOT NULL,             -- Ej: "ANALISIS DE INVERSIONES"

  sumilla TEXT NOT NULL,                -- Texto de la sumilla del curso

  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now')),

  UNIQUE (programa_id, codigo),
  FOREIGN KEY (programa_id) REFERENCES programa_academico(id)
);
