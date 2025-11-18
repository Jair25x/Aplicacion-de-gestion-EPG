# routes/programas.py
from flask import render_template, request, redirect, url_for, flash
from db import get_db_connection
import sqlite3


def register_programas_routes(app):

    @app.route("/programas")
    def programas_list():
        """
        Listado + filtros de programas académicos.
        Filtros:
          - facultad_id
          - tipo (DOCTORADO / MAESTRIA / PREGRADO)
          - solo_activos
          - q (búsqueda por nombre / mención / promoción)
        """

        facultad_id = request.args.get("facultad_id", type=int)
        tipo = request.args.get("tipo", "").strip()
        solo_activos = request.args.get("solo_activos", "") == "1"
        q = request.args.get("q", "").strip()

        conn = get_db_connection()

        # Catálogo de facultades para el filtro
        facultades = conn.execute(
            "SELECT id, nombre FROM facultad WHERE activo = 1 ORDER BY nombre"
        ).fetchall()

        filtros = []
        params = []

        if facultad_id:
            filtros.append("pa.facultad_id = ?")
            params.append(facultad_id)

        if tipo:
            filtros.append("pa.tipo = ?")
            params.append(tipo)

        if solo_activos:
            filtros.append("pa.activo = 1")

        if q:
            filtros.append(
                "("
                "pa.nombre_corto LIKE ? OR "
                "IFNULL(pa.mencion, '') LIKE ? OR "
                "IFNULL(pa.promocion, '') LIKE ?"
                ")"
            )
            like_q = f"%{q}%"
            params.extend([like_q, like_q, like_q])

        where_clause = " AND ".join(filtros) if filtros else "1 = 1"

        sql = f"""
            SELECT
                pa.id,
                pa.nombre_corto,
                pa.mencion,
                pa.promocion,
                pa.tipo,
                pa.modalidad,
                pa.activo,
                f.nombre AS facultad_nombre
            FROM programa_academico pa
            JOIN facultad f ON f.id = pa.facultad_id
            WHERE {where_clause}
            ORDER BY f.nombre, pa.tipo DESC, pa.nombre_corto
        """

        programas = conn.execute(sql, params).fetchall()
        conn.close()

        tipos_programa = [
            ("", "Todos"),
            ("DOCTORADO", "Doctorados"),
            ("MAESTRIA", "Maestrías"),
            ("PREGRADO", "Pregrado"),
        ]

        return render_template(
            "programas_list.html",
            programas=programas,
            facultades=facultades,
            tipos_programa=tipos_programa,
            facultad_id=facultad_id,
            tipo=tipo,
            solo_activos=solo_activos,
            q=q,
        )

    @app.route("/programas/nuevo", methods=["GET", "POST"])
    def programa_nuevo():
        conn = get_db_connection()
        facultades = conn.execute(
            "SELECT id, nombre FROM facultad WHERE activo = 1 ORDER BY nombre"
        ).fetchall()

        if request.method == "POST":
            facultad_id = request.form.get("facultad_id")
            tipo = request.form.get("tipo", "").strip()
            nombre_corto = request.form.get("nombre_corto", "").strip()
            mencion = request.form.get("mencion", "").strip() or None
            promocion = request.form.get("promocion", "").strip() or None
            modalidad = request.form.get("modalidad", "").strip() or None
            activo = 1 if request.form.get("activo") == "1" else 0

            if not facultad_id or not tipo or not nombre_corto:
                flash(
                    "Facultad, tipo de programa y nombre corto son obligatorios.",
                    "danger",
                )
                return render_template(
                    "programa_form.html",
                    programa=None,
                    facultades=facultades,
                )

            try:
                conn.execute(
                    """
                    INSERT INTO programa_academico (
                        facultad_id, tipo, nombre_corto, mencion, promocion,
                        modalidad, activo
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        facultad_id,
                        tipo,
                        nombre_corto,
                        mencion,
                        promocion,
                        modalidad,
                        activo,
                    ),
                )
                conn.commit()
                flash("Programa académico creado correctamente ✅", "success")
                return redirect(url_for("programas_list"))
            except sqlite3.Error as e:
                flash(f"Error al crear el programa: {e}", "danger")
                return render_template(
                    "programa_form.html",
                    programa=None,
                    facultades=facultades,
                )
            finally:
                conn.close()

        conn.close()
        return render_template(
            "programa_form.html",
            programa=None,
            facultades=facultades,
        )

    @app.route("/programas/<int:programa_id>/editar", methods=["GET", "POST"])
    def programa_editar(programa_id):
        conn = get_db_connection()
        programa = conn.execute(
            """
            SELECT pa.*
            FROM programa_academico pa
            WHERE pa.id = ?
            """,
            (programa_id,),
        ).fetchone()

        if not programa:
            conn.close()
            flash("Programa académico no encontrado.", "danger")
            return redirect(url_for("programas_list"))

        facultades = conn.execute(
            "SELECT id, nombre FROM facultad WHERE activo = 1 ORDER BY nombre"
        ).fetchall()

        if request.method == "POST":
            facultad_id = request.form.get("facultad_id")
            tipo = request.form.get("tipo", "").strip()
            nombre_corto = request.form.get("nombre_corto", "").strip()
            mencion = request.form.get("mencion", "").strip() or None
            promocion = request.form.get("promocion", "").strip() or None
            modalidad = request.form.get("modalidad", "").strip() or None
            activo = 1 if request.form.get("activo") == "1" else 0

            if not facultad_id or not tipo or not nombre_corto:
                flash(
                    "Facultad, tipo de programa y nombre corto son obligatorios.",
                    "danger",
                )
                return render_template(
                    "programa_form.html",
                    programa=programa,
                    facultades=facultades,
                )

            try:
                conn.execute(
                    """
                    UPDATE programa_academico
                    SET facultad_id = ?,
                        tipo = ?,
                        nombre_corto = ?,
                        mencion = ?,
                        promocion = ?,
                        modalidad = ?,
                        activo = ?
                    WHERE id = ?
                    """,
                    (
                        facultad_id,
                        tipo,
                        nombre_corto,
                        mencion,
                        promocion,
                        modalidad,
                        activo,
                        programa_id,
                    ),
                )
                conn.commit()
                flash("Programa académico actualizado correctamente ✅", "success")
                return redirect(url_for("programas_list"))
            except sqlite3.Error as e:
                flash(f"Error al actualizar el programa: {e}", "danger")
                return render_template(
                    "programa_form.html",
                    programa=programa,
                    facultades=facultades,
                )
            finally:
                conn.close()

        conn.close()
        return render_template(
            "programa_form.html",
            programa=programa,
            facultades=facultades,
        )

    @app.route("/programas/<int:programa_id>/toggle_activo", methods=["POST"])
    def programa_toggle_activo(programa_id):
        """
        Activar / desactivar un programa desde el listado.
        """

        conn = get_db_connection()
        row = conn.execute(
            "SELECT activo FROM programa_academico WHERE id = ?",
            (programa_id,),
        ).fetchone()

        if not row:
            conn.close()
            flash("Programa académico no encontrado.", "danger")
            return redirect(url_for("programas_list"))

        nuevo_estado = 0 if row["activo"] else 1
        conn.execute(
            "UPDATE programa_academico SET activo = ? WHERE id = ?",
            (nuevo_estado, programa_id),
        )
        conn.commit()
        conn.close()

        msg = (
            "Programa desactivado correctamente."
            if nuevo_estado == 0
            else "Programa reactivado correctamente."
        )
        flash(msg + " ✅", "info")

        # Preservar filtros actuales
        facultad_id = request.form.get("facultad_id")
        tipo = request.form.get("tipo", "")
        solo_activos = request.form.get("solo_activos", "")
        q = request.form.get("q", "")

        return redirect(
            url_for(
                "programas_list",
                facultad_id=facultad_id,
                tipo=tipo,
                solo_activos=solo_activos,
                q=q,
            )
        )
