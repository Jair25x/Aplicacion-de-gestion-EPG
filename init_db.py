import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "docentes.db"
SCHEMA_PATH = BASE_DIR / "schema.sql"


def parse_nombre(nombre_completo: str):
    """
    Intenta separar nombres y apellidos de 'DR. NOMBRE APELLIDO APELLIDO'.
    No será perfecto, pero para esta app es suficiente.
    """
    titulo_prefixes = {
        "DR.", "DRA.", "DR", "DRA",
        "Mg.", "MG.", "MG", "MGT.", "MGT",
        "MTRA.", "MTRA",
        "Lic.", "LIC."
    }

    parts = nombre_completo.split()
    if not parts:
        return nombre_completo, None, None

    # Si el primer token es un título, lo quitamos
    if parts[0].upper() in titulo_prefixes:
        parts = parts[1:]

    if len(parts) == 0:
        return nombre_completo, None, None
    elif len(parts) == 1:
        return nombre_completo, parts[0], None
    elif len(parts) == 2:
        return nombre_completo, parts[0], parts[1]
    else:
        nombres = " ".join(parts[:-2])
        apellidos = " ".join(parts[-2:])
        return nombre_completo, nombres, apellidos


def split_fechas_en_semanas(fechas_texto: str):
    """
    A partir de un texto tipo:
        '07, 08, 09, 21, 22 Y 23 de noviembre 2025'
    intenta separar en:
        sem1 = '07, 08, 09'
        sem2 = '21, 22, 23'

    Si no calza en 6 días, devuelve todo en sem1 y sem2 vacío.
    """
    if not fechas_texto:
        return "", ""

    # Tomamos todo antes del primer " de " (para quitar mes/año)
    lower = fechas_texto.lower()
    idx = lower.find(" de ")
    if idx != -1:
        solo_dias = fechas_texto[:idx]
    else:
        solo_dias = fechas_texto

    # Normalizar " Y " a coma
    solo_dias = solo_dias.replace(" Y ", ", ").replace(" y ", ", ")

    # Separar por comas, quedarnos con trozos que parezcan días
    tokens = [t.strip() for t in solo_dias.split(",") if t.strip()]
    dias = []
    for t in tokens:
        # quitar posibles cosas raras
        t_clean = "".join(ch for ch in t if ch.isdigit())
        if t_clean:
            dias.append(t_clean)

    if len(dias) == 6:
        sem1 = ", ".join(dias[:3])
        sem2 = ", ".join(dias[3:])
    else:
        # Caso genérico: todo en sem1
        sem1 = ", ".join(dias)
        sem2 = ""

    return sem1, sem2


