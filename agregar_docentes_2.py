#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Carga Lote 2 de docentes (IDs 48–100) en la base docentes.db

- Usa el mismo esquema de schema.sql
- Upsert por DNI en tabla docente
- Registra grados en docente_grado_academico sin perder información
"""

import os
import sqlite3
from pathlib import Path
from typing import Dict, Any, List

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = ROOT_DIR / "schema.sql"

load_dotenv()

DOCENTES_DB_PATH = os.getenv("DOCENTES_DB_PATH")
if not DOCENTES_DB_PATH:
    DOCENTES_DB_PATH = str(ROOT_DIR / "docentes.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DOCENTES_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    """
    Si la tabla docente no existe, aplica schema.sql completo.
    """
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='docente';"
    )
    row = cur.fetchone()
    if row:
        return

    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"No se encontró schema.sql en {SCHEMA_PATH}")

    with SCHEMA_PATH.open("r", encoding="utf-8") as f:
        sql = f.read()
    conn.executescript(sql)
    conn.commit()


def _texto_valido(value: str) -> bool:
    """
    Devuelve False si el texto está vacío o es 'NO REGISTRA GRADO EN SUNEDU'.
    """
    if not value:
        return False
    txt = value.strip().upper()
    if not txt:
        return False
    if "NO REGISTRA GRADO EN SUNEDU" in txt:
        return False
    return True


def _determinar_mayor_grado(d: Dict[str, Any]) -> str | None:
    """
    Determina qué tipo de grado marcar como mayor para docente_grado_academico.
    Prioridad: DOCTORADO > MAGISTER > TITULO_PROFESIONAL.
    """
    if _texto_valido(d.get("grado_doctor", "")):
        return "DOCTORADO"
    if _texto_valido(d.get("grado_magister", "")):
        return "MAGISTER"
    if _texto_valido(d.get("titulo_profesional", "")):
        return "TITULO_PROFESIONAL"
    return None


def _upsert_grados_academicos(conn: sqlite3.Connection, docente_id: int, d: Dict[str, Any]) -> None:
    """
    Inserta (si no existen) los grados del docente en docente_grado_academico.
    No intenta partir fechas; guarda la denominación tal cual viene.
    """
    cur = conn.cursor()
    mayor = _determinar_mayor_grado(d)

    definiciones = [
        ("TITULO_PROFESIONAL", "titulo_profesional", "titulo_universidad"),
        ("MAGISTER", "grado_magister", "magister_universidad"),
        ("DOCTORADO", "grado_doctor", "doctor_universidad"),
    ]

    for tipo, campo_den, campo_uni in definiciones:
        denominacion = (d.get(campo_den) or "").strip()
        universidad = (d.get(campo_uni) or "").strip()

        if not _texto_valido(denominacion):
            continue
        if not universidad:
            # No forzamos universidad si viene vacía
            universidad = ""

        es_mayor = 1 if mayor == tipo else 0

        # Evitar duplicados exactos
        cur.execute(
            """
            SELECT id FROM docente_grado_academico
            WHERE docente_id = ? AND tipo = ? AND denominacion = ? AND universidad = ?
            """,
            (docente_id, tipo, denominacion, universidad),
        )
        row = cur.fetchone()
        if row:
            # Ya existe, podríamos actualizar es_mayor_grado si fuera necesario
            cur.execute(
                """
                UPDATE docente_grado_academico
                SET es_mayor_grado = CASE WHEN ? = 1 THEN 1 ELSE es_mayor_grado END
                WHERE id = ?
                """,
                (es_mayor, row["id"]),
            )
        else:
            cur.execute(
                """
                INSERT INTO docente_grado_academico
                    (docente_id, tipo, denominacion, universidad, fecha_expedicion, es_mayor_grado, observaciones)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    docente_id,
                    tipo,
                    denominacion,
                    universidad,
                    None,           # fecha_expedicion la dejamos NULL para no inventar
                    es_mayor,
                    None,
                ),
            )

    conn.commit()


