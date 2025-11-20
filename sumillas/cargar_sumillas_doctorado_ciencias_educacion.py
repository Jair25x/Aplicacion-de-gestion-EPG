# cargar_sumillas_doctorado_ciencias_educacion.py
#
# Script para:
# 1) Configurar silabo_programa_config para TODAS las promociones del
#    Doctorado en Ciencias de la Educación (DCE)
# 2) Cargar / actualizar las sumillas de los cursos en silabo_curso_base
#
# NOTA:
# - Este script se ejecuta manualmente (como prefieres) cuando quieras poblar
#   config + sumillas para DCE.
# - Requiere:
#   * programa_academico con promociones DCE registradas.
#   * silabo_programa_config con UNIQUE(programa_id).
#   * silabo_curso_base con UNIQUE(programa_id, codigo).

import sqlite3
import sys
from pathlib import Path

# === AÑADIR RAÍZ DEL PROYECTO AL sys.path ===
ROOT_DIR = Path(__file__).resolve().parent.parent  # .../gestion-docentes-app
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from db import get_db_connection  # noqa: E402

# =====================================================
# 1) Perfil del egresado + resultados de aprendizaje
#    (texto que irá en silabo_programa_config)
# =====================================================

PERFIL_EGRESADO_DCE = """
Está capacitado para aplicar sus conocimientos y actividades teóricos-prácticos profesionales, \
en la investigación desde una perspectiva interdisciplinaria, transversal y en trabajo \
multidisciplinario-científico. Desarrolla su capacidad de análisis y profundiza sus conocimientos \
que le permita asumir eficientemente la función de asesorías en sus áreas de competencia de \
conocimiento. Perfecciona sus habilidades necesarias para desempeñarse en el ámbito académico, \
en temas relativos a su área y dar soluciones a los problemas que competen a su especialidad. \
Cultiva una disposición inquisitiva, crítica y valorativa ante los problemas identificados en la \
realidad desde una perspectiva científica, siendo capaz de utilizar los conocimientos, \
procedimientos y habilidades necesarias para realizar investigaciones que aporten soluciones y \
alternativas válidas, generando nuevos conocimientos en las disciplinas a través de los métodos \
adecuados propios de la investigación científica.
""".strip()

RESULTADOS_APRENDIZAJE_DCE = """
Tabla 1: Competencias y resultados de aprendizaje

Competencias del perfil de egresado del Programa de doctorado      Resultados de aprendizaje
Redactar uno o más resultados de aprendizaje por cada competencia

1. Está capacitado para aplicar sus conocimientos y actividades teóricos-prácticos profesionales, \
en la investigación desde una perspectiva interdisciplinaria, transversal y en trabajo \
multidisciplinario-científico.                                           1.1.1.  1.1.2.

2. Desarrolla su capacidad de análisis y profundiza sus conocimientos que le permita asumir \
eficientemente la función de asesorías en sus áreas de competencia de conocimiento.          2.1.1.

3. Perfecciona sus habilidades necesarias para desempeñarse en el ámbito académico, en temas \
relativos a su área y dar soluciones a los problemas que competen a su especialidad.         3.1.1.

4. Cultiva una disposición inquisitiva, crítica y valorativa ante los problemas identificados \
en la realidad desde una perspectiva científica, siendo capaz de utilizar los conocimientos, \
procedimientos y habilidades necesarias para realizar investigaciones que aporten soluciones \
y alternativas válidas, generando nuevos conocimientos en las disciplinas a través de los \
métodos adecuados propios de la investigación científica.                                    4.1.1.

Fuente: Propuesta de Escobar C. P., 2018.
""".strip()


# =====================================================
# 2) Sumillas por asignatura (Doctorado en Ciencias de la Educación)
#    NOTA: los "codigo" aquí son internos, solo para silabo_curso_base.
#          El sílabo los puede encontrar por NOMBRE de asignatura.
# =====================================================

