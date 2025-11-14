# add_cursos_diciembre_2025.py

import os
import re
import sqlite3
from pathlib import Path
from dotenv import load_dotenv

# ============================
# Configuración de rutas / .env
# ============================
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

DB_PATH = os.getenv("DOCENTES_DB_PATH", str(BASE_DIR / "docentes.db"))


def parse_monto(monto_str: str | None) -> float | None:
    """
    Convierte 'S/. 5,900.00' -> 5900.00
    Devuelve None si viene vacío o '-'.
    """
    if not monto_str:
        return None
    s = monto_str.strip()
    if s in ("-", "--", ""):
        return None

    # Quitar prefijos de moneda y espacios
    for pref in ["S/.", "S/", "s/.", "s/"]:
        s = s.replace(pref, "")
    s = s.replace(" ", "")

    # Quitar separador de miles y dejar solo punto decimal
    s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def split_sem1_sem2(fechas_texto: str | None) -> tuple[str | None, str | None]:
    """
    A partir de un texto como:
      '05, 06, 07, 19, 20 y 21 de diciembre 2025'
    devuelve:
      sem1 = '05, 06 y 07 de diciembre 2025'
      sem2 = '19, 20 y 21 de diciembre 2025'
    Si no se puede partir, devuelve (None, None).
    """
    if not fechas_texto:
        return None, None

    # Extraer todos los días como números
    dias = re.findall(r"\d{1,2}", fechas_texto)
    if len(dias) < 4:
        # Si no hay al menos 4 días, no intentamos dividir
        return None, None

    # Partimos en dos mitades (normalmente 3 y 3)
    mid = len(dias) // 2
    dias_sem1 = dias[:mid]
    dias_sem2 = dias[mid:]

    # Intentar conservar el sufijo 'de diciembre 2025' o similar
    sufijo = ""
    pos = fechas_texto.find("de ")
    if pos != -1:
        sufijo = fechas_texto[pos:]  # ej. 'de diciembre 2025'

    def formatear_bloque(dias_bloque: list[str]) -> str | None:
        if not dias_bloque:
            return None
        if len(dias_bloque) == 1:
            cuerpo = dias_bloque[0]
        elif len(dias_bloque) == 2:
            cuerpo = f"{dias_bloque[0]} y {dias_bloque[1]}"
        else:
            cuerpo = ", ".join(dias_bloque[:-1]) + f" y {dias_bloque[-1]}"
        return f"{cuerpo} {sufijo}".strip()

    sem1 = formatear_bloque(dias_sem1)
    sem2 = formatear_bloque(dias_sem2)
    return sem1, sem2


# 2) Mapeo de nombres de programa (lo que escribes en el contrato) -> nombre_corto real en BD
PROGRAMA_NAME_CANON = {
    # Diferencias de texto respecto a init_db.py
    "Doctorado en Ciencias de la Educación 15va Promoción Presencial":
        "Doctorado en Ciencias de la Educación 15va Promoción",
    "Doctorado en Ciencias de la Educación 2da Promoción a Distancia":
        "Doctorado en Ciencias de la Educación 2da Promoción a Distancia/Presencial",
    "Doctorado en Medio Ambiente y Desarrollo Sostenible 2da Promoción a Distancia":
        "Doctorado en Medio Ambiente y Desarrollo Sostenible 2da Promoción Presencial",
    "Doctorado en Medio Ambiente y Desarrollo Sostenible 12va Promoción":
        "Doctorado en Medio Ambiente y Desarrollo Sostenible 12va Promoción Presencial",
    "Doctorado en Administración 2da Promoción a Distancia":
        "Doctorado en Administración 2da Promoción a Distancia/presencial",
    "Doctorado en Administración 4ta Promoción Presencial":
        "Doctorado en Administración 4ta Promoción presencial",
    # El resto de programas usan el mismo nombre que en el contrato
}

