# reporte_docentes_sunedu.py
"""
Exportador CSV tipo SUNEDU para docentes EPG.

Genera un CSV que Excel abre sin problemas, con las cabeceras pedidas:

- N°
- DOCENTE (APELLIDO PATERNO)
- DOCENTE (APELLIDO MATERNO)
- DOCENTE (NOMBRES)
- PAÍS (NACIONALIDAD)
- N° DE DNI / CARNET DE EXTRANJERÍA
- FECHA DE INGRESO COMO DOCENTE EN LA UNIVERSIDAD
- ¿ERA DOCENTE UNIVERSITARIO A LA ENTRADA EN VIGENCIA DE LA LEY 30220...? (Sí/No)
- MAYOR GRADO ACADÉMICO DEL DOCENTE
- MENCIÓN DEL MAYOR GRADO DOCENTE
- UNIVERSIDAD QUE OTORGÓ EL MAYOR GRADO DOCENTE
- PAÍS / UNIVERSIDAD QUE OTORGÓ EL MAYOR GRADO DEL DOCENTE
- PREGRADO / MAESTRÍA / DOCTORADO (Sí/No)
- CATEGORÍA DOCENTE
- RÉGIMEN DE DEDICACIÓN
- HORAS CLASES / OTRAS / TOTAL
- DOCENTE INVESTIGADOR (Sí/No)
- DOCENTE REGISTRADO EN DINA (Sí/No)
- PERIODO ACADÉMICO
- OBSERVACIONES
- FILIAL
- ESPECIALIDAD
"""

from flask import request, Response
from datetime import datetime
from io import StringIO
import csv
import re

# Fecha de referencia de la Ley Universitaria 30220 (entrada en vigencia)
LU_REFERENCE_DATE = datetime(2014, 7, 10).date()


def _si_no(value) -> str:
    """Convierte 0/1, True/False o None a 'Sí' / 'No' / ''."""
    if value is None:
        return ""
    return "Sí" if bool(value) else "No"


def _parse_fecha(fecha_str: str):
    """Intenta parsear fechas en formatos comunes y devuelve date o None."""
    if not fecha_str:
        return None
    s = str(fecha_str).strip()
    if not s:
        return None

    formatos = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]
    for fmt in formatos:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _era_docente_antes_lu(fecha_ingreso: str) -> str:
    """
    Devuelve 'Sí' si la fecha de ingreso es anterior o igual a la fecha de referencia
    de la Ley Universitaria; 'No' si es posterior; '' si no hay dato.
    """
    fecha = _parse_fecha(fecha_ingreso)
    if not fecha:
        return ""
    return "Sí" if fecha <= LU_REFERENCE_DATE else "No"


def _dividir_nombre_completo(nombre_completo: str):
    """
    Fallback cuando no tenemos apellido_paterno / apellido_materno / nombres.
    Usa una heurística simple: [ap_paterno] [ap_materno] [nombres...].
    """
    if not nombre_completo:
        return "", "", ""

    partes = nombre_completo.strip().split()
    if len(partes) >= 3:
        ap_paterno = partes[0]
        ap_materno = partes[1]
        nombres = " ".join(partes[2:])
    elif len(partes) == 2:
        ap_paterno = partes[0]
        ap_materno = ""
        nombres = partes[1]
    else:
        ap_paterno = ""
        ap_materno = ""
        nombres = nombre_completo.strip()

    return ap_paterno, ap_materno, nombres


def _extraer_mencion(nombre_grado: str) -> str:
    """
    A partir de algo tipo 'Doctor en Ciencias de la Educación',
    intenta extraer la mención ('Ciencias de la Educación').
    Si no puede, devuelve el texto original sin cambios.
    """
    if not nombre_grado:
        return ""

    texto = nombre_grado.strip()

    patrones = [
        r"(?i)^doctor(a)? en\s+",
        r"(?i)^mag[ií]ster en\s+",
        r"(?i)^maestr[ií]a en\s+",
        r"(?i)^licenciado(a)? en\s+",
        r"(?i)^t[ií]tulo profesional en\s+",
    ]
    for pat in patrones:
        texto = re.sub(pat, "", texto).strip()

    return texto or nombre_grado.strip()


