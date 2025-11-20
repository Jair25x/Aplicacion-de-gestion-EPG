# update_codigos_categorias_dic_2025.py
"""
Asigna 'codigo' y 'categoria' a los cursos de Diciembre 2025
en la tabla curso_programado, usando la lista ya validada
(en tu app) que contiene Código y Categoría.

- Match 1 a 1 por:
    periodo (2025-12) + programa_academico.nombre_corto + asignatura + fechas_texto
- Fallback: si no encuentra con fechas_texto, intenta solo por
    periodo + programa + asignatura
- Idempotente:
    - Solo escribe codigo/categoria si actualmente están NULL o vacíos.
    - Si ya tienen valor distinto, NO los pisa, solo muestra un mensaje.

Requiere:
  - DOCENTES_DB_PATH en .env (como en add_cursos_diciembre_2025.py)
  - Columnas 'codigo' y 'categoria' en curso_programado.
"""

import os
import sqlite3
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

DB_PATH = os.getenv("DOCENTES_DB_PATH", str(BASE_DIR / "docentes.db"))


def ensure_columns(cursor):
    """
    Verifica que curso_programado tenga las columnas 'codigo' y 'categoria'.
    Si no existen, lanza RuntimeError con mensaje claro.
    """
    cursor.execute("PRAGMA table_info(curso_programado);")
    cols = {row[1] for row in cursor.fetchall()}  # row[1] = name

    missing = []
    for col in ("codigo", "categoria"):
        if col not in cols:
            missing.append(col)

    if missing:
        raise RuntimeError(
            "❌ La tabla 'curso_programado' no tiene las columnas requeridas: "
            + ", ".join(missing)
            + ".\n"
              "Agrega las columnas antes de ejecutar este script, por ejemplo:\n"
              "  ALTER TABLE curso_programado ADD COLUMN codigo TEXT;\n"
              "  ALTER TABLE curso_programado ADD COLUMN categoria TEXT;"
        )


# ============================
#  Datos: códigos y categorías
#  Diciembre 2025
# ============================

# NOTA:
# - 'programa' debe coincidir EXACTO con programa_academico.nombre_corto.
# - 'fechas_texto' debe coincidir con curso_programado.fechas_texto.
# - Para los cursos marcados con ⚠️ en tu tabla, dejamos codigo/categoria = None
#   para no pisar nada (se completarán luego a mano o en otro script).