def init_db():
    print(f"Usando base de datos: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1) Crear esquema desde schema.sql
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    cursor.executescript(schema_sql)
    conn.commit()
    print("Esquema creado correctamente ✅")

    # 2) Facultades
    facultades = [
        ("Facultad de Ciencias y Humanidades", "FCH"),
        ("Facultad de Ciencias de la Salud", "FCS"),
        ("Facultad de Ingenierías y Arquitectura", "FIA"),
        ("Facultad de Ciencias Económicas y Contables", "FCEC"),
        ("Facultad de Derecho y Ciencia Política", "FDCP"),
    ]
    cursor.executemany(
        "INSERT INTO facultad (nombre, codigo, activo) VALUES (?, ?, 1);",
        facultades,
    )
    conn.commit()

    # Mapa nombre_facultad -> id
    cursor.execute("SELECT id, nombre FROM facultad;")
    facultad_rows = cursor.fetchall()
    facultad_map = {nombre: fid for fid, nombre in facultad_rows}

    # 3) Periodo: Noviembre 2025
    cursor.execute(
        "INSERT OR IGNORE INTO periodo (anio, mes, etiqueta) VALUES (?, ?, ?);",
        (2025, 11, "Noviembre 2025"),
    )
    conn.commit()

    cursor.execute("SELECT id FROM periodo WHERE anio=? AND mes=?;", (2025, 11))
    row = cursor.fetchone()
    if not row:
        raise RuntimeError("No se pudo obtener el periodo Noviembre 2025")
    periodo_id = row[0]

    # 4) Programas académicos usados en Noviembre 2025
    programas = [
        # Facultad de Ciencias y Humanidades
        {
            "code": "DCE_15_PRES",
            "facultad": "Facultad de Ciencias y Humanidades",
            "tipo": "DOCTORADO",
            "nombre_corto": "Doctorado en Ciencias de la Educación 15va Promoción",
            "promocion": "15va Promoción",
            "modalidad": "PRESENCIAL",
            "universidad": "UNIVERSIDAD CESAR VALLEJO",
        },
        {
            "code": "DCE_2_MIX",
            "facultad": "Facultad de Ciencias y Humanidades",
            "tipo": "DOCTORADO",
            "nombre_corto": "Doctorado en Ciencias de la Educación 2da Promoción a Distancia/Presencial",
            "promocion": "2da Promoción",
            "modalidad": "DISTANCIA/PRESENCIAL",
            "universidad": "UNIVERSIDAD CESAR VALLEJO",
        },
        {
            "code": "DCE_4_DIST",
            "facultad": "Facultad de Ciencias y Humanidades",
            "tipo": "DOCTORADO",
            "nombre_corto": "Doctorado en Ciencias de la Educación 4ta Promoción a Distancia",
            "promocion": "4ta Promoción",
            "modalidad": "DISTANCIA",
            "universidad": "UNIVERSIDAD CÉSAR VALLEJO",
        },
        {
            "code": "DCE_5_DIST",
            "facultad": "Facultad de Ciencias y Humanidades",
            "tipo": "DOCTORADO",
            "nombre_corto": "Doctorado en Ciencias de la Educación 5ta Promoción a Distancia",
            "promocion": "5ta Promoción",
            "modalidad": "DISTANCIA",
            "universidad": "UNIVERSIDAD CÉSAR VALLEJO",
        },
        {
            "code": "MDU_4_DIST",
            "facultad": "Facultad de Ciencias y Humanidades",
            "tipo": "MAESTRIA",
            "nombre_corto": "Maestría en Docencia Universitaria 4ta Promoción a Distancia",
            "promocion": "4ta Promoción",
            "modalidad": "DISTANCIA",
            "universidad": "UNIVERSIDAD ANDINA NESTOR CACERES VELASQUEZ DE JULIACA",
        },
        {
            "code": "MDU_6_DIST",
            "facultad": "Facultad de Ciencias y Humanidades",
            "tipo": "MAESTRIA",
            "nombre_corto": "Maestría en Docencia Universitaria 6ta Promoción a Distancia",
            "promocion": "6ta Promoción",
            "modalidad": "DISTANCIA",
            "universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        },
        {
            "code": "MDU_7_DIST",
            "facultad": "Facultad de Ciencias y Humanidades",
            "tipo": "MAESTRIA",
            "nombre_corto": "Maestría en Docencia Universitaria 7ma Promoción a Distancia",
            "promocion": "7ma Promoción",
            "modalidad": "DISTANCIA",
            "universidad": "UNIVERSIDAD SIMÓN BOLÍVAR",
        },
        {
            "code": "MDU_5_DIST",
            "facultad": "Facultad de Ciencias y Humanidades",
            "tipo": "MAESTRIA",
            "nombre_corto": "Maestría en Docencia Universitaria 5ta Promoción a Distancia",
            "promocion": "5ta Promoción",
            "modalidad": "DISTANCIA",
            "universidad": "UNIVERSIDAD CATÓLICA DE SANTA MARÍA",
        },

        # Facultad de Ciencias de la Salud
        {
            "code": "DPSI_1_DIST",
            "facultad": "Facultad de Ciencias de la Salud",
            "tipo": "DOCTORADO",
            "nombre_corto": "Doctorado en Psicología 1ra Promoción a Distancia",
            "promocion": "1ra Promoción",
            "modalidad": "DISTANCIA",
            "universidad": "UNIVERSIDAD PRIVADA CÉSAR VALLEJO",
        },
        {
            "code": "DCS_2_DIST",
            "facultad": "Facultad de Ciencias de la Salud",
            "tipo": "DOCTORADO",
            "nombre_corto": "Doctorado en Ciencias de la Salud 2da Promoción a Distancia",
            "promocion": "2da Promoción",
            "modalidad": "DISTANCIA",
            "universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        },
        {
            "code": "DCS_3_DIST",
            "facultad": "Facultad de Ciencias de la Salud",
            "tipo": "DOCTORADO",
            "nombre_corto": "Doctorado en Ciencias de la Salud 3ra Promoción a Distancia",
            "promocion": "3ra Promoción",
            "modalidad": "DISTANCIA",
            "universidad": "UNIVERSIDAD NACIONAL MAYOR DE SAN MARCOS",
        },
        {
            "code": "DCS_4_DIST",
            "facultad": "Facultad de Ciencias de la Salud",
            "tipo": "DOCTORADO",
            "nombre_corto": "Doctorado en Ciencias de la Salud 4ta Promoción a Distancia",
            "promocion": "4ta Promoción",
            "modalidad": "DISTANCIA",
            "universidad": "UNIVERSIDAD CATÓLICA SANTA MARIA DE AREQUIPA",
        },

        # Facultad de Ingenierías y Arquitectura
        {
            "code": "DMA_2_PRES",
            "facultad": "Facultad de Ingenierías y Arquitectura",
            "tipo": "DOCTORADO",
            "nombre_corto": "Doctorado en Medio Ambiente y Desarrollo Sostenible 2da Promoción Presencial",
            "promocion": "2da Promoción",
            "modalidad": "PRESENCIAL",
            "universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        },
        {
            "code": "DMA_3_DIST",
            "facultad": "Facultad de Ingenierías y Arquitectura",
            "tipo": "DOCTORADO",
            "nombre_corto": "Doctorado en Medio Ambiente y Desarrollo Sostenible 3ra Promoción a Distancia",
            "promocion": "3ra Promoción",
            "modalidad": "DISTANCIA",
            "universidad": "PONTIFÍCIA UNIVERSIDADE CATÓLICA DO RIO DE JANEIRO",
        },
        {
            "code": "DMA_5_DIST",
            "facultad": "Facultad de Ingenierías y Arquitectura",
            "tipo": "DOCTORADO",
            "nombre_corto": "Doctorado en Medio Ambiente y Desarrollo Sostenible 5ta Promoción a Distancia",
            "promocion": "5ta Promoción",
            "modalidad": "DISTANCIA",
            "universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        },
        {
            "code": "DMA_12_PRES",
            "facultad": "Facultad de Ingenierías y Arquitectura",
            "tipo": "DOCTORADO",
            "nombre_corto": "Doctorado en Medio Ambiente y Desarrollo Sostenible 12va Promoción Presencial",
            "promocion": "12va Promoción",
            "modalidad": "PRESENCIAL",
            "universidad": "UNIVERSIDAD CÉSAR VALLEJO",
        },
        {
            "code": "DMA_6_DIST",
            "facultad": "Facultad de Ingenierías y Arquitectura",
            "tipo": "DOCTORADO",
            "nombre_corto": "Doctorado en Medio Ambiente y Desarrollo Sostenible 6ta Promoción a Distancia",
            "promocion": "6ta Promoción",
            "modalidad": "DISTANCIA",
            "universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        },
        {
            "code": "DMA_4_DIST",
            "facultad": "Facultad de Ingenierías y Arquitectura",
            "tipo": "DOCTORADO",
            "nombre_corto": "Doctorado en Medio Ambiente y Desarrollo Sostenible 4ta Promoción a Distancia",
            "promocion": "4ta Promoción",
            "modalidad": "DISTANCIA",
            "universidad": "UNIVERSIDAD NACIONAL DE SAN AGUSTÍN DE AREQUIPA",
        },
        {
            "code": "MIC_ESTR_4_DIST",
            "facultad": "Facultad de Ingenierías y Arquitectura",
            "tipo": "MAESTRIA",
            "nombre_corto": "Maestría en Ingeniería Civil mención en Estructuras 4ta Promoción a Distancia",
            "promocion": "4ta Promoción",
            "modalidad": "DISTANCIA",
            "universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        },
        {
            "code": "MIC_ESTR_5_DIST",
            "facultad": "Facultad de Ingenierías y Arquitectura",
            "tipo": "MAESTRIA",
            "nombre_corto": "Maestría en Ingeniería Civil mención en Estructuras 5ta Promoción a Distancia",
            "promocion": "5ta Promoción",
            "modalidad": "DISTANCIA",
            "universidad": "PONTIFICIA UNIVERSIDAD CATÓLICA DEL PERÚ",
        },
        {
            "code": "MIC_TRANS_2_PRES",
            "facultad": "Facultad de Ingenierías y Arquitectura",
            "tipo": "MAESTRIA",
            "nombre_corto": "Maestría en Ingeniería Civil mención en Transportes 2da Promoción Presencial",
            "promocion": "2da Promoción",
            "modalidad": "PRESENCIAL",
            "universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        },
        {
            "code": "MIC_ESTR_6_DIST",
            "facultad": "Facultad de Ingenierías y Arquitectura",
            "tipo": "MAESTRIA",
            "nombre_corto": "Maestría en Ingeniería Civil mención en Estructuras 6ta Promoción a Distancia",
            "promocion": "6ta Promoción",
            "modalidad": "DISTANCIA",
            "universidad": "PONTIFICIA UNIVERSIDAD CATÓLICA DE CHILE",
        },
        {
            "code": "MIC_HID_4_DIST",
            "facultad": "Facultad de Ingenierías y Arquitectura",
            "tipo": "MAESTRIA",
            "nombre_corto": "Maestría en Ingeniería Civil mención en Hidráulica y Ambiental 4ta Promoción a Distancia",
            "promocion": "4ta Promoción",
            "modalidad": "DISTANCIA",
            "universidad": "UNIVERSIDAD MAYOR DE SAN SIMÓN",
        },
        {
            "code": "MIC_ESTR_7_DIST",
            "facultad": "Facultad de Ingenierías y Arquitectura",
            "tipo": "MAESTRIA",
            "nombre_corto": "Maestría en Ingeniería Civil mención en Estructuras 7ma Promoción a Distancia",
            "promocion": "7ma Promoción",
            "modalidad": "DISTANCIA",
            "universidad": "UNIVERSIDAD CÉSAR VALLEJO",
        },

        # Facultad de Ciencias Económicas y Contables
        {
            "code": "DADM_2_MIX",
            "facultad": "Facultad de Ciencias Económicas y Contables",
            "tipo": "DOCTORADO",
            "nombre_corto": "Doctorado en Administración 2da Promoción a Distancia/presencial",
            "promocion": "2da Promoción",
            "modalidad": "DISTANCIA/PRESENCIAL",
            "universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        },
        {
            "code": "DADM_3_DIST",
            "facultad": "Facultad de Ciencias Económicas y Contables",
            "tipo": "DOCTORADO",
            "nombre_corto": "Doctorado en Administración 3ra Promoción a Distancia",
            "promocion": "3ra Promoción",
            "modalidad": "DISTANCIA",
            "universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        },
        {
            "code": "DADM_4_PRES",
            "facultad": "Facultad de Ciencias Económicas y Contables",
            "tipo": "DOCTORADO",
            "nombre_corto": "Doctorado en Administración 4ta Promoción presencial",
            "promocion": "4ta Promoción",
            "modalidad": "PRESENCIAL",
            "universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        },
        {
            "code": "DADM_4_DIST",
            "facultad": "Facultad de Ciencias Económicas y Contables",
            "tipo": "DOCTORADO",
            "nombre_corto": "Doctorado en Administración 4ta Promoción a Distancia",
            "promocion": "4ta Promoción",
            "modalidad": "DISTANCIA",
            "universidad": "UNIVERSIDAD NACIONAL DE SAN AGUSTÍN DE AREQUIPA",
        },
        {
            "code": "DCONT_2_DIST",
            "facultad": "Facultad de Ciencias Económicas y Contables",
            "tipo": "DOCTORADO",
            "nombre_corto": "Doctorado en Contabilidad 2da Promoción a Distancia",
            "promocion": "2da Promoción",
            "modalidad": "DISTANCIA",
            "universidad": "UNIVERSIDAD NACIONAL FEDERICO VILLARREAL",
        },
        {
            "code": "MAN_2_DIST",
            "facultad": "Facultad de Ciencias Económicas y Contables",
            "tipo": "MAESTRIA",
            "nombre_corto": "Maestría en Administración de Negocios 2da Promoción a Distancia",
            "promocion": "2da Promoción",
            "modalidad": "DISTANCIA",
            "universidad": "UNIVERSIDAD DEL PACÍFICO",
        },
        {
            "code": "MAN_3_DIST",
            "facultad": "Facultad de Ciencias Económicas y Contables",
            "tipo": "MAESTRIA",
            "nombre_corto": "Maestría en Administración de Negocios 3ra Promoción a Distancia",
            "promocion": "3ra Promoción",
            "modalidad": "DISTANCIA",
            "universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        },
        {
            "code": "MAN_4_DIST",
            "facultad": "Facultad de Ciencias Económicas y Contables",
            "tipo": "MAESTRIA",
            "nombre_corto": "Maestría en Administración de Negocios 4ta Promoción a Distancia",
            "promocion": "4ta Promoción",
            "modalidad": "DISTANCIA",
            "universidad": "ESCUELA DE POSGRADO NEWMAN",
        },
        {
            "code": "MCONT_AUD_3_DIST",
            "facultad": "Facultad de Ciencias Económicas y Contables",
            "tipo": "MAESTRIA",
            "nombre_corto": "Maestría en Contabilidad mención en Auditoría y Control Interno 3ra Promoción a Distancia",
            "promocion": "3ra Promoción",
            "modalidad": "DISTANCIA",
            "universidad": "UNIVERSIDAD DEL PACÍFICO",
        },
        {
            "code": "MCONT_AUD_4_DIST",
            "facultad": "Facultad de Ciencias Económicas y Contables",
            "tipo": "MAESTRIA",
            "nombre_corto": "Maestría en Contabilidad mención en Auditoría y Control Interno 4ta Promoción a Distancia",
            "promocion": "4ta Promoción",
            "modalidad": "DISTANCIA",
            "universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        },
        {
            "code": "MCONT_AUD_5_DIST",
            "facultad": "Facultad de Ciencias Económicas y Contables",
            "tipo": "MAESTRIA",
            "nombre_corto": "Maestría en Contabilidad mención en Auditoría y Control Interno 5ta Promoción a Distancia",
            "promocion": "5ta Promoción",
            "modalidad": "DISTANCIA",
            "universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        },

        # Facultad de Derecho y Ciencia Política
        {
            "code": "DDER_2_DIST",
            "facultad": "Facultad de Derecho y Ciencia Política",
            "tipo": "DOCTORADO",
            "nombre_corto": "Doctorado en Derecho 2da Promoción a Distancia",
            "promocion": "2da Promoción",
            "modalidad": "DISTANCIA",
            "universidad": "UNIVERSIDAD ANDINA NÉSTOR CÁCERES VELÁSQUEZ",
        },
        {
            "code": "DDER_3_DIST",
            "facultad": "Facultad de Derecho y Ciencia Política",
            "tipo": "DOCTORADO",
            "nombre_corto": "Doctorado en Derecho 3ra Promoción a Distancia",
            "promocion": "3ra Promoción",
            "modalidad": "DISTANCIA",
            "universidad": "UNIVERSIDAD CATÓLICA DE SANTA MARÍA",
        },
        {
            "code": "DDER_4_DIST",
            "facultad": "Facultad de Derecho y Ciencia Política",
            "tipo": "DOCTORADO",
            "nombre_corto": "Doctorado en Derecho 4ta Promoción a Distancia",
            "promocion": "4ta Promoción",
            "modalidad": "DISTANCIA",
            "universidad": "UNIVERSIDAD NACIONAL MAYOR DE SAN MARCOS",
        },
        {
            "code": "DDER_5_DIST",
            "facultad": "Facultad de Derecho y Ciencia Política",
            "tipo": "DOCTORADO",
            "nombre_corto": "Doctorado en Derecho 5ta Promoción a Distancia",
            "promocion": "5ta Promoción",
            "modalidad": "DISTANCIA",
            "universidad": "UNIVERSIDAD DE SAN MARTÍN DE PORRES",
        },
        {
            "code": "DDER_6_DIST",
            "facultad": "Facultad de Derecho y Ciencia Política",
            "tipo": "DOCTORADO",
            "nombre_corto": "Doctorado en Derecho 6ta Promoción a Distancia",
            "promocion": "6ta Promoción",
            "modalidad": "DISTANCIA",
            "universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        },
        {
            "code": "MDER_CIV_2_DIST",
            "facultad": "Facultad de Derecho y Ciencia Política",
            "tipo": "MAESTRIA",
            "nombre_corto": "Maestría en Derecho Civil y Comercial 2da Promoción a Distancia",
            "promocion": "2da Promoción",
            "modalidad": "DISTANCIA",
            "universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        },
        {
            "code": "MDER_REG_2_DIST",
            "facultad": "Facultad de Derecho y Ciencia Política",
            "tipo": "MAESTRIA",
            "nombre_corto": "Maestría en Derecho Registral y Notarial 2da Promoción a Distancia",
            "promocion": "2da Promoción",
            "modalidad": "DISTANCIA",
            "universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        },
        {
            "code": "MDER_CONST_3_DIST",
            "facultad": "Facultad de Derecho y Ciencia Política",
            "tipo": "MAESTRIA",
            "nombre_corto": "Maestría en Derecho Constitucional 3ra Promoción a Distancia",
            "promocion": "3ra Promoción",
            "modalidad": "DISTANCIA",
            "universidad": "UNIVERSIDAD DE SAN MARTÍN DE PORRES",
        },
        {
            "code": "MDER_CIV_3_DIST",
            "facultad": "Facultad de Derecho y Ciencia Política",
            "tipo": "MAESTRIA",
            "nombre_corto": "Maestría en Derecho Civil y Comercial 3ra Promoción a Distancia",
            "promocion": "3ra Promoción",
            "modalidad": "DISTANCIA",
            "universidad": "UNIVERSIDAD DEL PACÍFICO",
        },
        {
            "code": "MDER_CONST_4_DIST",
            "facultad": "Facultad de Derecho y Ciencia Política",
            "tipo": "MAESTRIA",
            "nombre_corto": "Maestría en Derecho Constitucional 4ta Promoción a Distancia",
            "promocion": "4ta Promoción",
            "modalidad": "DISTANCIA",
            "universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        },
        {
            "code": "MDER_REG_3_DIST",
            "facultad": "Facultad de Derecho y Ciencia Política",
            "tipo": "MAESTRIA",
            "nombre_corto": "Maestría en Derecho Registral y Notarial 3ra Promoción a Distancia",
            "promocion": "3ra Promoción",
            "modalidad": "DISTANCIA",
            "universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        },
        {
            "code": "MDER_CONST_5_DIST",
            "facultad": "Facultad de Derecho y Ciencia Política",
            "tipo": "MAESTRIA",
            "nombre_corto": "Maestría en Derecho Constitucional 5ta Promoción a Distancia",
            "promocion": "5ta Promoción",
            "modalidad": "DISTANCIA",
            "universidad": "PONTIFICIA UNIVERSIDAD CATÓLICA DEL PERÚ",
        },
        {
            "code": "MDER_REG_4_DIST",
            "facultad": "Facultad de Derecho y Ciencia Política",
            "tipo": "MAESTRIA",
            "nombre_corto": "Maestría en Derecho Registral y Notarial 4ta Promoción a Distancia",
            "promocion": "4ta Promoción",
            "modalidad": "DISTANCIA",
            "universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        },
        {
            "code": "MDER_CIV_4_DIST",
            "facultad": "Facultad de Derecho y Ciencia Política",
            "tipo": "MAESTRIA",
            "nombre_corto": "Maestría en Derecho Civil y Comercial 4ta Promoción a Distancia",
            "promocion": "4ta Promoción",
            "modalidad": "DISTANCIA",
            "universidad": "UNIVERSIDAD DEL PAÍS VASCO/EUSKAL HERRIKO UNIBERTSITATEA",
        },
    ]

    programa_id_map = {}

    for p in programas:
        fac_id = facultad_map[p["facultad"]]
        cursor.execute(
            """
            INSERT INTO programa_academico
                (facultad_id, tipo, nombre_corto, mencion, promocion, modalidad, universidad_procedencia, activo)
            VALUES (?, ?, ?, NULL, ?, ?, ?, 1);
            """,
            (
                fac_id,
                p["tipo"],
                p["nombre_corto"],
                p.get("promocion"),
                p.get("modalidad"),
                p.get("universidad"),
            ),
        )
        programa_id = cursor.lastrowid
        programa_id_map[p["code"]] = programa_id

    conn.commit()
    print(f"Programas académicos insertados: {len(programa_id_map)} ✅")

    # 5) Docentes
    docentes = [
        # 1 - 44: Docentes locales
        ("23863492", "DR. ELIAS MELENDREZ VELASCO", "LOCAL"),
        ("40543399", "DRA. EDDY TELLO YARIN", "LOCAL"),
        ("42780119", "DRA. JHAKELINNE YOVANNA VILA GARRAFA", "LOCAL"),
        ("40290670", "DR. BEYMAR PEDRO SOLIS TRUJILLO", "LOCAL"),
        ("23963570", "DRA. PAULA PATRICIA LUKSIC GIBAJA", "LOCAL"),
        ("40634924", "MG. WILBERT COLQUE CANDIA", "LOCAL"),
        ("49079955", "DR. LORNEL ANTONIO RIVAS MAGO", "LOCAL"),
        ("06580697", "DR. JUAN AGLIBERTO QUIJANO PACHECO", "LOCAL"),
        ("41884386", "DR. GARETH DEL CASTILLO ESTRADA", "LOCAL"),
        ("47025143", "DRA. KAREN MELISSA GARCES PORRAS", "LOCAL"),
        ("002219801", "DRA. CAROLINA DIANA PARADA QUINAYA", "LOCAL"),
        ("45924301", "DR. TEODORO HUARHUA CHIPANI", "LOCAL"),
        ("24004480", "DRA. LIZET VARGAS VERA", "LOCAL"),
        ("23894327", "DRA. MILUSKA FRISANCHO CAMERO", "LOCAL"),
        ("23858562", "MG. ALVARO HORACIO FLORES BOZA", "LOCAL"),
        ("44885194", "MG. MIJAIL MONTESINOS ESCOBAR", "LOCAL"),
        ("46086133", "MG. ED GUTIERREZ CARLOTTO", "LOCAL"),
        ("70747162", "MG. JULIO CESAR SUCASACA RODRIGUEZ", "LOCAL"),
        ("24484766", "MG. GORKI FEDERICO ASCUE SALAS", "LOCAL"),
        ("23865073", "DR. RAUL APAZA MENESES", "LOCAL"),
        ("41206297", "Dr. ABRAHAM PUENTE DE LA VEGA CACERES", "LOCAL"),
        ("41826776", "DRA. EVELYN JESUS CARAZAS ARAUJO", "LOCAL"),
        ("43581088", "DR. MARIO NICANOR VARGAS BEJARANO", "LOCAL"),
        ("23988416", "DR. CLETO DE LA TORRE DUEÑAS", "LOCAL"),
        ("23847092", "DR. RENNE WILFREDO PEREZ VILLAFUERTE", "LOCAL"),
        ("08687564", "MG. WERNHER OMAR GUEVARA MONTESINOS", "LOCAL"),
        ("23998983", "DR. WALDO ALEX PANDO DIAZ", "LOCAL"),
        ("23983332", "MG. HUGO ESPETIA HUAMANGA", "LOCAL"),
        ("44683350", "MG. LUIS ALBERTO ESPINOZA PANTY", "LOCAL"),
        ("23806625", "MG. GABRIEL MOZO AYMA", "LOCAL"),
        ("23994524", "MG. TATIANA CHOQUEHUANCA CONTRERAS", "LOCAL"),
        ("23854868", "DR. EDWARDS JESUS AGUIRRE ESPINOZA", "LOCAL"),
        ("28268722", "DR. SIDNEY ALEX BRAVO MELGAR", "LOCAL"),
        ("10281126", "DR. ISAAC ENRIQUE CASTRO CUBA BARINEZA", "LOCAL"),
        ("23839206", "DR. PAUL JOSE CASAFRANCA BUOB", "LOCAL"),
        ("73435847", "DRA. GABRIELA FERNANDA PINARES PAYNE", "LOCAL"),
        ("24713007", "DRA. DUNIA VICTORIA TERRAZAS GONZALES", "LOCAL"),
        ("47307488", "Mg. MIGUEL ALEJANDRO ESTELA LA PUENTE", "LOCAL"),
        ("06664112", "DR. MARIO ANDREA CAMOIRANO GARAVENTA", "LOCAL"),
        ("24008206", "DR. JUAN COSIO MUÑOZ", "LOCAL"),
        ("07267102", "DR. RENZO GUILLERMO ORTIZ DIAZ", "LOCAL"),
        ("45827055", "MGT. YULIANO QUISPE ANDRADE", "LOCAL"),
        ("23987320", "DRA LILIANA CORONADO GAMARRA", "LOCAL"),
        ("23950891", "MTRA. CLORINDA POZO ROLDAN", "LOCAL"),

        # 45 - 49: Docentes ordinarizados
        ("24484917", "DR. GUIDO AMERICO TORRES CASTILLO", "ORDINARIZADO"),
        ("23815007", "DRA. BENEDICTA SOLEDAD URRUTIA MELLADO", "ORDINARIZADO"),
        ("23821151", "DR. JULIO TRINIDAD RIOS MAYORGA", "ORDINARIZADO"),
        ("07933864", "DRA. GLADIS EDITH ROJAS SALAS", "ORDINARIZADO"),
        ("23913968", "DRA. HERMINIA CALLO SANCHEZ", "ORDINARIZADO"),
    ]

    docente_id_map = {}

    for dni, nombre_completo, tipo_docente in docentes:
        nombre_completo_norm, nombres, apellidos = parse_nombre(nombre_completo)
        cursor.execute(
            """
            INSERT INTO docente
                (nombre_completo, nombres, apellidos, dni, tipo_docente, activo)
            VALUES (?, ?, ?, ?, ?, 1);
            """,
            (nombre_completo_norm, nombres, apellidos, dni, tipo_docente),
        )
        docente_id_map[dni] = cursor.lastrowid

    conn.commit()
    print(f"Docentes insertados: {len(docente_id_map)} ✅")

    # 6) Cursos programados – DOCENTES EPG – MES NOVIEMBRE 2025
    #    Todos con estado_programacion = 'CONFIRMADO'
    cursos = [
        # Facultad de Ciencias y Humanidades
        # Doctorado en Ciencias de la Educación
        {
            "program_code": "DCE_15_PRES",
            "dni": "23863492",
            "ciclo": "VI",
            "asignatura": "SEMINARIO DE TESIS V",
            "fechas": "07, 08, 09, 21, 22 Y 23 de noviembre 2025",
            "rem_texto": "S/. 5,900.00",
            "rem_monto": 5900.00,
            "poi": "257423",
            "tipo_docente_mes": "LOCAL",
        },
        {
            "program_code": "DCE_2_MIX",
            "dni": "40543399",
            "ciclo": "IV",
            "asignatura": "GESTIÓN EDUCATIVA Y LIDERAZGO",
            "fechas": "07, 08, 09, 21, 22 Y 23 de noviembre 2025",
            "rem_texto": "S/. 5,900.00",
            "rem_monto": 5900.00,
            "poi": "257429",
            "tipo_docente_mes": "LOCAL",
        },
        {
            "program_code": "DCE_4_DIST",
            "dni": "42780119",
            "ciclo": "II",
            "asignatura": "REFORMAS Y POLÍTICAS EDUCATIVAS",
            "fechas": "14, 15, 16, 28, 29 Y 30 de noviembre 2025",
            "rem_texto": "S/. 5,900.00",
            "rem_monto": 5900.00,
            "poi": "257431",
            "tipo_docente_mes": "LOCAL",
        },
        {
            "program_code": "DCE_5_DIST",
            "dni": "40290670",
            "ciclo": "I",
            "asignatura": "METODOLOGÍA DE LA INVESTIGACIÓN CIENTÍFICA",
            "fechas": "07, 08, 09, 21, 22 Y 23 de noviembre 2025",
            "rem_texto": "S/. 5,900.00",
            "rem_monto": 5900.00,
            "poi": "257432",
            "tipo_docente_mes": "LOCAL",
        },

        # Maestría en Docencia Universitaria
        {
            "program_code": "MDU_4_DIST",
            "dni": "23963570",
            "ciclo": "IV",
            "asignatura": "PLANIFICACIÓN DE LOS APRENDIZAJES - SILABO Y SESION DE CLASE",
            "fechas": "14, 15, 16, 28, 29 Y 30 de noviembre 2025",
            "rem_texto": "S/. 4,140.00",
            "rem_monto": 4140.00,
            "poi": "257403",
            "tipo_docente_mes": "LOCAL",
        },
        {
            "program_code": "MDU_6_DIST",
            "dni": "40634924",
            "ciclo": "II",
            "asignatura": "CURRÍCULO Y FORMACIÓN POR COMPETENCIAS EN LA EDUCACIÓN SUPERIOR",
            "fechas": "14, 15, 16, 28, 29 Y 30 de noviembre 2025",
            "rem_texto": "S/. 4,140.00",
            "rem_monto": 4140.00,
            "poi": "257405",
            "tipo_docente_mes": "LOCAL",
        },
        {
            "program_code": "MDU_7_DIST",
            "dni": "49079955",
            "ciclo": "I",
            "asignatura": "METODOLOGÍA CIENTÍFICA DE LA INVESTIGACIÓN",
            "fechas": "14, 15, 16, 28, 29 Y 30 de noviembre 2025",
            "rem_texto": "S/. 4,140.00",
            "rem_monto": 4140.00,
            "poi": "257406",
            "tipo_docente_mes": "LOCAL",
        },

        # Facultad de Ciencias de la Salud
        {
            "program_code": "DPSI_1_DIST",
            "dni": "06580697",
            "ciclo": "VI",
            "asignatura": "ELABORACIÓN Y PUBLICACIÓN DE ARTÍCULOS CIENTÍFICOS",
            "fechas": "14, 15, 16, 28, 29 Y 30 de noviembre 2025",
            "rem_texto": "S/. 5,900.00",
            "rem_monto": 5900.00,
            "poi": "257446",
            "tipo_docente_mes": "LOCAL",
        },
        {
            "program_code": "DCS_2_DIST",
            "dni": "41884386",
            "ciclo": "VI",
            "asignatura": "MARKETING APLICADO A CIENCIA DE LA SALUD",
            "fechas": "14, 15, 16, 28, 29 Y 30 de noviembre 2025",
            "rem_texto": "S/. 5,900.00",
            "rem_monto": 5900.00,
            "poi": "257445",
            "tipo_docente_mes": "LOCAL",
        },

        # Facultad de Ingenierías y Arquitectura – Doctorado en Medio Ambiente...
        {
            "program_code": "DMA_2_PRES",
            "dni": "47025143",
            "ciclo": "VI",
            "asignatura": "CALIDAD Y SALUD AMBIENTAL",
            "fechas": "14, 15, 16, 28, 29 Y 30 de noviembre 2025",
            "rem_texto": "S/. 5,900.00",
            "rem_monto": 5900.00,
            "poi": "257441",
            "tipo_docente_mes": "LOCAL",
        },
        {
            "program_code": "DMA_3_DIST",
            "dni": "002219801",
            "ciclo": "V",
            "asignatura": "CULTURA ACADÉMICA Y DOCENCIA",
            "fechas": "14, 15, 16, 28, 29 Y 30 de noviembre 2025",
            "rem_texto": "S/. 5,900.00",
            "rem_monto": 5900.00,
            "poi": "257439",
            "tipo_docente_mes": "LOCAL",
        },
        {
            "program_code": "DMA_5_DIST",
            "dni": "45924301",
            "ciclo": "II",
            "asignatura": "SEMINARIO DE TESIS I",
            "fechas": "07, 08, 09, 21, 22 Y 23 de noviembre 2025",
            "rem_texto": "S/. 5,900.00",
            "rem_monto": 5900.00,
            "poi": "257441",
            "tipo_docente_mes": "LOCAL",
        },
        {
            "program_code": "DMA_12_PRES",
            "dni": "24004480",
            "ciclo": "II",
            "asignatura": "DESARROLLO SOSTENIBLE Y POLÍTICAS PÚBLICAS",
            "fechas": "07, 08, 09, 21, 22 Y 23 de noviembre 2025",
            "rem_texto": "S/. 5,900.00",
            "rem_monto": 5900.00,
            "poi": "257424",
            "tipo_docente_mes": "LOCAL",
        },
        {
            "program_code": "DMA_6_DIST",
            "dni": "23894327",
            "ciclo": "I",
            "asignatura": "CONTAMINACIÓN AMBIENTAL Y PROPUESTA DE ACCIONES",
            "fechas": "14, 15, 16, 28, 29 Y 30 de noviembre 2025",
            "rem_texto": "S/. 5,900.00",
            "rem_monto": 5900.00,
            "poi": "257442",
            "tipo_docente_mes": "LOCAL",
        },

        # Maestría en Ingeniería Civil
        {
            "program_code": "MIC_ESTR_4_DIST",
            "dni": "23858562",
            "ciclo": "IV",
            "asignatura": "TESIS III",
            "fechas": "07, 08, 09, 21, 22 Y 23 de noviembre 2025",
            "rem_texto": "S/. 4,140.00",
            "rem_monto": 4140.00,
            "poi": "257416",
            "tipo_docente_mes": "LOCAL",
        },
        {
            "program_code": "MIC_ESTR_5_DIST",
            "dni": "44885194",
            "ciclo": "III",
            "asignatura": "TEMAS AVANZADOS DE INGENIERIA ESTRUCTURAL EN LA GEOTECNICA",
            "fechas": "14, 15, 16, 28, 29 Y 30 de noviembre 2025",
            "rem_texto": "S/. 4,140.00",
            "rem_monto": 4140.00,
            "poi": "257417",
            "tipo_docente_mes": "LOCAL",
        },
        {
            "program_code": "MIC_TRANS_2_PRES",
            "dni": "46086133",
            "ciclo": "III",
            "asignatura": "OPERACIONES DE TRÁFICO",
            "fechas": "14, 15, 16, 28, 29 Y 30 de noviembre 2025",
            "rem_texto": "S/. 4,140.00",
            "rem_monto": 4140.00,
            "poi": "257396",
            "tipo_docente_mes": "LOCAL",
        },
        {
            "program_code": "MIC_ESTR_6_DIST",
            "dni": "70747162",
            "ciclo": "II",
            "asignatura": "INGENIERIA SISMORESISTENTE Y SISMOTECTONICA",
            "fechas": "14, 15, 16, 28, 29 Y 30 de noviembre 2025",
            "rem_texto": "S/. 4,140.00",
            "rem_monto": 4140.00,
            "poi": "257418",
            "tipo_docente_mes": "LOCAL",
        },
        {
            "program_code": "MIC_HID_4_DIST",
            "dni": "24484766",
            "ciclo": "II",
            "asignatura": "ECOLOGIA Y MEDIO AMBIENTE",
            "fechas": "14, 15, 16, 28, 29 Y 30 de noviembre 2025",
            "rem_texto": "S/. 4,140.00",
            "rem_monto": 4140.00,
            "poi": "257421",
            "tipo_docente_mes": "LOCAL",
        },
        {
            "program_code": "MIC_ESTR_7_DIST",
            "dni": "23865073",
            "ciclo": "I",
            "asignatura": "METODOLOGIA CIENTIFICA DE LA INVESTIGACION",
            "fechas": "14, 15, 16, 28, 29 Y 30 de noviembre 2025",
            "rem_texto": "S/. 4,140.00",
            "rem_monto": 4140.00,
            "poi": "257419",
            "tipo_docente_mes": "LOCAL",
        },

        # Facultad de Ciencias Económicas y Contables
        # Doctorado en Administración
        {
            "program_code": "DADM_2_MIX",
            "dni": "41206297",
            "ciclo": "V",
            "asignatura": "FINANZAS CORPORATIVAS AVANZADAS",
            "fechas": "07, 08, 09, 21, 22 Y 23 de noviembre 2025",
            "rem_texto": "S/. 5,900.00",
            "rem_monto": 5900.00,
            "poi": "257425",
            "tipo_docente_mes": "LOCAL",
        },
        {
            "program_code": "DADM_3_DIST",
            "dni": "41826776",
            "ciclo": "IV",
            "asignatura": "DIRECCIÓN DE NEGOCIOS INTERNACIONALES",
            "fechas": "14, 15, 16, 28, 29 Y 30 de noviembre 2025",
            "rem_texto": "S/. 5,900.00",
            "rem_monto": 5900.00,
            "poi": "257426",
            "tipo_docente_mes": "LOCAL",
        },
        {
            "program_code": "DADM_4_PRES",
            "dni": "43581088",
            "ciclo": "II",
            "asignatura": "ANÁLISIS DE INVERSIONES",
            "fechas": "07, 08, 09, 21, 22 Y 23 de noviembre 2025",
            "rem_texto": "S/. 5,900.00",
            "rem_monto": 5900.00,
            "poi": "257422",
            "tipo_docente_mes": "LOCAL",
        },
        {
            "program_code": "DADM_4_DIST",
            "dni": "23988416",
            "ciclo": "II",
            "asignatura": "ESTADÍSTICA APLICADA A LOS NEGOCIOS",
            "fechas": "07, 08, 09, 21, 22 Y 23 de noviembre 2025",
            "rem_texto": "S/. 5,900.00",
            "rem_monto": 5900.00,
            "poi": "257427",
            "tipo_docente_mes": "LOCAL",
        },

        # Doctorado en Contabilidad
        {
            "program_code": "DCONT_2_DIST",
            "dni": "23847092",
            "ciclo": "III",
            "asignatura": "SEMINARIO DE TESIS II",
            "fechas": "07, 08, 09, 21, 22 Y 23 de noviembre 2025",
            "rem_texto": "S/. 5,900.00",
            "rem_monto": 5900.00,
            "poi": "257428",
            "tipo_docente_mes": "LOCAL",
        },

        # Maestría en Administración de Negocios
        {
            "program_code": "MAN_2_DIST",
            "dni": "08687564",
            "ciclo": "IV",
            "asignatura": "GERENCIA ESTRATEGICA Y POLITICAS DE EMPRESA",
            "fechas": "07, 08, 09, 21, 22 Y 23 de noviembre 2025",
            "rem_texto": "S/. 4,140.00",
            "rem_monto": 4140.00,
            "poi": "257397",
            "tipo_docente_mes": "LOCAL",
        },
        {
            "program_code": "MAN_3_DIST",
            "dni": "23998983",
            "ciclo": "III",
            "asignatura": "FORMULACION, EVALUACION Y GESTION DE PROYECTOS",
            "fechas": "07, 08, 09, 21, 22 Y 23 de noviembre 2025",
            "rem_texto": "S/. 4,140.00",
            "rem_monto": 4140.00,
            "poi": "257398",
            "tipo_docente_mes": "LOCAL",
        },
        {
            "program_code": "MAN_4_DIST",
            "dni": "23983332",
            "ciclo": "II",
            "asignatura": "ADMINISTRACIÓN DE SISTEMAS DE INFORMACIÓN",
            "fechas": "07, 08, 09, 21, 22 Y 23 de noviembre 2025",
            "rem_texto": "S/. 4,140.00",
            "rem_monto": 4140.00,
            "poi": "257399",
            "tipo_docente_mes": "LOCAL",
        },

        # Maestría en Contabilidad mención en Auditoría y Control Interno
        {
            "program_code": "MCONT_AUD_3_DIST",
            "dni": "44683350",
            "ciclo": "IV",
            "asignatura": "TOPICOS ESPECIALES DE AUDITORIA TRIBUTARIA",
            "fechas": "07, 08, 09, 21, 22 Y 23 de noviembre 2025",
            "rem_texto": "S/. 4,140.00",
            "rem_monto": 4140.00,
            "poi": "257400",
            "tipo_docente_mes": "LOCAL",
        },
        {
            "program_code": "MCONT_AUD_4_DIST",
            "dni": "23806625",
            "ciclo": "III",
            "asignatura": "PERITAJE CONTABLE",
            "fechas": "07, 08, 09, 21, 22 Y 23 de noviembre 2025",
            "rem_texto": "S/. 4,140.00",
            "rem_monto": 4140.00,
            "poi": "257401",
            "tipo_docente_mes": "LOCAL",
        },
        {
            "program_code": "MCONT_AUD_5_DIST",
            "dni": "23994524",
            "ciclo": "II",
            "asignatura": "METODOLOGÍA CIENTÍFICA DE LA INVESTIGACIÓN",
            "fechas": "14, 15, 16, 28, 29 Y 30 de noviembre 2025",
            "rem_texto": "S/. 4,140.00",
            "rem_monto": 4140.00,
            "poi": "257402",
            "tipo_docente_mes": "LOCAL",
        },

        # Facultad de Derecho y Ciencia Política – Doctorado en Derecho
        {
            "program_code": "DDER_2_DIST",
            "dni": "23854868",
            "ciclo": "V",
            "asignatura": "CULTURA ACADEMICA Y DOCENCIA",
            "fechas": "07, 08, 09, 21, 22 Y 23 de noviembre 2025",
            "rem_texto": "S/. 5,900.00",
            "rem_monto": 5900.00,
            "poi": "257433",
            "tipo_docente_mes": "LOCAL",
        },
        {
            "program_code": "DDER_4_DIST",
            "dni": "28268722",
            "ciclo": "III",
            "asignatura": "TEORIA DE LOS DERECHOS HUMANOS",
            "fechas": "07, 08, 09, 21, 22 Y 23 de noviembre 2025",
            "rem_texto": "S/. 5,900.00",
            "rem_monto": 5900.00,
            "poi": "257433",
            "tipo_docente_mes": "LOCAL",
        },
        {
            "program_code": "DDER_5_DIST",
            "dni": "10281126",
            "ciclo": "II",
            "asignatura": "SEMINARIO DE TESIS I",
            "fechas": "14, 15, 16, 28, 29 Y 30 de noviembre 2025",
            "rem_texto": "S/. 5,900.00",
            "rem_monto": 5900.00,
            "poi": "257436",
            "tipo_docente_mes": "LOCAL",
        },
        {
            "program_code": "DDER_6_DIST",
            "dni": "23839206",
            "ciclo": "I",
            "asignatura": "TEORIA GENERAL DEL DERECHO",
            "fechas": "07, 08, 09, 21, 22 Y 23 de noviembre 2025",
            "rem_texto": "S/. 5,900.00",
            "rem_monto": 5900.00,
            "poi": "257437",
            "tipo_docente_mes": "LOCAL",
        },

        # Maestría en Derecho
        {
            "program_code": "MDER_CIV_2_DIST",
            "dni": "73435847",
            "ciclo": "IV",
            "asignatura": "TUTELA JURÍDICA CIVIL Y TUTELA JURISDICCIONAL",
            "fechas": "07, 08, 09, 21, 22 Y 23 de noviembre 2025",
            "rem_texto": "S/. 4,140.00",
            "rem_monto": 4140.00,
            "poi": "257413",
            "tipo_docente_mes": "LOCAL",
        },
        {
            "program_code": "MDER_REG_2_DIST",
            "dni": "24713007",
            "ciclo": "IV",
            "asignatura": "DERECHO INMOBILIARIO III",
            "fechas": "07, 08, 09, 21, 22 Y 23 de noviembre 2025",
            "rem_texto": "S/. 4,140.00",
            "rem_monto": 4140.00,
            "poi": "257410",
            "tipo_docente_mes": "LOCAL",
        },
        {
            "program_code": "MDER_CONST_3_DIST",
            "dni": "47307488",
            "ciclo": "IV",
            "asignatura": "DERECHO CONSTITUCIONAL ECONÓMICO",
            "fechas": "14, 15, 16, 28, 29 Y 30 de noviembre 2025",
            "rem_texto": "S/. 4,140.00",
            "rem_monto": 4140.00,
            "poi": "257407",
            "tipo_docente_mes": "LOCAL",
        },
        {
            "program_code": "MDER_CIV_3_DIST",
            "dni": "06664112",
            "ciclo": "III",
            "asignatura": "CONTRATOS INTERNACIONALES",
            "fechas": "14, 15, 16, 28, 29 Y 30 de noviembre 2025",
            "rem_texto": "S/. 4,140.00",
            "rem_monto": 4140.00,
            "poi": "257414",
            "tipo_docente_mes": "LOCAL",
        },
        {
            "program_code": "MDER_CONST_4_DIST",
            "dni": "24008206",
            "ciclo": "III",
            "asignatura": "TESIS II",
            "fechas": "07, 08, 09, 21, 22 Y 23 de noviembre 2025",
            "rem_texto": "S/. 4,140.00",
            "rem_monto": 4140.00,
            "poi": "257408",
            "tipo_docente_mes": "LOCAL",
        },
        {
            "program_code": "MDER_REG_3_DIST",
            "dni": "07267102",
            "ciclo": "III",
            "asignatura": "DERECHO INMOBILIARIO II",
            "fechas": "14, 15, 16, 28, 29 Y 30 de noviembre 2025",
            "rem_texto": "S/. 4,140.00",
            "rem_monto": 4140.00,
            "poi": "257411",
            "tipo_docente_mes": "LOCAL",
        },
        {
            "program_code": "MDER_CONST_5_DIST",
            "dni": "45827055",
            "ciclo": "II",
            "asignatura": "LA JURISDICCIÓN CONSTITUCIONAL",
            "fechas": "07, 08, 09, 21, 22 Y 23 de noviembre 2025",
            "rem_texto": "S/. 4,140.00",
            "rem_monto": 4140.00,
            "poi": "257409",
            "tipo_docente_mes": "LOCAL",
        },
        {
            "program_code": "MDER_REG_4_DIST",
            "dni": "23987320",
            "ciclo": "II",
            "asignatura": "METODOLOGIA CIENTIFICA DE LA INVESTIGACIÓN",
            "fechas": "07, 08, 09, 21, 22 Y 23 de noviembre 2025",
            "rem_texto": "S/. 4,140.00",
            "rem_monto": 4140.00,
            "poi": "257412",
            "tipo_docente_mes": "LOCAL",
        },
        {
            "program_code": "MDER_CIV_4_DIST",
            "dni": "23950891",
            "ciclo": "II",
            "asignatura": "TESIS I",
            "fechas": "14, 15, 16, 28, 29 Y 30 de noviembre 2025",
            "rem_texto": "S/. 4,140.00",
            "rem_monto": 4140.00,
            "poi": "257415",
            "tipo_docente_mes": "LOCAL",
        },

        # Docentes Ordinarizados
        {
            "program_code": "DCS_3_DIST",
            "dni": "24484917",
            "ciclo": "III",
            "asignatura": "SALUD PÚBLICA",
            "fechas": "14, 15, 16, 28, 29 Y 30 de noviembre 2025",
            "rem_texto": "S/. 5,900.00",
            "rem_monto": 5900.00,
            "poi": "257444",
            "tipo_docente_mes": "ORDINARIZADO",
        },
        {
            "program_code": "DMA_4_DIST",
            "dni": "23815007",
            "ciclo": "III",
            "asignatura": "ECONOMÍA ECOLÓGICA",
            "fechas": "14, 15, 16, 28, 29 Y 30 de noviembre 2025",
            "rem_texto": "S/. 5,900.00",
            "rem_monto": 5900.00,
            "poi": "257440",
            "tipo_docente_mes": "ORDINARIZADO",
        },
        {
            "program_code": "DDER_3_DIST",
            "dni": "23821151",
            "ciclo": "IV",
            "asignatura": "PRODUCCION INTELECTUAL",
            "fechas": "07, 08, 09, 21, 22 Y 23 de noviembre 2025",
            "rem_texto": "S/. 5,900.00",
            "rem_monto": 5900.00,
            "poi": "257434",
            "tipo_docente_mes": "ORDINARIZADO",
        },
        {
            "program_code": "DCS_4_DIST",
            "dni": "07933864",
            "ciclo": "II",
            "asignatura": "BIOÉTICA",
            "fechas": "14, 15, 16, 28, 29 Y 30 de noviembre 2025",
            "rem_texto": "S/. 5,900.00",
            "rem_monto": 5900.00,
            "poi": "257445",
            "tipo_docente_mes": "ORDINARIZADO",
        },
        {
            "program_code": "MDU_5_DIST",
            "dni": "23913968",
            "ciclo": "III",
            "asignatura": "EVALUACIÓN EN EDUCACIÓN",
            "fechas": "07, 08, 09, 21, 22 Y 23 de noviembre 2025",
            "rem_texto": "S/. 4,140.00",
            "rem_monto": 4140.00,
            "poi": "257404",
            "tipo_docente_mes": "ORDINARIZADO",
        },
    ]

    for c in cursos:
        program_code = c["program_code"]
        dni = c["dni"]

        programa_id = programa_id_map.get(program_code)
        docente_id = docente_id_map.get(dni)

        if programa_id is None:
            raise RuntimeError(f"Programa no encontrado para code={program_code}")
        if docente_id is None:
            raise RuntimeError(f"Docente no encontrado para dni={dni}")

        # Derivamos sem1/sem2 desde el texto de fechas
        sem1, sem2 = split_fechas_en_semanas(c["fechas"])

        # Por ahora no tenemos código/categoría de asignatura aquí, se pueden
        # actualizar luego desde la UI o un script aparte.
        codigo = c.get("codigo")
        categoria = c.get("categoria")

        cursor.execute(
            """
            INSERT INTO curso_programado
                (periodo_id, programa_id, docente_id,
                 ciclo, asignatura, fechas_texto,
                 remuneracion_monto, remuneracion_texto,
                 poi, dni_docente,
                 tipo_docente_mes, estado_programacion,
                 codigo, categoria, sem1, sem2)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                periodo_id,
                programa_id,
                docente_id,
                c["ciclo"],
                c["asignatura"],
                c["fechas"],
                c["rem_monto"],
                c["rem_texto"],
                c["poi"],
                dni,
                c["tipo_docente_mes"],
                "CONFIRMADO",
                codigo,
                categoria,
                sem1,
                sem2,
            ),
        )

    conn.commit()
    conn.close()
    print(f"Cursos programados insertados: {len(cursos)} ✅")
    print("Base de datos inicializada completamente con Noviembre 2025 🎉")


if __name__ == "__main__":
    init_db()
