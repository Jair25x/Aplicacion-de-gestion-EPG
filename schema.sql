-- ============================
-- TABLA: facultad
-- ============================
DROP TABLE IF EXISTS facultad;

CREATE TABLE facultad (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nombre TEXT NOT NULL,      -- Ej: "Facultad de Ciencias y Humanidades"
  codigo TEXT,               -- Opcional
  activo INTEGER NOT NULL DEFAULT 1
);

-- ============================
-- TABLA: programa_academico
-- ============================
DROP TABLE IF EXISTS programa_academico;

CREATE TABLE programa_academico (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  facultad_id INTEGER NOT NULL,
  tipo TEXT NOT NULL,                -- "DOCTORADO" | "MAESTRIA"
  nombre_corto TEXT NOT NULL,        -- Ej: "Doctorado en Ciencias de la Educación 15va Promoción"
  mencion TEXT,                      -- opcional
  promocion TEXT,                    -- opcional
  modalidad TEXT,                    -- "PRESENCIAL" | "DISTANCIA" | "MIXTA" | etc.
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
  UNIQUE (anio, mes)
);

-- ============================
-- TABLA: docente (maestro de docentes)
-- ============================
DROP TABLE IF EXISTS docente;

CREATE TABLE docente (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nombre_completo TEXT NOT NULL,
  nombres TEXT,
  apellidos TEXT,
  especialidad TEXT,
  dni TEXT UNIQUE,
  direccion TEXT,
  correo TEXT,
  telefono TEXT,

  -- grados/títulos
  titulo_profesional TEXT,
  titulo_fecha TEXT,
  titulo_universidad TEXT,

  grado_magister TEXT,
  magister_fecha TEXT,
  magister_universidad TEXT,

  grado_doctor TEXT,
  doctor_fecha TEXT,
  doctor_universidad TEXT,

  -- NUEVO: universidad de procedencia (atributo propio del docente)
  universidad_procedencia TEXT,

  antecedentes TEXT,
  tipo_docente TEXT,                 -- LOCAL | ORDINARIZADO | EXTERNO | etc.

  tiene_cv INTEGER NOT NULL DEFAULT 0,
  link_cv TEXT,
  fecha_recepcion_cv TEXT,

  activo INTEGER NOT NULL DEFAULT 1,

  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now'))
);

-- =========================================
-- TABLA: programa_periodo (matriculados por programa y período)
-- =========================================
DROP TABLE IF EXISTS programa_periodo;

CREATE TABLE programa_periodo (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  programa_id INTEGER NOT NULL,
  periodo_id INTEGER NOT NULL,

  -- Constantes del período académico para ese programa
  matriculados INTEGER NOT NULL,     -- Número de matriculados del programa en ese período
  observaciones TEXT,

  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now')),

  UNIQUE (programa_id, periodo_id),
  FOREIGN KEY (programa_id) REFERENCES programa_academico(id),
  FOREIGN KEY (periodo_id) REFERENCES periodo(id)
);

-- ============================
-- TABLA: curso_programado (programación mensual)
-- ============================
DROP TABLE IF EXISTS curso_programado;

CREATE TABLE curso_programado (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  periodo_id INTEGER NOT NULL,
  programa_id INTEGER NOT NULL,
  docente_id INTEGER,                -- curso sin docente asignado permitido

  ciclo TEXT,
  asignatura TEXT NOT NULL,

  fechas_texto TEXT NOT NULL,        -- "07, 08, 09, 21, 22 Y 23 de noviembre 2025"
  fecha_inicio TEXT,                 -- opcional "2025-11-07"
  fecha_fin TEXT,                    -- opcional "2025-11-23"

  -- Horas propias del curso (se mantiene acá)
  horas_texto TEXT,                  -- Ej: "19 horas"

  remuneracion_monto REAL,
  remuneracion_texto TEXT,           -- "S/. 5,900.00"
  poi TEXT,
  dni_docente TEXT,                  -- copia del dni del docente para reportería rápida

  tipo_docente_mes TEXT,             -- LOCAL | ORDINARIZADO | etc.
  estado_programacion TEXT DEFAULT 'PROPUESTO',
  -- PROPUESTO | CONFIRMADO | ENVIADO_RRHH | OBSERVADO | ANULADO

  observaciones TEXT,

  -- Datos para carta de invitación / oficios
  codigo TEXT,                       -- DU36, DK05, MS04, etc.
  categoria TEXT,                    -- FMA, FDO, INV, etc.
  sem1 TEXT,                         -- "07, 08, 09"
  sem2 TEXT,                         -- "21, 22, 23"

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
  estado TEXT NOT NULL DEFAULT 'PROPUESTO',   -- PROPUESTO | APROBADO | DESCARTADO
  notas TEXT,

  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now')),

  UNIQUE (docente_id, periodo_id),
  FOREIGN KEY (docente_id) REFERENCES docente(id),
  FOREIGN KEY (periodo_id) REFERENCES periodo(id)
);

-- ============================
-- TABLA: docente_carga_academica (por periodo académico)
-- ============================
DROP TABLE IF EXISTS docente_carga_academica;

CREATE TABLE docente_carga_academica (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  docente_id INTEGER NOT NULL,
  periodo_academico TEXT NOT NULL,   -- Ej: '2025-III'

  horas_clase INTEGER NOT NULL DEFAULT 0,
  horas_otras_actividades INTEGER NOT NULL DEFAULT 0,
  horas_total INTEGER NOT NULL DEFAULT 0,

  observaciones TEXT,
  filial TEXT,                       -- Si quieres sobreescribir la filial del docente

  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now')),

  UNIQUE (docente_id, periodo_academico),
  FOREIGN KEY (docente_id) REFERENCES docente(id)
);