# 3) Programas nuevos que podrían no existir aún en programa_academico
NEW_PROGRAM_INFO = {
    "Doctorado en Ciencias de la Educación 3ra Promoción a Distancia": {
        "facultad": "Facultad de Ciencias y Humanidades",
        "tipo": "DOCTORADO",
        "promocion": "3ra Promoción",
        "modalidad": "DISTANCIA",
        "universidad": "UNIVERSIDAD CÉSAR VALLEJO",
    },
    "Doctorado en Psicología 3ra Promoción a Distancia": {
        "facultad": "Facultad de Ciencias de la Salud",
        "tipo": "DOCTORADO",
        "promocion": "3ra Promoción",
        "modalidad": "DISTANCIA",
        "universidad": "UNIVERSIDAD PRIVADA CÉSAR VALLEJO",
    },
    "Maestría en Ingeniería Civil mención en Hidráulica y Ambiental 2da Promoción a Distancia": {
        "facultad": "Facultad de Ingenierías y Arquitectura",
        "tipo": "MAESTRIA",
        "promocion": "2da Promoción",
        "modalidad": "DISTANCIA",
        "universidad": "UNIVERSIDAD MAYOR DE SAN SIMÓN",
    },
}


def get_programa_id(conn: sqlite3.Connection, cursor: sqlite3.Cursor, programa_label: str) -> int:
    """
    Dado el texto de PROGRAMA que usas en tu lista,
    devuelve el id de programa_academico.
    Crea el programa si está en NEW_PROGRAM_INFO y aún no existe.
    """
    db_name = PROGRAMA_NAME_CANON.get(programa_label, programa_label)

    # Intentar encontrar el programa
    cursor.execute(
        "SELECT id FROM programa_academico WHERE nombre_corto = ?",
        (db_name,),
    )
    row = cursor.fetchone()
    if row:
        return row[0]

    # Si no existe, ver si está definido como nuevo
    info = NEW_PROGRAM_INFO.get(db_name)
    if not info:
        raise RuntimeError(
            f"❌ No se encontró el programa '{db_name}' en la BD "
            f"y tampoco está definido en NEW_PROGRAM_INFO."
        )

    # Buscar facultad
    cursor.execute(
        "SELECT id FROM facultad WHERE nombre = ?",
        (info["facultad"],),
    )
    fac = cursor.fetchone()
    if not fac:
        raise RuntimeError(
            f"❌ No se encontró la facultad '{info['facultad']}' en la tabla facultad."
        )

    facultad_id = fac[0]
    cursor.execute(
        """
        INSERT INTO programa_academico
            (facultad_id, tipo, nombre_corto, mencion, promocion,
             modalidad, universidad_procedencia, activo)
        VALUES (?, ?, ?, NULL, ?, ?, ?, 1);
        """,
        (
            facultad_id,
            info["tipo"],
            db_name,
            info.get("promocion"),
            info.get("modalidad"),
            info.get("universidad"),
        ),
    )
    conn.commit()
    new_id = cursor.lastrowid
    print(f"✅ Programa creado: {db_name} (id={new_id})")
    return new_id