codigos_dic_2025 = [
    # ---------- DOCTORADOS FCEC ----------
    {
        "programa": "Doctorado en Administración 2da Promoción a Distancia/Presencial",
        "asignatura": "GESTIÓN DE RIESGOS Y TOMA DE DECISIONES EN INCERTIDUMBRE",
        "fechas_texto": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "codigo": "DM11",
        "categoria": "FDO",
    },
    {
        "programa": "Doctorado en Administración 3ra Promoción a Distancia",
        "asignatura": "MACROECONOMÍA Y POLÍTICAS ECONÓMICAS",
        "fechas_texto": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "codigo": "DM09",
        "categoria": "FDO",
    },
    {
        "programa": "Doctorado en Administración 4ta Promoción Presencial",
        "asignatura": "SEMINARIO DE TESIS I",
        "fechas_texto": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "codigo": "DK19",
        "categoria": "INV",
    },
    {
        "programa": "Doctorado en Administración 4ta Promoción a Distancia",
        "asignatura": "RESPONSABILIDAD SOCIAL EMPRESARIAL",
        "fechas_texto": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "codigo": "DM05",
        "categoria": "FDO",
    },

    # ---------- DOCTORADO EN CIENCIAS DE LA EDUCACIÓN ----------
    {
        "programa": "Doctorado en Ciencias de la Educación 15va Promoción",
        "asignatura": "DEFENSA NACIONAL Y SEGURIDAD",
        "fechas_texto": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "codigo": "DO01",
        "categoria": "FDO",
    },
    {
        "programa": "Doctorado en Ciencias de la Educación 2da Promoción a Distancia/Presencial",
        "asignatura": "TECNOLOGÍAS DE INFORMACIÓN Y COMUNICACIÓN",
        "fechas_texto": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "codigo": "DN09",
        "categoria": "INV",
    },
    {
        "programa": "Doctorado en Ciencias de la Educación 3ra Promoción a Distancia",
        "asignatura": "SISTEMAS DE EVALUACIÓN DEL APRENDIZAJE",
        "fechas_texto": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "codigo": "DN08",
        "categoria": "FDO",
    },
    {
        "programa": "Doctorado en Ciencias de la Educación 4ta Promoción a Distancia",
        "asignatura": "RESPONSABILIDAD ETICO SOCIAL",
        "fechas_texto": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "codigo": "DN07",
        "categoria": "FDO",
    },
    {
        "programa": "Doctorado en Ciencias de la Educación 5ta Promoción a Distancia",
        "asignatura": "ÉTICA EN LA EDUCACIÓN",
        "fechas_texto": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "codigo": "DN06",
        "categoria": "FDO",
    },

    # ---------- DOCTORADO EN CIENCIAS DE LA SALUD / PSICOLOGÍA ----------
    {
        "programa": "Doctorado en Ciencias de la Salud 2da Promoción a Distancia",
        "asignatura": "SEMINARIO TEMÁTICO",
        "fechas_texto": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "codigo": "DO17",
        "categoria": "FDO",
    },
    {
        "programa": "Doctorado en Ciencias de la Salud 3ra Promoción a Distancia",
        "asignatura": "SEMINARIO DE TESIS II",
        "fechas_texto": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "codigo": "DK20",
        "categoria": "INV",
    },
    {
        "programa": "Doctorado en Ciencias de la Salud 4ta Promoción a Distancia",
        "asignatura": "SEMINARIO DE TESIS I",
        "fechas_texto": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "codigo": "DK19",
        "categoria": "INV",
    },
    {
        "programa": "Doctorado en Psicología 1ra Promoción a Distancia",
        "asignatura": "SEMINARIO DE TESIS V",
        "fechas_texto": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "codigo": "DK23",
        "categoria": "INV",
    },
    {
        # ⚠️ No tienes aún código/categoría definidos en la tabla.
        "programa": "Doctorado en Psicología 3ra Promoción a Distancia",
        "asignatura": "SEMINARIO DE TESIS I",
        "fechas_texto": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "codigo": None,
        "categoria": None,
    },

    # ---------- DOCTORADO EN CONTABILIDAD ----------
    {
        "programa": "Doctorado en Contabilidad 2da Promoción a Distancia",
        "asignatura": "POLÍTICA ECONÓMICA Y GLOBALIZACIÓN",
        "fechas_texto": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "codigo": "DG14",
        "categoria": "FDO",
    },

    # ---------- DOCTORADO EN DERECHO ----------
    {
        "programa": "Doctorado en Derecho 2da Promoción a Distancia",
        "asignatura": "SEMINARIO DE TESIS IV",
        "fechas_texto": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "codigo": "DK22",
        "categoria": "INV",
    },
    {
        "programa": "Doctorado en Derecho 3ra Promoción a Distancia",
        "asignatura": "SEMINARIO DE TESIS III",
        "fechas_texto": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "codigo": "DK21",
        "categoria": "INV",
    },
    {
        "programa": "Doctorado en Derecho 4ta Promoción a Distancia",
        "asignatura": "MEDIOS ALTERNATIVOS PARA LA RESOLUCION DE CONFLICTOS",
        "fechas_texto": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "codigo": "DD16",
        "categoria": "FDO",
    },
    {
        "programa": "Doctorado en Derecho 5ta Promoción a Distancia",
        "asignatura": "SEMINARIO: TEORIAS AVANZADAS DEL DERECHO PENAL EN EL SIGLO XXI",
        "fechas_texto": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "codigo": "DD15",
        "categoria": "FDO",
    },
    {
        "programa": "Doctorado en Derecho 6ta Promoción a Distancia",
        "asignatura": "CIENCIA POLITICA Y GOBERNABILIDAD",
        "fechas_texto": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "codigo": "DD14",
        "categoria": "FDO",
    },

    # ---------- DOCTORADO EN MEDIO AMBIENTE Y DESARROLLO SOSTENIBLE ----------
    {
        "programa": "Doctorado en Medio Ambiente y Desarrollo Sostenible 12va Promoción Presencial",
        "asignatura": "LEGISLACIÓN AMBIENTAL",
        "fechas_texto": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "codigo": "DK03",
        "categoria": "FDO",
    },
    {
        "programa": "Doctorado en Medio Ambiente y Desarrollo Sostenible 2da Promoción Presencial / Distancia",
        "asignatura": "ELABORACIÓN Y PUBLICACIÓN DE ARTÍCULOS CIENTÍFICOS",
        "fechas_texto": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "codigo": "DJ01",
        "categoria": "INV",
    },
    {
        "programa": "Doctorado en Medio Ambiente y Desarrollo Sostenible 3ra Promoción a Distancia/Presencial",
        "asignatura": "SEMINARIO DE TESIS IV",
        "fechas_texto": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "codigo": "DK22",
        "categoria": "INV",
    },
    {
        "programa": "Doctorado en Medio Ambiente y Desarrollo Sostenible 4ta Promoción a Distancia",
        "asignatura": "SISTEMAS DE INFORMACIÓN AMBIENTAL",
        "fechas_texto": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "codigo": "DK24",
        "categoria": "FDO",
    },
    {
        "programa": "Doctorado en Medio Ambiente y Desarrollo Sostenible 5ta Promoción a Distancia",
        "asignatura": "BIOÉTICA",
        "fechas_texto": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "codigo": "DO02",
        "categoria": "FDO",
    },
    {
        "programa": "Doctorado en Medio Ambiente y Desarrollo Sostenible 6ta Promoción a Distancia",
        "asignatura": "METODOLOGÍA DE LA INVESTIGACIÓN CIENTÍFICA",
        "fechas_texto": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "codigo": "DK17",
        "categoria": "INV",
    },

    # ---------- MAESTRÍA EN ADMINISTRACIÓN / CONTABILIDAD ----------
    {
        "programa": "Maestría en Administración de Negocios 2da Promoción a Distancia",
        "asignatura": "TESIS II",
        "fechas_texto": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "codigo": "MS06",
        "categoria": "INV",
    },
    {
        "programa": "Maestría en Administración de Negocios 3ra Promoción a Distancia",
        "asignatura": "TESIS I",
        "fechas_texto": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "codigo": "MS05",
        "categoria": "INV",
    },
    {
        "programa": "Maestría en Administración de Negocios 4ta Promoción a Distancia",
        "asignatura": "METODOLOGIA CIENTIFICA DE LA INVESTIGACION",
        "fechas_texto": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "codigo": "MS04",
        "categoria": "INV",
    },
    {
        "programa": "Maestría en Contabilidad mención en Auditoría y Control Interno 3ra Promoción a Distancia",
        "asignatura": "TESIS II",
        "fechas_texto": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "codigo": "MS06",
        "categoria": "INV",
    },
    {
        # ⚠️ Aún sin código/categoría definidos
        "programa": "Maestría en Contabilidad mención en Auditoría y Control Interno 4ta Promoción a Distancia",
        "asignatura": "TESIS I",
        "fechas_texto": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "codigo": None,
        "categoria": None,
    },
    {
        "programa": "Maestría en Contabilidad mención en Auditoría y Control Interno 5ta Promoción a Distancia",
        "asignatura": "AUDITORIA FINANCIERA I",
        "fechas_texto": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "codigo": "ML04",
        "categoria": "FMA",
    },

    # ---------- MAESTRÍAS EN DERECHO ----------
    {
        "programa": "Maestría en Derecho Civil y Comercial 2da Promoción a Distancia",
        "asignatura": "TESIS III",
        "fechas_texto": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "codigo": "MS07",
        "categoria": "INV",
    },
    {
        "programa": "Maestría en Derecho Civil y Comercial 3ra Promoción a Distancia",
        "asignatura": "TESIS II",
        "fechas_texto": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "codigo": "MS06",
        "categoria": "INV",
    },
    {
        "programa": "Maestría en Derecho Civil y Comercial 4ta Promoción a Distancia",
        "asignatura": "TUTELA JURÍDICA DE LA POSESIÓN Y LA PROPIEDAD",
        "fechas_texto": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "codigo": "MD14",
        "categoria": "FMA",
    },
    {
        "programa": "Maestría en Derecho Constitucional 3ra Promoción a Distancia",
        "asignatura": "TESIS III",
        "fechas_texto": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "codigo": "MS07",
        "categoria": "INV",
    },
    {
        "programa": "Maestría en Derecho Constitucional 4ta Promoción a Distancia",
        "asignatura": "TEMAS ESPECIALES",
        "fechas_texto": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "codigo": "MS09",
        "categoria": "FMA",
    },
    {
        "programa": "Maestría en Derecho Constitucional 5ta Promoción a Distancia",
        "asignatura": "TESIS I",
        "fechas_texto": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "codigo": "MS05",
        "categoria": "INV",
    },
    {
        "programa": "Maestría en Derecho Registral y Notarial 2da Promoción a Distancia",
        "asignatura": "TESIS II",
        "fechas_texto": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "codigo": "MS06",
        "categoria": "INV",
    },
    {
        "programa": "Maestría en Derecho Registral y Notarial 3ra Promoción a Distancia",
        "asignatura": "TESIS I",
        "fechas_texto": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "codigo": "MS05",
        "categoria": "INV",
    },
    {
        "programa": "Maestría en Derecho Registral y Notarial 4ta Promoción a Distancia",
        "asignatura": "DERECHO INMOBILIARIO I",
        "fechas_texto": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "codigo": "MS07",
        "categoria": "FMA",
    },

    # ---------- MAESTRÍA EN DOCENCIA UNIVERSITARIA ----------
    {
        "programa": "Maestría en Docencia Universitaria 4ta Promoción a Distancia",
        "asignatura": "TESIS III",
        "fechas_texto": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "codigo": "MS07",
        "categoria": "INV",
    },
    {
        "programa": "Maestría en Docencia Universitaria 5ta Promoción a Distancia",
        "asignatura": "TESIS II",
        "fechas_texto": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "codigo": "MS06",
        "categoria": "INV",
    },
    {
        "programa": "Maestría en Docencia Universitaria 6ta Promoción a Distancia",
        "asignatura": "TESIS I",
        "fechas_texto": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "codigo": "MS05",
        "categoria": "INV",
    },
    {
        "programa": "Maestría en Docencia Universitaria 7ma Promoción a Distancia",
        "asignatura": "PLANIFICACIÓN Y GESTIÓN DE LA CALIDAD DE LA EDUCACIÓN",
        "fechas_texto": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "codigo": "DU29",
        "categoria": "FMA",
    },

    # ---------- MAESTRÍAS EN INGENIERÍA CIVIL ----------
    {
        "programa": "Maestría en Ingeniería Civil mención en Estructuras 4ta Promoción a Distancia",
        "asignatura": "TEMAS AVANZADOS DE INGENIERIA ESTRUCTURAL EN LA HIDRAULICA",
        "fechas_texto": "05, 06, 07, 19, 20 y 21 de diciembre 2025",
        "codigo": "MK12",
        "categoria": "FMA",
    },
    {
        "programa": "Maestría en Ingeniería Civil mención en Estructuras 5ta Promoción a Distancia",
        "asignatura": "TESIS II",
        "fechas_texto": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "codigo": "MS06",
        "categoria": "INV",
    },
    {
        "programa": "Maestría en Ingeniería Civil mención en Estructuras 6ta Promoción a Distancia",
        "asignatura": "TESIS I",
        "fechas_texto": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "codigo": "MS05",
        "categoria": "INV",
    },
    {
        "programa": "Maestría en Ingeniería Civil mención en Estructuras 7ma Promoción a Distancia",
        "asignatura": "COMPORTAMIENTO Y DISEÑO DEL CONCRETO",
        "fechas_texto": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "codigo": "MK03",
        "categoria": "FMA",
    },
    {
        "programa": "Maestría en Ingeniería Civil mención en Hidráulica y Ambiental 2da Promoción a Distancia",
        "asignatura": "TEMAS ESPECIALES",
        "fechas_texto": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "codigo": "MS09",
        "categoria": "FMA",
    },
    {
        "programa": "Maestría en Ingeniería Civil mención en Hidráulica y Ambiental 4ta Promoción a Distancia",
        "asignatura": "TRATAMIENTO DE AGUAS SERVIDAS E INDUSTRIALES",
        "fechas_texto": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "codigo": "MH05",
        "categoria": "FMA",
    },
    {
        "programa": "Maestría en Ingeniería Civil mención en Transportes 2da Promoción Presencial",
        "asignatura": "TESIS I",
        "fechas_texto": "12, 13, 14, 26, 27 y 28 de diciembre 2025",
        "codigo": "MS05",
        "categoria": "INV",
    },
]


