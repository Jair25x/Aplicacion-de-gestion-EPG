# routes/cartas.py
from flask import render_template, request, redirect, url_for, flash, send_file
from db import get_db_connection
from config import CARTAS_OUTPUT_DIR, PLANTILLA_CARTA, TRY_PDF_WEB, docx2pdf_convert
from docxtpl import DocxTemplate
from generar_cartas import (
    fecha_larga_es,
    calc_remuneracion,
    limpiar_nombre_archivo,
    extraer_titulo_paterno_nombre,
    MESES_ES,
)
from utils_programas import normalizar_programa_base
from io import BytesIO
import zipfile


def register_cartas_routes(app):

    @app.route("/cartas_invitacion", methods=["GET", "POST"])
    def cartas_invitacion():
        """
        Vista para:
        - Elegir período
        - Ver cursos programados y estado de datos para carta
        - Seleccionar cursos y generar cartas .docx/.pdf (ZIP)
        """
        conn = get_db_connection()
        cur = conn.cursor()

        # Períodos para el combo
        periodos = cur.execute(
            "SELECT id, etiqueta FROM periodo ORDER BY anio DESC, mes DESC"
        ).fetchall()

        # Determinar período seleccionado (GET o POST)
        periodo_id = request.args.get("periodo_id") or request.form.get("periodo_id")

        # -------- GET: mostrar listado de cursos del período --------
        if request.method == "GET":
            cursos = []
            if periodo_id:
                cursos = cur.execute(
                    """
                    SELECT cp.*,
                           d.nombre_completo AS docente_nombre,
                           pa.nombre_corto   AS programa_nombre,
                           pa.tipo           AS programa_tipo,
                           pa.modalidad      AS programa_modalidad
                    FROM curso_programado cp
                    JOIN programa_academico pa ON pa.id = cp.programa_id
                    LEFT JOIN docente d ON d.id = cp.docente_id
                    WHERE cp.periodo_id = ?
                    ORDER BY programa_nombre, asignatura
                    """,
                    (periodo_id,),
                ).fetchall()

            conn.close()
            return render_template(
                "cartas_invitacion.html",
                periodos=periodos,
                periodo_id=periodo_id,
                cursos=cursos,
            )

        # -------- POST: generar cartas --------
        if not PLANTILLA_CARTA.exists():
            conn.close()
            flash(
                f"No se encuentra la plantilla de carta: {PLANTILLA_CARTA.name}. "
                f"Colócala en la misma carpeta que app.py.",
                "danger",
            )
            return redirect(url_for("cartas_invitacion", periodo_id=periodo_id))

        selected_ids = request.form.getlist("curso_id")
        if not selected_ids:
            conn.close()
            flash("No seleccionaste ningún curso para generar cartas.", "warning")
            return redirect(url_for("cartas_invitacion", periodo_id=periodo_id))

        # N° de carta inicial (opcional)
        start_num_str = request.form.get("start_num") or ""
        try:
            next_num = int(start_num_str) if start_num_str else None
        except ValueError:
            next_num = None

        # Info del período (para carpeta)
        periodo_row = None
        if periodo_id:
            periodo_row = cur.execute(
                "SELECT id, etiqueta, anio, mes FROM periodo WHERE id = ?",
                (periodo_id,),
            ).fetchone()

        placeholders = ",".join("?" for _ in selected_ids)

        rows = cur.execute(
            f"""
            SELECT cp.*,
                   d.nombre_completo AS docente_nombre,
                   pa.nombre_corto   AS programa_nombre,
                   pa.tipo           AS programa_tipo,
                   pa.modalidad      AS programa_modalidad,
                   pe.anio           AS periodo_anio,
                   pe.mes            AS periodo_mes,
                   pe.etiqueta       AS periodo_etiqueta
            FROM curso_programado cp
            JOIN programa_academico pa ON pa.id = cp.programa_id
            JOIN periodo pe ON pe.id = cp.periodo_id
            LEFT JOIN docente d ON d.id = cp.docente_id
            WHERE cp.id IN ({placeholders})
            ORDER BY cp.id
            """,
            selected_ids,
        ).fetchall()

        if not rows:
            conn.close()
            flash("No se encontraron cursos para generar cartas.", "danger")
            return redirect(url_for("cartas_invitacion", periodo_id=periodo_id))

        # Carpeta específica del período
        if periodo_row:
            etiqueta_periodo = periodo_row["etiqueta"]
            periodo_anio_default = periodo_row["anio"]
            periodo_mes_default = periodo_row["mes"]
        else:
            etiqueta_periodo = rows[0]["periodo_etiqueta"]
            periodo_anio_default = rows[0]["periodo_anio"]
            periodo_mes_default = rows[0]["periodo_mes"]

        subdir_name = f"Cartas de invitación {etiqueta_periodo}"
        output_dir = CARTAS_OUTPUT_DIR / subdir_name
        output_dir.mkdir(parents=True, exist_ok=True)

        zip_buffer = BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for row in rows:
                docente = row["docente_nombre"] or "DOCENTE POR DEFINIR"
                asignatura = row["asignatura"]
                programa_nombre = row["programa_nombre"] or ""
                programa_tipo = (row["programa_tipo"] or "").upper()
                programa_modalidad = (row["programa_modalidad"] or "").strip()

                # Programa base (texto)
                programa_base = normalizar_programa_base(
                    programa_nombre, programa_tipo
                )
                if programa_tipo == "DOCTORADO":
                    programa_texto = f"del {programa_base}"
                elif programa_tipo == "MAESTRIA":
                    programa_texto = f"de la {programa_base}"
                else:
                    programa_texto = programa_base

                # Modalidad
                mod_up = programa_modalidad.upper()
                if mod_up == "DISTANCIA":
                    modalidad_texto = "MODALIDAD A DISTANCIA"
                elif mod_up:
                    modalidad_texto = f"MODALIDAD {mod_up}"
                else:
                    modalidad_texto = ""

                codigo = row["codigo"] or ""
                categoria = row["categoria"] or ""
                sem1 = row["sem1"] or ""
                sem2 = row["sem2"] or ""

                # Fecha larga SIEMPRE actual
                fecha_larga, anio = fecha_larga_es(None)
                ciudad = "Cusco"

                # MES en la tabla: a partir de periodo.anio / periodo.mes
                anio_periodo = row["periodo_anio"] or periodo_anio_default
                mes_periodo = row["periodo_mes"] or periodo_mes_default

                mes_tabla = ""
                try:
                    mes_int = int(mes_periodo)
                    if 1 <= mes_int <= 12:
                        mes_nombre = MESES_ES[mes_int - 1]
                        mes_tabla = f"{mes_nombre.upper()} {anio_periodo}"
                except Exception:
                    mes_tabla = ""

                if not mes_tabla:
                    # Fallback: etiqueta de periodo en mayúsculas
                    periodo_etiqueta_row = (
                        row["periodo_etiqueta"] or etiqueta_periodo
                    )
                    mes_tabla = (periodo_etiqueta_row or "").upper()

                # Remuneración por tabla (o override explícito)
                override = None
                if row["remuneracion_monto"] is not None:
                    override = str(row["remuneracion_monto"])
                remuneracion_num = calc_remuneracion(programa_texto, override)
                remuneracion = remuneracion_num

                # Numeración de carta con ceros a la izquierda
                if next_num is not None:
                    numero = f"{next_num:03d}"
                    next_num += 1
                else:
                    # Si no se indicó inicio, usamos "000"
                    numero = "000"

                titulo = ""  # si luego quieres "Dr." etc., se puede usar aquí

                context = {
                    "ciudad": ciudad,
                    "fecha_larga": fecha_larga,
                    "numero": numero,      # se usará en la plantilla: CARTA Nº {{ numero }}-{{ anio }}-EPG-UAC
                    "anio": anio,
                    "titulo": titulo,
                    "docente": docente,
                    "asignatura": asignatura,
                    "programa": programa_texto,
                    "modalidad": modalidad_texto,
                    "codigo": codigo,
                    "categoria": categoria,
                    "cred": "04",
                    "mes": mes_tabla,
                    "sem1": sem1,
                    "sem2": sem2,
                    "horarios": (
                        "VIERNES: 5-10 PM; SABADO: 8-1 PM Y 4 -9 PM; "
                        "DOMINGO: 8-1 PM"
                    ),
                    "remuneracion": remuneracion,
                }

                # Render de la plantilla DOCX
                tpl = DocxTemplate(str(PLANTILLA_CARTA))
                tpl.render(context)

                # Nombre de archivo: "CARTA N°{numero} {TITULO} {PATERNO} {NOMBRE}.docx"
                titulo_abrev, paterno, nombre = extraer_titulo_paterno_nombre(docente)

                if titulo_abrev:
                    file_stub = f"CARTA N°{numero} {titulo_abrev} {paterno} {nombre}"
                else:
                    file_stub = f"CARTA N°{numero} {paterno} {nombre}"

                filename_docx = limpiar_nombre_archivo(file_stub) + ".docx"

                out_path = output_dir / filename_docx
                tpl.save(out_path)

                # Agregamos DOCX al ZIP
                with open(out_path, "rb") as f:
                    zf.writestr(filename_docx, f.read())

                # Opcional: PDF
                if TRY_PDF_WEB and docx2pdf_convert is not None:
                    try:
                        out_pdf_path = out_path.with_suffix(".pdf")

                        # Intentar inicializar COM explícitamente en Windows
                        try:
                            import pythoncom  # requiere pywin32
                            pythoncom.CoInitialize()
                            try:
                                docx2pdf_convert(str(out_path), str(out_pdf_path))
                            finally:
                                pythoncom.CoUninitialize()
                        except ImportError:
                            # Si no está pythoncom, igual intentamos la conversión directa
                            docx2pdf_convert(str(out_path), str(out_pdf_path))

                        # Agregar PDF al ZIP
                        with open(out_pdf_path, "rb") as fpdf:
                            zf.writestr(out_pdf_path.name, fpdf.read())

                    except Exception as e:
                        print(
                            f"[Aviso] No se pudo generar PDF para "
                            f"{out_path.name}: {e}"
                        )

        conn.close()

        zip_buffer.seek(0)
        zip_filename = (
            f"cartas_invitacion_{etiqueta_periodo.replace(' ', '_')}.zip"
        )

        flash(
            f"Cartas generadas correctamente en la carpeta '{subdir_name}' "
            f"y descargadas como ZIP (DOCX{', PDF' if TRY_PDF_WEB else ''}) ✅",
            "success",
        )
        return send_file(
            zip_buffer,
            as_attachment=True,
            download_name=zip_filename,
            mimetype="application/zip",
        )