# 4) Definición de cursos de Diciembre 2025 (sin docente asignado)
cursos_diciembre = [
    # ============================
    # Facultad de Ciencias y Humanidades
    # Doctorado en Ciencias de la Educación
    # ============================
    {
        "nro": 1,
        "programa": "Doctorado en Ciencias de la Educación 15va Promoción Presencial",
        "ciclo": "VI",
        "asignatura": "DEFENSA NACIONAL Y SEGURIDAD",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 5,900.00",
        "poi": "257423",
        "observaciones": None,
    },
    {
        "nro": 2,
        "programa": "Doctorado en Ciencias de la Educación 2da Promoción a Distancia",
        "ciclo": "IV",
        "asignatura": "TECNOLOGÍAS DE INFORMACIÓN Y COMUNICACIÓN",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 5,900.00",
        "poi": "257429",
        "observaciones": None,
    },
    {
        "nro": 3,
        "programa": "Doctorado en Ciencias de la Educación 3ra Promoción a Distancia",
        "ciclo": "III",
        "asignatura": "SISTEMAS DE EVALUACIÓN DEL APRENDIZAJE",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 5,900.00",
        "poi": "257430",
        "observaciones": None,
    },
    {
        "nro": 4,
        "programa": "Doctorado en Ciencias de la Educación 4ta Promoción a Distancia",
        "ciclo": "II",
        "asignatura": "RESPONSABILIDAD ETICO SOCIAL",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "remuneracion_texto": "S/. 5,900.00",
        "poi": "257431",
        "observaciones": None,
    },
    {
        "nro": 5,
        "programa": "Doctorado en Ciencias de la Educación 5ta Promoción a Distancia",
        "ciclo": "I",
        "asignatura": "ÉTICA EN LA EDUCACIÓN",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 5,900.00",
        "poi": "257432",
        "observaciones": "Dra. Liliam Lucy Campos Cornejo – 980580459 – Confirmó el 21/10 en reunión.",
    },

    # Maestría en Docencia Universitaria
    {
        "nro": 6,
        "programa": "Maestría en Docencia Universitaria 4ta Promoción a Distancia",
        "ciclo": "IV",
        "asignatura": "TESIS III",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "remuneracion_texto": "S/. 4,140.00",
        "poi": "257403",
        "observaciones": None,
    },
    {
        "nro": 7,
        "programa": "Maestría en Docencia Universitaria 5ta Promoción a Distancia",
        "ciclo": "III",
        "asignatura": "TESIS II",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 4,140.00",
        "poi": "257404",
        "observaciones": None,
    },
    {
        "nro": 8,
        "programa": "Maestría en Docencia Universitaria 6ta Promoción a Distancia",
        "ciclo": "II",
        "asignatura": "TESIS I",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 4,140.00",
        "poi": "257405",
        "observaciones": None,
    },
    {
        "nro": 9,
        "programa": "Maestría en Docencia Universitaria 7ma Promoción a Distancia",
        "ciclo": "I",
        "asignatura": "PLANIFICACIÓN Y GESTIÓN DE LA CALIDAD DE LA EDUCACIÓN",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "remuneracion_texto": "S/. 4,140.00",
        "poi": "257406",
        "observaciones": None,
    },

    # ============================
    # Facultad de Ciencias de la Salud
    # Doctorado en Psicología
    # ============================
    {
        "nro": 10,
        "programa": "Doctorado en Psicología 1ra Promoción a Distancia",
        "ciclo": "VI",
        "asignatura": "SEMINARIO DE TESIS V",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 5,900.00",
        "poi": "257446",
        "observaciones": None,
    },
    {
        "nro": 11,
        "programa": "Doctorado en Psicología 3ra Promoción a Distancia",
        "ciclo": "II",
        "asignatura": "SEMINARIO DE TESIS I",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "remuneracion_texto": None,  # no se consigna
        "poi": None,
        "observaciones": "Llevará con el Doctorado en Ciencias de la Salud 4ta Promoción a Distancia.",
    },

    # Doctorado en Ciencias de la Salud
    {
        "nro": 12,
        "programa": "Doctorado en Ciencias de la Salud 2da Promoción a Distancia",
        "ciclo": "VI",
        "asignatura": "SEMINARIO TEMÁTICO",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "remuneracion_texto": "S/. 5,900.00",
        "poi": "257443",
        "observaciones": None,
    },
    {
        "nro": 13,
        "programa": "Doctorado en Ciencias de la Salud 3ra Promoción a Distancia",
        "ciclo": "III",
        "asignatura": "SEMINARIO DE TESIS II",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "remuneracion_texto": "S/. 5,900.00",
        "poi": "257444",
        "observaciones": None,
    },
    {
        "nro": 14,
        "programa": "Doctorado en Ciencias de la Salud 4ta Promoción a Distancia",
        "ciclo": "II",
        "asignatura": "SEMINARIO DE TESIS I",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "remuneracion_texto": "S/. 5,900.00",
        "poi": "257445",
        "observaciones": "Llevará con el Doctorado en Psicología 3ra Promoción a Distancia.",
    },

    # ============================
    # Facultad de Ingenierías y Arquitectura
    # Doctorado en Medio Ambiente y Desarrollo Sostenible
    # ============================
    {
        "nro": 15,
        "programa": "Doctorado en Medio Ambiente y Desarrollo Sostenible 2da Promoción a Distancia",
        "ciclo": "VI",
        "asignatura": "ELABORACIÓN Y PUBLICACIÓN DE ARTÍCULOS CIENTÍFICOS",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "remuneracion_texto": "S/. 5,900.00",
        "poi": "257438",
        "observaciones": None,
    },
    {
        "nro": 16,
        "programa": "Doctorado en Medio Ambiente y Desarrollo Sostenible 3ra Promoción a Distancia",
        "ciclo": "V",
        "asignatura": "SEMINARIO DE TESIS IV",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "remuneracion_texto": "S/. 5,900.00",
        "poi": "257439",
        "observaciones": None,
    },
    {
        "nro": 17,
        "programa": "Doctorado en Medio Ambiente y Desarrollo Sostenible 4ta Promoción a Distancia",
        "ciclo": "III",
        "asignatura": "SISTEMAS DE INFORMACIÓN AMBIENTAL",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "remuneracion_texto": "S/. 5,900.00",
        "poi": "257440",
        "observaciones": None,
    },
    {
        "nro": 18,
        "programa": "Doctorado en Medio Ambiente y Desarrollo Sostenible 5ta Promoción a Distancia",
        "ciclo": "II",
        "asignatura": "BIOÉTICA",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 5,900.00",
        "poi": "257441",
        "observaciones": None,
    },
    {
        "nro": 19,
        "programa": "Doctorado en Medio Ambiente y Desarrollo Sostenible 12va Promoción",
        "ciclo": "II",
        "asignatura": "LEGISLACIÓN AMBIENTAL",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 5,900.00",
        "poi": "257424",
        "observaciones": None,
    },
    {
        "nro": 20,
        "programa": "Doctorado en Medio Ambiente y Desarrollo Sostenible 6ta Promoción a Distancia",
        "ciclo": "I",
        "asignatura": "METODOLOGÍA DE LA INVESTIGACIÓN CIENTÍFICA",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "remuneracion_texto": "S/. 5,900.00",
        "poi": "257442",
        "observaciones": None,
    },

    # Maestría en Ingeniería Civil
    {
        "nro": 21,
        "programa": "Maestría en Ingeniería Civil mención en Estructuras 4ta Promoción a Distancia",
        "ciclo": "IV",
        "asignatura": "TEMAS AVANZADOS DE INGENIERIA ESTRUCTURAL EN LA HIDRAULICA",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 4,140.00",
        "poi": "257416",
        "observaciones": "Núñez del Prado dictó en julio. Solicitud a la Mg. Ana Cecilia.",
    },
    {
        "nro": 22,
        "programa": "Maestría en Ingeniería Civil mención en Hidráulica y Ambiental 2da Promoción a Distancia",
        "ciclo": "IV",
        "asignatura": "TEMAS ESPECIALES",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "remuneracion_texto": "S/. 4,140.00",
        "poi": "257420",
        "observaciones": "Consignar bien el nombre del curso, buscar en el ERP.",
    },
    {
        "nro": 23,
        "programa": "Maestría en Ingeniería Civil mención en Estructuras 5ta Promoción a Distancia",
        "ciclo": "III",
        "asignatura": "TESIS II",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "remuneracion_texto": "S/. 4,140.00",
        "poi": "257417",
        "observaciones": None,
    },
    {
        "nro": 24,
        "programa": "Maestría en Ingeniería Civil mención en Transportes 2da Promoción Presencial",
        "ciclo": "III",
        "asignatura": "TESIS I",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "remuneracion_texto": "S/. 4,140.00",
        "poi": "257396",
        "observaciones": None,
    },
    {
        "nro": 25,
        "programa": "Maestría en Ingeniería Civil mención en Estructuras 6ta Promoción a Distancia",
        "ciclo": "II",
        "asignatura": "TESIS I",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "remuneracion_texto": "S/. 4,140.00",
        "poi": "257418",
        "observaciones": None,
    },
    {
        "nro": 26,
        "programa": "Maestría en Ingeniería Civil mención en Hidráulica y Ambiental 4ta Promoción a Distancia",
        "ciclo": "II",
        "asignatura": "TRATAMIENTO DE AGUAS SERVIDAS E INDUSTRIALES",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "remuneracion_texto": "S/. 4,140.00",
        "poi": "257421",
        "observaciones": None,
    },
    {
        "nro": 27,
        "programa": "Maestría en Ingeniería Civil mención en Estructuras 7ma Promoción a Distancia",
        "ciclo": "I",
        "asignatura": "COMPORTAMIENTO Y DISEÑO DEL CONCRETO",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "remuneracion_texto": "S/. 4,140.00",
        "poi": "257419",
        "observaciones": None,
    },

    # ============================
    # Facultad de Ciencias Económicas y Contables
    # Doctorado en Administración
    # ============================
    {
        "nro": 28,
        "programa": "Doctorado en Administración 2da Promoción a Distancia",
        "ciclo": "V",
        "asignatura": "GESTIÓN DE RIESGOS Y TOMA DE DECISIONES EN INCERTIDUMBRE",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 5,900.00",
        "poi": "257425",
        "observaciones": None,
    },
    {
        "nro": 29,
        "programa": "Doctorado en Administración 3ra Promoción a Distancia",
        "ciclo": "IV",
        "asignatura": "MACROECONOMÍA Y POLÍTICAS ECONÓMICAS",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "remuneracion_texto": "S/. 5,900.00",
        "poi": "257426",
        "observaciones": None,
    },
    {
        "nro": 30,
        "programa": "Doctorado en Administración 4ta Promoción Presencial",
        "ciclo": "II",
        "asignatura": "SEMINARIO DE TESIS I",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 5,900.00",
        "poi": "257422",
        "observaciones": None,
    },
    {
        "nro": 31,
        "programa": "Doctorado en Administración 4ta Promoción a Distancia",
        "ciclo": "II",
        "asignatura": "RESPONSABILIDAD SOCIAL EMPRESARIAL",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 5,900.00",
        "poi": "257427",
        "observaciones": None,
    },

    # Doctorado en Contabilidad
    {
        "nro": 32,
        "programa": "Doctorado en Contabilidad 2da Promoción a Distancia",
        "ciclo": "III",
        "asignatura": "POLÍTICA ECONÓMICA Y GLOBALIZACIÓN",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 5,900.00",
        "poi": "257428",
        "observaciones": None,
    },

    # Maestría en Administración de Negocios
    {
        "nro": 33,
        "programa": "Maestría en Administración de Negocios 2da Promoción a Distancia",
        "ciclo": "IV",
        "asignatura": "TESIS II",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 4,140.00",
        "poi": "257397",
        "observaciones": None,
    },
    {
        "nro": 34,
        "programa": "Maestría en Administración de Negocios 3ra Promoción a Distancia",
        "ciclo": "III",
        "asignatura": "TESIS I",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 4,140.00",
        "poi": "257398",
        "observaciones": "Llevará con Maestría en Contabilidad mención en Auditoría y Control Interno 4ta Promoción a Distancia.",
    },
    {
        "nro": 35,
        "programa": "Maestría en Administración de Negocios 4ta Promoción a Distancia",
        "ciclo": "II",
        "asignatura": "METODOLOGIA CIENTIFICA DE LA INVESTIGACION",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 4,140.00",
        "poi": "257399",
        "observaciones": None,
    },

    # Maestría en Contabilidad mención en Auditoría y Control Interno
    {
        "nro": 36,
        "programa": "Maestría en Contabilidad mención en Auditoría y Control Interno 3ra Promoción a Distancia",
        "ciclo": "IV",
        "asignatura": "TESIS II",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 4,140.00",
        "poi": "257400",
        "observaciones": None,
    },
    {
        "nro": 37,
        "programa": "Maestría en Contabilidad mención en Auditoría y Control Interno 5ta Promoción a Distancia",
        "ciclo": "II",
        "asignatura": "AUDITORIA FINANCIERA I",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "remuneracion_texto": "S/. 4,140.00",
        "poi": "257402",
        "observaciones": "Docente que se propone. Revisar si tenemos CV de Miriam Cledy Zarate Muñiz.",
    },
    {
        "nro": 38,
        "programa": "Maestría en Contabilidad mención en Auditoría y Control Interno 4ta Promoción a Distancia",
        "ciclo": "III",
        "asignatura": "TESIS I",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": None,  # viene '-'
        "poi": None,
        "observaciones": "Llevarán con Maestría en Administración 3ra Promoción.",
    },

    # ============================
    # Facultad de Derecho y Ciencia Política
    # Doctorado en Derecho
    # ============================
    {
        "nro": 39,
        "programa": "Doctorado en Derecho 2da Promoción a Distancia",
        "ciclo": "V",
        "asignatura": "SEMINARIO DE TESIS IV",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 5,900.00",
        "poi": "257433",
        "observaciones": None,
    },
    {
        "nro": 40,
        "programa": "Doctorado en Derecho 3ra Promoción a Distancia",
        "ciclo": "IV",
        "asignatura": "SEMINARIO DE TESIS III",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 5,900.00",
        "poi": "257434",
        "observaciones": None,
    },
    {
        "nro": 41,
        "programa": "Doctorado en Derecho 4ta Promoción a Distancia",
        "ciclo": "III",
        "asignatura": "MEDIOS ALTERNATIVOS PARA LA RESOLUCION DE CONFLICTOS",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 5,900.00",
        "poi": "257435",
        "observaciones": None,
    },
    {
        "nro": 42,
        "programa": "Doctorado en Derecho 5ta Promoción a Distancia",
        "ciclo": "II",
        "asignatura": "SEMINARIO: TEORIAS AVANZADAS DEL DERECHO PENAL EN EL SIGLO XXI",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "remuneracion_texto": "S/. 5,900.00",
        "poi": "257436",
        "observaciones": None,
    },
    {
        "nro": 43,
        "programa": "Doctorado en Derecho 6ta Promoción a Distancia",
        "ciclo": "I",
        "asignatura": "CIENCIA POLITICA Y GOBERNABILIDAD",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 5,900.00",
        "poi": "257437",
        "observaciones": None,
    },

    # Maestría en Derecho
    {
        "nro": 44,
        "programa": "Maestría en Derecho Civil y Comercial 2da Promoción a Distancia",
        "ciclo": "IV",
        "asignatura": "TESIS III",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 4,140.00",
        "poi": "257413",
        "observaciones": None,
    },
    {
        "nro": 45,
        "programa": "Maestría en Derecho Registral y Notarial 2da Promoción a Distancia",
        "ciclo": "IV",
        "asignatura": "TESIS II",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 4,140.00",
        "poi": "257410",
        "observaciones": None,
    },
    {
        "nro": 46,
        "programa": "Maestría en Derecho Constitucional 3ra Promoción a Distancia",
        "ciclo": "IV",
        "asignatura": "TESIS III",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "remuneracion_texto": "S/. 4,140.00",
        "poi": "257407",
        "observaciones": None,
    },
    {
        "nro": 47,
        "programa": "Maestría en Derecho Civil y Comercial 3ra Promoción a Distancia",
        "ciclo": "III",
        "asignatura": "TESIS II",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 4,140.00",
        "poi": "257414",
        "observaciones": None,
    },
    {
        "nro": 48,
        "programa": "Maestría en Derecho Constitucional 4ta Promoción a Distancia",
        "ciclo": "III",
        "asignatura": "TEMAS ESPECIALES",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 4,140.00",
        "poi": "257408",
        "observaciones": None,
    },
    {
        "nro": 49,
        "programa": "Maestría en Derecho Registral y Notarial 3ra Promoción a Distancia",
        "ciclo": "III",
        "asignatura": "TESIS I",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "remuneracion_texto": "S/. 4,140.00",
        "poi": "257411",
        "observaciones": None,
    },
    {
        "nro": 50,
        "programa": "Maestría en Derecho Constitucional 5ta Promoción a Distancia",
        "ciclo": "II",
        "asignatura": "TESIS I",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 4,140.00",
        "poi": "257409",
        "observaciones": None,
    },
    {
        "nro": 51,
        "programa": "Maestría en Derecho Registral y Notarial 4ta Promoción a Distancia",
        "ciclo": "II",
        "asignatura": "DERECHO INMOBILIARIO I",
        "fechas": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "remuneracion_texto": "S/. 4,140.00",
        "poi": "257412",
        "observaciones": None,
    },
    {
        "nro": 52,
        "programa": "Maestría en Derecho Civil y Comercial 4ta Promoción a Distancia",
        "ciclo": "II",
        "asignatura": "TUTELA JURÍDICA DE LA POSESIÓN Y LA PROPIEDAD",
        "fechas": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "remuneracion_texto": "S/. 4,140.00",
        "poi": "257415",
        "observaciones": None,
    },
]