def upsert_docente_completo(conn: sqlite3.Connection, d: Dict[str, Any]) -> int:
    """
    Inserta o actualiza un docente en la tabla docente, usando DNI como clave.
    Solo llena columnas donde tenemos datos directos de tu tabla.
    """
    cur = conn.cursor()
    dni = d["dni"].strip()

    cur.execute("SELECT id FROM docente WHERE dni = ?", (dni,))
    row = cur.fetchone()

    if row:
        docente_id = row["id"]
        cur.execute(
            """
            UPDATE docente
            SET
                nombre_completo = ?,
                especialidad = ?,
                direccion = ?,
                correo = ?,
                telefono = ?,
                titulo_profesional = ?,
                titulo_universidad = ?,
                grado_magister = ?,
                magister_universidad = ?,
                grado_doctor = ?,
                doctor_universidad = ?,
                updated_at = datetime('now')
            WHERE id = ?
            """,
            (
                d["nombre_completo"].strip(),
                d["especialidad"].strip() if d.get("especialidad") else None,
                d["direccion"].strip() if d.get("direccion") else None,
                d["correo"].strip() if d.get("correo") else None,
                d["telefono"].strip() if d.get("telefono") else None,
                d["titulo_profesional"].strip() if d.get("titulo_profesional") else None,
                d["titulo_universidad"].strip() if d.get("titulo_universidad") else None,
                d["grado_magister"].strip() if d.get("grado_magister") else None,
                d["magister_universidad"].strip() if d.get("magister_universidad") else None,
                d["grado_doctor"].strip() if d.get("grado_doctor") else None,
                d["doctor_universidad"].strip() if d.get("doctor_universidad") else None,
                docente_id,
            ),
        )
    else:
        cur.execute(
            """
            INSERT INTO docente (
                nombre_completo,
                especialidad,
                dni,
                direccion,
                correo,
                telefono,
                titulo_profesional,
                titulo_universidad,
                grado_magister,
                magister_universidad,
                grado_doctor,
                doctor_universidad
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                d["nombre_completo"].strip(),
                d["especialidad"].strip() if d.get("especialidad") else None,
                dni,
                d["direccion"].strip() if d.get("direccion") else None,
                d["correo"].strip() if d.get("correo") else None,
                d["telefono"].strip() if d.get("telefono") else None,
                d["titulo_profesional"].strip() if d.get("titulo_profesional") else None,
                d["titulo_universidad"].strip() if d.get("titulo_universidad") else None,
                d["grado_magister"].strip() if d.get("grado_magister") else None,
                d["magister_universidad"].strip() if d.get("magister_universidad") else None,
                d["grado_doctor"].strip() if d.get("grado_doctor") else None,
                d["doctor_universidad"].strip() if d.get("doctor_universidad") else None,
            ),
        )
        docente_id = cur.lastrowid

    conn.commit()

    # Ahora aseguramos los grados en la tabla de detalle
    _upsert_grados_academicos(conn, docente_id, d)

    return docente_id


DOCENTES_LOTE_2: List[Dict[str, Any]] = [
    {
        "nro": 48,
        "nombre_completo": "DR. JOSE VICTOR MANCHEGO ENRIQUEZ",
        "especialidad": "MÉDICO CIRUJANO",
        "dni": "01332872",
        "direccion": "JR. PARURO H1 URBANIZACIÓN PROGRESO WANCHAQ",
        "correo": "vmanchegoe@gmail.com",
        "telefono": "984555531",
        "titulo_profesional": "MEDICO CIRUJANO 25-08-2000",
        "titulo_universidad": "UNIVERSIDAD NACIONAL DEL ALTIPLANO",
        "grado_magister": "MAESTRÍA EN CIENCIAS: MEDICINA 24-07-2017",
        "magister_universidad": "UNIVERSIDAD NACIONAL DE SAN AGUSTIN DE AREQUIPA",
        "grado_doctor": "DOCTOR EN CIENCIAS: MEDICINA 20-03-2020",
        "doctor_universidad": "UNIVERSIDAD NACIONAL DE SAN AGUSTIN DE AREQUIPA",
    },
    {
        "nro": 49,
        "nombre_completo": "DR. JUAN CARLOS ALVAREZ NEGRON",
        "especialidad": "LICENCIADO EN INVESTIGACIÓN OPERATIVA",
        "dni": "09551407",
        "direccion": "AV. INDUSTRIAL O-I EDIFICIO LA PLANICIE DPTO 203 HUANCARO",
        "correo": "juancarlosperu2003@yahoo.es",
        "telefono": "980518270",
        "titulo_profesional": "LICENCIADO EN INVESTIGACIÓN OPERATIVA 20-01-1999",
        "titulo_universidad": "UNIVERSIDAD NACIONAL MAYOR DE SAN MARCOS",
        "grado_magister": "MAESTRÍA MBA INTERNACIONAL EN GESTIÓN EMPRESARIAL 11-08-2014 (Reconocimiento)",
        "magister_universidad": "UNIVERSITAT RAMON LLULL",
        "grado_doctor": "DOCTOR EN GESTIÓN ECONÓMICA GLOBAL 19-08-2015",
        "doctor_universidad": "UNIVERSIDAD NACIONAL MAYOR DE SAN MARCOS",
    },
    {
        "nro": 50,
        "nombre_completo": "DR. JUAN EULOGIO ARROYO LAGUNA",
        "especialidad": "LICENCIADO EN SOCIOLOGÍA",
        "dni": "06267382",
        "direccion": "AV. DEL EJERCITO 1218, DPTO 401 SAN ISIDRO LIMA",
        "correo": "juan.arroyo@upch.pe",
        "telefono": "999973141",
        "titulo_profesional": "LICENCIADO EN SOCIOLOGÍA 14-07-2014",
        "titulo_universidad": "UNIVERSIDAD NACIONAL MAYOR DE SAN MARCOS",
        "grado_magister": "MAESTRÍA EN SALUD PÚBLICA 18-02-1998",
        "magister_universidad": "UNIVERSIDAD PERUANA CAYETANO HEREDIA",
        "grado_doctor": "DOCTOR EN CIENCIAS SOCIALES SOCIOLOGIA 21/02/2007",
        "doctor_universidad": "UNIVERSIDAD NACIONAL MAYOR DE SAN MARCOS",
    },
    {
        "nro": 51,
        "nombre_completo": "DR. JULIO CESAR ABARCA CORDERO",
        "especialidad": "PSICÓLOGO",
        "dni": "43504693",
        "direccion": "CONDOMINIO VALLE BLANCO 75 III ETAPA TORRE 4 DPTO 103 CALLAPAMPA AV GARCILAZO DE LA VEGA CERRO COLORADO AREQUIPA",
        "correo": "julioabar@gmail.com",
        "telefono": "994607920",
        "titulo_profesional": "PSICOLOGO 21-01-2011",
        "titulo_universidad": "UNIVERSIDAD NACIONAL DE SAN AGUSTIN DE AREQUIPA",
        "grado_magister": "MAESTRÍA EN CIENCIAS ADMINISTRACIÓN MBA GERENCIA DE RECURSOS HUMANOS 29-01-2016",
        "magister_universidad": "UNIVERSIDAD NACIONAL DE SAN AGUSTIN DE AREQUIPA",
        "grado_doctor": "DOCTOR EN ADMINISTRACIÓN 07-06-2019",
        "doctor_universidad": "UNIVERSIDAD NACIONAL DE SAN AGUSTIN DE AREQUIPA",
    },
    {
        "nro": 52,
        "nombre_completo": "DR. JULIO QUILLAHUAMAN LASTEROS",
        "especialidad": "LICENCIADO EN EDUCACIÓN",
        "dni": "23975471",
        "direccion": "PICCHU RINCONADA O-5 CUSCO",
        "correo": "julioql2@gmail.com",
        "telefono": "944214152",
        "titulo_profesional": "LICENCIADO EN EDUCACIÓN 02-09-1996",
        "titulo_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "grado_magister": "MAESTRÍA EN EDUCACIÓN MENCIÓN EN EDUCACIÓN 28-11-2011",
        "magister_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "grado_doctor": "DOCTOR EN CIENCIAS DE LA EDUCACIÓN 22-05-17",
        "doctor_universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
    },
    {
        "nro": 53,
        "nombre_completo": "DR. LAURO ENCISO RODAS",
        "especialidad": "INGENIERO QUÍMICO",
        "dni": "23853228",
        "direccion": "COVIDUC MZ. H LOTE 8",
        "correo": "lauro.enciso@unsaac.edu.pe",
        "telefono": "984002511",
        "titulo_profesional": "INGENIERO QUÍMICO 17-12-1976",
        "titulo_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "grado_magister": "MAESTRÍA EN CIENCIAS ESPECIALIDAD EN INGENIERÍA EN COMPUTACIÓN 22-06-2007",
        "magister_universidad": "UNIVERSIDAD CENTRAL DE FLORIDA",
        "grado_doctor": "DOCTOR EN INGENIERÍA DE SISTEMAS 04-12-2014",
        "doctor_universidad": "UNIVERSIDAD NACIONAL FEDERICO VILLAREAL",
    },
    {
        "nro": 54,
        "nombre_completo": "DR. LUIS ALFONSO SARMIENTO NUÑEZ",
        "especialidad": "ABOGADO",
        "dni": "31001811",
        "direccion": "AV. INDUSTRIAL 117 DPTO 114",
        "correo": "luissn100@hotmail.com",
        "telefono": "940184307",
        "titulo_profesional": "ABOGADO 30-01-1984",
        "titulo_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "grado_magister": "MAESTRÍA EN DERECHO MENCIÓN EN DERECHO PENAL Y PROCESAL PENAL 06-05-2015",
        "magister_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "grado_doctor": "DOCTOR EN DERECHO 11-08-2017",
        "doctor_universidad": "UNIVERIDAD ANDINA DEL CUSCO",
    },
    {
        "nro": 55,
        "nombre_completo": "DR. LUIS MANUEL CASTILLO LUNA",
        "especialidad": "ABOGADO",
        "dni": "10439164",
        "direccion": "URB. MARISCAL GAMARRA 2DA ETAPA A-41 CUSCO",
        "correo": "luiscastilloluna@hotmail.com",
        "telefono": "984128182",
        "titulo_profesional": "ABOGADO 01-04-1996",
        "titulo_universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        "grado_magister": "MAESTRIA EN DERECHO CIVIL 04-09-2008",
        "magister_universidad": "UNIVERSIDAD CATÓLICA DE SANTA MARÍA",
        "grado_doctor": "DOCTORADO EN DERECHO 27-07-16",
        "doctor_universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
    },
    {
        "nro": 56,
        "nombre_completo": "DR. MANUEL ANTONIO MATTOS VELA",
        "especialidad": "CIRUJANO DENTISTA",
        "dni": "07463598",
        "direccion": "CALLE AMERICO VESPUCIO MZ G LT 5 URB STA PATRICIA 3RA ETAPA",
        "correo": "mmattosv@unmsm.edu.pe",
        "telefono": "990770787",
        "titulo_profesional": "CIRUJANO DENTISTA 24-08-1994",
        "titulo_universidad": "UNIVERSIDAD PERUANA CAYETANO HEREDIA",
        "grado_magister": "MAESTRÍA EN ESTOMATOLOGÍA 09-08-2007",
        "magister_universidad": "UNIVERSIDAD NACIONAL MAYOR DE SAN MARCOS",
        "grado_doctor": "DOCTOR EN ESTOMATOLOGÍA 08-09-2015",
        "doctor_universidad": "UNIVERSIDAD NACIONAL MAYOR DE SAN MARCOS",
    },
    {
        "nro": 57,
        "nombre_completo": "DR. MARCO ANTONIO HERRERA VARGAS",
        "especialidad": "LICENCIADO EN MATEMÁTICAS",
        "dni": "23934173",
        "direccion": "CONJ. HAB. PACHACUTEC A-302",
        "correo": "marco3108h@gmail.com",
        "telefono": "945628437",
        "titulo_profesional": "MATEMÁTICO 16-01-2001",
        "titulo_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "grado_magister": "MAESTRÍA EN DOCENCIA UNIVERSITARIA E INVESTIGACIÓN PEDAGÓGICA 30-05-2011",
        "magister_universidad": "UNIVERSIDAD SAN PEDRO",
        "grado_doctor": "DOCTOR EN GESTIÓN Y CIENCIAS DE LA EDUCACIÓN 16-01-2015",
        "doctor_universidad": "UNIVERSIDAD SAN PEDRO",
    },
    {
        "nro": 58,
        "nombre_completo": "DR. MARCO AUGUSTO SOTOMAYOR BERRÍO",
        "especialidad": "INGENIERO ZOOTECNISTA",
        "dni": "23843628",
        "direccion": "CALLE LOS SAUCES F-7 PAMPA CHACRA",
        "correo": "marcosotomayor10@hotmail.com",
        "telefono": "987841820 - 987100695",
        "titulo_profesional": "INGENIERO ZOOTECNISTA 30-12-1982",
        "titulo_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "grado_magister": "MAESTRIA EN DESARROLLO HUMANO Y SUSTENTABLE (Reconocimiento)",
        "magister_universidad": "UNIVERSIDAD BOLIVARIANA CLADES CHILE",
        "grado_doctor": "DOCTOR EN DESARROLLO HUMANO Y SUSTENTABLE (Reconocimiento)",
        "doctor_universidad": "UNIVERSIDAD BOLIVARIANA CLADES CHILE",
    },
    {
        "nro": 59,
        "nombre_completo": "DR. MAURO CHECCORI TTITO",
        "especialidad": "LICENCIADO EN EDUCACIÓN",
        "dni": "23925021",
        "direccion": "PROGRESO S-4 WANCHAQ CUSCO",
        "correo": "elcheccori22@hotmail.com",
        "telefono": "984070609",
        "titulo_profesional": "LICENCIADO EN EDUCACIÓN 27-10-1995",
        "titulo_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "grado_magister": "MAESTRÍA EN DOCENCIA UNIVERSIARIA E INVESTIGACIÓN PEDAGÓGICA 28-11-2014",
        "magister_universidad": "UNIVERSIDAD DE SAN PEDRO",
        "grado_doctor": "DOCTOR EN GESTIÓN Y CIENCIAS DE LA EDUCACIÓN 21-03-2016",
        "doctor_universidad": "UNIVERSIDA DE SAN PEDRO",
    },
    {
        "nro": 60,
        "nombre_completo": "DR. MAXIMO CORDOVA HUAMANI",
        "especialidad": "ABOGADO",
        "dni": "23845466",
        "direccion": "PJE. VILCANOTA W-1-9 URB TTIO",
        "correo": "maximo.cordova@unsaac.edu.pe",
        "telefono": "997495327",
        "titulo_profesional": "LICENCIADO EN EDUCACIÓN 25-05-1993 - LICENCIADO EN CIENCIAS DE LA COMUNICACIÓN 01-02-1994 - ABOGADO 12-07-1996",
        "titulo_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO - UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "grado_magister": "MAESTRÍA EN DERECHO CIVIL Y PROCESAL CIVIL 21-03-2007 - MAESTRÍA EN ADMINISTRACIÓN 23-12-2006 - MAESTRÍA EN DOCENCIA UNIVERSITARIA 16-04-2008",
        "magister_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO - UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO - UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "grado_doctor": "DOCTOR EN EDUCACIÓN 10-09-2010",
        "doctor_universidad": "UNIVERSIDAD ANDINA NESTOR CACERES VELASQUEZ DE JULIACA",
    },
    {
        "nro": 61,
        "nombre_completo": "DR. MENDOZA ESCALANTE SANDY MIJAIL",
        "especialidad": "ABOGADO",
        "dni": "29602344",
        "direccion": "CALLE PASEO REAL 121 URB. LAS LOMAS DE LA MOLINA",
        "correo": "mmendoza@consultoriaconstitucional.com",
        "telefono": "913660031",
        "titulo_profesional": "ABOGADO 16-04-1998",
        "titulo_universidad": "UNIVERSIDAD NACIONAL DE SAN AGUSTIN",
        "grado_magister": "NO REGISTRA GRADO EN SUNEDU",
        "magister_universidad": "NO REGISTRA GRADO EN SUNEDU",
        "grado_doctor": "DOCTOR EN DERECHO (Reconocimiento)",
        "doctor_universidad": "UNIVERSIDAD COMPLUTENSE DE MADRID (REVALIDADO EN  PONTIFICIA UNIVERSIDAD CATOLICA DEL PERU)",
    },
    {
        "nro": 62,
        "nombre_completo": "DR. MIGUEL ANGEL ZUÑIGA MARINO",
        "especialidad": "ABOGADO",
        "dni": "41249533",
        "direccion": "CALLE BOLOGNESI 431 MIRAFLORES AREQUIPA",
        "correo": "mazmk@hotmail.com",
        "telefono": "958190114",
        "titulo_profesional": "ABOGADO 25-03-2010",
        "titulo_universidad": "UNIVERSIDAD ALAS PERUANAS",
        "grado_magister": "MAESTRÍA EN DERECHO DEL TRABAJO Y DE LA SEGURIDAD SOCIAL 15-01-2015",
        "magister_universidad": "UNIVERSIDAD CATÓLICA DE SANTA MARÍA",
        "grado_doctor": "DOCTOR EN DERECHO 24-01-2018",
        "doctor_universidad": "UNIVERSIDAD CATÓLICA DE SANTA MARÍA",
    },
    {
        "nro": 63,
        "nombre_completo": "DR. NORMAN JESUS BELTRAN CASTAÑON",
        "especialidad": "INGENIERO ECONOMISTA",
        "dni": "01325035",
        "direccion": "JR. SAN MARTIN DE PORRAS NRO 230 PUNO",
        "correo": "normanjesus@gmail.com",
        "telefono": "939220054",
        "titulo_profesional": "INGENIERO ECONOMISTA 23-06-17 - INGENIERO MECÁNICO ELECTRICISTA 03-01-03",
        "titulo_universidad": "UNIVERSIDAD NACIONAL DEL ALTIPLANO - UNIVERSIDAD NACIONAL DEL ALTIPLANO",
        "grado_magister": "MAESTRÍA EN ENERGÍA (Reconocimiento)",
        "magister_universidad": "UNIVERSIDAD DE SAO PAULO",
        "grado_doctor": "DOCTOR EN CIENCIAS: INGENIERÍA DE PRODUCCIÓN",
        "doctor_universidad": "UNIVERSIDAD NACIONAL DE SAN AGUSTIN",
    },
    {
        "nro": 64,
        "nombre_completo": "DR. OSCAR VALIENTE CASTILLO",
        "especialidad": "MÉDICO CIRUJANO",
        "dni": "23931132",
        "direccion": "AV. RICARDO PALMA L-18 URB. SANTA MONICA WANCHAQ CUSCO",
        "correo": "osvacal18@yahoo.es",
        "telefono": "984618626",
        "titulo_profesional": "MEDICO CIRUJANO 04-09-1981",
        "titulo_universidad": "UNIVERSIDAD NACIONAL MAYOR DE SAN MARCOS",
        "grado_magister": "MAESTRÍA EN SALUD PÚBLICA MENCIÓN EN GERENCIA EN SALUD 11-02-2004",
        "magister_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "grado_doctor": "DOCTOR EN CIENCIAS DE LA SALUD 29-09-2011",
        "doctor_universidad": "UNIVERSIDAD CATOLICA DE SANTA MARIA",
    },
    {
        "nro": 65,
        "nombre_completo": "DR. OSWALDO ANTONIO VALLEJOS AGREDA",
        "especialidad": "CONTADOR PÚBLICO",
        "dni": "09876981",
        "direccion": "CALLE DOÑA MARGARITA 142 URB LOS ROSALES",
        "correo": "ovallejosa@hotmail.com",
        "telefono": "971157879",
        "titulo_profesional": "CONTADOR PÚBLICO 04-09-1972",
        "titulo_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "grado_magister": "MAESTRÍA EN ADMINISTRACIÓN PÚBLICA (Reconociemiento)",
        "magister_universidad": "CENTRO DE INVESTIGACIÓN Y DOCENCIA ECONÓMICAS A.C.CIDE",
        "grado_doctor": "DOCTOR EN CONTABILIDAD 04-05-2000",
        "doctor_universidad": "UNIVERSIDAD INCA GARCILAZO DE LA VEGA",
    },
    {
        "nro": 66,
        "nombre_completo": "DR. PAVEL HUMBERTO VALER BELLOTA",
        "especialidad": "ABOGADO",
        "dni": "23925634",
        "direccion": "PILIVIO HUMPIRE 10",
        "correo": "pvalerb@yahoo.com",
        "telefono": "958174803",
        "titulo_profesional": "ABOGADO 26-08-1996",
        "titulo_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "grado_magister": "MAESTRÍA EN AYUDA INTERNACIONAL HUMANITARIA (Reconocimiento)",
        "magister_universidad": "UNIVERSIDAD DE DEUSTO",
        "grado_doctor": "DOCTOR DENTRO DEL PROGRAMA DE ESTUDIOS AVANZADOS EN DERECHO ADMINISTRATIVO, CONSTITUCIONAL Y TEORÍA DEL DERECHO (Reconocimiento)",
        "doctor_universidad": "UNIVERSIDAD DEL PAÍS VASCO",
    },
    {
        "nro": 67,
        "nombre_completo": "DR. PERCY ANTONIO VILCHEZ OLIVARES",
        "especialidad": "CONTADOR PÚBLICO",
        "dni": "07712178",
        "direccion": "CALLE ARCO IRIS 345 URB. LA ALBORADA SANTIAGO DE SURCO",
        "correo": "pvilchezcpa@gmail.com",
        "telefono": "999639566",
        "titulo_profesional": "CONTADOR PÚBLICO 02-02-1989",
        "titulo_universidad": "UNIVERSIDAD NACIONAL MAYOR DE SAN MARCOS",
        "grado_magister": "MAESTRÍA EN DESARROLLO Y COMPORTAMIENTO ORGANIZACIONAL 25-05-1999 (Reconocimiento)",
        "magister_universidad": "UNIVERSIDAD DIEGO PORTALES",
        "grado_doctor": "DOCTOR EN CIENCIAS CONTABLES Y EMPRESARIALES 14-02-2017",
        "doctor_universidad": "UNIVERSIDAD NACIONAL MAYOR DE SAN MARCOS",
    },
    {
        "nro": 68,
        "nombre_completo": "DR. RAMIRO JESUS GUTIERREZ VASQUEZ",
        "especialidad": "PSICÓLOGO",
        "dni": "08103651",
        "direccion": "RESIDENCIAL SAN FELIPE TORRE 4C DPTO 1002",
        "correo": "raguvas48@gmail.com",
        "telefono": "958792573",
        "titulo_profesional": "LICENCIADO EN PSICOLOGÍA 20-02-1985",
        "titulo_universidad": "UNIVERSIDAD PERUANA CAYETANO HEREDIA",
        "grado_magister": "MAESTRÍA EN CIENCIAS PSICOLOGIA 29-08-1990",
        "magister_universidad": "UNIVERSIDAD PERUANA CAYETANO HEREDIA",
        "grado_doctor": "DOCTOR EN CIENCIAS MENCIÓN PSICOLOGÍA 11-06-1997",
        "doctor_universidad": "UNIVERSIDAD PERUANA CAYETANO HEREDIA",
    },
    {
        "nro": 69,
        "nombre_completo": "DR. RAUL ALBERTO RENGIFO LOZANO",
        "especialidad": "ABOGADO",
        "dni": "07537379",
        "direccion": "JR. TACNA 3815 URB. PERU SAN MARTIN DE PORRES LIMA",
        "correo": "rrengif@hotmail.com",
        "telefono": "963200676",
        "titulo_profesional": "ECONOMISTA 20-10-1997 - ABOGADO 10-03-2016 - LICENCIADO EN EDUCACIÓN 20-12-2006",
        "titulo_universidad": "UNIVERSIDAD INCA GARCILASO DE LA VEGA - UNIVERSIDAD INCA GARCILASO DE LA VEGA - UNIVERSIDAD PRIVADA SAN PEDRO",
        "grado_magister": "MAESTRIA EN SEGURIDAD Y DEFENSA NACIONAL 19-09-2011 - MAESTRIA EN FINANZAS Y MERCADOS FINANCIEROS 26-07-2007",
        "magister_universidad": "CENTRO DE ALTOS ESTUDIOS (CAEN) - UNIVERSIDAD INCA GARCILASO DE LA VEGA",
        "grado_doctor": "DOCTOR EN ECONOMIA 28-04-2009",
        "doctor_universidad": "UNIVERSIDAD INCA GARCILASO DE LA VEGA",
    },
    {
        "nro": 70,
        "nombre_completo": "DR. RENNE WILFREDO PEREZ VILLAFUERTE",
        "especialidad": "CONTADOR PÚBLICO",
        "dni": "23847092",
        "direccion": "URB. SANTA MARIA B-3",
        "correo": "cpc_rpv@yahoo.es",
        "telefono": "984381432",
        "titulo_profesional": "CONTADOR PÚBLICO 23-08-1993 - LICENCIADO EN EDUCACIÓN 05-03-2008",
        "titulo_universidad": "UNIVERSIDAD NACIONAL SAN ANTONIO ABAD DEL CUSCO - UNIVERSIDAD PRIVADA SAN IGNACIO DE LOYOLA",
        "grado_magister": "MAESTRIA EN CONTABILIDAD CON MENCION EN AUDITORIA 13-08-2008",
        "magister_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "grado_doctor": "DOCTOR EN CONTABILIDAD 22-11-2013 - DOCTOR EN EDUCACIÓN 18-12-14",
        "doctor_universidad": "UNIVERSIDAD NACIONAL FEDERICO VILLAREAL - UNIVERSIDAD CATÓLICA DE SANTA MARÍA",
    },
    {
        "nro": 71,
        "nombre_completo": "DR. RICHARD SUAREZ SANCHEZ",
        "especialidad": "LICENCIADO EN EDUCACIÓN",
        "dni": "23945736",
        "direccion": "URB. LUCREPATA C-3 SAN BLAS CUSCO",
        "correo": "suarezsanchezrichard@gmail.com",
        "telefono": "984349137",
        "titulo_profesional": "LICENCIADO EN EDUCACIÓN 20-02-1995",
        "titulo_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "grado_magister": "MAESTRÍA EN EDUCACIÓN MENCIÓN EN GESTIÓN DE LA EDUCACIÓN 19-10-2005",
        "magister_universidad": "PONTIFICIA UNIVERSIDAD CATÓLICA DEL PERÚ",
        "grado_doctor": "DOCTOR EN SOCIEDAD DEMOCRÁTICA, ESTADO Y DERECHO (Reconocimiento)",
        "doctor_universidad": "UNIVERSIDAD DEL PAÍS VASCO",
    },
    {
        "nro": 72,
        "nombre_completo": "DR. ROLANDO REÁTEGUI LOZANO",
        "especialidad": "INGENIERO PESQUERO",
        "dni": "06418510",
        "direccion": "JR. SAN MARTIN 1903 LAMAS - SAN MARTIN",
        "correo": "rolandoreateguilozano@gmail.com",
        "telefono": "990410828",
        "titulo_profesional": "INGENIERO PESQUERO 15-09-1986 - ABOGADO 18-12-2012",
        "titulo_universidad": "UNIVERSIDAD SAN LUIS GONZAGA - UNIVERSIDAD ALAS PERUANAS",
        "grado_magister": "MAESTRÍA EN SANIDAD MEDIOAMBIENTAL 03-02-1997",
        "magister_universidad": "UNIVERSITAT DE VALENCIA",
        "grado_doctor": "DOCTOR EN CIENCIAS BIOLÓGICAS (Reconocimiento)",
        "doctor_universidad": "UNIVERSIDAD DE VALENCIA ESPAÑA",
    },
    {
        "nro": 73,
        "nombre_completo": "DR. RONY VILLAFUERTE SERNA",
        "especialidad": "INGENIERO INFORMÁTICO",
        "dni": "23957778",
        "direccion": "URB. VILLA MIRAFLORES E-21 SAN JERÓNIMO",
        "correo": "rony.villafuerte@unsaac.edu.pe",
        "telefono": "984749818",
        "titulo_profesional": "INGENIERO INFORMÁTICO Y DE SISTEMAS 01-03-2002",
        "titulo_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "grado_magister": "MAESTRÍA EN DOCENCIA UNIVERSITARIA 15-08-2013",
        "magister_universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        "grado_doctor": "DOCTOR EN CIENCIAS DE LA EDUCACIÓN 08-11-2018",
        "doctor_universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
    },
    {
        "nro": 74,
        "nombre_completo": "DR. RUBEN GILBERTO RODRIGUEZ FLORES",
        "especialidad": "INGENIERO QUÍMICO",
        "dni": "04401210",
        "direccion": "AV. BRASIL 1458 DPTO 803-A PUEBLO LIBRE LIMA",
        "correo": "rubengrf4@yahoo.es",
        "telefono": "995846808",
        "titulo_profesional": "INGENIERO QUÍMICO 08-02-1993",
        "titulo_universidad": "UNIVERSIDAD NACIONAL DE SAN AGUSTÍN",
        "grado_magister": "NO REGISTRA GRADO EN SUNEDU",
        "magister_universidad": "NO REGISTRA GRADO EN SUNEDU",
        "grado_doctor": "DOCTOR EN INGENIERÍA QUÍMICA (Reconocimineto)",
        "doctor_universidad": "UNIVERSIDAD DE VALLADOLID",
    },
    {
        "nro": 75,
        "nombre_completo": "DR. SEBASTIAN BUSTAMANTE EDQUEN",
        "especialidad": "LICENCIADO EN ENFERMERÍA",
        "dni": "18183130",
        "direccion": "PSJE. GIRARDOT 1324 - 1326 LA ESPERANZA LA LIBERTAD TRUJILLO",
        "correo": "edquen@gmail.com",
        "telefono": "949640353",
        "titulo_profesional": "LICENCIADO EN ENFERMERÍA 06-01-1986",
        "titulo_universidad": "UNIVERSIDAD NACIONAL DE CAJAMARCA",
        "grado_magister": "MAESTRÍA EN ENFERMERÍA MENCIÓN EN ENFERMERÍA EN SALUD COMUNITARIA 23-01-1992",
        "magister_universidad": "UNIVERSIDAD DE CONCEPCIÓN",
        "grado_doctor": "DOCTOR EN ENFERMERÍA MENCIÓN EN LA ENFERMERÍA EN EL CONTEXTO SOCIAL BRASILEÑO",
        "doctor_universidad": "UNIVERISIDAD FEDERAL DE RIO DE JANEIRO",
    },
    {
        "nro": 76,
        "nombre_completo": "DR. SIDNEY ALEX BRAVO MELGAR",
        "especialidad": "ABOGADO",
        "dni": "28268722",
        "direccion": "CALLE CAPRICORNIO 241 URB. MERCURIO LOS OLIVOS",
        "correo": "sidneybravo@hotmail.com",
        "telefono": "996997784",
        "titulo_profesional": "ABOGADO 23-10-1993",
        "titulo_universidad": "UNIVERSIDAD CATÓLICA DE SANTA MARÍA",
        "grado_magister": "MAESTRÍA EN DERECHO 26-12-1996",
        "magister_universidad": "UNIVERSIDAD DE SAN MARTÍN DE PORRES",
        "grado_doctor": "DOCTOR EN DERECHO Y CIENCIA POLÍTICA 17-05-2000",
        "doctor_universidad": "UNIVERSIDAD NACIONAL MAYOR DE SAN MARCOS",
    },
    {
        "nro": 77,
        "nombre_completo": "DR. VICTOR IVAN FERNANDEZ DAVILA GONZALES",
        "especialidad": "INGENIERO CIVIL",
        "dni": "06303702",
        "direccion": "JR. PUERTO PIZARRO N° 104 DPTO 502 URB. ALICIA SANTIAGO DE SURCO LIMA",
        "correo": "vifdavila@outlook.com",
        "telefono": "975517652",
        "titulo_profesional": "INGENIERO CIVIL 26-01-1990",
        "titulo_universidad": "UNIVERSIDAD NACIONAL DE INGENIERÍA",
        "grado_magister": "MAESTRÍA EN CIENCIAS DE LA INGENIERÍA (Reconocimiento)",
        "magister_universidad": "PONTIFICIA UNIVERSIDAD CATÓLICA DE CHILE",
        "grado_doctor": "DOCTOR EN CIENCIAS DE LA INGENIERÍA (Reconocimiento)",
        "doctor_universidad": "PONTIFICIA UNIVERSIDAD CATÓLICA DE CHILE",
    },
    {
        "nro": 78,
        "nombre_completo": "DR. WALDO ALEX PANDO DIAZ",
        "especialidad": "LICENCIADO EN ADMINISTRACIÓN",
        "dni": "23998983",
        "direccion": "JR. CHANKAS E-27 URB. LOS NOGALES SAN SEBASTIAN",
        "correo": "alpadi33@gmail.com",
        "telefono": "940184270",
        "titulo_profesional": "LICENCIADO EN ADMINISTRACIÓN 28-02-2007",
        "titulo_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "grado_magister": "MAESTRÍA EN ADMINISTRACIÓN 06-07-2016",
        "magister_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "grado_doctor": "DOCTOR EN ADMINISTRACIÓN 07-03-2023",
        "doctor_universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
    },
    {
        "nro": 79,
        "nombre_completo": "DR. WALDO ENRIQUE CAMPAÑA MORRO",
        "especialidad": "LICENCIADO EN ADMINISTRACIÓN",
        "dni": "23933923",
        "direccion": "URB. SANTA ROSA PSJE CANDIA 252 WANCHAQ",
        "correo": "waencamo@gmail.com",
        "telefono": "984648727",
        "titulo_profesional": "LICENCIADO EN ADMINISTRACIÓN 21-07-2010",
        "titulo_universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        "grado_magister": "MAESTRÍA EN ADMINISTRACIÓN DE LA EDUCACIÓN 24-06-2014",
        "magister_universidad": "UNIVERSIDAD PRIVADA CESAR VALLEJO",
        "grado_doctor": "DOCTOR EN EDUCACIÓN 29-02-2016",
        "doctor_universidad": "UNIVERSIDAD PRIVADA CESAR VALLEJO",
    },
    {
        "nro": 80,
        "nombre_completo": "DR. WALDRICK CESAR MORRO SUMARY",
        "especialidad": "INGENIERO INDUSTRIAL",
        "dni": "44045227",
        "direccion": "AV. TULLUMAYO 395",
        "correo": "waldrickmorro@hotmail.com",
        "telefono": "926938879",
        "titulo_profesional": "INGENIERO INDUSTRIAL 06-05-2010",
        "titulo_universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        "grado_magister": "MAESTRÍA EN ADMINISTRACIÓN DE LA EDUCACIÓN 24-06-2014",
        "magister_universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        "grado_doctor": "DOCTOR EN PROYECTOS 31-08-2022",
        "doctor_universidad": "UNIVERSIDAD CENTRO PANAMERICANO DE ESTUDIOS SUPERIORES",
    },
    {
        "nro": 81,
        "nombre_completo": "DR. WALKER HERNAN ARAUJO BERRIO",
        "especialidad": "ABOGADO",
        "dni": "23960589",
        "direccion": "URB. BARRIO PROFESIONAL B-7",
        "correo": "waraujo1@gmail.com",
        "telefono": "984651631",
        "titulo_profesional": "ABOGADO 16-10-1992",
        "titulo_universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        "grado_magister": "MAESTRÍA EN DERECHO CIVIL Y PROCESAL CIVIL 16-10-2013",
        "magister_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "grado_doctor": "DOCTOR EN DERECHO 13-12-2018",
        "doctor_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
    },
    {
        "nro": 82,
        "nombre_completo": "DR. WALTER EDGAR GOMEZ GONZALES",
        "especialidad": "LICENCIADO EN ENFERMERÍA",
        "dni": "19836297",
        "direccion": "AV. JORGE CHAVEZ N° 977 BREÑA LIMA-PERÚ",
        "correo": "waltergomez29@yahoo.com",
        "telefono": "998469500",
        "titulo_profesional": "LICENCIADO EN ENFERMERÍA 29-01-1986",
        "titulo_universidad": "UNIVERSIDAD NACIONAL DEL CENTRO DEL PERÚ",
        "grado_magister": "MAESTRÍA EN POLÍTICA SOCIAL 01-04-2004",
        "magister_universidad": "UNIVERSIDAD NACIONAL MAYOR DE SAN MARCOS",
        "grado_doctor": "DOCTOR EN CIENCIAS DE LA SALUD 19-08-2014",
        "doctor_universidad": "UNIVERSIDAD NACIONAL MAYOR DE SAN MARCOS",
    },
    {
        "nro": 83,
        "nombre_completo": "DR. WALTER SAUL APAZA MENDOZA",
        "especialidad": "CONTADOR PÚBLICO",
        "dni": "00249887",
        "direccion": "JR. JUNIN N° 240 DPTO 403 MAGDALENA DEL MAR LIMA",
        "correo": "walterapaza@gmx.es",
        "telefono": "953563601",
        "titulo_profesional": "CONTADOR PÚBLICO 29-10-1999",
        "titulo_universidad": "UNIVERSIDAD NACIONAL DE TUMBES",
        "grado_magister": "MAESTRÍA EN CONTABILIDAD Y FINANZAS DIRECCIÓN FINANCIERA 08-02-2013",
        "magister_universidad": "UNIVERSIDAD DE SAN MARTÍN DE PORRES",
        "grado_doctor": "DOCTOR EN CIENCIAS CONTABLES Y FINANCIERAS 04-09-2015",
        "doctor_universidad": "UNIVERSIDAD DE SAN MARTIN DE PORRES",
    },
    {
        "nro": 84,
        "nombre_completo": "DR. ZENON LATORRE VALDEIGLESIAS",
        "especialidad": "CONTADOR PÚBLICO",
        "dni": "23849024",
        "direccion": "CALLE SAPHY N° 851",
        "correo": "zelava@hotmail.com",
        "telefono": "984727017",
        "titulo_profesional": "CONTADOR PUBLICO - ABOGADO 02-06-2005",
        "titulo_universidad": "UNIVERSIDAD NACIONAL SAN ANTONIO ABAD DEL CUSCO - UNIVERSIDAD ANDINA DEL CUSCO",
        "grado_magister": "MAESTRIA EN CONTABILIDAD CON MENCION EN AUDITORIA 29-09-2009",
        "magister_universidad": "UNIVERSIDAD ALAS PERUANAS",
        "grado_doctor": "DOCTOR EN CONTABILIDAD 21-02-2014",
        "doctor_universidad": "UNIVERSIDAD NACIONAL FEDERICO VILLAREAL",
    },
    {
        "nro": 85,
        "nombre_completo": "DR. ZOILO WILFREDO ZAMALLOA MASIAS",
        "especialidad": "LICENCIADO EN MATEMÁTICAS",
        "dni": "23922015",
        "direccion": "URB. VILLA LA RINCONADA LAS ORQUIDEAS Ñ-6 SAN JERONIMO",
        "correo": "zoilozamalloamasias@hotmail.com",
        "telefono": "941727046",
        "titulo_profesional": "LICENCIADO EN FÍSICO MATEMÁTICAS 08-01-1987",
        "titulo_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "grado_magister": "MAESTRÍA EN GESTIÓN AMBIENTAL 17-02-2012",
        "magister_universidad": "UNIVERSIDAD NACIONAL FEDERICO VILLAREAL",
        "grado_doctor": "DOCTOR EN INGENIERÍA AMBIENTAL 26-03-2013",
        "doctor_universidad": "UNIVERSIDAD NACIONAL FEDERICO VILLAREAL",
    },
    {
        "nro": 86,
        "nombre_completo": "DRA. BEATRIZ GUADALUPE CARDENAS DIAZ",
        "especialidad": "ABOGADO",
        "dni": "23921455",
        "direccion": "AV. LA CULTURA N° 2428",
        "correo": "bcardenas@uandina.edu.pe",
        "telefono": "984038894",
        "titulo_profesional": "ABOGADA 07-10-2011",
        "titulo_universidad": "UNIVERSIDAD INCA GARCILASO DE LA VEGA",
        "grado_magister": "MAESTRÍA EN DOCENCIA UNIVERSITARIA 05-11-1992",
        "magister_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "grado_doctor": "DOCTORA EN ADMINISTRACIÓN 11-05-2010",
        "doctor_universidad": "UNIVERSIDAD NACIONAL FEDERICO VILLAREAL",
    },
    {
        "nro": 87,
        "nombre_completo": "DRA. CECILIA JULIA HUAYCOCHEA NUÑEZ DE LA TORRE",
        "especialidad": "ABOGADO",
        "dni": "23929928",
        "direccion": "AV. JORGE CHAVEZ C-3-10 URB TTIO WANCHAQ",
        "correo": "ceciliafis20@hotmail.com",
        "telefono": "984115876",
        "titulo_profesional": "ABOGADA 27-04-1995",
        "titulo_universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        "grado_magister": "MAESTRÍA EN DERECHO MENCIÓN DERECHO CONSTITUCIONAL Y PROCESAL CONSTITUCIONAL 26-01-2017",
        "magister_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "grado_doctor": "DOCTORA EN DERECHO 05-05-2022",
        "doctor_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
    },
    {
        "nro": 88,
        "nombre_completo": "DRA. CRAYLA ALFARO AUCCA",
        "especialidad": "ARQUITECTO",
        "dni": "40767295",
        "direccion": "CONJ. HABITACIONAL PACHACUTEQ P-301",
        "correo": "calfaro@uandina.edu.pe",
        "telefono": "984106323",
        "titulo_profesional": "ARQUITECTA 02-12-2006",
        "titulo_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "grado_magister": "MAESTRÍA EN GESTIÓN DEL PATRIMONIO CULTURAL 29-05-2018",
        "magister_universidad": "UNIVERSIDAD NACIONAL MAYOR DE SAN MARCOS",
        "grado_doctor": "DOCTOR EN CIENCIAS DE LA EDUCACIÓN 12-03-2020",
        "doctor_universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
    },
    {
        "nro": 89,
        "nombre_completo": "DRA. EDDY TELLO YARIN",
        "especialidad": "LICENCIADO EN EDUCACIÓN",
        "dni": "40543399",
        "direccion": "URB. LARAPA H9-2A",
        "correo": "yarinte22@hotmail.com",
        "telefono": "987490612",
        "titulo_profesional": "LICENCIADA EN EDUCACIÓN 10-01-2002",
        "titulo_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "grado_magister": "MAESTRÍA EN LINGÜÍSTICA ANDINA Y EDUCACIÓN 17-04-2019",
        "magister_universidad": "UNIVERSIDAD NACIONAL DEL ALTIPLANO",
        "grado_doctor": "DOCTORA EN EDUCACIÓN 08-05-2023",
        "doctor_universidad": "UNIVERSIDAD CESAR VALLEJO",
    },
    {
        "nro": 90,
        "nombre_completo": "DRA. ESTELA QUISPE RAMOS",
        "especialidad": "CONTADOR PÚBLICO",
        "dni": "25199031",
        "direccion": "URB. SANTA BEATRIZ H-10-B DPTO 601",
        "correo": "esquira6@yahoo.es",
        "telefono": "984015620",
        "titulo_profesional": "CONTADOR PUBLICO 03-03-2003",
        "titulo_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "grado_magister": "MAESTRÍA EN CONTABILIDAD MENCIÓN AUDITORÍA 08-09-2011",
        "magister_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "grado_doctor": "DOCTORA EN CONTABILIDAD 15-03-22",
        "doctor_universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
    },
    {
        "nro": 91,
        "nombre_completo": "DRA. HAYDEE ORTIZ DE ORUE LUCANA",
        "especialidad": "ECONOMISTA",
        "dni": "23835455",
        "direccion": "JR. PANAMA F-5 DPTO 601 URB QUISPICANCHI",
        "correo": "haydeeortizdeorue@gmail.com",
        "telefono": "940157039",
        "titulo_profesional": "ECONOMISTA 01-04-1991",
        "titulo_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "grado_magister": "MAESTRÍA EN ECONOMÍA DEL MEDIO AMBIENTE Y RECURSOS NATURALES 15-03-1997",
        "magister_universidad": "UNIVERSIDAD DE LOS ANDES COLOMBIA",
        "grado_doctor": "DOCTORA EN ECONOMÍA DE LOS RECURSOS NATURALES Y DESARROLLO SUSTENTABLE 23-12-2020",
        "doctor_universidad": "UNIVERSIDAD NACIONAL AGRARIA LA MOLINA",
    },
    {
        "nro": 92,
        "nombre_completo": "DRA. JOSEFINA ARIMATEA GARCIA CRUZ",
        "especialidad": "LICENCIADO EN EDUCACIÓN",
        "dni": "08061348",
        "direccion": "URB. ALPAMAYO AV. EL BANCO MZ. A LOTE 9 ATE",
        "correo": "Josefina5619@gmail.com",
        "telefono": "986108811",
        "titulo_profesional": "LICENCIADA EN EDUCACIÓN 06-03-2002",
        "titulo_universidad": "UNIVERSIDAD PERUANA CAYETANO HEREDIA",
        "grado_magister": "MAESTRÍA EN EDUCACIÓN MENCIÓN EN ADMINISTRACIÓN DE LA EDUCACIÓN UNIVERSITARIA 12-11-2008",
        "magister_universidad": "UNIVERSIDAD NACIONAL MAYOR DE SAN MARCOS",
        "grado_doctor": "DOCTORA EN EDUCACIÓN 13-08-2009",
        "doctor_universidad": "UNIVERSIDAD NACIONAL MAYOR DE SAN MARCOS",
    },
    {
        "nro": 93,
        "nombre_completo": "DRA. JUDITH ELIANA GARAVITO BACA",
        "especialidad": "PSICÓLOGO",
        "dni": "29639134",
        "direccion": "NICOLAS DE PIEROLA IV ETAPA D-203",
        "correo": "jegb1976@hotmail.com",
        "telefono": "958798483",
        "titulo_profesional": "PSICOLOGA 06-07-2001",
        "titulo_universidad": "UNIVERSIDA NACIONAL DE SAN AGUSTÍN",
        "grado_magister": "MAESTRÍA EN CIENCIAS PSICOLOGICA CLINICA, EDUCATIVA, INFANTIL Y ADOLESCENCIAL 19-01-2007",
        "magister_universidad": "UNIVERSIDAD NACIONAL DE SAN AGUSTÍN",
        "grado_doctor": "DOCTORA EN PSICOLOGÍA 13-05-2016",
        "doctor_universidad": "UNIVERSIDAD NACIONAL DE SAN AGUSTIN",
    },
    {
        "nro": 94,
        "nombre_completo": "DRA. KELMA RUTH MAYHUA CURO",
        "especialidad": "CONTADOR PÚBLICO",
        "dni": "80491489",
        "direccion": "PSJE DEMOCRACIA L-2-12 CUSCO",
        "correo": "ruth_mayhua@hotmail.com",
        "telefono": "968293569",
        "titulo_profesional": "CONTADOR PUBLICO 12-06-2000 - ABOGADA 30-04-2008",
        "titulo_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO - UNIVERSIDAD ANDINA DEL CUSCO",
        "grado_magister": "MAESTRÍA EN CONTABILIDAD AUDITORÍA 29-12-2009",
        "magister_universidad": "UNIVERSIDAD ALAS PERUANAS",
        "grado_doctor": "DOCTORA EN CONTABILIDAD",
        "doctor_universidad": "UNIVERSIDAD NACIONAL FEDERICO VILLAREAL",
    },
    {
        "nro": 95,
        "nombre_completo": "DRA. LILIANA CORONADO GAMARRA",
        "especialidad": "ABOGADO",
        "dni": "949754330",
        "direccion": "URB. VILLA DEL SOL A-9 SANTIAGO",
        "correo": "tesis@investigareperu.com",
        "telefono": "949754330",
        "titulo_profesional": "ABOGADA",
        "titulo_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "grado_magister": "MAESTRÍA EN DERECHO CIVIL Y PROCESAL CIVIL 24-04-2017",
        "magister_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "grado_doctor": "DOCTORA EN DERECHO 12-05-2023",
        "doctor_universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
    },
    {
        "nro": 96,
        "nombre_completo": "DRA. LUCILA OLIVARES TORRES",
        "especialidad": "LICENCIADO EN EDUCACIÓN",
        "dni": "23956511",
        "direccion": "URB. LARAPA C3-B6",
        "correo": "lucila.olivares@unsaac.edu.pe",
        "telefono": "932762878",
        "titulo_profesional": "LICENCIADA EN EDUCACIÓN 01-02-1993",
        "titulo_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "grado_magister": "MAESTRÍA EN EDUCACIÓN MENCIÓN EN PLANIFICACIÓN Y ADMINISTRACIÓN EDUCATIVA 19-04-2004",
        "magister_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "grado_doctor": "DOCTORA EN EDUCACIÓN 03-06-2014",
        "doctor_universidad": "UNIVERSIDAD NACIONAL MAYOR DE SAN MARCOS",
    },
    {
        "nro": 97,
        "nombre_completo": "DRA. MONICA TESALIA VALCARCEL BUSTOS",
        "especialidad": "ABOGADO",
        "dni": "23980467",
        "direccion": "AV. BRASIL 3639 MAGDALENA DEL MAR LIMA",
        "correo": "valcarcelabogadosinternacional@gmail.com",
        "telefono": "908968960 - 956520775",
        "titulo_profesional": "ABOGADO 15-04-1999",
        "titulo_universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        "grado_magister": "MAESTRÍA EN GESTIÓN Y POLÍTICAS PÚBLICAS 18-03-2005 - MAESTRÍA EN ABOGACÍA 15-02-2017",
        "magister_universidad": "UNIVERSIDAD DE CHILE - UNIVERSIDAD DEL PAÍS VASCO",
        "grado_doctor": "DOCTORA EN EL PROGRAMA SOCIEDAD DEMOCRATICA, ESTADO Y DERECHO 27-02-2014",
        "doctor_universidad": "UNIVERSIDAD DEL PAÍS VASCO",
    },
    {
        "nro": 98,
        "nombre_completo": "DRA. PAULA PATRICIA LUKSIC GIBAJA",
        "especialidad": "LICENCIADO EN EDUCACIÓN",
        "dni": "23963570",
        "direccion": "URB. SANTA URSULA N-5",
        "correo": "paty421@hotmail.com",
        "telefono": "984688881",
        "titulo_profesional": "LICENCIADA EN EDUCACION 23-11-2005",
        "titulo_universidad": "UNIVERSIDAD CAYETANO HEREDIA",
        "grado_magister": "MAESTRIA EN EDUCACION CON MENCION EN DOCENCIA E INVESTIGACION EN EDUCACION SUPERIOR 24-11-2004",
        "magister_universidad": "UNIVERSIDAD PERUANA CAYETANO HEREDIA",
        "grado_doctor": "DOCTORA EN EDUCACION 17-08-2012",
        "doctor_universidad": "UNIVERSIDAD ANDINA NESTOR CACERES VELASQUEZ DE JULIACA",
    },
    {
        "nro": 99,
        "nombre_completo": "DRA. ROCIO LINEY PEZUA VASQUEZ",
        "especialidad": "PSICÓLOGO",
        "dni": "40110608",
        "direccion": "AV. ARGENTINA CALLE ALTO PERÚ C-8",
        "correo": "lineycita@hotmail.com",
        "telefono": "941619799",
        "titulo_profesional": "PSICÓLOGA 01-09-2006",
        "titulo_universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        "grado_magister": "MAESTRÍA EN ADMINISTRACIÓN 25-11-2015 - MAESTRÍA EN PSICOLOGÍA EDUCATIVA 25-07-2014",
        "magister_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO - UNIVERSIDAD PRIVADA CESAR VALLEJO",
        "grado_doctor": "DOCTORA EN EDUCACIÓN 25-10-2016",
        "doctor_universidad": "UNIVERSIDAD PRIVADA CESAR VALLEJO",
    },
    {
        "nro": 100,
        "nombre_completo": "DRA. SANDRA SOFIA IZQUIERDO MARIN",
        "especialidad": "PSICÓLOGO",
        "dni": "42796297",
        "direccion": "PEDRO MUÑIZ 602-604 URB. SANCHEZ CARRION",
        "correo": "ps.sofiamarin@gmail.com",
        "telefono": "947808353",
        "titulo_profesional": "LICENCIADA EN PSICOLOGÍA 21-10-2008",
        "titulo_universidad": "UNIVERSIDAD PRIVADA CESAR VALLEJO",
        "grado_magister": "MAESTRÍA EN EDUCACIÓN EN DIDÁCTICA DE LA EDUCACIÓN SUPERIOR 14-02-2011",
        "magister_universidad": "UNIVERSIDAD PRIVADA ANTENOR ORREGO",
        "grado_doctor": "DOCTORA EN PSICOLOGIA 18-07-2014",
        "doctor_universidad": "UNIVERSIDAD PRIVADA CESAR VALLEJO",
    },
]


def main() -> None:
    print(f"Usando base de datos: {DOCENTES_DB_PATH}")
    conn = get_connection()
    ensure_schema(conn)

    procesados = 0
    for d in DOCENTES_LOTE_2:
        docente_id = upsert_docente_completo(conn, d)
        print(f"✔ Docente procesado: {d['nombre_completo']} (id={docente_id})")
        procesados += 1

    print(f"\n✅ Lote 2 completado. Docentes procesados: {procesados}")


if __name__ == "__main__":
    main()
