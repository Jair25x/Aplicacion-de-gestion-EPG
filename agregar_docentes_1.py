# -*- coding: utf-8 -*-
"""
agregar_docentes_1.py

Script para agregar/actualizar la primera lista de docentes
en la base de datos docentes.db.

- Usa DOCENTES_DB_PATH si está definido en .env
- Si no, usa ./docentes.db
"""

import os
import sqlite3
from pathlib import Path
from typing import Dict, Optional
from dotenv import load_dotenv

# ============================
# Configuración de ruta DB
# ============================
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

DB_PATH = Path(os.getenv("DOCENTES_DB_PATH", str(BASE_DIR / "docentes.db")))


# ============================
# Helpers
# ============================

def _normalizar_texto(valor: Optional[str]) -> Optional[str]:
    """
    Limpia cadenas vacías o espacios de más.
    Devuelve None si la cadena está vacía.
    """
    if valor is None:
        return None
    v = str(valor).strip()
    return v if v else None


def _es_no_registra_grado(texto: Optional[str]) -> bool:
    if not texto:
        return False
    t = texto.strip().upper()
    return "NO REGISTRA GRADO" in t


def _elegir_mayor_grado(
    titulo_profesional: Optional[str],
    grado_magister: Optional[str],
    grado_doctor: Optional[str],
) -> Optional[str]:
    """
    Para mayor_grado_academico en tabla docente:
    - Prioriza doctorado si existe y no es "NO REGISTRA GRADO..."
    - Si no, magíster (si existe y no es 'NO REGISTRA...')
    - Si no, título profesional.
    """
    if grado_doctor and not _es_no_registra_grado(grado_doctor):
        return grado_doctor
    if grado_magister and not _es_no_registra_grado(grado_magister):
        return grado_magister
    if titulo_profesional:
        return titulo_profesional
    return None


def _upsert_docente(conn: sqlite3.Connection, data: Dict) -> int:
    """
    Inserta o actualiza un docente en la tabla 'docente'.

    Criterio de búsqueda:
    - Primero por DNI (si existe).
    - Si no hay DNI, por nombre_completo.

    Reglas:
    - Si el docente ya existe, solo completa campos que estén NULL
      usando COALESCE(nuevo, existente).
    - Si no existe, lo inserta con los datos que vengan en data.
    """
    nombre_completo = _normalizar_texto(data.get("nombre_completo"))
    dni = _normalizar_texto(data.get("dni"))
    especialidad = _normalizar_texto(data.get("especialidad"))
    direccion = _normalizar_texto(data.get("direccion"))
    correo = _normalizar_texto(data.get("correo"))
    telefono = _normalizar_texto(data.get("telefono"))

    titulo_profesional = _normalizar_texto(data.get("titulo_profesional"))
    titulo_universidad = _normalizar_texto(data.get("titulo_universidad"))

    grado_magister = _normalizar_texto(data.get("grado_magister"))
    magister_universidad = _normalizar_texto(data.get("magister_universidad"))

    grado_doctor = _normalizar_texto(data.get("grado_doctor"))
    doctor_universidad = _normalizar_texto(data.get("doctor_universidad"))

    universidad_procedencia = _normalizar_texto(
        data.get("universidad_procedencia") or titulo_universidad
    )

    mayor_grado_academico = _elegir_mayor_grado(
        titulo_profesional=titulo_profesional,
        grado_magister=grado_magister,
        grado_doctor=grado_doctor,
    )

    # 1) Buscar por DNI (si tenemos)
    row = None
    if dni:
        row = conn.execute(
            "SELECT id FROM docente WHERE dni = ?;",
            (dni,),
        ).fetchone()

    # 2) Si no se encontró por DNI, buscar por nombre_completo
    if not row and nombre_completo:
        row = conn.execute(
            "SELECT id FROM docente WHERE nombre_completo = ?;",
            (nombre_completo,),
        ).fetchone()

    if row:
        docente_id = row[0]
        # Actualizamos solo campos que estén en NULL usando COALESCE
        conn.execute(
            """
            UPDATE docente
            SET
                especialidad          = COALESCE(?, especialidad),
                direccion             = COALESCE(?, direccion),
                correo                = COALESCE(?, correo),
                telefono              = COALESCE(?, telefono),

                titulo_profesional    = COALESCE(?, titulo_profesional),
                titulo_universidad    = COALESCE(?, titulo_universidad),

                grado_magister        = COALESCE(?, grado_magister),
                magister_universidad  = COALESCE(?, magister_universidad),

                grado_doctor          = COALESCE(?, grado_doctor),
                doctor_universidad    = COALESCE(?, doctor_universidad),

                universidad_procedencia = COALESCE(?, universidad_procedencia),
                mayor_grado_academico   = COALESCE(?, mayor_grado_academico)
            WHERE id = ?;
            """,
            (
                especialidad,
                direccion,
                correo,
                telefono,
                titulo_profesional,
                titulo_universidad,
                grado_magister,
                magister_universidad,
                grado_doctor,
                doctor_universidad,
                universidad_procedencia,
                mayor_grado_academico,
                docente_id,
            ),
        )
        return docente_id

    # 3) Insertar nuevo docente
    cursor = conn.execute(
        """
        INSERT INTO docente (
            apellido_paterno,
            apellido_materno,
            nombres,
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
            doctor_universidad,
            universidad_procedencia,
            mayor_grado_academico
        )
        VALUES (
            NULL, NULL, NULL,
            ?, ?, ?, ?, ?, ?,
            ?, ?,
            ?, ?,
            ?, ?,
            ?, ?
        );
        """,
        (
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
            doctor_universidad,
            universidad_procedencia,
            mayor_grado_academico,
        ),
    )
    return cursor.lastrowid


# ============================
# Datos: DOCENTES LOTE 1
# ============================

