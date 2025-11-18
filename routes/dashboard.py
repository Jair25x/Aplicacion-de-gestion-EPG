# routes/dashboard.py
from flask import render_template
from db import get_db_connection


def register_dashboard_routes(app):
    # ====== Datos comunes inyectados a todas las vistas ======
    @app.context_processor
    def inject_common_filters():
        conn = get_db_connection()
        facultades = conn.execute(
            "SELECT id, nombre FROM facultad WHERE activo = 1 ORDER BY nombre"
        ).fetchall()

        periodos = conn.execute(
            "SELECT id, etiqueta FROM periodo ORDER BY anio DESC, mes DESC"
        ).fetchall()
        conn.close()

        tipos_programa = [
            ("", "Todos"),
            ("DOCTORADO", "Doctorado"),
            ("MAESTRIA", "Maestría"),
        ]

        tipos_docente_mes = [
            ("", "Todos"),
            ("LOCAL", "Local"),
            ("ORDINARIZADO", "Ordinarizado"),
        ]

        return dict(
            facultades_global=facultades,
            periodos_global=periodos,
            tipos_programa_global=tipos_programa,
            tipos_docente_mes_global=tipos_docente_mes,
        )

    # ====== Dashboard ======
    @app.route("/")
    def index():
        conn = get_db_connection()

        # Período actual: último por año/mes
        periodo = conn.execute(
            """
            SELECT id, etiqueta, anio, mes, periodo_academico
            FROM periodo
            ORDER BY anio DESC, mes DESC
            LIMIT 1
            """
        ).fetchone()

        if periodo:
            periodo_id = periodo["id"]
            etiqueta_periodo = periodo["etiqueta"]
        else:
            periodo_id = None
            etiqueta_periodo = "Sin periodos"

        # Total docentes activos
        row_doc = conn.execute(
            "SELECT COUNT(*) as c FROM docente WHERE activo = 1"
        ).fetchone()
        total_docentes = row_doc["c"] if row_doc else 0

        # Cursos y remuneración del período actual (si existe)
        if periodo_id is not None:
            row_cur = conn.execute(
                "SELECT COUNT(*) as c FROM curso_programado WHERE periodo_id = ?",
                (periodo_id,),
            ).fetchone()
            total_cursos = row_cur["c"] if row_cur else 0

            row_rem = conn.execute(
                """
                SELECT COALESCE(SUM(remuneracion_monto), 0) as total
                FROM curso_programado
                WHERE periodo_id = ?
                """,
                (periodo_id,),
            ).fetchone()
            total_rem = row_rem["total"] if row_rem else 0
        else:
            total_cursos = 0
            total_rem = 0

        # 👉 NUEVO: períodos académicos distintos para el combo SUNEDU
        periodos_academicos = conn.execute(
            """
            SELECT DISTINCT periodo_academico
            FROM periodo
            WHERE periodo_academico IS NOT NULL
              AND periodo_academico <> ''
            ORDER BY periodo_academico DESC
            """
        ).fetchall()

        conn.close()

        return render_template(
            "index.html",
            periodo=periodo,
            etiqueta_periodo=etiqueta_periodo,
            total_docentes=total_docentes,
            total_cursos=total_cursos,
            total_rem=total_rem,
            periodos_academicos=periodos_academicos,
        )