def encontrar_curso(cursor, periodo_id, programa, asignatura, fechas_texto):
    """
    Devuelve (id, codigo_actual, categoria_actual) de curso_programado
    usando:
      1º intento: match completo con fechas_texto
      2º intento: sin fechas_texto (por si se editó manualmente)
    """
    # 1) obtener programa_id
    cursor.execute(
        "SELECT id FROM programa_academico WHERE nombre_corto = ?;",
        (programa,)
    )
    row = cursor.fetchone()
    if not row:
        print(f"❌ Programa no encontrado en programa_academico: '{programa}'")
        return None
    programa_id = row[0]

    # 1er intento: con fechas_texto
    cursor.execute(
        """
        SELECT id, codigo, categoria
        FROM curso_programado
        WHERE periodo_id = ?
          AND programa_id = ?
          AND asignatura = ?
          AND fechas_texto = ?;
        """,
        (periodo_id, programa_id, asignatura, fechas_texto),
    )
    rows = cursor.fetchall()

    if len(rows) == 1:
        return rows[0]
    elif len(rows) > 1:
        print(
            f"⚠️ Varios cursos coinciden (periodo={periodo_id}, programa='{programa}', "
            f"asignatura='{asignatura}', fechas='{fechas_texto}'). No se actualiza."
        )
        return None

    # 2º intento: sin fechas_texto
    cursor.execute(
        """
        SELECT id, codigo, categoria
        FROM curso_programado
        WHERE periodo_id = ?
          AND programa_id = ?
          AND asignatura = ?;
        """,
        (periodo_id, programa_id, asignatura),
    )
    rows2 = cursor.fetchall()

    if len(rows2) == 1:
        print(
            f"ℹ️ No se encontró con fechas_texto, pero se encontró un curso "
            f"por periodo+programa+asignatura. Se usará ese registro "
            f"(periodo={periodo_id}, programa='{programa}', asignatura='{asignatura}')."
        )
        return rows2[0]
    elif len(rows2) > 1:
        print(
            f"⚠️ Varios cursos coinciden sin fechas_texto "
            f"(periodo={periodo_id}, programa='{programa}', asignatura='{asignatura}'). "
            f"No se actualiza."
        )
        return None

    print(
        f"❌ No se encontró ningún curso_programado para "
        f"(periodo={periodo_id}, programa='{programa}', asignatura='{asignatura}', "
        f"fechas='{fechas_texto}')."
    )
    return None


