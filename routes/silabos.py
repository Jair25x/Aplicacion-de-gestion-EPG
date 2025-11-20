# routes/silabos.py

import os
import sqlite3
from flask import Blueprint, send_file, abort, render_template, request
from db import get_db_connection
from generar_cartas import generar_silabo_curso

bp = Blueprint("silabos", __name__, url_prefix="/silabos")


@bp.route("/", methods=["GET"])
def listar_silabos():
    """
    Pantalla para listar cursos por período y generar sílabos.
    URL: /silabos?periodo_id=<id>
    """
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    periodos = cur.execute(
        "SELECT id, etiqueta FROM periodo ORDER BY anio DESC, mes DESC"
    ).fetchall()

    periodo_id = request.args.get("periodo_id")

    cursos = []
    if periodo_id:
        cursos = cur.execute(
            """
            SELECT
                cp.*,
                p.periodo_academico,
                prog.id            AS programa_id,
                prog.nombre_corto  AS programa_nombre,
                d.nombre_completo  AS docente_nombre,
                d.correo           AS docente_correo
            FROM curso_programado cp
            JOIN periodo p ON p.id = cp.periodo_id
            JOIN programa_academico prog ON prog.id = cp.programa_id
            LEFT JOIN docente d ON d.id = cp.docente_id
            WHERE cp.periodo_id = ?
            ORDER BY prog.nombre_corto, cp.asignatura
            """,
            (periodo_id,),
        ).fetchall()

    conn.close()

    return render_template(
        "silabos_cursos.html",
        periodos=periodos,
        periodo_id=periodo_id,
        cursos=cursos,
    )


@bp.route("/curso/<int:curso_id>")
def generar_silabo_para_curso(curso_id: int):
    """
    Genera y descarga el sílabo para un curso_programado.
    URL: /silabos/curso/<curso_id>
    """
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    curso = cur.execute(
        """
        SELECT
            cp.*,
            p.periodo_academico,
            prog.id            AS programa_id,
            prog.nombre_corto  AS programa_nombre,
            d.nombre_completo  AS docente_nombre,
            d.correo           AS docente_correo
        FROM curso_programado cp
        JOIN periodo p ON p.id = cp.periodo_id
        JOIN programa_academico prog ON prog.id = cp.programa_id
        LEFT JOIN docente d ON d.id = cp.docente_id
        WHERE cp.id = ?
        """,
        (curso_id,),
    ).fetchone()

    if not curso:
        conn.close()
        abort(404, "Curso no encontrado")

    output_path = generar_silabo_curso(conn, curso)
    conn.close()

    if not os.path.exists(output_path):
        abort(500, "No se pudo generar el sílabo")

    return send_file(
        output_path,
        as_attachment=True,
        download_name=os.path.basename(output_path),
    )