CURSOS_DCE = [
    # PRIMER CICLO
    {
        "codigo": "DCE_C1_EPISTEMOLOGIA",
        "asignatura": "EPISTEMOLOGÍA",
        "sumilla": """
Asignatura de naturaleza teórico-práctica, cuyo propósito es dar a conocer los fundamentos \
elementales de la Epistemología como base para las labores de la investigación científica en \
el ámbito de los estudios de doctorado. Comprende: introducción a la epistemología y sus \
aplicaciones en las ciencias de la educación; fundamentos filosóficos de la ciencia \
(positivismo, empirismo, racionalismo, constructivismo, etc.); la teoría del conocimiento y la \
construcción del conocimiento científico en educación; la epistemología crítica y la \
investigación en educación desde una perspectiva crítica; epistemología y teoría educativa: \
relación entre la teoría y la práctica educativa; desarrollo de un enfoque epistemológico \
propio: reflexión crítica y perspectivas futuras.
""".strip(),
    },
    {
        "codigo": "DCE_C1_SEMINARIO_INV_CUANTITATIVA",
        "asignatura": "SEMINARIO DE INVESTIGACIÓN CUANTITATIVA",
        "sumilla": """
Asignatura de naturaleza teórico-práctica, cuyo propósito es elaborar el diseño del trabajo de \
investigación que conduce a la presentación de una tesis para optar el grado de doctor en las \
diferentes menciones que ofrece la Escuela de Posgrado, permitiendo el asesoramiento, la \
revisión exhaustiva y pormenorizada de los temas centrales a ser desarrollados. Comprende: \
aspectos generales del proyecto, plan de investigación, metodología y referencias \
bibliográficas.
""".strip(),
    },
    {
        "codigo": "DCE_C1_METODOLOGIA_INV_CIENTIFICA",
        "asignatura": "METODOLOGIA DE LA INVESTIGACION CIENTIFICA",
        "sumilla": """
Asignatura de naturaleza teórico-práctica, cuyo propósito es proporcionar las herramientas \
necesarias para realizar investigaciones rigurosas y de calidad en el campo de la educación. \
Se guía al estudiante en el proceso de diseño, implementación y análisis de proyectos de \
investigación, con énfasis en la identificación de problemas relevantes y la formulación de \
preguntas de investigación pertinentes. Tiene como objetivo la elaboración de una matriz de \
consistencia que contenga la propuesta de investigación para el proyecto de tesis de grado. \
Comprende: introducción a la metodología de la investigación en educación; diseño de proyectos \
de investigación; análisis y selección de métodos y técnicas de investigación; ética en la \
investigación educativa; análisis de datos; escritura y presentación de informes de \
investigación.
""".strip(),
    },
    {
        "codigo": "DCE_C1_ETICA_EN_LA_EDUCACION",
        "asignatura": "ETICA EN LA EDUCACION.",
        "sumilla": """
Asignatura de naturaleza teórico-práctica, cuyo propósito es aproximar al doctorando al \
conocimiento y comprensión crítica de la ética en la educación. Presenta la ética como una \
concepción valorativa de la vida y analiza los principios éticos de la educación en el \
contexto de nuestra sociedad, promoviendo la reflexión acerca de las actitudes de \
responsabilidad y profesionalidad. Comprende: enfoques de la ética en educación, ética \
profesional, y ética e integridad en la gestión educativa.
""".strip(),
    },

    # SEGUNDO CICLO
    {
        "codigo": "DCE_C2_REALIDAD_EDUCATIVA_PERUANA",
        "asignatura": "REALIDAD EDUCATIVA PERUANA.",
        "sumilla": """
Asignatura de naturaleza teórico-práctica, cuyo propósito es proporcionar a los estudiantes \
una comprensión profunda de la realidad educativa en el Perú, incluyendo su historia, \
políticas y prácticas educativas actuales. Comprende: historia de la educación en el Perú; \
políticas educativas; desafíos actuales de la educación; educación intercultural y bilingüe; \
educación y tecnología; análisis crítico de la realidad educativa peruana.
""".strip(),
    },
    {
        "codigo": "DCE_C2_REFORMAS_POLITICAS_EDUCATIVAS",
        "asignatura": "REFORMAS Y POLÍTICAS EDUCATIVAS.",
        "sumilla": """
Asignatura de naturaleza teórico-práctica, cuyo propósito es desarrollar una revisión \
crítico-reflexiva de la evolución y generación de políticas, reformas y programas educativos \
para entender la realidad educativa actual en los escenarios regionales del globo y \
vislumbrar nociones futuras de estas políticas a través del tiempo, considerando las \
transformaciones nacionales e internacionales. Busca hacer propuestas viables para una \
educación de calidad con equidad y ética en nuestro país. Comprende: análisis de la política \
y reformas educativas; contexto histórico de las reformas; equidad; calidad de la educación; \
diversidad cultural; tecnología.
""".strip(),
    },
    {
        "codigo": "DCE_C2_SEMINARIO_TESIS_I",
        "asignatura": "SEMINARIO DE TESIS I.",
        "sumilla": """
Asignatura de naturaleza teórico-práctica, cuyo propósito es orientar en la formulación y \
ejecución de proyectos de investigación científica. Comprende: proceso de investigación \
científica cuantitativa, cualitativa y mixta, teniendo como eje la elaboración del proyecto \
de tesis: elección del tema, título de la investigación, redacción del problema, objetivos, \
justificación, hipótesis, variables o categorías, diseño metodológico, técnicas e \
instrumentos de recolección de información.
""".strip(),
    },
    {
        "codigo": "DCE_C2_RESPONSABILIDAD_ETICO_SOCIAL",
        "asignatura": "RESPONSABILIDAD ÉTICO SOCIAL.",
        "sumilla": """
Asignatura de naturaleza teórico-práctica, cuyo propósito es proporcionar a los estudiantes \
las herramientas necesarias para entender y aplicar los conceptos de responsabilidad social \
y ética en el contexto de la educación. A través de un enfoque interdisciplinario se explora \
la importancia de la responsabilidad social y ética en la educación y su relación con los \
valores y la cultura de una sociedad. Comprende: fundamentos teóricos de la responsabilidad \
social y ética en la educación; responsabilidad social y ética en la toma de decisiones \
educativas; ética y moral en educación; responsabilidad social en la gestión educativa; \
responsabilidad social en la investigación educativa; educación para el desarrollo \
sostenible.
""".strip(),
    },

    # TERCER CICLO
    {
        "codigo": "DCE_C3_SEMINARIO_INV_CUALITATIVA",
        "asignatura": "SEMINARIO DE INVESTIGACIÓN CUALITATIVA.",
        "sumilla": """
Asignatura de naturaleza teórico-práctica, cuyo propósito es desarrollar en los participantes \
el conocimiento y dominio de las técnicas y herramientas de investigación cualitativa, así \
como el análisis e interpretación de datos. Comprende: principios básicos de la investigación \
cualitativa, el profesor investigador y el desarrollo de habilidades para la investigación.
""".strip(),
    },
    {
        "codigo": "DCE_C3_ADMINISTRACION_DE_LA_EDUCACION",
        "asignatura": "ADMINISTRACIÓN DE LA EDUCACIÓN.",
        "sumilla": """
Asignatura de naturaleza teórico-práctica, cuyo propósito es aplicar los fundamentos teóricos \
y metodológicos de las ciencias de la pedagogía, la tecnología curricular y otras ciencias \
básicas para manejar con calidad y ética los procesos de gestión de instituciones educativas \
públicas y privadas, mostrando actitudes de aprendizaje autónomo y trabajo en equipo. \
Comprende: definiciones de gestión educativa, dimensiones de la gestión educativa, procesos \
de gestión educativa, documentos e instrumentos de gestión.
""".strip(),
    },
    {
        "codigo": "DCE_C3_SEMINARIO_TESIS_II",
        "asignatura": "SEMINARIO DE TESIS II.",
        "sumilla": """
Asignatura de naturaleza teórico-práctica, cuyo propósito es conducir al estudiante a la \
elaboración del marco teórico de una investigación, a partir de la búsqueda y sistematización \
de teorías e investigaciones relacionadas con el tema a nivel internacional, nacional y \
local, demostrando dominio en el uso de bases de datos y repositorios. Comprende: marco \
teórico, marco conceptual, diseño de investigación, bases de datos y repositorios \
científicos.
""".strip(),
    },
    {
        "codigo": "DCE_C3_SISTEMAS_EVAL_APRENDIZAJE",
        "asignatura": "SISTEMAS DE EVALUACION DEL APRENDIZAJE.",
        "sumilla": """
Asignatura de naturaleza teórico-práctica, cuyo propósito es generar espacios y oportunidades \
para analizar y reflexionar críticamente el currículo desde un enfoque basado en competencias, \
considerando las fases del proceso de evaluación curricular para diseñar y sustentar sistemas \
de evaluación del aprendizaje coherentes. Comprende: fundamentos teóricos de la evaluación, \
planificación, diseño e implementación de sistemas de evaluación efectivos.
""".strip(),
    },

    # CUARTO CICLO
    {
        "codigo": "DCE_C4_TIC",
        "asignatura": "TECNOLOGIAS DE INFORMACION Y COMUNICACIÓN",
        "sumilla": """
Asignatura de naturaleza teórico-práctica, cuyo propósito es promover el uso de las \
tecnologías de la información para el procesamiento y la construcción del conocimiento. \
Comprende: evolución de las tecnologías y perspectivas; la nube como recurso de información; \
aplicativos de procesamiento de información en la nube; almacenamiento de información en la \
nube.
""".strip(),
    },
    {
        "codigo": "DCE_C4_GESTION_EDUCATIVA_LIDERAZGO",
        "asignatura": "GESTIÓN EDUCATIVA Y LIDERAZGO",
        "sumilla": """
Asignatura de naturaleza teórico-práctica, cuyo propósito es efectuar el deslinde teórico de \
los principales conceptos dentro del sistema educativo peruano en cuanto a gestión educativa \
(enfoques, modelos, dimensiones y procesos), así como desarrollar temáticas relacionadas al \
liderazgo. Comprende: gestión educativa; liderazgo (enfoques, dimensiones, estilos); \
liderazgo pedagógico; liderazgo para el aprendizaje; liderazgo distribuido y liderazgo \
educativo.
""".strip(),
    },
    {
        "codigo": "DCE_C4_SEMINARIO_TESIS_III",
        "asignatura": "SEMINARIO DE TESIS III",
        "sumilla": """
Asignatura de naturaleza teórico-práctica, cuyo propósito es continuar el proceso de diseño \
del proyecto de investigación doctoral en educación: construcción de las bases teóricas, \
metodológicas, tratamiento estadístico, presentación y discusión de resultados y criterios \
para la redacción final de la investigación siguiendo estándares científicos.
""".strip(),
    },
    {
        "codigo": "DCE_C4_PRODUCCION_INTELECTUAL",
        "asignatura": "PRODUCCION INTELECTUAL.",
        "sumilla": """
Asignatura de naturaleza teórico-práctica, cuyo propósito es proporcionar las herramientas y \
recursos necesarios para producir trabajos académicos de alta calidad en el contexto del \
doctorado en ciencias de la educación. Comprende: tipos de producción intelectual \
(científica, técnica, artística); visibilidad de la producción científica; normas de \
redacción; propiedad intelectual y sus tipos.
""".strip(),
    },

    # QUINTO CICLO
    {
        "codigo": "DCE_C5_EDUCACION_DESARROLLO_SUSTENTABLE",
        "asignatura": "EDUCACIÓN Y DESARROLLO SUSTENTABLE",
        "sumilla": """
Asignatura de naturaleza teórico-práctica, cuyo propósito es brindar a los estudiantes un \
conocimiento profundo de la relación entre la educación y el desarrollo sustentable. \
Comprende: enfoques teóricos de desarrollo sostenible; modelos de desarrollo y desarrollo \
sostenible; estrategias de aplicación; experiencias de desarrollo sostenible en educación; \
estrategias de sostenibilidad en educación; gestión pública y políticas públicas vinculadas a \
la sustentabilidad.
""".strip(),
    },
    {
        "codigo": "DCE_C5_CONSULTORIA_EDUCATIVA",
        "asignatura": "CONSULTORÍA EDUCATIVA.",
        "sumilla": """
Asignatura de naturaleza teórico-práctica, cuyo propósito es proporcionar a los estudiantes \
los conocimientos y habilidades necesarios en el campo de la consultoría educativa. \
Comprende: planificación y gestión de proyectos educativos; evaluación y diagnóstico de \
necesidades; diseño y ejecución de programas de capacitación; asesoramiento y coaching a \
docentes y directivos; análisis de tendencias en consultoría educativa y su relación con el \
entorno social y tecnológico.
""".strip(),
    },
    {
        "codigo": "DCE_C5_SEMINARIO_TESIS_IV",
        "asignatura": "SEMINARIO DE TESIS IV.",
        "sumilla": """
Asignatura de naturaleza teórico-práctica, cuyo propósito es proporcionar aspectos avanzados \
de la investigación y apoyar a los estudiantes en la realización de sus investigaciones de \
tesis de doctorado en ciencias de la educación. Comprende: diseño de investigación en \
educación, redacción de resultados y presentación y discusión de los mismos.
""".strip(),
    },
    {
        "codigo": "DCE_C5_CALIDAD_ACREDITACION_IE",
        "asignatura": "CALIDAD Y ACREDITACION DE INSTITUCIONES EDUCATIVAS.",
        "sumilla": """
Asignatura de naturaleza teórico-práctica, cuyo propósito es lograr una comprensión profunda \
y crítica de los conceptos, metodologías y herramientas utilizados en la evaluación de la \
calidad y acreditación de instituciones educativas. Comprende: modelos de evaluación y \
acreditación; sistemas de aseguramiento de la calidad; gestión de la calidad en educación; \
evaluación de programas y procesos educativos.
""".strip(),
    },

    # SEXTO CICLO
    {
        "codigo": "DCE_C6_CULTURA_ACADEMICA_DOCENCIA",
        "asignatura": "CULTURA ACADEMICA Y DOCENCIA",
        "sumilla": """
Asignatura de naturaleza teórico-práctica, cuyo propósito es analizar la cultura académica \
universitaria conformada por discursos, representaciones, motivaciones, normas éticas, \
concepciones, visiones y prácticas institucionales de los actores universitarios acerca de \
las tareas de docencia, investigación, extensión y transferencia, aplicando estrategias \
competitivas en gestión educativa, pedagógica y de investigación especializada dentro de un \
proceso de calidad. Comprende: ética y responsabilidad social del docente; planificación y \
diseño de cursos; evaluación del aprendizaje; gestión de la enseñanza y aprendizaje; \
innovación educativa.
""".strip(),
    },
    {
        "codigo": "DCE_C6_DEFENSA_NACIONAL_SEGURIDAD",
        "asignatura": "DEFENSA NACIONAL Y SEGURIDAD",
        "sumilla": """
Asignatura de naturaleza teórico-práctica, cuyo propósito es proporcionar a los estudiantes \
una comprensión integral de los conceptos, principios y prácticas de la defensa nacional y la \
seguridad. Comprende: conceptos sobre defensa nacional y seguridad; evolución histórica de la \
defensa y la seguridad; amenazas y desafíos actuales y futuros; actores involucrados; papel \
de las Fuerzas Armadas y agencias de seguridad; planificación y ejecución de políticas y \
estrategias de defensa; relación con la política exterior; implicancias éticas y legales.
""".strip(),
    },
    {
        "codigo": "DCE_C6_SEMINARIO_TESIS_V",
        "asignatura": "SEMINARIO DE TESIS V",
        "sumilla": """
Asignatura de naturaleza teórico-práctica, cuyo propósito es consolidar la tesis, \
sistematizando la información con rigor científico y ético. Comprende: discusión, \
conclusiones, recomendaciones, propuesta y redacción de la tesis según normatividad \
internacional, teniendo como producto la tesis concluida.
""".strip(),
    },
    {
        "codigo": "DCE_C6_ELABORACION_PUBLICACION_ARTICULOS",
        "asignatura": "ELABORACION Y PUBLICACION DE ARTICULOS CIENTIFICOS.",
        "sumilla": """
Asignatura de naturaleza teórico-práctica, cuyo propósito es desarrollar en el estudiante la \
capacidad de redactar artículos científicos referidos a su especialidad. Comprende: \
fundamentos de la comunicación científica; estructura básica del artículo científico; \
principios básicos de redacción; proceso de publicación y difusión de artículos científicos.
""".strip(),
    },
]


