# routes/programacion.py
from flask import render_template, request, redirect, url_for, flash
from db import get_db_connection
import sqlite3


def register_programacion_routes(app):

    @app.route("/programacion", methods=["GET"])
    def programacion():
        conn = get_db_connection()
        cur = conn.cursor()

        # Catálogos para filtros (incluimos periodo_academico para el template)
        cur.execute(
            "SELECT id, etiqueta, periodo_academico "
            "FROM periodo "
            "ORDER BY anio DESC, mes DESC"
        )
        periodos_global = cur.fetchall()

        cur.execute("SELECT id, nombre FROM facultad WHERE activo = 1 ORDER BY nombre")
        facultades_global = cur.fetchall()

        tipos_programa_global = [
            ("", "Todos"),
            ("DOCTORADO", "Doctorados"),
            ("MAESTRIA", "Maestrías"),
        ]

        tipos_docente_mes_global = [
            ("", "Todos"),
            ("LOCAL", "Local"),
            ("ORDINARIZADO", "Ordinarizado"),
        ]

        # --------- Filtros ----------
        periodo_id = request.args.get("periodo_id", type=int)
        facultad_id = request.args.get("facultad_id", type=int)
        tipo_programa = request.args.get("tipo_programa", default="", type=str)
        tipo_docente_mes = request.args.get("tipo_docente_mes", default="", type=str)
        solo_matriculados = (
            request.args.get("solo_matriculados", default="", type=str) == "1"
        )
        min_matriculados = request.args.get("min_matriculados", default="", type=str)
        try:
            min_matriculados_int = int(min_matriculados) if min_matriculados else None
        except ValueError:
            min_matriculados_int = None

        # Si no se envía periodo_id, usamos por defecto el último período (más reciente)
        if not periodo_id and periodos_global:
            periodo_id = periodos_global[0]["id"]

        filtros = []
        params = []

        if periodo_id:
            filtros.append("cp.periodo_id = ?")
            params.append(periodo_id)

        if facultad_id:
            filtros.append("pa.facultad_id = ?")
            params.append(facultad_id)

        if tipo_programa:
            filtros.append("pa.tipo = ?")
            params.append(tipo_programa)

        if tipo_docente_mes:
            filtros.append("cp.tipo_docente_mes = ?")
            params.append(tipo_docente_mes)

        if solo_matriculados:
            # Solo cursos cuyos programas tienen matriculados (> 0)
            filtros.append(
                "(pp.matriculados IS NOT NULL AND pp.matriculados > 0)"
            )

        if min_matriculados_int is not None:
            filtros.append(
                "(pp.matriculados IS NOT NULL AND pp.matriculados >= ?)"
            )
            params.append(min_matriculados_int)

        where_clause = " AND ".join(filtros) if filtros else "1 = 1"

        # --------- Query principal de cursos ----------
        # Incluimos:
        # - matriculados (desde programa_periodo o curso)
        # - cantidad_sugeridos = número de docentes sugeridos para ese curso
        sql_cursos = f"""
            SELECT
                cp.id AS curso_id,
                f.nombre AS facultad_nombre,
                pa.tipo AS programa_tipo,
                pa.nombre_corto AS programa_nombre,
                COALESCE(d.nombre_completo, '') AS docente_nombre,
                cp.dni_docente,
                cp.tipo_docente_mes,
                cp.ciclo,
                cp.asignatura,
                cp.fechas_texto,
                cp.remuneracion_texto,
                cp.poi,
                cp.observaciones,
                pa.id AS programa_id,
                pp.matriculados AS matriculados,
                COALESCE(dsc.sugeridos_count, 0) AS cantidad_sugeridos
            FROM curso_programado cp
            JOIN programa_academico pa ON cp.programa_id = pa.id
            JOIN facultad f ON pa.facultad_id = f.id
            LEFT JOIN docente d ON cp.docente_id = d.id
            LEFT JOIN programa_periodo pp
                   ON pp.programa_id = pa.id
                  AND pp.periodo_id = cp.periodo_id
            LEFT JOIN (
                SELECT curso_id, COUNT(*) AS sugeridos_count
                FROM docente_sugerido_curso
                WHERE estado = 'SUGERIDO'
                GROUP BY curso_id
            ) dsc ON dsc.curso_id = cp.id
            WHERE {where_clause}
            ORDER BY f.nombre, pa.tipo, pa.nombre_corto, cp.ciclo, cp.asignatura
        """
        cur.execute(sql_cursos, params)
        cursos = cur.fetchall()

        # --------- Total de remuneración (coherente con mismos filtros) ----------
        sql_total = f"""
            SELECT COALESCE(SUM(cp.remuneracion_monto), 0) AS total_rem
            FROM curso_programado cp
            JOIN programa_academico pa ON cp.programa_id = pa.id
            LEFT JOIN programa_periodo pp
                   ON pp.programa_id = pa.id
                  AND pp.periodo_id = cp.periodo_id
            WHERE {where_clause}
        """
        cur.execute(sql_total, params)
        total_row = cur.fetchone()
        total_remuneracion = total_row["total_rem"] if total_row else 0.0

        total_cursos = len(cursos)

        # --------- Info del período seleccionado (para el resumen) ----------
        periodo_info = None
        if periodo_id:
            cur.execute(
                "SELECT id, etiqueta, periodo_academico "
                "FROM periodo "
                "WHERE id = ?",
                (periodo_id,),
            )
            periodo_info = cur.fetchone()

        conn.close()

        return render_template(
            "cursos_programados.html",
            periodo_id=periodo_id,
            facultad_id=facultad_id,
            tipo_programa=tipo_programa,
            tipo_docente_mes=tipo_docente_mes,
            periodos_global=periodos_global,
            facultades_global=facultades_global,
            tipos_programa_global=tipos_programa_global,
            tipos_docente_mes_global=tipos_docente_mes_global,
            periodo_info=periodo_info,
            cursos=cursos,
            total_cursos=total_cursos,
            total_remuneracion=total_remuneracion,
            solo_matriculados=solo_matriculados,
            min_matriculados=min_matriculados,
        )

    @app.route("/programacion/nuevo", methods=["GET", "POST"])
    def programacion_nueva():
        conn = get_db_connection()

        # Incluimos periodo_academico para que el template pueda mostrarlo
        periodos = conn.execute(
            "SELECT id, etiqueta, periodo_academico "
            "FROM periodo "
            "ORDER BY anio DESC, mes DESC"
        ).fetchall()

        facultades = conn.execute(
            "SELECT id, nombre FROM facultad WHERE activo = 1 ORDER BY nombre"
        ).fetchall()

        programas = conn.execute(
            """
            SELECT pa.id, pa.nombre_corto, pa.tipo, f.nombre AS facultad_nombre
            FROM programa_academico pa
            JOIN facultad f ON f.id = pa.facultad_id
            WHERE pa.activo = 1
            ORDER BY f.nombre, pa.tipo DESC, pa.nombre_corto
            """
        ).fetchall()

        docentes = conn.execute(
            "SELECT id, nombre_completo, dni FROM docente "
            "WHERE activo = 1 ORDER BY nombre_completo"
        ).fetchall()

        conn.close()

        selected_periodo_id = request.args.get("periodo_id")

        if request.method == "POST":
            periodo_id = request.form.get("periodo_id")
            programa_id = request.form.get("programa_id")
            docente_id_raw = request.form.get("docente_id")
            ciclo = request.form.get("ciclo", "").strip()
            asignatura = request.form.get("asignatura", "").strip()
            fechas_texto = request.form.get("fechas_texto", "").strip()
            remuneracion_monto_str = request.form.get(
                "remuneracion_monto", ""
            ).strip()
            remuneracion_texto = request.form.get(
                "remuneracion_texto", ""
            ).strip()
            poi = request.form.get("poi", "").strip()
            tipo_docente_mes = request.form.get(
                "tipo_docente_mes", ""
            ).strip() or None
            estado_programacion = (
                request.form.get("estado_programacion", "").strip() or "PROPUESTO"
            )
            observaciones = (
                request.form.get("observaciones", "").strip() or None
            )

            codigo = request.form.get("codigo", "").strip() or None
            categoria = request.form.get("categoria", "").strip() or None
            sem1 = request.form.get("sem1", "").strip() or None
            sem2 = request.form.get("sem2", "").strip() or None

            docente_id = int(docente_id_raw) if docente_id_raw else None

            if not periodo_id or not programa_id or not asignatura or not fechas_texto:
                flash(
                    "Período, programa, asignatura y fechas son obligatorios",
                    "danger",
                )
                return render_template(
                    "curso_form.html",
                    periodos=periodos,
                    facultades=facultades,
                    programas=programas,
                    docentes=docentes,
                    curso=None,
                    selected_periodo_id=selected_periodo_id,
                )

            try:
                remuneracion_monto = (
                    float(remuneracion_monto_str)
                    if remuneracion_monto_str
                    else None
                )
            except ValueError:
                flash("La remuneración debe ser un número válido", "danger")
                return render_template(
                    "curso_form.html",
                    periodos=periodos,
                    facultades=facultades,
                    programas=programas,
                    docentes=docentes,
                    curso=None,
                    selected_periodo_id=selected_periodo_id,
                )

            if not remuneracion_texto and remuneracion_monto is not None:
                remuneracion_texto = (
                    f"S/. {remuneracion_monto:,.2f}"
                    .replace(",", "X")
                    .replace(".", ",")
                    .replace("X", ".")
                )

            conn = get_db_connection()

            dni_docente = None
            if docente_id is not None:
                dni_row = conn.execute(
                    "SELECT dni FROM docente WHERE id = ?", (docente_id,)
                ).fetchone()
                dni_docente = dni_row["dni"] if dni_row else None

            conn.execute(
                """
                INSERT INTO curso_programado (
                    periodo_id, programa_id, docente_id,
                    ciclo, asignatura,
                    fechas_texto,
                    remuneracion_monto, remuneracion_texto,
                    poi, dni_docente,
                    tipo_docente_mes, estado_programacion, observaciones,
                    codigo, categoria, sem1, sem2
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    periodo_id,
                    programa_id,
                    docente_id,
                    ciclo,
                    asignatura,
                    fechas_texto,
                    remuneracion_monto,
                    remuneracion_texto,
                    poi,
                    dni_docente,
                    tipo_docente_mes,
                    estado_programacion,
                    observaciones,
                    codigo,
                    categoria,
                    sem1,
                    sem2,
                ),
            )
            conn.commit()
            conn.close()

            flash("Curso programado creado correctamente ✅", "success")
            return redirect(url_for("programacion", periodo_id=periodo_id))

        return render_template(
            "curso_form.html",
            periodos=periodos,
            facultades=facultades,
            programas=programas,
            docentes=docentes,
            curso=None,
            selected_periodo_id=selected_periodo_id,
        )

    @app.route("/programacion/<int:curso_id>/editar", methods=["GET", "POST"])
    def programacion_editar(curso_id):
        conn = get_db_connection()

        curso = conn.execute(
            """
            SELECT cp.*, d.nombre_completo AS docente_nombre
            FROM curso_programado cp
            LEFT JOIN docente d ON d.id = cp.docente_id
            WHERE cp.id = ?
            """,
            (curso_id,),
        ).fetchone()

        if not curso:
            conn.close()
            flash("Curso no encontrado", "danger")
            return redirect(url_for("programacion"))

        # Incluimos periodo_academico
        periodos = conn.execute(
            "SELECT id, etiqueta, periodo_academico "
            "FROM periodo "
            "ORDER BY anio DESC, mes DESC"
        ).fetchall()

        facultades = conn.execute(
            "SELECT id, nombre FROM facultad WHERE activo = 1 ORDER BY nombre"
        ).fetchall()

        programas = conn.execute(
            """
            SELECT pa.id, pa.nombre_corto, pa.tipo, f.nombre AS facultad_nombre
            FROM programa_academico pa
            JOIN facultad f ON f.id = pa.facultad_id
            WHERE pa.activo = 1
            ORDER BY f.nombre, pa.tipo DESC, pa.nombre_corto
            """
        ).fetchall()

        docentes = conn.execute(
            "SELECT id, nombre_completo, dni FROM docente "
            "WHERE activo = 1 ORDER BY nombre_completo"
        ).fetchall()

        if request.method == "POST":
            periodo_id = request.form.get("periodo_id")
            programa_id = request.form.get("programa_id")
            docente_id_raw = request.form.get("docente_id")
            ciclo = request.form.get("ciclo", "").strip()
            asignatura = request.form.get("asignatura", "").strip()
            fechas_texto = request.form.get("fechas_texto", "").strip()
            remuneracion_monto_str = request.form.get(
                "remuneracion_monto", ""
            ).strip()
            remuneracion_texto = request.form.get(
                "remuneracion_texto", ""
            ).strip()
            poi = request.form.get("poi", "").strip()
            tipo_docente_mes = request.form.get(
                "tipo_docente_mes", ""
            ).strip() or None
            estado_programacion = (
                request.form.get("estado_programacion", "").strip() or "PROPUESTO"
            )
            observaciones = (
                request.form.get("observaciones", "").strip() or None
            )

            codigo = request.form.get("codigo", "").strip() or None
            categoria = request.form.get("categoria", "").strip() or None
            sem1 = request.form.get("sem1", "").strip() or None
            sem2 = request.form.get("sem2", "").strip() or None

            docente_id = int(docente_id_raw) if docente_id_raw else None

            if not periodo_id or not programa_id or not asignatura or not fechas_texto:
                flash(
                    "Período, programa, asignatura y fechas son obligatorios",
                    "danger",
                )
                return render_template(
                    "curso_form.html",
                    periodos=periodos,
                    facultades=facultades,
                    programas=programas,
                    docentes=docentes,
                    curso=curso,
                    selected_periodo_id=None,
                )

            try:
                remuneracion_monto = (
                    float(remuneracion_monto_str)
                    if remuneracion_monto_str
                    else None
                )
            except ValueError:
                flash("La remuneración debe ser un número válido", "danger")
                return render_template(
                    "curso_form.html",
                    periodos=periodos,
                    facultades=facultades,
                    programas=programas,
                    docentes=docentes,
                    curso=curso,
                    selected_periodo_id=None,
                )

            if not remuneracion_texto and remuneracion_monto is not None:
                remuneracion_texto = (
                    f"S/. {remuneracion_monto:,.2f}"
                    .replace(",", "X")
                    .replace(".", ",")
                    .replace("X", ".")
                )

            dni_docente = None
            if docente_id is not None:
                dni_row = conn.execute(
                    "SELECT dni FROM docente WHERE id = ?", (docente_id,)
                ).fetchone()
                dni_docente = dni_row["dni"] if dni_row else None

            conn.execute(
                """
                UPDATE curso_programado
                SET periodo_id = ?,
                    programa_id = ?,
                    docente_id = ?,
                    ciclo = ?,
                    asignatura = ?,
                    fechas_texto = ?,
                    remuneracion_monto = ?,
                    remuneracion_texto = ?,
                    poi = ?,
                    dni_docente = ?,
                    tipo_docente_mes = ?,
                    estado_programacion = ?,
                    observaciones = ?,
                    codigo = ?,
                    categoria = ?,
                    sem1 = ?,
                    sem2 = ?,
                    updated_at = datetime('now')
                WHERE id = ?
                """,
                (
                    periodo_id,
                    programa_id,
                    docente_id,
                    ciclo,
                    asignatura,
                    fechas_texto,
                    remuneracion_monto,
                    remuneracion_texto,
                    poi,
                    dni_docente,
                    tipo_docente_mes,
                    estado_programacion,
                    observaciones,
                    codigo,
                    categoria,
                    sem1,
                    sem2,
                    curso_id,
                ),
            )
            conn.commit()
            conn.close()

            flash("Curso programado actualizado correctamente ✅", "success")
            return redirect(url_for("programacion", periodo_id=periodo_id))

        conn.close()
        return render_template(
            "curso_form.html",
            periodos=periodos,
            facultades=facultades,
            programas=programas,
            docentes=docentes,
            curso=curso,
            selected_periodo_id=None,
        )

    @app.route("/programacion/<int:curso_id>/eliminar", methods=["POST"])
    def programacion_eliminar(curso_id):
        periodo_id = request.form.get("periodo_id")
        facultad_id = request.form.get("facultad_id")
        tipo_programa = request.form.get("tipo_programa", "")
        tipo_docente_mes = request.form.get("tipo_docente_mes", "")
        solo_matriculados = request.form.get("solo_matriculados", "")
        min_matriculados = request.form.get("min_matriculados", "")

        conn = get_db_connection()
        conn.execute("DELETE FROM curso_programado WHERE id = ?", (curso_id,))
        conn.commit()
        conn.close()

        flash("Curso programado eliminado correctamente ✅", "success")
        return redirect(
            url_for(
                "programacion",
                periodo_id=periodo_id,
                facultad_id=facultad_id,
                tipo_programa=tipo_programa,
                tipo_docente_mes=tipo_docente_mes,
                solo_matriculados=solo_matriculados,
                min_matriculados=min_matriculados,
            )
        )

    # =========================
    # GESTIÓN DE DOCENTES SUGERIDOS POR CURSO
    # =========================

    @app.route("/programacion/<int:curso_id>/sugeridos", methods=["GET", "POST"])
    def programacion_sugeridos(curso_id):
        """
        Vista para gestionar docentes sugeridos para un curso:
        - GET: lista docentes sugeridos + formulario para agregar uno nuevo.
        - POST: agrega un nuevo docente sugerido y redirige (PRG).
        """
        conn = get_db_connection()

        curso = conn.execute(
            """
            SELECT cp.*,
                   pa.nombre_corto AS programa_nombre,
                   pa.tipo AS programa_tipo,
                   f.nombre AS facultad_nombre,
                   per.etiqueta AS periodo_etiqueta,
                   per.periodo_academico
            FROM curso_programado cp
            JOIN programa_academico pa ON pa.id = cp.programa_id
            JOIN facultad f ON f.id = pa.facultad_id
            JOIN periodo per ON per.id = cp.periodo_id
            WHERE cp.id = ?
            """,
            (curso_id,),
        ).fetchone()

        if not curso:
            conn.close()
            flash("Curso no encontrado", "danger")
            return redirect(url_for("programacion"))

        if request.method == "POST":
            docente_id_raw = request.form.get("docente_id")
            if not docente_id_raw:
                flash("Debe seleccionar un docente para sugerir.", "danger")
                conn.close()
                return redirect(url_for("programacion_sugeridos", curso_id=curso_id))

            try:
                docente_id = int(docente_id_raw)
            except ValueError:
                docente_id = None

            if docente_id is None:
                flash("Docente inválido.", "danger")
                conn.close()
                return redirect(url_for("programacion_sugeridos", curso_id=curso_id))

            # Verificamos si ya existe sugerencia activa
            existe = conn.execute(
                """
                SELECT id
                FROM docente_sugerido_curso
                WHERE curso_id = ? AND docente_id = ? AND estado = 'SUGERIDO'
                """,
                (curso_id, docente_id),
            ).fetchone()

            if existe:
                flash("Este docente ya figura como sugerido para este curso.", "info")
                conn.close()
                return redirect(url_for("programacion_sugeridos", curso_id=curso_id))

            conn.execute(
                """
                INSERT INTO docente_sugerido_curso (curso_id, docente_id, estado)
                VALUES (?, ?, 'SUGERIDO')
                """,
                (curso_id, docente_id),
            )
            conn.commit()
            conn.close()

            flash("Docente agregado como sugerido ✅", "success")
            return redirect(url_for("programacion_sugeridos", curso_id=curso_id))

        # GET: cargamos docentes y sugeridos
        docentes = conn.execute(
            """
            SELECT id, nombre_completo, dni, tipo_docente
            FROM docente
            WHERE activo = 1
            ORDER BY nombre_completo
            """
        ).fetchall()

        sugeridos = conn.execute(
            """
            SELECT dsc.id,
                   d.id AS docente_id,
                   d.nombre_completo,
                   d.dni,
                   d.tipo_docente
            FROM docente_sugerido_curso dsc
            JOIN docente d ON d.id = dsc.docente_id
            WHERE dsc.curso_id = ?
              AND dsc.estado = 'SUGERIDO'
            ORDER BY d.nombre_completo
            """,
            (curso_id,),
        ).fetchall()

        conn.close()

        return render_template(
            "curso_sugeridos.html",
            curso=curso,
            docentes=docentes,
            sugeridos=sugeridos,
        )

    @app.route(
        "/programacion/<int:curso_id>/sugeridos/<int:sugerido_id>/eliminar",
        methods=["POST"],
    )
    def programacion_sugerido_eliminar(curso_id, sugerido_id):
        """
        Elimina una sugerencia (hard delete).
        """
        conn = get_db_connection()
        conn.execute(
            "DELETE FROM docente_sugerido_curso WHERE id = ? AND curso_id = ?",
            (sugerido_id, curso_id),
        )
        conn.commit()
        conn.close()

        flash("Sugerencia eliminada correctamente ✅", "success")
        return redirect(url_for("programacion_sugeridos", curso_id=curso_id))
