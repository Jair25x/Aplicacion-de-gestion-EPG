# routes/docentes.py
from flask import render_template, request, redirect, url_for, flash
import sqlite3
from db import get_db_connection


def register_docentes_routes(app):

    @app.route("/docentes")
    def docentes_list():
        tipo_docente = request.args.get("tipo_docente", "").strip()
        q = request.args.get("q", "").strip()
        periodo_propuesto_id = request.args.get(
            "periodo_propuesto_id", type=int
        )
        solo_con_cv = request.args.get("solo_con_cv", "") == "1"
        solo_propuestos = request.args.get("solo_propuestos", "") == "1"
        solo_sugeridos = request.args.get("solo_sugeridos", "") == "1"

        conn = get_db_connection()

        # Catálogo de periodos para el combo "Período para propuestos"
        periodos_global = conn.execute(
            "SELECT id, etiqueta, periodo_academico FROM periodo ORDER BY anio DESC, mes DESC"
        ).fetchall()

        # 👉 NUEVO: lista de períodos académicos distintos para el botón SUNEDU
        periodos_academicos = conn.execute(
            """
            SELECT DISTINCT periodo_academico
            FROM periodo
            WHERE periodo_academico IS NOT NULL
              AND periodo_academico <> ''
            ORDER BY periodo_academico DESC
            """
        ).fetchall()

        # Período actual (último por año/mes)
        periodo_actual = conn.execute(
            "SELECT id FROM periodo ORDER BY anio DESC, mes DESC LIMIT 1"
        ).fetchone()
        periodo_actual_id = periodo_actual["id"] if periodo_actual else None

        # Filtro para contar cursos solo del período actual (para columna cantidad_cursos)
        if periodo_actual_id is not None:
            periodo_cursos_filter = f"AND cp.periodo_id = {periodo_actual_id}"
            periodo_sugeridos_filter = f"AND cp2.periodo_id = {periodo_actual_id}"
            periodo_solo_sugeridos_filter = f"AND cp3.periodo_id = {periodo_actual_id}"
        else:
            periodo_cursos_filter = ""
            periodo_sugeridos_filter = ""
            periodo_solo_sugeridos_filter = ""

        params: list = []

        # Columna booleana "es_propuesto" + condición para filtrar solo propuestos
        if periodo_propuesto_id:
            sub_existe_propuesto = """
              CASE WHEN EXISTS(
                SELECT 1 FROM docente_propuesto dp
                WHERE dp.docente_id = d.id
                  AND dp.periodo_id = ?
              ) THEN 1 ELSE 0 END AS es_propuesto
            """
            existe_condicion = """
              EXISTS(
                SELECT 1 FROM docente_propuesto dp2
                WHERE dp2.docente_id = d.id
                  AND dp2.periodo_id = ?
              )
            """
            # Primer parámetro corresponde a la columna calculada es_propuesto
            params.append(periodo_propuesto_id)
        else:
            sub_existe_propuesto = """
              CASE WHEN EXISTS(
                SELECT 1 FROM docente_propuesto dp
                WHERE dp.docente_id = d.id
              ) THEN 1 ELSE 0 END AS es_propuesto
            """
            existe_condicion = """
              EXISTS(
                SELECT 1 FROM docente_propuesto dp2
                WHERE dp2.docente_id = d.id
              )
            """

        # Query base con:
        # - cantidad_cursos (período actual)
        # - cantidad_sugeridos (período actual)
        # - es_propuesto (para el período seleccionado o cualquiera)
        base_query = f"""
            SELECT d.*,
                (
                    SELECT COUNT(*)
                    FROM curso_programado cp
                    WHERE cp.docente_id = d.id
                    {periodo_cursos_filter}
                ) AS cantidad_cursos,
                (
                    SELECT COUNT(*)
                    FROM docente_sugerido_curso dsc
                    JOIN curso_programado cp2 ON cp2.id = dsc.curso_id
                    WHERE dsc.docente_id = d.id
                      AND dsc.estado = 'SUGERIDO'
                      {periodo_sugeridos_filter}
                ) AS cantidad_sugeridos,
                {sub_existe_propuesto}
            FROM docente d
            WHERE d.activo = 1
        """

        # Filtros adicionales
        if tipo_docente:
            base_query += " AND d.tipo_docente = ?"
            params.append(tipo_docente)

        if q:
            base_query += " AND (d.nombre_completo LIKE ? OR d.dni LIKE ?)"
            like_q = f"%{q}%"
            params.extend([like_q, like_q])

        if solo_con_cv:
            base_query += " AND d.tiene_cv = 1"

        if solo_propuestos:
            base_query += f" AND {existe_condicion}"
            if periodo_propuesto_id:
                # Segundo uso del período (para el WHERE EXISTS)
                params.append(periodo_propuesto_id)

        if solo_sugeridos:
            base_query += f"""
              AND EXISTS (
                SELECT 1
                FROM docente_sugerido_curso dsc3
                JOIN curso_programado cp3 ON cp3.id = dsc3.curso_id
                WHERE dsc3.docente_id = d.id
                  AND dsc3.estado = 'SUGERIDO'
                  {periodo_solo_sugeridos_filter}
              )
            """

        base_query += " ORDER BY d.nombre_completo ASC"

        docentes = conn.execute(base_query, params).fetchall()
        conn.close()

        return render_template(
            "docentes_list.html",
            docentes=docentes,
            tipo_docente=tipo_docente,
            q=q,
            periodo_propuesto_id=periodo_propuesto_id or "",
            solo_con_cv=solo_con_cv,
            solo_propuestos=solo_propuestos,
            solo_sugeridos=solo_sugeridos,
            periodos_global=periodos_global,
            # 👉 NUEVO: para el botón de export SUNEDU en esta vista
            periodos_academicos=periodos_academicos,
        )
        
    @app.route("/docentes/<int:docente_id>/sugerencias")
    def docente_sugerencias(docente_id):
        """
        Vista de detalle: muestra todos los cursos en los que
        el docente está sugerido (docente_sugerido_curso),
        con filtros por período y estado.
        """
        periodo_id = request.args.get("periodo_id", type=int)
        estado = request.args.get("estado", "").strip() or None

        conn = get_db_connection()

        # 1) Datos del docente
        docente = conn.execute(
            "SELECT * FROM docente WHERE id = ?",
            (docente_id,),
        ).fetchone()

        if not docente:
            conn.close()
            flash("Docente no encontrado", "danger")
            return redirect(url_for("docentes_list"))

        # 2) Períodos en los que el docente tiene cursos sugeridos
        periodos_docente = conn.execute(
            """
            SELECT DISTINCT p.id, p.etiqueta, p.periodo_academico, p.anio, p.mes
            FROM docente_sugerido_curso dsc
            JOIN curso_programado cp ON cp.id = dsc.curso_id
            JOIN periodo p ON p.id = cp.periodo_id
            WHERE dsc.docente_id = ?
            ORDER BY p.anio DESC, p.mes DESC
            """,
            (docente_id,),
        ).fetchall()

        # 3) Lista de cursos donde está sugerido el docente
        params = [docente_id]
        query_sugerencias = """
            SELECT
                dsc.id AS sugerencia_id,
                dsc.estado,

                cp.id AS curso_id,
                cp.asignatura AS nombre_curso,
                cp.codigo AS codigo_curso,
                cp.modalidad_dictado AS modalidad,
                cp.fecha_inicio,
                cp.fecha_fin,

                p.id AS periodo_id,
                p.etiqueta,
                p.periodo_academico,
                p.anio,
                p.mes,

                pa.nombre_corto AS programa_nombre_corto
            FROM docente_sugerido_curso dsc
            JOIN curso_programado cp ON cp.id = dsc.curso_id
            JOIN periodo p ON p.id = cp.periodo_id
            LEFT JOIN programa_academico pa ON pa.id = cp.programa_id
            WHERE dsc.docente_id = ?
        """

        if periodo_id:
            query_sugerencias += " AND cp.periodo_id = ?"
            params.append(periodo_id)

        if estado:
            query_sugerencias += " AND dsc.estado = ?"
            params.append(estado)

        query_sugerencias += """
            ORDER BY p.anio DESC, p.mes DESC, cp.fecha_inicio, cp.id
        """

        sugerencias = conn.execute(query_sugerencias, params).fetchall()

        # 4) Resumen por estado (chips de arriba)
        params_resumen = [docente_id]
        query_resumen = """
            SELECT dsc.estado, COUNT(*) AS total
            FROM docente_sugerido_curso dsc
            JOIN curso_programado cp ON cp.id = dsc.curso_id
            WHERE dsc.docente_id = ?
        """

        if periodo_id:
            query_resumen += " AND cp.periodo_id = ?"
            params_resumen.append(periodo_id)

        query_resumen += " GROUP BY dsc.estado ORDER BY dsc.estado"

        resumen_estados = conn.execute(query_resumen, params_resumen).fetchall()

        conn.close()

        return render_template(
            "docente_sugerencias.html",
            docente=docente,
            sugerencias=sugerencias,
            periodos_docente=periodos_docente,
            periodo_id=periodo_id or "",
            estado=estado or "",
            resumen_estados=resumen_estados,
        )

    @app.route("/docentes/nuevo", methods=["GET", "POST"])
    def docente_nuevo():
        if request.method == "POST":
            apellido_paterno = request.form.get("apellido_paterno", "").strip() or None
            apellido_materno = request.form.get("apellido_materno", "").strip() or None
            nombres = request.form.get("nombres", "").strip() or None

            nombre_completo = request.form.get("nombre_completo", "").strip()
            dni = request.form.get("dni", "").strip() or None
            pais_nacionalidad = request.form.get("pais_nacionalidad", "").strip() or None
            direccion = request.form.get("direccion", "").strip() or None
            especialidad = request.form.get("especialidad", "").strip() or None
            telefono = request.form.get("telefono", "").strip() or None
            correo = request.form.get("correo", "").strip() or None

            fecha_ingreso_universidad = (
                request.form.get("fecha_ingreso_universidad", "").strip() or None
            )
            categoria_docente = (
                request.form.get("categoria_docente", "").strip() or None
            )
            regimen_dedicacion = (
                request.form.get("regimen_dedicacion", "").strip() or None
            )
            tipo_docente = request.form.get("tipo_docente", "").strip() or None

            es_docente_investigador = (
                1 if request.form.get("es_docente_investigador") == "1" else 0
            )
            registrado_en_dina = (
                1 if request.form.get("registrado_en_dina") == "1" else 0
            )
            era_docente_antes_ley_30220 = (
                1 if request.form.get("era_docente_antes_ley_30220") == "1" else 0
            )

            puede_pregrado = 1 if request.form.get("puede_pregrado") == "1" else 0
            puede_maestria = 1 if request.form.get("puede_maestria") == "1" else 0
            puede_doctorado = 1 if request.form.get("puede_doctorado") == "1" else 0

            titulo_profesional = (
                request.form.get("titulo_profesional", "").strip() or None
            )
            titulo_fecha = request.form.get("titulo_fecha", "").strip() or None
            titulo_universidad = (
                request.form.get("titulo_universidad", "").strip() or None
            )

            grado_magister = request.form.get("grado_magister", "").strip() or None
            magister_fecha = request.form.get("magister_fecha", "").strip() or None
            magister_universidad = (
                request.form.get("magister_universidad", "").strip() or None
            )

            grado_doctor = request.form.get("grado_doctor", "").strip() or None
            doctor_fecha = request.form.get("doctor_fecha", "").strip() or None
            doctor_universidad = (
                request.form.get("doctor_universidad", "").strip() or None
            )

            mayor_grado_academico = (
                request.form.get("mayor_grado_academico", "").strip() or None
            )
            mayor_grado_mencion = (
                request.form.get("mayor_grado_mencion", "").strip() or None
            )
            universidad_procedencia = (
                request.form.get("universidad_procedencia", "").strip() or None
            )

            tiene_cv = 1 if request.form.get("tiene_cv") == "1" else 0
            link_cv = request.form.get("link_cv", "").strip() or None
            fecha_recepcion_cv = (
                request.form.get("fecha_recepcion_cv", "").strip() or None
            )

            antecedentes = request.form.get("antecedentes", "").strip() or None

            if not nombre_completo:
                flash("Nombre completo es obligatorio", "danger")
                return render_template("docente_form.html", docente=None)

            conn = get_db_connection()
            try:
                conn.execute(
                    """
                    INSERT INTO docente (
                        apellido_paterno,
                        apellido_materno,
                        nombres,
                        nombre_completo,
                        especialidad,
                        dni,
                        pais_nacionalidad,
                        direccion,
                        correo,
                        telefono,
                        fecha_ingreso_universidad,
                        era_docente_antes_ley_30220,
                        categoria_docente,
                        regimen_dedicacion,
                        es_docente_investigador,
                        registrado_en_dina,
                        puede_pregrado,
                        puede_maestria,
                        puede_doctorado,
                        titulo_profesional,
                        titulo_fecha,
                        titulo_universidad,
                        grado_magister,
                        magister_fecha,
                        magister_universidad,
                        grado_doctor,
                        doctor_fecha,
                        doctor_universidad,
                        universidad_procedencia,
                        mayor_grado_academico,
                        mayor_grado_mencion,
                        antecedentes,
                        tipo_docente,
                        tiene_cv,
                        link_cv,
                        fecha_recepcion_cv
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                    """,
                    (
                        apellido_paterno,
                        apellido_materno,
                        nombres,
                        nombre_completo,
                        especialidad,
                        dni,
                        pais_nacionalidad,
                        direccion,
                        correo,
                        telefono,
                        fecha_ingreso_universidad,
                        era_docente_antes_ley_30220,
                        categoria_docente,
                        regimen_dedicacion,
                        es_docente_investigador,
                        registrado_en_dina,
                        puede_pregrado,
                        puede_maestria,
                        puede_doctorado,
                        titulo_profesional,
                        titulo_fecha,
                        titulo_universidad,
                        grado_magister,
                        magister_fecha,
                        magister_universidad,
                        grado_doctor,
                        doctor_fecha,
                        doctor_universidad,
                        universidad_procedencia,
                        mayor_grado_academico,
                        mayor_grado_mencion,
                        antecedentes,
                        tipo_docente,
                        tiene_cv,
                        link_cv,
                        fecha_recepcion_cv,
                    ),
                )
                conn.commit()
                flash("Docente creado correctamente ✅", "success")
                return redirect(url_for("docentes_list"))
            except sqlite3.IntegrityError:
                flash("Ya existe un docente con ese DNI", "danger")
                return render_template("docente_form.html", docente=None)
            finally:
                conn.close()

        return render_template("docente_form.html", docente=None)

    @app.route("/docentes/<int:docente_id>/editar", methods=["GET", "POST"])
    def docente_editar(docente_id):
        conn = get_db_connection()
        docente = conn.execute(
            "SELECT * FROM docente WHERE id = ?", (docente_id,)
        ).fetchone()
        if not docente:
            conn.close()
            flash("Docente no encontrado", "danger")
            return redirect(url_for("docentes_list"))

        if request.method == "POST":
            apellido_paterno = request.form.get("apellido_paterno", "").strip() or None
            apellido_materno = request.form.get("apellido_materno", "").strip() or None
            nombres = request.form.get("nombres", "").strip() or None

            nombre_completo = request.form.get("nombre_completo", "").strip()
            dni = request.form.get("dni", "").strip() or None
            pais_nacionalidad = request.form.get("pais_nacionalidad", "").strip() or None
            direccion = request.form.get("direccion", "").strip() or None
            especialidad = request.form.get("especialidad", "").strip() or None
            telefono = request.form.get("telefono", "").strip() or None
            correo = request.form.get("correo", "").strip() or None

            fecha_ingreso_universidad = (
                request.form.get("fecha_ingreso_universidad", "").strip() or None
            )
            categoria_docente = (
                request.form.get("categoria_docente", "").strip() or None
            )
            regimen_dedicacion = (
                request.form.get("regimen_dedicacion", "").strip() or None
            )
            tipo_docente = request.form.get("tipo_docente", "").strip() or None

            es_docente_investigador = (
                1 if request.form.get("es_docente_investigador") == "1" else 0
            )
            registrado_en_dina = (
                1 if request.form.get("registrado_en_dina") == "1" else 0
            )
            era_docente_antes_ley_30220 = (
                1 if request.form.get("era_docente_antes_ley_30220") == "1" else 0
            )

            puede_pregrado = 1 if request.form.get("puede_pregrado") == "1" else 0
            puede_maestria = 1 if request.form.get("puede_maestria") == "1" else 0
            puede_doctorado = 1 if request.form.get("puede_doctorado") == "1" else 0

            titulo_profesional = (
                request.form.get("titulo_profesional", "").strip() or None
            )
            titulo_fecha = request.form.get("titulo_fecha", "").strip() or None
            titulo_universidad = (
                request.form.get("titulo_universidad", "").strip() or None
            )

            grado_magister = request.form.get("grado_magister", "").strip() or None
            magister_fecha = request.form.get("magister_fecha", "").strip() or None
            magister_universidad = (
                request.form.get("magister_universidad", "").strip() or None
            )

            grado_doctor = request.form.get("grado_doctor", "").strip() or None
            doctor_fecha = request.form.get("doctor_fecha", "").strip() or None
            doctor_universidad = (
                request.form.get("doctor_universidad", "").strip() or None
            )

            mayor_grado_academico = (
                request.form.get("mayor_grado_academico", "").strip() or None
            )
            mayor_grado_mencion = (
                request.form.get("mayor_grado_mencion", "").strip() or None
            )
            universidad_procedencia = (
                request.form.get("universidad_procedencia", "").strip() or None
            )

            tiene_cv = 1 if request.form.get("tiene_cv") == "1" else 0
            link_cv = request.form.get("link_cv", "").strip() or None
            fecha_recepcion_cv = (
                request.form.get("fecha_recepcion_cv", "").strip() or None
            )

            antecedentes = request.form.get("antecedentes", "").strip() or None

            if not nombre_completo:
                flash("Nombre completo es obligatorio", "danger")
                conn.close()
                return render_template("docente_form.html", docente=docente)

            try:
                conn.execute(
                    """
                    UPDATE docente
                    SET apellido_paterno = ?,
                        apellido_materno = ?,
                        nombres = ?,
                        nombre_completo = ?,
                        especialidad = ?,
                        dni = ?,
                        pais_nacionalidad = ?,
                        direccion = ?,
                        correo = ?,
                        telefono = ?,
                        fecha_ingreso_universidad = ?,
                        era_docente_antes_ley_30220 = ?,
                        categoria_docente = ?,
                        regimen_dedicacion = ?,
                        es_docente_investigador = ?,
                        registrado_en_dina = ?,
                        puede_pregrado = ?,
                        puede_maestria = ?,
                        puede_doctorado = ?,
                        titulo_profesional = ?,
                        titulo_fecha = ?,
                        titulo_universidad = ?,
                        grado_magister = ?,
                        magister_fecha = ?,
                        magister_universidad = ?,
                        grado_doctor = ?,
                        doctor_fecha = ?,
                        doctor_universidad = ?,
                        universidad_procedencia = ?,
                        mayor_grado_academico = ?,
                        mayor_grado_mencion = ?,
                        antecedentes = ?,
                        tipo_docente = ?,
                        tiene_cv = ?,
                        link_cv = ?,
                        fecha_recepcion_cv = ?,
                        updated_at = datetime('now')
                    WHERE id = ?
                    """,
                    (
                        apellido_paterno,
                        apellido_materno,
                        nombres,
                        nombre_completo,
                        especialidad,
                        dni,
                        pais_nacionalidad,
                        direccion,
                        correo,
                        telefono,
                        fecha_ingreso_universidad,
                        era_docente_antes_ley_30220,
                        categoria_docente,
                        regimen_dedicacion,
                        es_docente_investigador,
                        registrado_en_dina,
                        puede_pregrado,
                        puede_maestria,
                        puede_doctorado,
                        titulo_profesional,
                        titulo_fecha,
                        titulo_universidad,
                        grado_magister,
                        magister_fecha,
                        magister_universidad,
                        grado_doctor,
                        doctor_fecha,
                        doctor_universidad,
                        universidad_procedencia,
                        mayor_grado_academico,
                        mayor_grado_mencion,
                        antecedentes,
                        tipo_docente,
                        tiene_cv,
                        link_cv,
                        fecha_recepcion_cv,
                        docente_id,
                    ),
                )
                conn.commit()
                flash("Docente actualizado correctamente ✅", "success")
                return redirect(url_for("docentes_list"))
            except sqlite3.IntegrityError:
                flash("Ya existe un docente con ese DNI", "danger")
                return render_template("docente_form.html", docente=docente)
            finally:
                conn.close()

        conn.close()
        return render_template("docente_form.html", docente=docente)

    @app.route("/docentes/<int:docente_id>/toggle_propuesto", methods=["POST"])
    def toggle_docente_propuesto(docente_id):
        periodo_id = request.form.get("periodo_id")
        if not periodo_id:
            flash("Periodo no especificado para propuesto", "danger")
            return redirect(url_for("docentes_list"))

        q = request.form.get("q", "")
        tipo_docente = request.form.get("tipo_docente", "")
        periodo_propuesto_id = request.form.get("periodo_propuesto_id", "")
        solo_con_cv = request.form.get("solo_con_cv", "")
        solo_propuestos = request.form.get("solo_propuestos", "")
        solo_sugeridos = request.form.get("solo_sugeridos", "")

        conn = get_db_connection()
        existe = conn.execute(
            "SELECT id FROM docente_propuesto "
            "WHERE docente_id = ? AND periodo_id = ?",
            (docente_id, periodo_id),
        ).fetchone()

        if existe:
            conn.execute(
                "DELETE FROM docente_propuesto "
                "WHERE docente_id = ? AND periodo_id = ?",
                (docente_id, periodo_id),
            )
            msg = "Docente quitado de propuestos para ese período."
        else:
            conn.execute(
                """
                INSERT INTO docente_propuesto (docente_id, periodo_id, estado)
                VALUES (?, ?, 'PROPUESTO')
                """,
                (docente_id, periodo_id),
            )
            msg = "Docente marcado como propuesto para ese período."
        conn.commit()
        conn.close()

        flash(msg, "info")

        return redirect(
            url_for(
                "docentes_list",
                q=q,
                tipo_docente=tipo_docente,
                periodo_propuesto_id=periodo_propuesto_id,
                solo_con_cv=solo_con_cv,
                solo_propuestos=solo_propuestos,
                solo_sugeridos=solo_sugeridos,
            )
        )
