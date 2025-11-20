# routes/cartas.py
from flask import render_template, request, redirect, url_for, flash, send_file
from db import get_db_connection
from config import (
    CARTAS_OUTPUT_DIR,
    PLANTILLA_CARTA,
    TRY_PDF_WEB,
    docx2pdf_convert,
)
from docxtpl import DocxTemplate
from generar_cartas import (
    fecha_larga_es,
    calc_remuneracion,
    limpiar_nombre_archivo,
    extraer_paterno_y_nombre,     # compatibilidad CLI
    separar_titulo_y_nombre,      # idem
    extraer_titulo_paterno_nombre,
    MESES_ES,
    generar_silabo_curso,         # generador de sílabos
)
from utils_programas import normalizar_programa_base
from io import BytesIO
import zipfile
import os


def register_cartas_routes(app):

    @app.route("/cartas_invitacion", methods=["GET", "POST"])
    def cartas_invitacion():
        """
        Vista para:
        - Elegir período
        - Ver cursos programados y estado de datos para carta
        - Seleccionar cursos y generar documentos .docx/.pdf (ZIP):
          * Siempre cartas
          * Opcionalmente, sílabos (según checkbox include_silabos)
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

        # -------- POST: generar cartas (y opcionalmente sílabos) --------
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
            flash("No seleccionaste ningún curso para generar documentos.", "warning")
            return redirect(url_for("cartas_invitacion", periodo_id=periodo_id))

        # N° de carta inicial (opcional)
        start_num_str = request.form.get("start_num") or ""
        try:
            next_num = int(start_num_str) if start_num_str else None
        except ValueError:
            next_num = None

        # Checkbox: incluir sílabos
        include_silabos = bool(request.form.get("include_silabos"))

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
                d.correo          AS docente_correo,
                pa.nombre_corto   AS programa_nombre,
                pa.tipo           AS programa_tipo,
                pa.modalidad      AS programa_modalidad,
                pe.anio           AS periodo_anio,
                pe.mes            AS periodo_mes,
                pe.etiqueta       AS periodo_etiqueta,
                pe.periodo_academico AS periodo_academico
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
            flash("No se encontraron cursos para generar documentos.", "danger")
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

                # Carpeta interna por docente en el ZIP
                docente_folder = limpiar_nombre_archivo(docente) or "DOCENTE_POR_DEFINIR"

                # Programa base (texto para la carta)
                programa_base = normalizar_programa_base(programa_nombre, programa_tipo)
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

                # Fecha larga (hoy)
                fecha_larga, anio = fecha_larga_es(None)
                ciudad = "Cusco"

                # Mes [TABLA] a partir de periodo.anio / periodo.mes
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
                    periodo_etiqueta_row = row["periodo_etiqueta"] or etiqueta_periodo
                    mes_tabla = (periodo_etiqueta_row or "").upper()

                # Remuneración
                override = None
                if row["remuneracion_monto"] is not None:
                    override = str(row["remuneracion_monto"])
                remuneracion_num = calc_remuneracion(programa_texto, override)
                remuneracion = remuneracion_num

                # Numeración de carta
                if next_num is not None:
                    numero = f"{next_num:03d}"
                    next_num += 1
                else:
                    numero = "000"

                titulo = ""

                context = {
                    "ciudad": ciudad,
                    "fecha_larga": fecha_larga,
                    "numero": numero,
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

                # === 1) Generar CARTA DOCX ===
                tpl = DocxTemplate(str(PLANTILLA_CARTA))
                tpl.render(context)

                titulo_abrev, paterno, nombre = extraer_titulo_paterno_nombre(docente)

                if titulo_abrev:
                    file_stub = f"CARTA N°{numero} {titulo_abrev} {paterno} {nombre}"
                else:
                    file_stub = f"CARTA N°{numero} {paterno} {nombre}"

                filename_docx = limpiar_nombre_archivo(file_stub) + ".docx"
                out_path = output_dir / filename_docx
                tpl.save(out_path)

                # Agregar carta DOCX al ZIP dentro de la carpeta del docente
                with open(out_path, "rb") as f:
                    zip_name_carta = f"{docente_folder}/{filename_docx}"
                    zf.writestr(zip_name_carta, f.read())

                # Opcional: PDF de la carta
                if TRY_PDF_WEB and docx2pdf_convert is not None:
                    try:
                        out_pdf_path = out_path.with_suffix(".pdf")
                        try:
                            import pythoncom  # requiere pywin32 en Windows
                            pythoncom.CoInitialize()
                            try:
                                docx2pdf_convert(str(out_path), str(out_pdf_path))
                            finally:
                                pythoncom.CoUninitialize()
                        except ImportError:
                            # Si no está pythoncom, intentamos la conversión directa
                            docx2pdf_convert(str(out_path), str(out_pdf_path))

                        with open(out_pdf_path, "rb") as fpdf:
                            zip_name_pdf = f"{docente_folder}/{out_pdf_path.name}"
                            zf.writestr(zip_name_pdf, fpdf.read())
                    except Exception as e:
                        print(f"[Aviso] No se pudo generar PDF para {out_path.name}: {e}")

                # === 2) Generar SÍLABO para este curso (si está habilitado y la config existe) ===
                if include_silabos:
                    try:
                        curso_row = dict(row)  # Row -> dict

                        # Aseguramos algunas claves que usa generar_silabo_curso
                        curso_row["programa_nombre"] = programa_nombre
                        curso_row["docente_nombre"] = docente
                        curso_row["docente_correo"] = row["docente_correo"] or ""
                        # periodo_academico ya está en row; si no, usamos etiqueta
                        if not curso_row.get("periodo_academico"):
                            curso_row["periodo_academico"] = (
                                row["periodo_academico"] or row["periodo_etiqueta"]
                            )

                        silabo_path = generar_silabo_curso(conn, curso_row)
                        silabo_filename = os.path.basename(silabo_path)

                        with open(silabo_path, "rb") as fs:
                            zip_name_silabo = f"{docente_folder}/{silabo_filename}"
                            zf.writestr(zip_name_silabo, fs.read())

                    except RuntimeError as e:
                        # Típico caso: no hay silabo_programa_config para ese programa
                        print(
                            f"[Aviso] No se pudo generar sílabo para curso {row['id']}: {e}"
                        )
                    except Exception as e:
                        print(
                            f"[Aviso] Error inesperado generando sílabo para curso {row['id']}: {e}"
                        )

        conn.close()

        zip_buffer.seek(0)
        zip_filename = (
            f"cartas_invitacion_{etiqueta_periodo.replace(' ', '_')}.zip"
        )

        detalle = "Cartas y sílabos" if include_silabos else "Cartas"
        flash(
            f"{detalle} generados correctamente en la carpeta '{subdir_name}' "
            f"y descargados como ZIP (DOCX{', PDF' if TRY_PDF_WEB else ''}) ✅",
            "success",
        )
        return send_file(
            zip_buffer,
            as_attachment=True,
            download_name=zip_filename,
            mimetype="application/zip",
        )