def _mayor_grado_info(doc_row):
    """
    Determina el mayor grado académico del docente en base a:
    - grado_doctor / doctor_universidad
    - grado_magister / magister_universidad
    - titulo_profesional / titulo_universidad

    Retorna: (tipo_grado, mencion, universidad, pais_universidad)
    Por ahora pais_universidad se deja vacío (puedes llenarlo manual en Excel).
    """
    candidatos = [
        (
            "DOCTORADO",
            doc_row["grado_doctor"],
            doc_row["doctor_universidad"],
            doc_row["doctor_fecha"],
        ),
        (
            "MAESTRÍA",
            doc_row["grado_magister"],
            doc_row["magister_universidad"],
            doc_row["magister_fecha"],
        ),
        (
            "TÍTULO PROFESIONAL",
            doc_row["titulo_profesional"],
            doc_row["titulo_universidad"],
            doc_row["titulo_fecha"],
        ),
    ]

    for tipo, nombre_grado, universidad, _fecha in candidatos:
        if nombre_grado and str(nombre_grado).strip():
            mencion = _extraer_mencion(str(nombre_grado))
            universidad_final = (universidad or "").strip()
            # Por ahora no tenemos país de la universidad -> devolver vacío
            pais_univ = ""
            return tipo, mencion, universidad_final, pais_univ

    # Sin datos
    return "", "", "", ""


