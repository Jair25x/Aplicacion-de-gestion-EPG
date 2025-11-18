# routes/periodos.py
from flask import render_template, request, redirect, url_for, flash
import sqlite3
from db import get_db_connection


def _compute_periodo_academico(anio: int, mes: int, valor_form: str | None) -> str:
    """
    Calcula el período académico en formato 'YYYY-I/II/III'.

    - Si el usuario ingresó algo en el formulario, se respeta (normalizado).
    - Si viene vacío, se calcula:
        I  -> meses 1 a 4
        II -> meses 5 a 8
        III-> meses 9 a 12
    """
    if valor_form:
        return valor_form.strip().upper()

    if 1 <= mes <= 4:
        sufijo = "I"
    elif 5 <= mes <= 8:
        sufijo = "II"
    else:
        sufijo = "III"

    return f"{anio}-{sufijo}"


def register_periodos_routes(app):

    @app.route("/periodos")
    def periodos_list():
        conn = get_db_connection()
        periodos = conn.execute(
            """
            SELECT p.*,
                (
                    SELECT COUNT(*)
                    FROM curso_programado cp
                    WHERE cp.periodo_id = p.id
                ) AS total_cursos
            FROM periodo p
            ORDER BY p.anio DESC, p.mes DESC
            """
        ).fetchall()
        conn.close()
        return render_template("periodos_list.html", periodos=periodos)

    @app.route("/periodos/nuevo", methods=["GET", "POST"])
    def periodo_nuevo():
        if request.method == "POST":
            anio = request.form.get("anio", "").strip()
            mes = request.form.get("mes", "").strip()
            etiqueta = request.form.get("etiqueta", "").strip()
            periodo_academico_form = request.form.get(
                "periodo_academico", ""
            ).strip()

            if not anio or not mes or not etiqueta:
                flash("Año, mes y etiqueta son obligatorios", "danger")
                return render_template("periodo_form.html", periodo=None)

            try:
                anio_int = int(anio)
                mes_int = int(mes)
                if mes_int < 1 or mes_int > 12:
                    raise ValueError
            except ValueError:
                flash("Mes debe ser un número entre 1 y 12", "danger")
                return render_template("periodo_form.html", periodo=None)

            periodo_academico = _compute_periodo_academico(
                anio_int, mes_int, periodo_academico_form or None
            )

            conn = get_db_connection()
            try:
                conn.execute(
                    """
                    INSERT INTO periodo (anio, mes, etiqueta, periodo_academico)
                    VALUES (?, ?, ?, ?)
                    """,
                    (anio_int, mes_int, etiqueta, periodo_academico),
                )
                conn.commit()
                flash("Período creado correctamente ✅", "success")
                return redirect(url_for("periodos_list"))
            except sqlite3.IntegrityError:
                flash(
                    "Ya existe un período con ese año y mes",
                    "danger",
                )
                return render_template("periodo_form.html", periodo=None)
            finally:
                conn.close()

        return render_template("periodo_form.html", periodo=None)

    @app.route("/periodos/<int:periodo_id>/editar", methods=["GET", "POST"])
    def periodo_editar(periodo_id):
        conn = get_db_connection()
        periodo = conn.execute(
            """
            SELECT id, etiqueta, anio, mes, periodo_academico
            FROM periodo
            ORDER BY anio DESC, mes DESC
            LIMIT 1
            """
        ).fetchone()
        if not periodo:
            conn.close()
            flash("Período no encontrado", "danger")
            return redirect(url_for("periodos_list"))

        if request.method == "POST":
            anio = request.form.get("anio", "").strip()
            mes = request.form.get("mes", "").strip()
            etiqueta = request.form.get("etiqueta", "").strip()
            periodo_academico_form = request.form.get(
                "periodo_academico", ""
            ).strip()

            if not anio or not mes or not etiqueta:
                flash("Año, mes y etiqueta son obligatorios", "danger")
                return render_template("periodo_form.html", periodo=periodo)

            try:
                anio_int = int(anio)
                mes_int = int(mes)
                if mes_int < 1 or mes_int > 12:
                    raise ValueError
            except ValueError:
                flash("Mes debe ser un número entre 1 y 12", "danger")
                return render_template("periodo_form.html", periodo=periodo)

            periodo_academico = _compute_periodo_academico(
                anio_int, mes_int, periodo_academico_form or None
            )

            try:
                conn.execute(
                    """
                    UPDATE periodo
                    SET anio = ?, mes = ?, etiqueta = ?, periodo_academico = ?
                    WHERE id = ?
                    """,
                    (anio_int, mes_int, etiqueta, periodo_academico, periodo_id),
                )
                conn.commit()
                flash("Período actualizado correctamente ✅", "success")
                return redirect(url_for("periodos_list"))
            except sqlite3.IntegrityError:
                flash(
                    "Ya existe un período con ese año y mes",
                    "danger",
                )
                return render_template("periodo_form.html", periodo=periodo)
            finally:
                conn.close()

        conn.close()
        return render_template("periodo_form.html", periodo=periodo)

    @app.route("/periodos/<int:periodo_id>/eliminar", methods=["POST"])
    def periodo_eliminar(periodo_id):
        conn = get_db_connection()
        cursos = conn.execute(
            "SELECT COUNT(*) as c FROM curso_programado WHERE periodo_id = ?",
            (periodo_id,),
        ).fetchone()["c"]

        if cursos > 0:
            conn.close()
            flash(
                "No se puede eliminar el período porque tiene cursos programados.",
                "danger",
            )
            return redirect(url_for("periodos_list"))

        conn.execute("DELETE FROM periodo WHERE id = ?", (periodo_id,))
        conn.commit()
        conn.close()
        flash("Período eliminado correctamente ✅", "success")
        return redirect(url_for("periodos_list"))
