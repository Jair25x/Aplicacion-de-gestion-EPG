# routes/export_routes.py
from flask import Response, request, send_file
from db import get_db_connection
from io import StringIO, BytesIO
import csv
from docx import Document
from docx.shared import Cm
from docx.enum.section import WD_ORIENT

from utils_programas import (
    facultad_sort_key,
    programa_sort_key,
    normalizar_programa_base,
    agrupar_por_facultad_y_programa_base,
)


def register_export_routes(app):

    # ========================
    # 4) EXPORTACIÓN CSV
    # ========================
    @app.route("/export/programacion.csv")
    def export_programacion_csv():
        periodo_id = request.args.get("periodo_id")
        facultad_id = request.args.get("facultad_id")
        tipo_programa = request.args.get("tipo_programa", "")
        tipo_docente_mes = request.args.get("tipo_docente_mes", "")
        solo_matriculados = request.args.get("solo_matriculados", "") == "1"
        min_matriculados = request.args.get("min_matriculados", "")
        try:
            min_matriculados_int = (
                int(min_matriculados) if min_matriculados else None
            )
        except ValueError:
            min_matriculados_int = None

        conn = get_db_connection()

        if not periodo_id:
            periodo = conn.execute(
                "SELECT id FROM periodo ORDER BY anio DESC, mes DESC LIMIT 1"
            ).fetchone()
            if periodo:
                periodo_id = periodo["id"]
            else:
                periodo_id = None

        params = []
        where_clauses = []

        if periodo_id:
            where_clauses.append("cp.periodo_id = ?")
            params.append(periodo_id)

        if facultad_id:
            where_clauses.append("f.id = ?")
            params.append(facultad_id)

        if tipo_programa:
            where_clauses.append("pa.tipo = ?")
            params.append(tipo_programa)

        if tipo_docente_mes:
            where_clauses.append("cp.tipo_docente_mes = ?")
            params.append(tipo_docente_mes)

        if solo_matriculados:
            where_clauses.append(
                "(COALESCE(pp.matriculados, cp.matriculados) IS NOT NULL "
                "AND COALESCE(pp.matriculados, cp.matriculados) > 0)"
            )

        if min_matriculados_int is not None:
            where_clauses.append(
                "(COALESCE(pp.matriculados, cp.matriculados) >= ?)"
            )
            params.append(min_matriculados_int)

        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        sql = f"""
            SELECT
                f.nombre AS facultad,
                pa.tipo AS tipo_programa,
                pa.nombre_corto AS programa,
                d.nombre_completo AS docente,
                d.dni AS dni,
                d.tipo_docente AS tipo_docente_global,
                cp.tipo_docente_mes,
                cp.ciclo,
                cp.asignatura,
                cp.fechas_texto,
                cp.remuneracion_texto,
                cp.remuneracion_monto,
                cp.poi,
                cp.codigo,
                cp.categoria,
                cp.sem1,
                cp.sem2,
                p.etiqueta AS periodo,
                p.periodo_academico AS periodo_academico,
                COALESCE(pp.matriculados, cp.matriculados) AS matriculados
            FROM curso_programado cp
            LEFT JOIN docente d ON d.id = cp.docente_id
            JOIN programa_academico pa ON pa.id = cp.programa_id
            JOIN facultad f ON f.id = pa.facultad_id
            JOIN periodo p ON p.id = cp.periodo_id
            LEFT JOIN programa_periodo pp
                ON pp.programa_id = pa.id
                AND pp.periodo_id = cp.periodo_id
            {where_sql}
            ORDER BY
                f.nombre,
                pa.tipo DESC,
                pa.nombre_corto,
                cp.ciclo,
                d.nombre_completo
        """

        rows = conn.execute(sql, params).fetchall()
        conn.close()

        si = StringIO()
        writer = csv.writer(si)
        writer.writerow(
            [
                "Facultad",
                "Tipo programa",
                "Programa",
                "Docente",
                "DNI",
                "Tipo docente (global)",
                "Tipo docente (mes)",
                "Ciclo",
                "Asignatura",
                "Fechas",
                "Remuneración texto",
                "Remuneración monto",
                "POI",
                "Código",
                "Categoría",
                "Sem1",
                "Sem2",
                "Periodo",
                "Período académico",
                "Matriculados",
            ]
        )
        for r in rows:
            writer.writerow(
                [
                    r["facultad"] or "",
                    r["tipo_programa"] or "",
                    r["programa"] or "",
                    r["docente"] or "",
                    r["dni"] or "",
                    r["tipo_docente_global"] or "",
                    r["tipo_docente_mes"] or "",
                    r["ciclo"] or "",
                    r["asignatura"] or "",
                    r["fechas_texto"] or "",
                    r["remuneracion_texto"] or "",
                    r["remuneracion_monto"] or "",
                    r["poi"] or "",
                    r["codigo"] or "",
                    r["categoria"] or "",
                    r["sem1"] or "",
                    r["sem2"] or "",
                    r["periodo"] or "",
                    r["periodo_academico"] or "",
                    r["matriculados"] or "",
                ]
            )

        output = si.getvalue()
        si.close()

        filename = "programacion_epg.csv"
        return Response(
            output,
            mimetype="text/csv; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    # ========================
    # 5) EXPORTACIÓN DOCX
    # ========================

    def pick_universidad(r):
        for k in ("doctor_universidad", "magister_universidad", "titulo_universidad"):
            val = r[k]
            if val:
                return val
        return r["universidad_procedencia"] or ""

    @app.route("/export/programacion.docx")
    def export_programacion_docx():
        periodo_id = request.args.get("periodo_id")
        facultad_id = request.args.get("facultad_id")
        tipo_programa = request.args.get("tipo_programa", "")
        tipo_docente_mes = request.args.get("tipo_docente_mes", "")

        col_observaciones = request.args.get("col_observaciones") == "1"
        col_universidad = request.args.get("col_universidad") == "1"
        col_telefono = request.args.get("col_telefono") == "1"
        col_correo = request.args.get("col_correo") == "1"
        col_direccion = request.args.get("col_direccion") == "1"

        col_matriculados = request.args.get("col_matriculados") == "1"
        solo_matriculados = request.args.get("solo_matriculados") == "1"
        min_matriculados = request.args.get("min_matriculados", "")
        try:
            min_matriculados_int = (
                int(min_matriculados) if min_matriculados else None
            )
        except ValueError:
            min_matriculados_int = None

        conn = get_db_connection()

        if not periodo_id:
            periodo_row = conn.execute(
                "SELECT id, etiqueta FROM periodo "
                "ORDER BY anio DESC, mes DESC LIMIT 1"
            ).fetchone()
            if periodo_row:
                periodo_id = periodo_row["id"]
            else:
                periodo_id = None

        params = []
        where_clauses = []

        if periodo_id:
            where_clauses.append("cp.periodo_id = ?")
            params.append(periodo_id)

        if facultad_id:
            where_clauses.append("f.id = ?")
            params.append(facultad_id)

        if tipo_programa:
            where_clauses.append("pa.tipo = ?")
            params.append(tipo_programa)

        if tipo_docente_mes:
            where_clauses.append("cp.tipo_docente_mes = ?")
            params.append(tipo_docente_mes)

        if solo_matriculados:
            where_clauses.append(
                "(COALESCE(pp.matriculados, cp.matriculados) IS NOT NULL "
                "AND COALESCE(pp.matriculados, cp.matriculados) > 0)"
            )

        if min_matriculados_int is not None:
            where_clauses.append(
                "(COALESCE(pp.matriculados, cp.matriculados) >= ?)"
            )
            params.append(min_matriculados_int)

        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        sql = f"""
            SELECT
                cp.id AS curso_id,
                f.nombre AS facultad,
                pa.tipo AS tipo_programa,
                pa.nombre_corto AS programa,
                pa.modalidad,
                d.universidad_procedencia,
                d.nombre_completo AS docente,
                d.dni,
                d.telefono,
                d.correo,
                d.direccion,
                d.tipo_docente AS tipo_docente_global,
                d.titulo_universidad,
                d.magister_universidad,
                d.doctor_universidad,
                cp.tipo_docente_mes,
                cp.ciclo,
                cp.asignatura,
                cp.fechas_texto,
                cp.remuneracion_texto,
                cp.remuneracion_monto,
                cp.poi,
                cp.observaciones,
                p.etiqueta AS periodo_etiqueta,
                p.periodo_academico AS periodo_academico,
                COALESCE(pp.matriculados, cp.matriculados) AS matriculados
            FROM curso_programado cp
            LEFT JOIN docente d ON d.id = cp.docente_id
            JOIN programa_academico pa ON pa.id = cp.programa_id
            JOIN facultad f ON f.id = pa.facultad_id
            JOIN periodo p ON p.id = cp.periodo_id
            LEFT JOIN programa_periodo pp
                ON pp.programa_id = pa.id
                AND pp.periodo_id = cp.periodo_id
            {where_sql}
            ORDER BY
                f.nombre,
                pa.tipo DESC,
                pa.nombre_corto,
                cp.tipo_docente_mes DESC,
                d.nombre_completo,
                cp.ciclo
        """

        rows = conn.execute(sql, params).fetchall()

        periodo_etiqueta = ""
        periodo_academico = ""
        if rows:
            periodo_etiqueta = rows[0]["periodo_etiqueta"]
            periodo_academico = rows[0]["periodo_academico"] or ""
        else:
            if periodo_id:
                row = conn.execute(
                    "SELECT etiqueta, periodo_academico "
                    "FROM periodo WHERE id = ?",
                    (periodo_id,),
                ).fetchone()
                if row:
                    periodo_etiqueta = row["etiqueta"]
                    periodo_academico = row["periodo_academico"] or ""

        conn.close()

        # Separar locales vs ordinarizados
        locales = []
        ordin = []

        for r in rows:
            tipo_mes = (r["tipo_docente_mes"] or "").upper()
            if tipo_mes == "ORDINARIZADO":
                ordin.append(r)
            else:
                locales.append(r)

        locales_grouped = agrupar_por_facultad_y_programa_base(locales)

        def _sort_key_ordin(r):
            facultad = r["facultad"] or ""
            programa = r["programa"] or ""
            tipo_prog = (r["tipo_programa"] or "").upper()
            programa_base = normalizar_programa_base(programa, tipo_prog)
            return (
                facultad_sort_key(facultad),
                programa_sort_key(programa_base),
                (r["docente"] or "").lower(),
                r["ciclo"] or "",
            )

        ordin_sorted = sorted(ordin, key=_sort_key_ordin)

        # Crear documento Word
        doc = Document()

        # Configuración de página: horizontal
        section = doc.sections[0]
        section.orientation = WD_ORIENT.LANDSCAPE
        new_width, new_height = section.page_height, section.page_width
        section.page_width = new_width
        section.page_height = new_height
        section.top_margin = Cm(1.5)
        section.bottom_margin = Cm(1.5)
        section.left_margin = Cm(1.5)
        section.right_margin = Cm(1.5)

        # Título general
        titulo = "DOCENTES EPG"
        if periodo_etiqueta:
            titulo += f" – MES {periodo_etiqueta.upper()}"
        if periodo_academico:
            titulo += f" – PERÍODO {periodo_academico}"

        p_title = doc.add_paragraph()
        r_title = p_title.add_run(titulo)
        r_title.bold = True
        p_title.alignment = 1  # centrado

        doc.add_paragraph("")

        def agregar_seccion(docx, encabezado, grouped, start_index):
            n = start_index
            if not grouped:
                return n

            p = docx.add_paragraph()
            r = p.add_run(encabezado)
            r.bold = True
            docx.add_paragraph("")

            facultades_ordenadas = sorted(
                grouped.keys(), key=facultad_sort_key
            )

            for facultad in facultades_ordenadas:
                programas_base = grouped[facultad]

                p_fac = docx.add_paragraph()
                texto_facultad = facultad
                if not facultad.lower().startswith("facultad"):
                    texto_facultad = f"Facultad de {facultad}"

                r_fac = p_fac.add_run(texto_facultad)
                r_fac.bold = True

                programas_ordenados = sorted(
                    programas_base.keys(), key=programa_sort_key
                )

                for programa_base in programas_ordenados:
                    cursos_prog = programas_base[programa_base]

                    p_prog = docx.add_paragraph(style="List Bullet")
                    r_prog = p_prog.add_run(programa_base)
                    r_prog.bold = True

                    headers = [
                        "N°",
                        "Docente",
                        "Programa",
                        "Ciclo",
                        "Asignatura",
                        "Fechas de dictado",
                        "Remuneración",
                        "POI",
                        "DNI",
                    ]

                    if col_matriculados:
                        headers.append("Matriculados")

                    extra_cols = []
                    if col_observaciones:
                        extra_cols.append("Observaciones")
                    if col_universidad:
                        extra_cols.append("Universidad de último grado")
                    if col_telefono:
                        extra_cols.append("Teléfono")
                    if col_correo:
                        extra_cols.append("Correo")
                    if col_direccion:
                        extra_cols.append("Dirección")

                    headers.extend(extra_cols)

                    table = docx.add_table(rows=1, cols=len(headers))
                    table.style = "Table Grid"
                    table.autofit = True

                    hdr_cells = table.rows[0].cells
                    for i, h in enumerate(headers):
                        hdr_cells[i].text = h

                    cursos_prog_ordenados = sorted(
                        cursos_prog,
                        key=lambda r: (
                            (r["ciclo"] or ""),
                            (r["docente"] or "").lower(),
                        ),
                    )

                    for rdata in cursos_prog_ordenados:
                        row_cells = table.add_row().cells
                        row_cells[0].text = f"{n:02d}"
                        row_cells[1].text = rdata["docente"] or ""
                        row_cells[2].text = rdata["programa"] or ""
                        row_cells[3].text = rdata["ciclo"] or ""
                        row_cells[4].text = rdata["asignatura"] or ""
                        row_cells[5].text = rdata["fechas_texto"] or ""
                        row_cells[6].text = rdata["remuneracion_texto"] or ""
                        row_cells[7].text = rdata["poi"] or ""
                        row_cells[8].text = rdata["dni"] or ""

                        col_idx = 9
                        if col_matriculados:
                            row_cells[col_idx].text = str(
                                rdata["matriculados"] or ""
                            )
                            col_idx += 1

                        if col_observaciones:
                            row_cells[col_idx].text = (
                                rdata["observaciones"] or ""
                            )
                            col_idx += 1
                        if col_universidad:
                            row_cells[col_idx].text = pick_universidad(rdata)
                            col_idx += 1
                        if col_telefono:
                            row_cells[col_idx].text = (
                                rdata["telefono"] or ""
                            )
                            col_idx += 1
                        if col_correo:
                            row_cells[col_idx].text = (
                                rdata["correo"] or ""
                            )
                            col_idx += 1
                        if col_direccion:
                            row_cells[col_idx].text = (
                                rdata["direccion"] or ""
                            )

                        n += 1

                    docx.add_paragraph("")

            return n

        def agregar_seccion_ordinarios(docx, encabezado, rows_ordin, start_index):
            n = start_index
            if not rows_ordin:
                return n

            p = docx.add_paragraph()
            r = p.add_run(encabezado)
            r.bold = True
            docx.add_paragraph("")

            headers = [
                "N°",
                "DOCENTE",
                "PROGRAMA",
                "CICLO",
                "ASIGNATURA",
                "FECHAS",
                "REMUNERACION",
                "POI",
                "DNI",
            ]

            extra_cols = []
            if col_matriculados:
                headers.append("Matriculados")
            if col_observaciones:
                extra_cols.append("OBSERVACIONES")
            if col_universidad:
                extra_cols.append("Universidad")
            if col_telefono:
                extra_cols.append("Teléfono")
            if col_correo:
                extra_cols.append("Correo")
            if col_direccion:
                extra_cols.append("Dirección")

            headers.extend(extra_cols)

            table = docx.add_table(rows=1, cols=len(headers))
            table.style = "Table Grid"
            table.autofit = True

            hdr_cells = table.rows[0].cells
            for i, h in enumerate(headers):
                hdr_cells[i].text = h

            for rdata in rows_ordin:
                row_cells = table.add_row().cells
                row_cells[0].text = f"{n:02d}"
                row_cells[1].text = rdata["docente"] or ""
                row_cells[2].text = rdata["programa"] or ""
                row_cells[3].text = rdata["ciclo"] or ""
                row_cells[4].text = rdata["asignatura"] or ""
                row_cells[5].text = rdata["fechas_texto"] or ""
                row_cells[6].text = rdata["remuneracion_texto"] or ""
                row_cells[7].text = rdata["poi"] or ""
                row_cells[8].text = rdata["dni"] or ""

                col_idx = 9
                if col_matriculados:
                    row_cells[col_idx].text = str(
                        rdata["matriculados"] or ""
                    )
                    col_idx += 1
                if col_observaciones:
                    row_cells[col_idx].text = (
                        rdata["observaciones"] or ""
                    )
                    col_idx += 1
                if col_universidad:
                    row_cells[col_idx].text = pick_universidad(rdata)
                    col_idx += 1
                if col_telefono:
                    row_cells[col_idx].text = rdata["telefono"] or ""
                    col_idx += 1
                if col_correo:
                    row_cells[col_idx].text = rdata["correo"] or ""
                    col_idx += 1
                if col_direccion:
                    row_cells[col_idx].text = (
                        rdata["direccion"] or ""
                    )

                n += 1

            docx.add_paragraph("")
            return n

        contador = 1
        contador = agregar_seccion(doc, "DOCENTES LOCALES", locales_grouped, contador)
        if ordin_sorted:
            contador = agregar_seccion_ordinarios(
                doc, "DOCENTES ORDINARIZADOS", ordin_sorted, contador
            )

        if not rows:
            doc.add_paragraph(
                "No hay cursos programados para el período seleccionado."
            )

        bio = BytesIO()
        doc.save(bio)
        bio.seek(0)

        filename = "Docentes_EPG"
        if periodo_etiqueta:
            filename += "_" + periodo_etiqueta.replace(" ", "_")
        filename += ".docx"

        return send_file(
            bio,
            as_attachment=True,
            download_name=filename,
            mimetype=(
                "application/vnd.openxmlformats-"
                "officedocument.wordprocessingml.document"
            ),
        )