def register_sunedu_routes(app, get_db_connection):
    """
    Registra en la app Flask la ruta:

        /export/docentes_sunedu.csv

    Parámetros opcionales:
      - periodo_academico: texto como '2025-III' para filtrar contra docente_carga_academica.
    """

    @app.route("/export/docentes_sunedu.csv")
    def export_docentes_sunedu():
        # Ejemplo de uso:
        #   /export/docentes_sunedu.csv?periodo_academico=2025-III
        periodo_academico = request.args.get("periodo_academico", "").strip()

        conn = get_db_connection()

        # LEFT JOIN con la tabla docente_carga_academica
        # Si periodo_academico viene vacío, el JOIN seguirá, pero probablemente no habrá filas de carga.
        sql = """
            SELECT
                d.*,
                ca.periodo_academico      AS ca_periodo_academico,
                ca.horas_clase            AS ca_horas_clase,
                ca.horas_otras_actividades AS ca_horas_otras,
                ca.horas_total            AS ca_horas_total,
                ca.observaciones          AS ca_observaciones,
                ca.filial                 AS ca_filial
            FROM docente d
            LEFT JOIN docente_carga_academica ca
                   ON ca.docente_id = d.id
                  AND (ca.periodo_academico = ? OR ? = '')
            WHERE d.activo = 1
            ORDER BY
                COALESCE(d.apellido_paterno, ''),
                COALESCE(d.apellido_materno, ''),
                COALESCE(d.nombres, d.nombre_completo)
        """

        rows = conn.execute(sql, (periodo_academico, periodo_academico)).fetchall()
        conn.close()

        # Construimos el CSV en memoria
        si = StringIO()
        writer = csv.writer(si)

        # === Cabeceras del reporte tipo SUNEDU ===
        header = [
            "N°",
            "DOCENTE (APELLIDO PATERNO)",
            "DOCENTE (APELLIDO MATERNO)",
            "DOCENTE (NOMBRES)",
            "PAÍS (NACIONALIDAD)",
            "N° DE DNI / CARNET DE EXTRANJERÍA",
            "FECHA DE INGRESO COMO DOCENTE EN LA UNIVERSIDAD",
            "¿ERA DOCENTE UNIVERSITARIO A LA ENTRADA EN VIGENCIA DE LA LEY 30220? (Sí/No)",
            "MAYOR GRADO ACADÉMICO DEL DOCENTE",
            "MENCIÓN DEL MAYOR GRADO DOCENTE",
            "UNIVERSIDAD QUE OTORGÓ EL MAYOR GRADO DOCENTE",
            "PAÍS / UNIVERSIDAD QUE OTORGÓ EL MAYOR GRADO DEL DOCENTE",
            "NIVEL PREGRADO (Sí/No)",
            "NIVEL MAESTRÍA (Sí/No)",
            "NIVEL DOCTORADO (Sí/No)",
            "CATEGORÍA DOCENTE",
            "RÉGIMEN DE DEDICACIÓN",
            "HORAS CLASES (SEMANALES)",
            "HORAS OTRAS ACTIVIDADES (SEMANALES)",
            "TOTAL HORAS SEMANALES",
            "DOCENTE INVESTIGADOR (Sí/No)",
            "DOCENTE REGISTRADO EN DINA (Sí/No)",
            "PERIODO ACADÉMICO",
            "OBSERVACIONES",
            "FILIAL",
            "ESPECIALIDAD",
        ]
        writer.writerow(header)

        for idx, d in enumerate(rows, start=1):
            # === Apellidos y nombres ===
            ap_paterno = d["apellido_paterno"]
            ap_materno = d["apellido_materno"]
            nombres = d["nombres"]

            if not (ap_paterno or ap_materno or nombres):
                # Fallback: intentar separar desde nombre_completo
                ap_paterno, ap_materno, nombres = _dividir_nombre_completo(
                    d["nombre_completo"]
                )

            # === Nacionalidad y documento ===
            nacionalidad = (d["nacionalidad_pais"] or "").strip()
            numero_doc = (d["dni"] or "").strip()

            # === Fecha de ingreso y condición Ley Universitaria ===
            fecha_ingreso_u = (d["fecha_ingreso_u"] or "").strip()
            era_antes_lu = _era_docente_antes_lu(fecha_ingreso_u)

            # === Mayor grado académico ===
            (
                tipo_mayor_grado,
                mencion_mayor_grado,
                univ_mayor_grado,
                pais_univ_mayor_grado,
            ) = _mayor_grado_info(d)

            # === Niveles en los que dicta (desde flags en docente) ===
            pregrado_sn = _si_no(d["nivel_pregrado"])
            maestria_sn = _si_no(d["nivel_maestria"])
            doctorado_sn = _si_no(d["nivel_doctorado"])

            # === Categoría, régimen y horas ===
            categoria = (d["categoria_docente"] or "").strip()
            regimen = (d["regimen_dedicacion"] or "").strip()

            horas_clase = d["ca_horas_clase"] if d["ca_horas_clase"] is not None else 0
            horas_otras = (
                d["ca_horas_otras"] if d["ca_horas_otras"] is not None else 0
            )
            horas_total = d["ca_horas_total"]
            if horas_total is None:
                horas_total = horas_clase + horas_otras

            # === Investigador / DINA ===
            docente_investigador = _si_no(d["es_docente_investigador"])
            registrado_dina = _si_no(d["registrado_dina"])

            # === Período académico ===
            periodo_acad_final = d["ca_periodo_academico"] or periodo_academico or ""

            # === Observaciones (priorizar las de carga académica) ===
            observaciones = (
                d["ca_observaciones"]
                or d["antecedentes"]
                or ""
            )

            # === Filial: primero de carga, si no de docente ===
            filial = d["ca_filial"] or (d["filial"] or "")

            especialidad = d["especialidad"] or ""

            row = [
                idx,
                ap_paterno or "",
                ap_materno or "",
                nombres or "",
                nacionalidad,
                numero_doc,
                fecha_ingreso_u,
                era_antes_lu,
                tipo_mayor_grado,
                mencion_mayor_grado,
                univ_mayor_grado,
                pais_univ_mayor_grado,
                pregrado_sn,
                maestria_sn,
                doctorado_sn,
                categoria,
                regimen,
                horas_clase,
                horas_otras,
                horas_total,
                docente_investigador,
                registrado_dina,
                periodo_acad_final,
                observaciones,
                filial,
                especialidad,
            ]

            writer.writerow(row)

        output = si.getvalue()
        si.close()

        filename = "reporte_docentes_sunedu.csv"
        if periodo_academico:
            safe_periodo = periodo_academico.replace(" ", "_")
            filename = f"reporte_docentes_sunedu_{safe_periodo}.csv"

        return Response(
            output,
            mimetype="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            },
        )
