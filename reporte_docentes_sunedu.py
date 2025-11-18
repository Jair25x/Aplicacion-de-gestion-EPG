# reporte_docentes_sunedu.py
"""
Exportador Excel (XLSX) tipo SUNEDU para docentes EPG.

Genera un archivo .xlsx con:
- Cabeceras estilo SUNEDU (SUPERINTENDENCIA…, FORMATO C, RELACIÓN DE DOCENTES)
- Nombre de la universidad en la parte superior.
- Doble fila de encabezados de tabla:
  * Fila superior con títulos agrupados (niveles de programa, horas semanales).
  * Fila inferior con subcolumnas (PREGRADO/MAESTRÍA/DOCTORADO, CLASES/OTRAS/TOTAL).

Ruta registrada:

    /export/docentes_sunedu.xlsx
    /export/docentes_sunedu.xlsx?periodo_academico=2025-III
"""

from flask import request, Response
from datetime import datetime
from io import BytesIO
import re

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter

# Fecha de referencia de la Ley Universitaria 30220 (entrada en vigencia)
LU_REFERENCE_DATE = datetime(2014, 7, 10).date()

# Ajusta si quisieras otro texto
UNIVERSITY_NAME = "UNIVERSIDAD ANDINA DEL CUSCO"


def _si_no(value) -> str:
    """Convierte 0/1, True/False, '0'/'1', 'sí/no' a 'Sí' / 'No' / ''."""
    if value is None:
        return ""
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"1", "si", "sí", "s", "y", "yes"}:
            return "Sí"
        if v in {"0", "no", "n"}:
            return "No"
        return "Sí" if bool(v) else "No"
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
    Devuelve 'Sí' si la fecha de ingreso es anterior o igual a la fecha de
    referencia de la Ley Universitaria; 'No' si es posterior; '' si no hay dato.
    """
    fecha = _parse_fecha(fecha_ingreso)
    if not fecha:
        return ""
    return "Sí" if fecha <= LU_REFERENCE_DATE else "No"


def _dividir_nombre_completo(nombre_completo: str):
    """
    Fallback cuando no tenemos apellido_paterno / apellido_materno / nombres.
    Usa heurística simple: [ap_paterno] [ap_materno] [nombres...].
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
    Determina el mayor grado académico del docente.

    1) Si en la tabla DOCENTE ya se llenó:
       - mayor_grado_academico
       - mayor_grado_mencion
       se usan directamente (mapeando a formato SUNEDU).

    2) Si no, se deriva de:
       - grado_doctor / doctor_universidad
       - grado_magister / magister_universidad
       - titulo_profesional / titulo_universidad

    Retorna: (tipo_grado, mencion, universidad, pais_universidad)
    (pais_universidad se deja vacío para llenarlo manualmente si se requiere).
    """
    mayor_tipo = (doc_row["mayor_grado_academico"] or "").strip().upper()
    mayor_mencion = (doc_row["mayor_grado_mencion"] or "").strip()

    if mayor_tipo or mayor_mencion:
        mapping = {
            "BACHILLER": "BACHILLER",
            "TITULO": "TÍTULO PROFESIONAL",
            "TÍTULO": "TÍTULO PROFESIONAL",
            "MAGISTER": "MAESTRÍA",
            "MÁGISTER": "MAESTRÍA",
            "MAESTRIA": "MAESTRÍA",
            "MAESTRÍA": "MAESTRÍA",
            "DOCTOR": "DOCTORADO",
        }
        tipo_final = mapping.get(mayor_tipo, mayor_tipo)
        universidad_final = (doc_row["universidad_procedencia"] or "").strip()
        pais_univ = ""
        return tipo_final, mayor_mencion, universidad_final, pais_univ

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
            pais_univ = ""
            return tipo, mencion, universidad_final, pais_univ

    return "", "", "", ""


def register_sunedu_routes(app, get_db_connection):
    """
    Registra en la app Flask la ruta:

        /export/docentes_sunedu.xlsx

    Parámetros opcionales (query string):
      - periodo_academico: texto como '2025-III' para filtrar contra
        docente_carga_academica.periodo_academico. Si se omite, trae la
        carga académica (si existe) de cualquier período, y el campo
        PERIODO ACADÉMICO se llena con el de la carga o con el filtro.
    """

    @app.route("/export/docentes_sunedu.xlsx")
    def export_docentes_sunedu():
        # Ejemplo:
        #   /export/docentes_sunedu.xlsx?periodo_academico=2025-III
        periodo_academico = request.args.get("periodo_academico", "").strip()

        conn = get_db_connection()
        sql = """
            SELECT
                d.*,
                ca.periodo_academico        AS ca_periodo_academico,
                ca.horas_clase              AS ca_horas_clase,
                ca.horas_otras_actividades  AS ca_horas_otras,
                ca.horas_total              AS ca_horas_total,
                ca.observaciones            AS ca_observaciones,
                ca.filial                   AS ca_filial,
                ca.nivel_pregrado           AS ca_nivel_pregrado,
                ca.nivel_maestria           AS ca_nivel_maestria,
                ca.nivel_doctorado          AS ca_nivel_doctorado
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

        wb = Workbook()
        ws = wb.active
        ws.title = "Docentes"

        # === Encabezado SUNEDU (tipo plantilla) ===
        # Fila 1: nombre de la superintendencia
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=26)
        c = ws.cell(
            row=1,
            column=1,
            value="SUPERINTENDENCIA NACIONAL DE EDUCACIÓN SUPERIOR UNIVERSITARIA",
        )
        c.font = Font(bold=True)
        c.alignment = Alignment(horizontal="center")

        # Fila 3: formato
        ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=26)
        c = ws.cell(row=3, column=1, value="FORMATO DE LICENCIAMIENTO C")
        c.font = Font(bold=True)
        c.alignment = Alignment(horizontal="center")

        # Fila 4: título relación de docentes
        ws.merge_cells(start_row=4, start_column=1, end_row=4, end_column=26)
        c = ws.cell(row=4, column=1, value="RELACIÓN DE DOCENTES")
        c.font = Font(bold=True)
        c.alignment = Alignment(horizontal="center")

        # Fila 5: nombre de la universidad
        ws.cell(row=5, column=1, value="NOMBRE DE LA UNIVERSIDAD")
        ws.cell(row=5, column=3, value=UNIVERSITY_NAME).font = Font(bold=True)

        # === Cabecera de tabla (doble fila como en SUNEDU) ===
        header_row_top = 7
        header_row_bottom = 8

        # Fila superior (títulos agrupados)
        ws.cell(row=header_row_top, column=1, value="N°")
        ws.cell(row=header_row_top, column=2, value="DOCENTE (APELLIDO PATERNO)")
        ws.cell(row=header_row_top, column=3, value="DOCENTE (APELLIDO MATERNO)")
        ws.cell(row=header_row_top, column=4, value="DOCENTE (NOMBRES)")
        ws.cell(row=header_row_top, column=5, value="PAÍS (NACIONALIDAD)")
        ws.cell(row=header_row_top, column=6, value="N° DE DNI / CARNET DE EXTRANJERÍA")
        ws.cell(
            row=header_row_top,
            column=7,
            value="FECHA DE INGRESO COMO DOCENTE EN LA UNIVERSIDAD",
        )
        ws.cell(
            row=header_row_top,
            column=8,
            value=(
                "¿ERA DOCENTE UNIVERSITARIO A LA ENTRADA EN VIGENCIA DE LA LEY 30220, LU?\n"
                "10/07/2014 (20/11/2015, QUE SE PUBLICÓ LA LEY UNIVERSITARIA)\n"
                "Sí/No (1)"
            ),
        )
        ws.cell(row=header_row_top, column=9, value="MAYOR GRADO ACADÉMICO DEL DOCENTE (2)")
        ws.cell(row=header_row_top, column=10, value="MENCIÓN DEL MAYOR GRADO DOCENTE (3)")
        ws.cell(
            row=header_row_top,
            column=11,
            value="UNIVERSIDAD QUE OTORGÓ EL MAYOR GRADO DOCENTE",
        )
        ws.cell(
            row=header_row_top,
            column=12,
            value="PAÍS / UNIVERSIDAD QUE OTORGÓ EL MAYOR GRADO DEL DOCENTE",
        )
        ws.cell(
            row=header_row_top,
            column=13,
            value="NIVELES DE PROGRAMA DE ESTUDIO EN LOS QUE DA CLASES EL DOCENTE",
        )
        ws.cell(row=header_row_top, column=16, value="CATEGORÍA DOCENTE (4)")
        ws.cell(row=header_row_top, column=17, value="RÉGIMEN DE DEDICACIÓN (5)")
        ws.cell(
            row=header_row_top,
            column=18,
            value="NÚMERO DE HORAS SEMANALES FIJADOS POR LA UNIVERSIDAD",
        )
        ws.cell(row=header_row_top, column=21, value="DOCENTE INVESTIGADOR  Sí/No (6)")
        ws.cell(row=header_row_top, column=22, value="DOCENTE REGISTRADO EN DINA Sí/No (7)")
        ws.cell(row=header_row_top, column=23, value="PERIODO ACADÉMICO (8)")
        ws.cell(row=header_row_top, column=24, value="OBSERVACIONES")
        ws.cell(row=header_row_top, column=25, value="FILIAL")
        ws.cell(row=header_row_top, column=26, value="ESPECIALIDAD")

        # Merges verticales (encabezados simples)
        for col in [
            1,
            2,
            3,
            4,
            5,
            6,
            7,
            8,
            9,
            10,
            11,
            12,
            16,
            17,
            21,
            22,
            23,
            24,
            25,
            26,
        ]:
            ws.merge_cells(
                start_row=header_row_top,
                start_column=col,
                end_row=header_row_bottom,
                end_column=col,
            )

        # Merges horizontales para grupos
        # Niveles de programa (pregrado/maestría/doctorado): columnas 13-15
        ws.merge_cells(
            start_row=header_row_top,
            start_column=13,
            end_row=header_row_top,
            end_column=15,
        )
        # Horas semanales: columnas 18-20
        ws.merge_cells(
            start_row=header_row_top,
            start_column=18,
            end_row=header_row_top,
            end_column=20,
        )

        # Fila inferior (sub-encabezados)
        ws.cell(row=header_row_bottom, column=13, value="PREGRADO\nSí/No")
        ws.cell(row=header_row_bottom, column=14, value="MAESTRÍA\nSí/No")
        ws.cell(row=header_row_bottom, column=15, value="DOCTORADO\nSí/No")
        ws.cell(row=header_row_bottom, column=18, value="CLASES")
        ws.cell(row=header_row_bottom, column=19, value="OTRAS ACTIVIDADES")
        ws.cell(row=header_row_bottom, column=20, value="TOTAL HORAS SEMANALES")

        # Estilos para cabeceras de tabla
        for row_idx in (header_row_top, header_row_bottom):
            for col in range(1, 27):
                cell = ws.cell(row=row_idx, column=col)
                if cell.value:
                    cell.font = Font(bold=True)
                    cell.alignment = Alignment(
                        horizontal="center",
                        vertical="center",
                        wrap_text=True,
                    )

        # Fijar paneles: deja encabezado visible
        ws.freeze_panes = f"A{header_row_bottom + 1}"

        # === Datos ===
        first_data_row = header_row_bottom + 1
        col_widths = [0] * 26

        def _update_widths(row_idx, values):
            for idx, value in enumerate(values, start=1):
                text = "" if value is None else str(value)
                # No queremos que cabeceras enormes disparen el ancho
                if row_idx >= first_data_row:
                    col_widths[idx - 1] = max(col_widths[idx - 1], len(text))

        current_row = first_data_row

        for idx, d in enumerate(rows, start=1):
            # Apellidos y nombres
            ap_paterno = d["apellido_paterno"]
            ap_materno = d["apellido_materno"]
            nombres = d["nombres"]

            if not (ap_paterno or ap_materno or nombres):
                ap_paterno, ap_materno, nombres = _dividir_nombre_completo(
                    d["nombre_completo"]
                )

            nacionalidad = (d["pais_nacionalidad"] or "").strip()
            numero_doc = (d["dni"] or "").strip()

            fecha_ingreso_u = (d["fecha_ingreso_universidad"] or "").strip()

            era_flag = d["era_docente_antes_ley_30220"]
            if era_flag is not None:
                era_antes_lu = _si_no(era_flag)
            else:
                era_antes_lu = _era_docente_antes_lu(fecha_ingreso_u)

            (
                tipo_mayor_grado,
                mencion_mayor_grado,
                univ_mayor_grado,
                pais_univ_mayor_grado,
            ) = _mayor_grado_info(d)

            ca_niv_pre = d["ca_nivel_pregrado"]
            ca_niv_mae = d["ca_nivel_maestria"]
            ca_niv_doc = d["ca_nivel_doctorado"]

            pregrado_sn = _si_no(
                ca_niv_pre if ca_niv_pre is not None else d["puede_pregrado"]
            )
            maestria_sn = _si_no(
                ca_niv_mae if ca_niv_mae is not None else d["puede_maestria"]
            )
            doctorado_sn = _si_no(
                ca_niv_doc if ca_niv_doc is not None else d["puede_doctorado"]
            )

            categoria = (d["categoria_docente"] or "").strip()
            regimen = (d["regimen_dedicacion"] or "").strip()

            horas_clase = d["ca_horas_clase"] if d["ca_horas_clase"] is not None else 0
            horas_otras = (
                d["ca_horas_otras"] if d["ca_horas_otras"] is not None else 0
            )
            horas_total = d["ca_horas_total"]
            if horas_total is None:
                horas_total = horas_clase + horas_otras

            docente_investigador = _si_no(d["es_docente_investigador"])
            registrado_dina = _si_no(d["registrado_en_dina"])

            periodo_acad_final = d["ca_periodo_academico"] or periodo_academico or ""

            observaciones = d["ca_observaciones"] or d["antecedentes"] or ""
            filial = d["ca_filial"] or ""
            especialidad = d["especialidad"] or ""

            data_row = [
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

            _update_widths(current_row, data_row)

            for col_idx, value in enumerate(data_row, start=1):
                ws.cell(row=current_row, column=col_idx, value=value)

            current_row += 1

        # Ajuste de anchos de columna basados en los datos
        for idx, width in enumerate(col_widths, start=1):
            col_letter = get_column_letter(idx)
            if width == 0:
                continue
            ws.column_dimensions[col_letter].width = min(width + 2, 50)

        # Serializar a bytes
        output = BytesIO()
        wb.save(output)
        output.seek(0)

        filename = "reporte_docentes_sunedu.xlsx"
        if periodo_academico:
            safe_periodo = periodo_academico.replace(" ", "_")
            filename = f"reporte_docentes_sunedu_{safe_periodo}.xlsx"

        return Response(
            output.getvalue(),
            mimetype=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