DOCENTES_DATA_1 = [
    {
        "nombre_completo": "DR. ADOLFO ANTONIO SALOMA GONZALEZ",
        "especialidad": "ARQUITECTO",
        "dni": "23836910",
        "direccion": "LIMACPAMPA GRANDE 505 CUSCO",
        "correo": "salomagonzalez47@hotmail.com",
        "telefono": "984669690",
        "titulo_profesional": "ARQUITECTO 31-03-1976",
        "titulo_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "grado_magister": "MAESTRIA EN CIENCIAS CON MENCION EN PLANIFICACION URBANA Y REGIONAL 30-09-1994",
        "magister_universidad": "UNIVERSIDAD NACIONAL DE INGENIERIA",
        "grado_doctor": "DOCTOR EN MEDIO AMBIENTE Y DESARROLLO SOSTENIBLE 12-07-2012",
        "doctor_universidad": "UNIVERSIDAD NACIONAL FEDERICO VILLAREAL",
        "universidad_procedencia": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
    },
    {
        "nombre_completo": "DR. ALAN ERROL ROZAS FLORES",
        "especialidad": "CONTADOR PÚBLICO",
        "dni": "10557884",
        "direccion": "AV. CAMINOS DEL INCA 1172 SANTIAGO DE SURCO LIMA",
        "correo": "arozas3@hotmail.com",
        "telefono": "971444043",
        "titulo_profesional": "CONTADOR PÚBLICO 20-07-1976",
        "titulo_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "grado_magister": "MAESTRÍA EN CONTABILIDAD MENCIÓN EN AUDITORÍA 06-12-2012",
        "magister_universidad": "UNIVERSIDAD NACIONAL MAYOR DE SAN MARCOS",
        "grado_doctor": "DOCTOR EN CIENCIAS CONTABLES Y EMPRESARIALES 19-09-2013",
        "doctor_universidad": "UNIVERSIDAD NACIONAL MAYOR DE SAN MARCOS",
        "universidad_procedencia": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
    },
    {
        "nombre_completo": "DR. ALAN FELIPE SALAZAR MUJICA",
        "especialidad": "ABOGADO",
        "dni": "41330293",
        "direccion": "URB. MARISCAL GAMARRA A-13 CUSCO",
        "correo": "alansalazarm@gmail.com",
        "telefono": "984930515",
        "titulo_profesional": "ABOGADO 25-08-2008",
        "titulo_universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        "grado_magister": "MAESTRÍA EN DOCENCIA UNIVERSITARIA 11-12-2015",
        "magister_universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        "grado_doctor": "DOCTOR EN DERECHO 22-05-2017",
        "doctor_universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        "universidad_procedencia": "UNIVERSIDAD ANDINA DEL CUSCO",
    },
    {
        "nombre_completo": "DR. ALEJANDRO FELIX VELA QUICO",
        "especialidad": "MÉDICO CIRUJANO",
        "dni": "29394739",
        "direccion": "URB. LA ESTRELLA A-9 DISTRITO JOSE LUIS BUSTAMANTE AREQUIPA",
        "correo": "arcanoale@gmail.com",
        "telefono": "959318454",
        "titulo_profesional": "MEDICO CIRUJANO 28-10-1985 - LICENCIADO EN ANTROPOLOGÍA 07-08-2000",
        "titulo_universidad": "UNIVERSIDAD NACIONAL DE SAN AGUSTÍN - UNIVERSIDAD NACIONAL DE SAN AGUSTÍN",
        "grado_magister": "MAESTRÍA EN SALUD PÚBLICA 26-05-2004",
        "magister_universidad": "UNIVERSIDAD PERUANA CAYETANO HEREDIA",
        "grado_doctor": "DOCTOR EN CIENCIAS MEDICINA 28-10-2005",
        "doctor_universidad": "UNIVERSIDAD NACIONAL DE SAN AGUSTIN",
        "universidad_procedencia": "UNIVERSIDAD NACIONAL DE SAN AGUSTÍN",
    },
    {
        "nombre_completo": "DR. ALEJANDRO MONTESINOS PEREZ",
        "especialidad": "LICENCIADO EN EDUCACIÓN",
        "dni": "23875386",
        "direccion": "AV. JORGE CHAVEZ B-3-13 URB. TTIO WANCHAQ",
        "correo": "alemontepe13@hotmail.com",
        "telefono": "984933362",
        "titulo_profesional": "PROFESOR EN EDUCACIÓN SECUNDARIA COMÚN ESPECIALIDAD FÍSICA Y QUÍMICA 02-05-1967",
        "titulo_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "grado_magister": "MAESTRÍA EN DOCENCIA UNIVERSITARIA 04-09-1992",
        "magister_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "grado_doctor": "DOCTOR EN EDUCACIÓN 22-09-2011",
        "doctor_universidad": "UNIVERSIDAD NACIONAL MAYOR DE SAN MARCOS",
        "universidad_procedencia": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
    },
    {
        "nombre_completo": "DR. ALFREDO PELAYO CALATAYUD MENDOZA",
        "especialidad": "INGENIERO ECONOMISTA",
        "dni": "01297141",
        "direccion": "AV. ALTO ALIANZA N° 1356 PUNO",
        "correo": "alfredopelayo@yahoo.com",
        "telefono": "980274542",
        "titulo_profesional": "INGENIERO ECONOMISTA 03-07-1998",
        "titulo_universidad": "UNIVERSIDAD NACIONAL DEL ALTIPLANO",
        "grado_magister": "MAESTRÍA EN ECONOMÍA 29-03-2006",
        "magister_universidad": "PONTIFICIA UNIVERSIDAD CATOLICA DEL PERU",
        "grado_doctor": "DOCTOR EN CIENCIAS EN ECONOMÍA AGRÍCOLA (Reconocimiento)",
        "doctor_universidad": "UNIVERSIDAD AUTÓNOMA CHAPINGO",
        "universidad_procedencia": "UNIVERSIDAD NACIONAL DEL ALTIPLANO",
    },
    {
        "nombre_completo": "DR. ALFREDO VALENCIA TOLEDO",
        "especialidad": "LICENCIADO EN MATEMÁTICAS",
        "dni": "43162177",
        "direccion": "PJE. PUNTA SAL 256 SAN SEBASTIAN CUSCO",
        "correo": "valenciatoledo@gmail.com",
        "telefono": "984077969",
        "titulo_profesional": "LICENCIADO EN MATEMÁTICA MENCIÓN ESTADÍSTICA 23-07-2009",
        "titulo_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "grado_magister": "MAESTRÍA UNIVERSITARIA EN TÉCNICAS ESTADÍSTICAS (Reconocimineto)",
        "magister_universidad": "UNIVERSIDAD DE SANTIAGO DE COMPOSTELA UNIVERSIDAD DE A CORUÑA Y UNIVERSIDAD DE VIGO",
        "grado_doctor": "DOCTORADO DENTRO DEL PROGRAMA CONJUNTO DE DOCTORADO EN ESTADÍSTICA E INVESTIGACIÓN OPERATIVA (Reconocimiento)",
        "doctor_universidad": "UNIVERSIDAD DE VIGO, UNIVERSIDAD DE SANTIAGO DE COMPOSTELA Y UNIVERSIDAD DE A CORUÑA",
        "universidad_procedencia": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
    },
    {
        "nombre_completo": "DR. ARMANDO LOAIZA MANRIQUE",
        "especialidad": "CONTADOR PÚBLICO",
        "dni": "23876436",
        "direccion": "URB. MATEO PUMACAHUA N° B-2-B",
        "correo": "aloaiza64@hotmail.com",
        "telefono": "984621433",
        "titulo_profesional": "CONTADOR PÚBLICO",
        "titulo_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "grado_magister": "MAESTRÍA EN CONTABILIDAD CON MENCIÓN EN TRIBUTACIÓN 11-04-14",
        "magister_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "grado_doctor": "DOCTOR EN CONTABILIDAD 04-12-14",
        "doctor_universidad": "UNIVERSIDAD NACIONAL FEDERICO VILLAREAL",
        "universidad_procedencia": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
    },
    {
        "nombre_completo": "DR. AUGUSTO MAGNO HUAROMA VASQUEZ",
        "especialidad": "LICENCIADO EN EDUCACIÓN",
        "dni": "32983025",
        "direccion": "URB. NICOLAS GARATEA 101-39 NUEVO CHIMBOTE",
        "correo": "huaromavasquezaugusto@gmail.com",
        "telefono": "920709569",
        "titulo_profesional": "LICENCIADO EN EDUCACIÓN PRIMARIA 20-12-1996",
        "titulo_universidad": "UNIVERSIDAD PRIVADA DE SAN PEDRO",
        "grado_magister": "MAESTRÍA EN EDUCACIÓN DOCENCIA Y GESTIÓN EDUCATIVA 27-10-2009 - MAESTRÍA EN DERECHO PENAL Y PROCESARL PENAL 25-10-2010",
        "magister_universidad": "UNIVERSIDAD PRIVADA CESAR VALLEJO - UNIVERSIDAD CATÓLICA LOS ÁNGELES DE CHIMBOTE",
        "grado_doctor": "DOCTOR EN DERECHO 18-02-2016",
        "doctor_universidad": "UNIVERSIDAD SAN PEDRO",
        "universidad_procedencia": "UNIVERSIDAD PRIVADA DE SAN PEDRO",
    },
    {
        "nombre_completo": "DR. BENJAMIN JOSE DAVILA FLORES",
        "especialidad": "BIÓLOGO",
        "dni": "29262116",
        "direccion": "AV. AREQUIPA 405 AREQUIPA",
        "correo": "jodavi56@gmail.com",
        "telefono": "959773717",
        "titulo_profesional": "BIOLOGO 08-12-1980",
        "titulo_universidad": "UNIVERSIDAD NACIONAL DE SAN AGUSTIN",
        "grado_magister": "MAESTRÍA EN ECOLOGÍA Y DESARROLLO AMBIENTAL 20-07-2000",
        "magister_universidad": "UNIVERSIDAD CATOLICA DE SANTA MARIA",
        "grado_doctor": "DOCTOR EN CIENCIAS Y TECNOLOGIAS MEDIOAMBIENTALES 08-05-2015",
        "doctor_universidad": "UNIVERSIDAD NACIONAL DE SAN AGUSTIN",
        "universidad_procedencia": "UNIVERSIDAD NACIONAL DE SAN AGUSTIN",
    },
    {
        "nombre_completo": "DR. BREDMAN EUSEBIO ARTEAGA ROJAS",
        "especialidad": "PSICÓLOGO",
        "dni": "07637359",
        "direccion": None,
        "correo": "psiclifor10@gmail.com",
        "telefono": "985245487",
        "titulo_profesional": "LICENCIADO EN PSICOLOGÍA 03-08-2009",
        "titulo_universidad": "UNIVERSIDAD SAN PEDRO",
        "grado_magister": "MAESTRÍA EN CRIMINALISTICA 27-05-2015",
        "magister_universidad": "UNIVERSIDAD NACIONAL FEDERICO VILLAREAL",
        "grado_doctor": "DOCTOR EN PSICOLOGIA 21-06-2021",
        "doctor_universidad": "UNIVERSIDAD PRIVADA CESAR VALLEJO",
        "universidad_procedencia": "UNIVERSIDAD SAN PEDRO",
    },
    {
        "nombre_completo": "DR. CARLOS ALBERTO PASTOR CARRASCO",
        "especialidad": "CONTADOR PÚBLICO",
        "dni": "06996479",
        "direccion": "AV. JOSÉ  A SUCRE 1180 DPTO 504 PUEBLO LIBRE LIMA",
        "correo": "cpastorc@gmail.com",
        "telefono": "951614020",
        "titulo_profesional": "CONTADOR PÚBLICO 12-10-1979",
        "titulo_universidad": "UNIVERSIDAD NACIONAL MAYOR DE SAN MARCOS",
        "grado_magister": "MAESTRÍA EN INGENIERÍA DE SISTEMAS E INFORMÁTICA MENCIÓN EN DIRECCIÓN Y GESTIÓN DE TECNOLOGÍA DE INFORMACIÓN 08-06-2011",
        "magister_universidad": "UNIVERSIDAD NACIONAL MAYOR DE SAN MARCOS",
        "grado_doctor": "DOCTOR EN CIENCIAS CONTABLES Y EMPRESARIALES 06-05-2013",
        "doctor_universidad": "UNIVERSIDAD NACIONAL MAYOR DE SAN MARCOS",
        "universidad_procedencia": "UNIVERSIDAD NACIONAL MAYOR DE SAN MARCOS",
    },
    {
        "nombre_completo": "DR. CARLOS EDWIN ROJAS SALDIVAR",
        "especialidad": "CONTADOR PÚBLICO",
        "dni": "01317302",
        "direccion": "CALLE ATAHUALPA 558 DPTO. 402 MIRAFLORES LIMA",
        "correo": "crojassaldivar@gmail.com",
        "telefono": "984760096 - 966810666",
        "titulo_profesional": "CONTADOR PUBLICO 03-06-1994 INGENIERO ECONOMISTA 20-10-2000",
        "titulo_universidad": "UNIVERSIDAD NACIONAL DEL ALTIPLANO - UNIVERSIDAD NACIONAL DEL ALTIPLANO",
        "grado_magister": "MAESTRÍA EN CONTABILIDAD MENCIÓN EN AUDITORÍA 03-03-2008",
        "magister_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "grado_doctor": "DOCTOR EN CONTABILIDAD 29-04-2014",
        "doctor_universidad": "UNIVERSIDAD NACIONAL FEDERICO VILLAREAL",
        "universidad_procedencia": "UNIVERSIDAD NACIONAL DEL ALTIPLANO",
    },
    {
        "nombre_completo": "DR. CARLOS HERACLIDES PAJUELO CAMONES",
        "especialidad": "LICENCIADO EN COOPERATIVISMO",
        "dni": "32117673",
        "direccion": "CALLE CLAUDE MONET MZ. D LT. 5 ALAMOS DE MONTERRICO",
        "correo": "cccpajuelo@gmail.com",
        "telefono": "998676425",
        "titulo_profesional": "LICENCIADO EN COOPERATIVISMO 30-10-1984",
        "titulo_universidad": "UNIVERSIDAD NACIONAL FEDERICO VILLAREAL",
        "grado_magister": "MAESTRÍA EN ADMINISTRACIÓN 04-09-2012",
        "magister_universidad": "UNIVERSIDAD NACIONAL FEDERICO VILLAREAL",
        "grado_doctor": "DOCTOR EN ADMINISTRACIÓN 26-03-2014",
        "doctor_universidad": "UNIVERSIDAD NACIONAL FEDERICO VILLAREAL",
        "universidad_procedencia": "UNIVERSIDAD NACIONAL FEDERICO VILLAREAL",
    },
    {
        "nombre_completo": "DR. CARLOS RAMON PONCE DIAZ",
        "especialidad": "PSICÓLOGO",
        "dni": "07827740",
        "direccion": "AV. MARISCAL LA MAR 1144 URB SANTA CRUZ MIRAFLORES",
        "correo": "cponcediaz@hotmail.com",
        "telefono": "975307418",
        "titulo_profesional": "PSICÓLOGO 05-07-1973",
        "titulo_universidad": "UNIVERSIDAD NACIONAL MAYOR DE SAN MARCOS",
        "grado_magister": "NO REGISTRA GRADO EN SUNEDU",
        "magister_universidad": "NO REGISTRA GRADO EN SUNEDU",
        "grado_doctor": "DOCTOR EN LETRAS ESPECIALIDAD PSICOLOGÍA 24-10-1988",
        "doctor_universidad": "UNIVERSIDAD NACIONAL MAYOR DE SAN MARCOS",
        "universidad_procedencia": "UNIVERSIDAD NACIONAL MAYOR DE SAN MARCOS",
    },
    {
        "nombre_completo": "DR. CARLOS SAMUEL RAMOS MEZA",
        "especialidad": "CIRUJANO DENTISTA",
        "dni": "42760429",
        "direccion": "AV. SUCRE K-6-A APART. 801 URB. HUANCARO",
        "correo": "cramosm@uandina.edu.pe",
        "telefono": "984765986",
        "titulo_profesional": "CIRUJANO DENTISTA 23-12-2021",
        "titulo_universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        "grado_magister": "MAESTRÍA EN ADMINISTRACIÓN ESTRATÉGICA DE EMPRESAS 06-08-2014",
        "magister_universidad": "PONTIFICIA UNIVERSIDAD CATÓLICA DEL PERÚ",
        "grado_doctor": "DOCTOR EN CIENCIAS DE LA EDUCACIÓN 22-06-2022",
        "doctor_universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        "universidad_procedencia": "UNIVERSIDAD ANDINA DEL CUSCO",
    },
    {
        "nombre_completo": "DR. CESAR ALFONSO LIP LICHAM",
        "especialidad": "MÉDICO CIRUJANO",
        "dni": "08142951",
        "direccion": "AV. JOSE ANTONIO SUCRE 1334 DPTO 207",
        "correo": "cesar.lip@upch.pe",
        "telefono": "994832928",
        "titulo_profesional": "MEDICO CIRUJANO 27-04-1977",
        "titulo_universidad": "UNIVERSIDAD PERUANA CAYETANO HEREDIA",
        "grado_magister": "MAESTRÍA EN ADMINISTRACIÓN DE SALUD 05-03-1997 - MAESTRÍA EN MEDICINA 28-08-1985",
        "magister_universidad": "UNIVERSIDAD PERUANA CAYETANO HEREDIA - UNIVERSIDAD PERUANA CAYETANO HEREDIA",
        "grado_doctor": "DOCTOR EN MEDICINA 31-10-1990",
        "doctor_universidad": "UNIVERSIDAD PERUANA CAYETANO HEREDIA",
        "universidad_procedencia": "UNIVERSIDAD PERUANA CAYETANO HEREDIA",
    },
    {
        "nombre_completo": "DR. CESAR VLADIMIR MUNAYCO ESCATE",
        "especialidad": "MÉDICO CIRUJANO",
        "dni": "21544362",
        "direccion": "CALLE SATURNO 117, Mz P LOTE 1 URB EL OLIMPO ATE VITARTE",
        "correo": "cvmunayco@gmail.com",
        "telefono": "982508166",
        "titulo_profesional": "MEDICO CIRUJANO 05-04-2001",
        "titulo_universidad": "UNIVERSIDAD NACIONAL SAN LUIS GONZAGA",
        "grado_magister": "MAESTRÍA EN EPIDEMIOLOGÍA 16-07-2007",
        "magister_universidad": "UNIVERSIDAD NACIONAL MAYOR DE SAN MARCOS",
        "grado_doctor": "DOCTOR EN SALUD PÚBLICA 25-05-2016",
        "doctor_universidad": "UNIFORMED SERVICES UNIVERSITY OF THE HEALTH SCIENCES (Reconocimiento)",
        "universidad_procedencia": "UNIVERSIDAD NACIONAL SAN LUIS GONZAGA",
    },
    {
        "nombre_completo": "DR. CHARLIE CARRASCO SALAZAR",
        "especialidad": "ABOGADO",
        "dni": "40799023",
        "direccion": "CALLE 1 N° 110 EDF 17 DPTO 303 EL RIMAC LIMA",
        "correo": "charliecarrascosalazar1@gmail.com",
        "telefono": "993672655 - 953564557",
        "titulo_profesional": "ABOGADO 10-02-2009",
        "titulo_universidad": "UNIVERSIDAD TECNOLÓGICA DE LOS ANDES",
        "grado_magister": "MAESTRÍA EN DERECHO CONSTITUCIONAL 08-06-2011",
        "magister_universidad": "UNIVERSIDAD NACIONAL FEDERICO VILLAREAL",
        "grado_doctor": "DOCTOR EN DERECHO 13-06-2012",
        "doctor_universidad": "UNIVERSIDAD NACIONAL FEDERICO VILLAREAL",
        "universidad_procedencia": "UNIVERSIDAD TECNOLÓGICA DE LOS ANDES",
    },
    {
        "nombre_completo": "DR. CHRISTIAN RICHARD MEJIA ALVAREZ",
        "especialidad": "MÉDICO CIRUJANO",
        "dni": "42339113",
        "direccion": "AV. LAS PALMERAS 5713 LOS OLIVOS LIMA PERU",
        "correo": "christian.mejia.md@gmail.com",
        "telefono": "997643516",
        "titulo_profesional": "MEDICO CIRUJANO 31-03-2010",
        "titulo_universidad": "UNIVERSIDAD RICARDO PALMA",
        "grado_magister": "MAESTRÍA EN SALUD OCUPACIONAL CON MENCIÓN EN MEDICINA OCUPACIONAL Y DEL MEDIO AMBIENTE 31-08-2015",
        "magister_universidad": "UNIVERSIDAD CIENTÍFICA DEL SUR S.A.C",
        "grado_doctor": "DOCTOR EN INVESTIGACIÓN CLÍNICA Y TRANSLACIONAL 28-11-2018",
        "doctor_universidad": "UNIVERSIDAD PRIVADA ANTENOR ORREGO",
        "universidad_procedencia": "UNIVERSIDAD RICARDO PALMA",
    },
    {
        "nombre_completo": "DR. CLETO DE LA TORRE DUEÑAS",
        "especialidad": "LICENCIADO EN MATEMÁTICAS",
        "dni": "23988416",
        "direccion": "URB. ACCION POPULAR J-2 SAN SEBASTIAN",
        "correo": "cletounsaac@gmail.com",
        "telefono": "984733980",
        "titulo_profesional": "LICENCIADO EN FISICO-MATEMATICAS 03-06-1998",
        "titulo_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "grado_magister": "MAESTRIA EN ESTADISTICA 29-08-2007",
        "magister_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "grado_doctor": "DOCTOR EN CIENCIAS CON MENCION EN ECONOMIA Y GESTION 17-06-2011",
        "doctor_universidad": "UNIVERSIDAD NACIONAL SAN AGUSTIN DE AREQUIPA",
        "universidad_procedencia": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
    },
    {
        "nombre_completo": "DR. DARWIN EFRAIN PAYNE MORA",
        "especialidad": "LICENCIADO EN EDUCACIÓN",
        "dni": "23926248",
        "direccion": "CALLE MARISCAL GAMARRA 920 URB FIDERANDA WANCHAQ",
        "correo": "darwinpm@gmail.com",
        "telefono": "984689038",
        "titulo_profesional": "LICENCIADO EN EDUCACIÓN 07-12-1992",
        "titulo_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "grado_magister": "MAESTRÍA EN EDUCACIÓN ESPECIALIDAD MENCIÓN EN PLANIFICACIÓN Y ADMINISTRACIÓN EDUCATIVA 02-06-2008",
        "magister_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "grado_doctor": "DOCTOR EN GESTIÓN Y CIENCIAS DE LA EDUCACIÓN",
        "doctor_universidad": "UNIVERSIDAD SAN PEDRO",
        "universidad_procedencia": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
    },
    {
        "nombre_completo": "DR. DEYVIS ROBINSON VILLA PALOMINO",
        "especialidad": "CIRUJANO DENTISTA",
        "dni": "40507551",
        "direccion": "AV. ALEMANIA FEDERAL I-3",
        "correo": "deyvisvilla@hotmail.com",
        "telefono": "984316198",
        "titulo_profesional": "CIRUJANO DENTISTA 27-05-2004",
        "titulo_universidad": "UNIVERSIDA ANDINA DEL CUSCO",
        "grado_magister": "MAESTRÍA EN POLÍTICAS Y GESTIÓN EN SALUD 03-07-2012",
        "magister_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "grado_doctor": "DOCTOR EN CIENCIAS DE LA EDUCACIÓN 16-06-2017",
        "doctor_universidad": "UNIVERSIDA ANDINA DEL CUSCO",
        "universidad_procedencia": "UNIVERSIDA ANDINA DEL CUSCO",
    },
    {
        "nombre_completo": "DR. EDER ARTURO ACO CORRALES",
        "especialidad": "LICENCIADO EN MATEMÁTICAS",
        "dni": "42495820",
        "direccion": "URB. SAN JOSE II ETAPA MZ H LT12",
        "correo": "eaco@uandima.edu.pe",
        "telefono": "984730536",
        "titulo_profesional": "LICENCIADO EN MATEMÁTICA Y FÍSICA 27-12-2012",
        "titulo_universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        "grado_magister": "MAESTRÍA EN DOCENCIA UNIVERSITARIA 04-07-2016",
        "magister_universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        "grado_doctor": "DOCTOR EN CIENCIAS DE LA EDUCACIÓN 15-10-2018",
        "doctor_universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        "universidad_procedencia": "UNIVERSIDAD ANDINA DEL CUSCO",
    },
    {
        "nombre_completo": "DR. EDWARDS JESUS AGUIRRE ESPINOZA",
        "especialidad": "LICENCIADO EN EDUCACIÓN",
        "dni": "23854868",
        "direccion": "AV. DINAMARCA A-25 SAN SEBASTIAN",
        "correo": "edwaguiespi@gmail.com",
        "telefono": "973247569",
        "titulo_profesional": "LICENCIADO EN EDUCACION 17-11-1992",
        "titulo_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "grado_magister": "MAESTRIA EN DOCENCIA UNIVERSITARIA 25-02-2009 - MAESTRIA EN GESTION DE LA EDUCACION 29-05-2009 - MAESTRIA EN GESTIÓN PÚBLICA 13-09-2016",
        "magister_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO - UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO - UNIVERSIDAD PRIVADA CESAR VALLEJO",
        "grado_doctor": "DOCTOR EN EDUCACION 03-06-2011",
        "doctor_universidad": "UNIVERSIDAD NESTOR CACERES VELASQUEZ",
        "universidad_procedencia": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
    },
    {
        "nombre_completo": "DR. EDWIN ASTETE SAMANEZ",
        "especialidad": "INGENIERO CIVIL",
        "dni": "25222417",
        "direccion": "CALLE GARCILASO N 309",
        "correo": "edwinastetesamanezz@gmail.com",
        "telefono": "946347988",
        "titulo_profesional": "INGENIERO CIVIL 13-03-2003",
        "titulo_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "grado_magister": "MAESTRIA EN INGENIERIA CIVIL MENCION RECURSOS HIDRICOS Y MEDIO AMBIENTE 03-06-2015",
        "magister_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "grado_doctor": "DOCTOR EN ADMINISTRACIÓN 19-12-2019",
        "doctor_universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        "universidad_procedencia": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
    },
    {
        "nombre_completo": "DR. EDWIN FREDY BOCARDO DELGADO",
        "especialidad": "BIÓLOGO",
        "dni": "29227646",
        "direccion": "AV. GUARDIA CIVIL F-5 PAUCARPATA AREQUIPA",
        "correo": "ebocardo@hotmail.com",
        "telefono": "959624111",
        "titulo_profesional": "BIÓLOGO 08-01-1993",
        "titulo_universidad": "UNIVERSIDAD NACIONAL DE SAN AGUSTIN",
        "grado_magister": "MAESTRÍA EN ECOLOGÍA Y DESARROLLO AMBIENTAL 12-08-2002",
        "magister_universidad": "UNIVERSIDAD CATÓLICA DE SANTA MARÍA",
        "grado_doctor": "DOCTOR EN CIENCIAS Y TECNOLOGIAS MEDIOAMBIENTALES 24-07-2009",
        "doctor_universidad": "UNIVERSIDAD NACIONAL DE SAN AGUSTIN",
        "universidad_procedencia": "UNIVERSIDAD NACIONAL DE SAN AGUSTIN",
    },
    {
        "nombre_completo": "DR. ELBERTH HERNAN SAMALVIDES MARQUEZ",
        "especialidad": "CONTADOR PÚBLICO",
        "dni": "30402488",
        "direccion": "URB. CAMPO VERDE MZ. E LT. 6",
        "correo": "esamalvides@ucsm.edu.pe",
        "telefono": "959297098",
        "titulo_profesional": "CONTADOR PÚBLICO 04-12-1992 - INGENIERO EN ADMINISTRACIÓN DE EMPRESAS (Reconocimiento)",
        "titulo_universidad": "UNIVERSIDAD NACIONAL JORGE BASADRE GROHMANN - UNIVERSIDAD DE TARAPACÁ",
        "grado_magister": "MAESTRÍA EN ADMINISTRACIÓN Y DIRECCIÓN DE EMPRESAS 10-05-1999",
        "magister_universidad": "UNIVERSIDAD PRIVADA DE TACNA",
        "grado_doctor": "DOCTOR EN ADMINISTRACIÓN 22-02-2017",
        "doctor_universidad": "UNIVERSIDAD PRIVADA DE TACNA",
        "universidad_procedencia": "UNIVERSIDAD NACIONAL JORGE BASADRE GROHMANN",
    },
    {
        "nombre_completo": "DR. ELIAS MELENDREZ VELASCO",
        "especialidad": "LICENCIADO EN EDUCACIÓN",
        "dni": "23863492",
        "direccion": "LOS SAUCES B-20",
        "correo": "elmeve01@hotmail.com",
        "telefono": "984624115",
        "titulo_profesional": "LICENCIADO EN EDUCACION 26-05-1994",
        "titulo_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "grado_magister": "MAESTRIA EN DOCENCIA E INVESTIGACION EN EDUCACION SUPERIOR 29-10-2008",
        "magister_universidad": "UNIVERSIDAD PERUANA CAYETANO HEREDIA",
        "grado_doctor": "DOCTOR EN ADMINISTRACION DE LA EDUCACION 15-11-2013",
        "doctor_universidad": "UNIVERSIDAD CESAR VALLEJO",
        "universidad_procedencia": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
    },
    {
        "nombre_completo": "DR. ELIOT PEZO ZEGARRA",
        "especialidad": "INGENIERO CIVIL",
        "dni": "24006901",
        "direccion": "PSJ BARRIO DE DIOS G-5",
        "correo": "eliotpz@gmail.com",
        "telefono": "984002949",
        "titulo_profesional": "INGENIERO CIVIL 26-10-2006",
        "titulo_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "grado_magister": "MAESTRÍA EN INGENIERÍA CIVIL 03-09-2012",
        "magister_universidad": "PONTIFICIA UNIVERSIDAD CATÓLICA DE RIO DE JANEIRO",
        "grado_doctor": "DOCTOR EN INGENIERÍA CIVIL 19-06-2017",
        "doctor_universidad": "PONTIFICIA UNIVERSIDAD CATÓLICA DE RIO DE JANEIRO",
        "universidad_procedencia": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
    },
    {
        "nombre_completo": "DR. ELVIS YURI MAMANI VARGAS",
        "especialidad": "INGENIERO CIVIL",
        "dni": "41610570",
        "direccion": "URB. TUPAC AMARU G-12 SAN SEBASTIAN",
        "correo": "emamaniv@gmail.com",
        "telefono": "965437368",
        "titulo_profesional": "INGENIERO CIVIL 12-07-2006",
        "titulo_universidad": "UNIVERSIDAD NACIONAL PEDRO RUIZ GALLO",
        "grado_magister": "MAESTRÍA EN INGENIERÍA CIVIL (Reconocimiento)",
        "magister_universidad": "PONTIFICIA UNIVERSIDAD CATÓLICA DE RIO DE JANEIRO",
        "grado_doctor": "DOCTOR EN INGENIERÍA CIVIL (Reconocimiento)",
        "doctor_universidad": "PONTIFICIA UNIVERSIDAD CATÓLICA DE RIO DE JANEIRO",
        "universidad_procedencia": "UNIVERSIDAD NACIONAL PEDRO RUIZ GALLO",
    },
    {
        "nombre_completo": "DR. EMER RONALD ROSALES SOLORZANO",
        "especialidad": "INGENIERO FORESTAL",
        "dni": "20083657",
        "direccion": "JR. MARACANA MZ A LT 17 PUERTO MALDONADO MDD",
        "correo": "errs1973@gmail.com",
        "telefono": "959189276",
        "titulo_profesional": "INGENIERO FORESTAL 23-12-1998",
        "titulo_universidad": "UNIVERSIDAD NACIONAL DEL CENTRO DEL PERÚ",
        "grado_magister": "MAESTRÍA EN GESTIÓN Y AUDITORÍAS AMBIENTALES 28-11-2008",
        "magister_universidad": "UNIVERSIDAD DE PIURA",
        "grado_doctor": "DOCTOR EN MEDIO AMBIENTE Y DESARROLLO SOSTENIBLE 30-04-2015",
        "doctor_universidad": "UNIVERSIDAD NACIONAL FEDERICO VILLAREAL",
        "universidad_procedencia": "UNIVERSIDAD NACIONAL DEL CENTRO DEL PERÚ",
    },
    {
        "nombre_completo": "DR. ERICSON DELGADO OTAZU",
        "especialidad": "ABOGADO",
        "dni": "41523532",
        "direccion": "CH PACHACUTEC G-105 WANCHAQ",
        "correo": "ericsondo@gmail.com",
        "telefono": "984755288",
        "titulo_profesional": "ABOGADO 23-03-2006 - LICENCIADO EN EDUCACIÓN SECUNDARIA ESPECIALIDAD DE HISTORIA, GEOGRAFÍA Y CIENCIAS 05-01-2012",
        "titulo_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO - UNIVERSIDAD SAN PEDRO",
        "grado_magister": "MAESTRÍA EN DERECHO CIVIL Y PROCESAL PENAL 23-03-2012",
        "magister_universidad": "UNIVERSIDAD ALAS PERUANAS S.A.",
        "grado_doctor": "DOCTOR EN DERECHO 25-11-2019",
        "doctor_universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        "universidad_procedencia": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
    },
    {
        "nombre_completo": "DR. ERNESTO LUCANO CRISOSTOMO",
        "especialidad": "PSICÓLOGO",
        "dni": "08065798",
        "direccion": "AV. A. VELASCO ASTETE # 111 - REC. LOS OLIVOS- CHALET B-5",
        "correo": "lucano1819@hotmail.com",
        "telefono": "984766258",
        "titulo_profesional": "LICENCIADO EN PSICOLOGÍA 09-04-1987",
        "titulo_universidad": "UNIVERSIDAD DE SAN MARTIN DE PORRES",
        "grado_magister": "MAESTRÍA EN CIENCIAS DE LA EDUCACIÓN MENCIÓN EN INVESTIGACIÓN Y DOCENCIA 31-08-2011",
        "magister_universidad": "UNIVERSIDAD NACIONAL PEDRO RUIZ GALLO",
        "grado_doctor": "DOCTOR EN CIENCIAS DE LA EDUCACIÓN 07-06-2016",
        "doctor_universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        "universidad_procedencia": "UNIVERSIDAD DE SAN MARTIN DE PORRES",
    },
    {
        "nombre_completo": "DR. EVANDRO ESTEBAN PANDIA CAYRO",
        "especialidad": "INGENIERO CIVIL",
        "dni": "44869314",
        "direccion": "PSJE. ANDRES AVELINO CACERES G32 JULIACA",
        "correo": "epandiac@uni.pe",
        "telefono": "913985342",
        "titulo_profesional": "INGENIERO CIVIL 25-07-2014",
        "titulo_universidad": "UNIVERSIDAD NACIONAL DE INGENIERÍA",
        "grado_magister": "MAESTRÍA EN INGENIERÍA ESPECIALIZACIÓN ESTRUCTURAS 01-07-2016",
        "magister_universidad": "UNIVERSIDADE FEDERAL DO RIO GRANDE DO SUL",
        "grado_doctor": "DOCTOR EN INGENIERÍA ESPECIALIZACIÓN ESTRUCTURAS 20-05-2021",
        "doctor_universidad": "UNIVERSIDADE FEDERAL DO RIO GRANDE DO SUL",
        "universidad_procedencia": "UNIVERSIDAD NACIONAL DE INGENIERÍA",
    },
    {
        "nombre_completo": "DR. FELIO CALDERON LA TORRE",
        "especialidad": "INGENIERO AGRÓNOMO",
        "dni": "25310696",
        "direccion": "URB. LARAPA D-2-12 SAN JERÓNIMO",
        "correo": "felioca@hotmail.com",
        "telefono": "955908241",
        "titulo_profesional": "INGENIERO AGRÓNOMO 30-12-1980",
        "titulo_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "grado_magister": "MAESTRÍA EN DESARROLLO RURAL 11-09-17",
        "magister_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "grado_doctor": "DOCTOR EN MEDIO AMBIENTE Y DESARROLLO SOSTENIBLE 28-11-2011",
        "doctor_universidad": "UNIVERSIDAD NACIONAL FEDERICO VILLAREAL",
        "universidad_procedencia": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
    },
    {
        "nombre_completo": "DR. FELIPE SANTIAGO LAQUIHUANACO LOZA",
        "especialidad": "CIRUJANO DENTISTA",
        "dni": "23951536",
        "direccion": "URB. LARAPA GRANDE C-8-1A SAN JERÓNIMO",
        "correo": "felipesanlalo@gmail.com",
        "telefono": "984740752",
        "titulo_profesional": "CIRUJANO DENTISTA 03-12-1979",
        "titulo_universidad": "UNIVERIDAD CATÓLICA DE SANTA MARÍA",
        "grado_magister": "MAESTRÍA EN POLÍTICA Y GESTIÓN EN SALUD 01-04-2009",
        "magister_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "grado_doctor": "DOCTOR EN CIENCIAS SALUD PÚBLICA 14-11-2014",
        "doctor_universidad": "UNIVERSIDAD NACIONAL DE SAN AGUSTIN",
        "universidad_procedencia": "UNIVERIDAD CATÓLICA DE SANTA MARÍA",
    },
    {
        "nombre_completo": "DR. GARETH DEL CASTILLO ESTRADA",
        "especialidad": "PSICÓLOGO",
        "dni": "41884386",
        "direccion": "URB. MANUEL PRADO M-1",
        "correo": "gdelcastillo@uandina.edu.pe",
        "telefono": "986230081",
        "titulo_profesional": "PSICOLOGO 04-10-2007",
        "titulo_universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        "grado_magister": "MAESTRÍA EN PSICOLOGÍA 07-02-2014 - MAESTRÍA EN ADMINISTRACIÓN 04-12-2013",
        "magister_universidad": "UNIVERSIDAD DE SAN MARTÍN DE PORRES - UNIVERSIDAD ESAN",
        "grado_doctor": "DOCTOR EN CIENCIAS DE LA EDUCACIÓN 28-12-2018",
        "doctor_universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        "universidad_procedencia": "UNIVERSIDAD ANDINA DEL CUSCO",
    },
    {
        "nombre_completo": "DR. HERBERT COSIO DUEÑAS",
        "especialidad": "CIRUJANO DENTISTA",
        "dni": "29663764",
        "direccion": "AV. TOMASA TTITO CONDEMAYTA 1432 WANCHAQ CUSCO",
        "correo": "hcosiod@hotmail.com",
        "telefono": "974216181",
        "titulo_profesional": "CIRUJANO DENTISTA 30-12-1998",
        "titulo_universidad": "UNIVERSIDAD CATÓLICA DE SANTA MARÍA",
        "grado_magister": "MAESTRÍA EN ESTOMATOLOGÍA 22-11-2006",
        "magister_universidad": "UNIVERSIDAD PERUANA CAYETANO HEREDIA",
        "grado_doctor": "DOCTOR EN EDUCACIÓN 06-04-2016",
        "doctor_universidad": "UNIVERSIDAD CATÓLICA DE SANTA MARÍA",
        "universidad_procedencia": "UNIVERSIDAD CATÓLICA DE SANTA MARÍA",
    },
    {
        "nombre_completo": "DR. HUGO BENITO CANAHUA LOZA",
        "especialidad": "INGENIERO METALURGISTA",
        "dni": "00419817",
        "direccion": "AV. INDEPENDENCIA S/N CERCADO AREQUIPA",
        "correo": "hcanahua@unsa.edu.pe",
        "telefono": "959436185",
        "titulo_profesional": "INGENIERO METALURGISTA 06-06-1988",
        "titulo_universidad": "UNIVERSIDAD NACIONAL JORGE BASADRE GROHMANN",
        "grado_magister": "NO REGISTRA GRADO EN SUNEDU",
        "magister_universidad": "NO REGISTRA GRADO EN SUNEDU",
        "grado_doctor": "DOCTOR EN INGENIERÍA INDUSTRIAL (Reconocimiento)",
        "doctor_universidad": "UNIVERSIDAD POLITÉCNICA DE MADRID",
        "universidad_procedencia": "UNIVERSIDAD NACIONAL JORGE BASADRE GROHMANN",
    },
    {
        "nombre_completo": "DR. ISAAC ENRIQUE CASTRO CUBA BARINEZA",
        "especialidad": "ABOGADO",
        "dni": "10281126",
        "direccion": "URB. LARAPA F-4-8 SAN JERONIMO",
        "correo": "ecastro_cuba@yahoo.com",
        "telefono": "985902125",
        "titulo_profesional": "INGENIERO METALURGISTA 09-01-1998 - ABOGADO 24-04-1998 - LICENCIADO EN EDUCACIÓN 13-02-2004",
        "titulo_universidad": "UNIVERSIDAD NACIONAL SAN AGUSTIN - UNIVERSIDAD NACIONAL SAN AGUSTIN",
        "grado_magister": "MAESTRIA EN EDUCACIÓN 26-06-1997",
        "magister_universidad": "UNIVERSIDAD PARTICULAR SAN MARTIN DE PORRAS",
        "grado_doctor": "DOCTOR EN EDUCACION 22-05-2001",
        "doctor_universidad": "UNIVERSIDAD PARTICULAR SAN MARTIN DE PORRAS",
        "universidad_procedencia": "UNIVERSIDAD NACIONAL SAN AGUSTIN",
    },
    {
        "nombre_completo": "DR. JAIME ZARATE DALENS",
        "especialidad": "INGENIERO QUÍMICO",
        "dni": "23903060",
        "direccion": "AV. UZATEGUI F 7",
        "correo": "jaimemaster52@hotmail.com",
        "telefono": "927798952",
        "titulo_profesional": "INGENIERO QUIMICO 10-04-1979",
        "titulo_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "grado_magister": "MAESTRÍA EN MATEMÁTICAS 18-02-1998 - MAESTRÍA EN ESTADÍSTICA 04-11-2015",
        "magister_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO - UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "grado_doctor": "DOCTOR EN GESTIÓN Y CIENCIAS DE LA EDUCACIÓN 04-09-2013",
        "doctor_universidad": "UNIVERSIDAD SAN PEDRO",
        "universidad_procedencia": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
    },
    {
        "nombre_completo": "DR. JESUS ABEL MEJIA MARCACUZCO",
        "especialidad": "INGENIERO AGRÍCOLA",
        "dni": "06443739",
        "direccion": "MZ A1 LT 2 ASOC VIV LOS INCAS CHORRILLOS  LIMA",
        "correo": "jabel@lamolina.edu.pe",
        "telefono": "954461640",
        "titulo_profesional": "INGENIERO AGRÍCOLA 16-08-1984",
        "titulo_universidad": "UNIVERSIDAD NACIONAL AGRARIA LA MOLINA",
        "grado_magister": "MAESTRÍA EN INGENIERÍA DE RECURSOS DE AGUA Y TIERRA 04-07-1985",
        "magister_universidad": "UNIVERSIDAD NACIONAL AGRARIA LA MOLINA",
        "grado_doctor": "DOCTORADO EN INGENIERÍA CIVIL ÁREA DE CONCENTRACIÓN INGENIERÍA HIDRÁULICA (Reconocimiento)",
        "doctor_universidad": "UNIVERSIDAD DE SAO PAULO",
        "universidad_procedencia": "UNIVERSIDAD NACIONAL AGRARIA LA MOLINA",
    },
    {
        "nombre_completo": "DR. JHONNY HERNAN TUPAYACHI SOTOMAYOR",
        "especialidad": "ABOGADO",
        "dni": "40961651",
        "direccion": "PROLONGACIÓN ARENALES #746 DPTO 602 MIRAFLORES",
        "correo": "jtcmf@hotmail.com",
        "telefono": "999521501",
        "titulo_profesional": "ABOGADO 05-08-2004",
        "titulo_universidad": "UNIVERSIDAD CATÓLICA DE SANTA MARÍA",
        "grado_magister": "MAESTRÍA EN DERECHO CONSTITUCIONAL 22-03-2007",
        "magister_universidad": "UNIVERSIDAD CATÓLICA DE SANTA MARÍA",
        "grado_doctor": "DOCTOR EN DERECHO Y CIENCIA POLÍTICA 15-06-2022",
        "doctor_universidad": "UNIVERSIDAD NACIONAL MAYOR DE SAN MARCOS",
        "universidad_procedencia": "UNIVERSIDAD CATÓLICA DE SANTA MARÍA",
    },
    {
        "nombre_completo": "DR. JORGE LEONCIO RIVERA MUÑOZ",
        "especialidad": "LICENCIADO EN EDUCACIÓN",
        "dni": "08742823",
        "direccion": "PATRIOTISMO MZ. EE5 LT. 26 URB. PRO. LIMA 39",
        "correo": "jorgeriveraunmsm@gmail.com",
        "telefono": "971107791 - 987485081",
        "titulo_profesional": "LICENCIADO EN EDUCACIÓN EN BIOLOGÍA Y QUÍMICA 05-06-1981",
        "titulo_universidad": "UNIVERSIDAD NACIONAL MAYOR DE SAN MARCOS",
        "grado_magister": "MAESTRÍA EN EDUCACIÓN CON MENCIÓN EN DOCENCIA EN EL NIVEL SUPERIOR 16-04-2015",
        "magister_universidad": "UNIVERSIDAD NACIONAL MAYOR DE SAN MARCOS",
        "grado_doctor": "DOCTOR EN EDUCACIÓN 28-08-2019",
        "doctor_universidad": "UNIVERSIDAD NACIONAL MAYOR DE SAN MARCOS",
        "universidad_procedencia": "UNIVERSIDAD NACIONAL MAYOR DE SAN MARCOS",
    },
    {
        "nombre_completo": "DR. JORGE PAUL ARCE ZANS",
        "especialidad": "ABOGADO",
        "dni": "40876494",
        "direccion": "AV. HIPÓLITO UNANUE NRO 52 D OFICINA 101 WANCHAQ",
        "correo": "jorgearcezans@yahoo.com",
        "telefono": "986744337",
        "titulo_profesional": "ABOGADO 05-01-2007",
        "titulo_universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        "grado_magister": "MAESTRÍA EN DERECHO MENCIÓN EN DERECHO PENAL Y PROCESAL PENAL 31-03-2017",
        "magister_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "grado_doctor": "DOCTOR EN DERECHO 24-12-19",
        "doctor_universidad": "UNIVERSIDAD NACIONAL DE SAN ANTONIO ABAD DEL CUSCO",
        "universidad_procedencia": "UNIVERSIDAD ANDINA DEL CUSCO",
    },
    {
        "nombre_completo": "DR. JOSE HILDEBRANDO DIAZ TORRES",
        "especialidad": "ABOGADO",
        "dni": "23956366",
        "direccion": "URB. LOS CIPRECES DE VERSALLES B-12",
        "correo": "hildebrandodiaz@yahoo.es",
        "telefono": "951606408",
        "titulo_profesional": "ABOGADO 31-07-2003",
        "titulo_universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        "grado_magister": "MAESTRÍA EN DOCENCIA UNIVERSITARIA 26-07-2012",
        "magister_universidad": "UNIVERSIDA ANDINA DEL CUSCO",
        "grado_doctor": "DOCTOR EN DERECHO 11-12-2015",
        "doctor_universidad": "UNIVERSIDAD ANDINA DEL CUSCO",
        "universidad_procedencia": "UNIVERSIDAD ANDINA DEL CUSCO",
    },
]


# ============================
# Main
# ============================

def main() -> None:
    print(f"Usando base de datos: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        total = 0
        for d in DOCENTES_DATA_1:
            docente_id = _upsert_docente(conn, d)
            total += 1
            print(f"✔ Docente procesado: {d['nombre_completo']} (id={docente_id})")
        conn.commit()
        print(f"\n✅ Lote 1 completado. Docentes procesados: {total}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