def main():
    print(f"Usando base de datos: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1) Obtener periodo Diciembre 2025
    cursor.execute(
        "SELECT id FROM periodo WHERE anio = ? AND mes = ?",
        (2025, 12),
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise RuntimeError(
            "❌ No se encontró el periodo 2025-12. "
            "Primero crea 'Diciembre 2025' en la tabla periodo."
        )

    periodo_dic_2025_id = row[0]
    print(f"Periodo Diciembre 2025 ID: {periodo_dic_2025_id}")

    # 5) Insertar cursos (sin docente_id) de forma idempotente
    insertados = 0
    saltados = 0

    for curso in cursos_diciembre:
        programa_label = curso["programa"]
        programa_id = get_programa_id(conn, cursor, programa_label)

        ciclo = curso["ciclo"]
        asignatura = curso["asignatura"]
        fechas_texto = curso["fechas"]
        remuneracion_texto = curso["remuneracion_texto"]
        remuneracion_monto = parse_monto(remuneracion_texto)
        poi = curso["poi"]
        observaciones = curso["observaciones"]

        sem1_texto, sem2_texto = split_sem1_sem2(fechas_texto)

        # Evitar duplicados: mismo periodo, programa, ciclo, asignatura y fechas
        cursor.execute(
            """
            SELECT id FROM curso_programado
            WHERE periodo_id = ?
              AND programa_id = ?
              AND ciclo = ?
              AND asignatura = ?
              AND fechas_texto = ?;
            """,
            (periodo_dic_2025_id, programa_id, ciclo, asignatura, fechas_texto),
        )
        ya_existe = cursor.fetchone()
        if ya_existe:
            saltados += 1
            print(
                f"⚠️  Ya existe curso (periodo={periodo_dic_2025_id}, programa='{programa_label}', "
                f"ciclo='{ciclo}', asignatura='{asignatura}'). Se omite."
            )
            continue

        cursor.execute(
            """
            INSERT INTO curso_programado
                (periodo_id, programa_id, docente_id,
                 ciclo, asignatura, fechas_texto,
                 remuneracion_monto, remuneracion_texto,
                 poi, dni_docente, tipo_docente_mes,
                 observaciones, sem1, sem2)
            VALUES (?, ?, NULL,
                    ?, ?, ?,
                    ?, ?,
                    ?, NULL, NULL,
                    ?, ?, ?);
            """,
            (
                periodo_dic_2025_id,
                programa_id,
                ciclo,
                asignatura,
                fechas_texto,
                remuneracion_monto,
                remuneracion_texto,
                poi,
                observaciones,
                sem1_texto,
                sem2_texto,
            ),
        )
        insertados += 1

    conn.commit()
    conn.close()

    print(f"✅ Cursos de Diciembre 2025 insertados: {insertados}")
    print(f"ℹ️ Cursos ya existentes (no se duplicaron): {saltados}")


if __name__ == "__main__":
    main()