def seed_dce(conn: sqlite3.Connection) -> None:
    """
    Carga config + sumillas para TODAS las promociones del Doctorado en
    Ciencias de la Educación registradas en programa_academico.
    """
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 1) Buscar TODAS las promociones DCE
    progs = cur.execute(
        """
        SELECT id, nombre_corto, modalidad
        FROM programa_academico
        WHERE tipo = 'DOCTORADO'
          AND nombre_corto LIKE '%Ciencias de la Educación%'
        ORDER BY id
        """
    ).fetchall()

    if not progs:
        raise SystemExit(
            "No se encontraron promociones del Doctorado en Ciencias de la Educación.\n"
            "Verifica el campo nombre_corto."
        )

    print(f"Se encontraron {len(progs)} promociones DCE.\n")

    for prog in progs:
        programa_id = prog["id"]
        nombre_corto = prog["nombre_corto"]
        modalidad_prog = (prog["modalidad"] or "PRESENCIAL").strip().upper()

        print(f"==> Programa: {nombre_corto}")
        print(f"    programa_id = {programa_id}")
        print(f"    modalidad_default = {modalidad_prog}")

        # 2) Upsert en silabo_programa_config POR CADA PROMOCIÓN
        cur.execute(
            """
            INSERT INTO silabo_programa_config (
                programa_id,
                nombre_programa,
                plantilla_archivo,
                numero_creditos,
                horas_teoricas,
                horas_practicas,
                modalidad_default,
                horario_texto,
                inicio_semestre,
                fin_semestre,
                perfil_egresado,
                resultados_aprendizaje
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(programa_id) DO UPDATE SET
                nombre_programa        = excluded.nombre_programa,
                plantilla_archivo      = excluded.plantilla_archivo,
                numero_creditos        = excluded.numero_creditos,
                horas_teoricas         = excluded.horas_teoricas,
                horas_practicas        = excluded.horas_practicas,
                modalidad_default      = excluded.modalidad_default,
                horario_texto          = excluded.horario_texto,
                inicio_semestre        = excluded.inicio_semestre,
                fin_semestre           = excluded.fin_semestre,
                perfil_egresado        = excluded.perfil_egresado,
                resultados_aprendizaje = excluded.resultados_aprendizaje,
                updated_at             = datetime('now')
            ;
            """,
            (
                programa_id,
                "DOCTORADO EN CIENCIAS DE LA EDUCACIÓN",
                "doctorado_ciencias_educacion_silabo.docx",  # tu plantilla
                4,      # créditos por defecto
                40,     # horas teóricas
                48,     # horas prácticas
                modalidad_prog,  # usa modalidad real de la promoción
                "vie. 17:00 a 22:00; sáb. 8:00 a 13:00 y 16:00 a 21:00; dom. 8:00 a 13:00",
                "1 de agosto de 2025",
                "31 de diciembre de 2025",
                PERFIL_EGRESADO_DCE,
                RESULTADOS_APRENDIZAJE_DCE,
            ),
        )

        # 3) Insertar / actualizar sumillas en silabo_curso_base
        for curso in CURSOS_DCE:
            cur.execute(
                """
                INSERT INTO silabo_curso_base (programa_id, codigo, asignatura, sumilla)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(programa_id, codigo) DO UPDATE SET
                    asignatura = excluded.asignatura,
                    sumilla    = excluded.sumilla,
                    updated_at = datetime('now')
                ;
                """,
                (
                    programa_id,
                    curso["codigo"],
                    curso["asignatura"],
                    curso["sumilla"],
                ),
            )

        print(f"    -> Sumillas cargadas/actualizadas: {len(CURSOS_DCE)}\n")

    conn.commit()
    print("✅ Config + sumillas DCE actualizadas para todas las promociones.")


def main():
    conn = get_db_connection()
    try:
        seed_dce(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
