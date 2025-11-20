# routes/export_routes.py
from flask import Response, request, send_file
from db import get_db_connection
from io import StringIO, BytesIO
import csv
from docx import Document
from docx.shared import Cm, Pt
from docx.enum.section import WD_ORIENT

from utils_programas import (
    facultad_sort_key,
    programa_sort_key,
    normalizar_programa_base,
    agrupar_por_facultad_y_programa_base,
)


def register_export_routes(app):
    # Adecuación de formatos
    def set_table_font_size(table, size_pt: int):
        """
        Ajusta la fuente de todo el contenido de la tabla al tamaño indicado (en puntos).
        """
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.font.size = Pt(size_pt)

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
            min_matriculados_int = int(min_matriculados) if min_matriculados else None
        except ValueError:
            min_matriculados_int = None

        conn = get_db_connection()

        # Si no llega periodo_id, usamos el último periodo creado
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
                COALESCE(pp.matriculados, cp.matriculados) AS matriculados,
                cp.fusion_grupo,
                cp.fusion_principal
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

        # Cabecera CSV
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
                "Fusión grupo",
                "Fusión principal",
            ]
        )

        for r in rows:
            remuneracion_monto = r["remuneracion_monto"]
            matriculados = r["matriculados"]
            fusion_principal = r["fusion_principal"]

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
                    # Convertimos numéricos a string respetando 0
                    "" if remuneracion_monto is None else str(remuneracion_monto),
                    "" if remuneracion_monto is None else str(remuneracion_monto),
                    r["poi"] or "",
                    r["codigo"] or "",
                    r["categoria"] or "",
                    r["sem1"] or "",
                    r["sem2"] or "",
                    r["periodo"] or "",
                    r["periodo_academico"] or "",
                    "" if matriculados is None else str(matriculados),
                    r["fusion_grupo"] or "",
                    "" if fusion_principal is None else str(fusion_principal),
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
        """
        Devuelve la universidad asociada al MAYOR grado del docente.

        Regla:
        - Si tiene doctor_universidad -> se asume mayor grado (Doctorado).
        - Si no, se usa magister_universidad.
        - Si no, se usa titulo_universidad.
        - Si nada de lo anterior, se cae a universidad_procedencia.
        """

        def _get(key):
            if r is None:
                return None

            if isinstance(r, dict):
                return r.get(key)

            # Para sqlite3.Row (y otros tipos con acceso por índice/clave)
            try:
                return r[key]
            except (KeyError, IndexError, TypeError):
                return None

        for k in ("doctor_universidad", "magister_universidad", "titulo_universidad"):
            val = _get(k)
            if val:
                return val

        return _get("universidad_procedencia") or ""

    def procesar_fusiones(rows):
        """
        Recibe una lista de dicts con los campos, incluyendo (si existen):
          - fusion_grupo
          - fusion_principal (1 si es curso "principal" del grupo, 0 si es secundario)

        Retorna una nueva lista de rows donde:
        - Los cursos sin fusion_grupo se dejan igual.
        - Los cursos con el mismo fusion_grupo se combinan:
          * Se elige un curso principal (fusion_principal=1, o el primero si ninguno está marcado).
          * Se suman los matriculados de todo el grupo.
          * Se añade una nota en observaciones indicando qué asignaturas se fusionan.
        """
        sin_fusion = []
        grupos = {}

        for r in rows:
            fg = (r.get("fusion_grupo") or "").strip()
            fp = r.get("fusion_principal")

            if not fg:
                sin_fusion.append(r)
                continue

            g = grupos.setdefault(fg, {"principales": [], "otros": []})
            if fp in (1, "1", True, "TRUE", "true"):
                g["principales"].append(r)
            else:
                g["otros"].append(r)

        resultado = list(sin_fusion)

        for fg, g in grupos.items():
            principales = g["principales"] or g["otros"]
            otros = g["otros"]

            if not principales:
                # Caso raro: solo cursos sin principal claramente marcado
                resultado.extend(otros)
                continue

            destino = principales[0]
            combinado = dict(destino)

            # Construir mensaje de fusión
            nombres_origen = sorted(
                {
                    (o.get("asignatura") or "").strip()
                    for o in otros
                    if o.get("asignatura")
                }
            )
            if nombres_origen:
                msg_fusion = (
                    f"FUSIÓN ({fg}): integra también "
                    + ", ".join(nombres_origen)
                    + "."
                )
            else:
                msg_fusion = f"FUSIÓN ({fg})."

            obs_actual = (combinado.get("observaciones") or "").strip()
            if obs_actual:
                combinado["observaciones"] = obs_actual + " | " + msg_fusion
            else:
                combinado["observaciones"] = msg_fusion

            # Sumar matriculados de todo el grupo (incluye principal + otros)
            try:
                total_m = 0
                for r_g in principales + otros:
                    m = r_g.get("matriculados")
                    if m is not None:
                        total_m += int(m)
                if total_m:
                    combinado["matriculados"] = total_m
            except Exception:
                # Si algo falla, dejamos el valor original de destino
                pass

            resultado.append(combinado)

        return resultado

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

        # NUEVO: checkbox para decidir si se combinan cursos fusionados
        incluir_fusiones = request.args.get("incluir_fusiones") == "1"

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
                COALESCE(pp.matriculados, cp.matriculados) AS matriculados,
                cp.fusion_grupo,
                cp.fusion_principal
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

        rows_db = conn.execute(sql, params).fetchall()

        # Convertimos a dict para manejar fusiones de forma más cómoda
        rows = [dict(r) for r in rows_db]

        periodo_etiqueta = ""
        periodo_academico = ""
        if rows:
            periodo_etiqueta = rows[0].get("periodo_etiqueta") or ""
            periodo_academico = rows[0].get("periodo_academico") or ""
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

        # Procesar fusiones para que el DOCX no duplique cursos fusionados
        if incluir_fusiones:
            rows_docx = procesar_fusiones(rows)
        else:
            rows_docx = rows

        # Separar locales vs ordinarizados
        locales = []
        ordin = []

        for r in rows_docx:
            tipo_mes = (r.get("tipo_docente_mes") or "").upper()
            if tipo_mes == "ORDINARIZADO":
                ordin.append(r)
            else:
                locales.append(r)

        locales_grouped = agrupar_por_facultad_y_programa_base(locales)

        def _sort_key_ordin(r):
            facultad = r.get("facultad") or ""
            programa = r.get("programa") or ""
            tipo_prog = (r.get("tipo_programa") or "").upper()
            programa_base = normalizar_programa_base(programa, tipo_prog)
            return (
                facultad_sort_key(facultad),
                programa_sort_key(programa_base),
                (r.get("docente") or "").lower(),
                r.get("ciclo") or "",
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
                        extra_cols.append("Universidad mayor grado")
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
                            (r.get("ciclo") or ""),
                            (r.get("docente") or "").lower(),
                        ),
                    )

                    for rdata in cursos_prog_ordenados:
                        row_cells = table.add_row().cells
                        row_cells[0].text = f"{n:02d}"

                        # Docente + universidad de mayor grado (con espacio en blanco entre ambos)
                        docente_nombre = rdata.get("docente") or ""
                        universidad_mayor = pick_universidad(rdata)

                        cell_docente = row_cells[1]
                        cell_docente.text = ""

                        p_nombre = cell_docente.paragraphs[0]
                        p_nombre.add_run(docente_nombre)

                        if universidad_mayor:
                            cell_docente.add_paragraph("")  # línea en blanco
                            p_uni = cell_docente.add_paragraph()
                            p_uni.add_run(universidad_mayor)

                        row_cells[2].text = rdata.get("programa") or ""
                        row_cells[3].text = rdata.get("ciclo") or ""
                        row_cells[4].text = rdata.get("asignatura") or ""
                        row_cells[5].text = rdata.get("fechas_texto") or ""
                        row_cells[6].text = rdata.get("remuneracion_texto") or ""
                        row_cells[7].text = rdata.get("poi") or ""
                        row_cells[8].text = rdata.get("dni") or ""

                        col_idx = 9
                        if col_matriculados:
                            row_cells[col_idx].text = str(
                                rdata.get("matriculados") or ""
                            )
                            col_idx += 1

                        if col_observaciones:
                            row_cells[col_idx].text = (
                                rdata.get("observaciones") or ""
                            )
                            col_idx += 1
                        if col_universidad:
                            row_cells[col_idx].text = pick_universidad(rdata)
                            col_idx += 1
                        if col_telefono:
                            row_cells[col_idx].text = (
                                rdata.get("telefono") or ""
                            )
                            col_idx += 1
                        if col_correo:
                            row_cells[col_idx].text = (
                                rdata.get("correo") or ""
                            )
                            col_idx += 1
                        if col_direccion:
                            row_cells[col_idx].text = (
                                rdata.get("direccion") or ""
                            )

                        n += 1

                    set_table_font_size(table, 8)
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
                extra_cols.append("Universidad mayor grado")
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

                docente_nombre = rdata.get("docente") or ""
                universidad_mayor = pick_universidad(rdata)

                cell_docente = row_cells[1]
                cell_docente.text = ""

                p_nombre = cell_docente.paragraphs[0]
                p_nombre.add_run(docente_nombre)

                if universidad_mayor:
                    cell_docente.add_paragraph("")  # línea en blanco
                    p_uni = cell_docente.add_paragraph()
                    p_uni.add_run(universidad_mayor)

                row_cells[2].text = rdata.get("programa") or ""
                row_cells[3].text = rdata.get("ciclo") or ""
                row_cells[4].text = rdata.get("asignatura") or ""
                row_cells[5].text = rdata.get("fechas_texto") or ""
                row_cells[6].text = rdata.get("remuneracion_texto") or ""
                row_cells[7].text = rdata.get("poi") or ""
                row_cells[8].text = rdata.get("dni") or ""

                col_idx = 9
                if col_matriculados:
                    row_cells[col_idx].text = str(
                        rdata.get("matriculados") or ""
                    )
                    col_idx += 1
                if col_observaciones:
                    row_cells[col_idx].text = (
                        rdata.get("observaciones") or ""
                    )
                    col_idx += 1
                if col_universidad:
                    row_cells[col_idx].text = pick_universidad(rdata)
                    col_idx += 1
                if col_telefono:
                    row_cells[col_idx].text = rdata.get("telefono") or ""
                    col_idx += 1
                if col_correo:
                    row_cells[col_idx].text = rdata.get("correo") or ""
                    col_idx += 1
                if col_direccion:
                    row_cells[col_idx].text = (
                        rdata.get("direccion") or ""
                    )

                n += 1

            set_table_font_size(table, 8)
            docx.add_paragraph("")
            return n

        contador = 1
        contador = agregar_seccion(doc, "DOCENTES LOCALES", locales_grouped, contador)
        if ordin_sorted:
            contador = agregar_seccion_ordinarios(
                doc, "DOCENTES ORDINARIZADOS", ordin_sorted, contador
            )

        if not rows_docx:
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