def main():
    print(f"Usando base de datos: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()

    # 0) Verificar columnas necesarias
    ensure_columns(cursor)

    # 1) Verificar período Diciembre 2025
    cursor.execute("SELECT id FROM periodo WHERE anio = ? AND mes = ?;", (2025, 12))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise RuntimeError(
            "❌ No se encontró el periodo 2025-12 en la tabla periodo. "
            "Asegúrate de haber corrido init_db.py y add_cursos_diciembre_2025.py."
        )
    periodo_dic_2025_id = row[0]
    print(f"Periodo Diciembre 2025 ID: {periodo_dic_2025_id}")

    actualizados = 0
    ya_tenian_valor = 0
    sin_datos = 0
    no_encontrados = 0

    for item in codigos_dic_2025:
        programa = item["programa"]
        asignatura = item["asignatura"]
        fechas_texto = item["fechas_texto"]
        nuevo_codigo = item["codigo"]
        nueva_categoria = item["categoria"]

        if not nuevo_codigo and not nueva_categoria:
            # Caso de filas marcadas con ⚠️ en tu tabla
            sin_datos += 1
            print(f"⏭️  Sin datos de código/categoría aún: '{programa}' - '{asignatura}'")
            continue

        found = encontrar_curso(
            cursor, periodo_dic_2025_id, programa, asignatura, fechas_texto
        )
        if not found:
            no_encontrados += 1
            continue

        curso_id, codigo_actual, categoria_actual = found

        codigo_actual_str = (codigo_actual or "").strip()
        categoria_actual_str = (categoria_actual or "").strip()

        updates = {}
        # Solo actualizamos si la BD está vacía para ese campo
        if nuevo_codigo and not codigo_actual_str:
            updates["codigo"] = nuevo_codigo
        if nueva_categoria and not categoria_actual_str:
            updates["categoria"] = nueva_categoria

        if not updates:
            ya_tenian_valor += 1
            print(
                f"ℹ️  Curso id={curso_id}: ya tenía código/categoría "
                f"(codigo='{codigo_actual}', categoria='{categoria_actual}'). No se modifica."
            )
            continue

        set_clause = ", ".join(f"{col} = ?" for col in updates.keys())
        params = list(updates.values()) + [curso_id]

        cursor.execute(
            f"UPDATE curso_programado SET {set_clause} WHERE id = ?;",
            params,
        )
        actualizados += 1
        print(
            f"✅ Actualizado curso id={curso_id}: "
            f"codigo='{nuevo_codigo or codigo_actual}', "
            f"categoria='{nueva_categoria or categoria_actual}'"
        )

    conn.commit()
    conn.close()

    print("\n===== RESUMEN =====")
    print(f"✅ Cursos actualizados (se llenó código y/o categoría): {actualizados}")
    print(f"ℹ️ Cursos que ya tenían valores (no modificados): {ya_tenian_valor}")
    print(f"⏭️ Cursos sin datos de código/categoría (⚠️): {sin_datos}")
    print(f"❌ Cursos no encontrados en la BD: {no_encontrados}")


if __name__ == "__main__":
    main()
