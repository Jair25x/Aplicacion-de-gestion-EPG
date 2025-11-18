# app.py
from flask import Flask
from config import SECRET_KEY
from db import ensure_columns, get_db_connection
from reporte_docentes_sunedu import register_sunedu_routes

from routes.dashboard import register_dashboard_routes
from routes.periodos import register_periodos_routes
from routes.docentes import register_docentes_routes
from routes.programacion import register_programacion_routes
from routes.export_routes import register_export_routes
from routes.cartas import register_cartas_routes
from routes.programas import register_programas_routes  # NUEVO


def create_app():
    app = Flask(__name__)
    app.secret_key = SECRET_KEY

    # Ajusta columnas si la DB viene de un schema anterior
    ensure_columns()

    # Registrar rutas por módulo
    register_dashboard_routes(app)
    register_periodos_routes(app)
    register_docentes_routes(app)
    register_programacion_routes(app)
    register_export_routes(app)
    register_cartas_routes(app)
    register_programas_routes(app)

    # Rutas del reporte SUNEDU
    register_sunedu_routes(app, get_db_connection)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
