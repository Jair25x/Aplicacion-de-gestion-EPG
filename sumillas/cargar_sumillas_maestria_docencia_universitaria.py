# cargar_sumillas_maestria_docencia_universitaria.py
#
# Script para:
# 1) Configurar silabo_programa_config para la Maestría en Docencia Universitaria (MDU)
# 2) Cargar / actualizar las sumillas de los cursos en silabo_curso_base
#
# Compatible con el generador actual:
# - Primero intenta match por codigo real (si coincide)
# - Si no, hace match por ASIGNATURA normalizada (tildes/puntos/espacios)
# - Por eso aquí guardamos nombres oficiales, y agregamos ALIAS para variantes comunes.

import sqlite3
import sys
from pathlib import Path

# === AÑADIR RAÍZ DEL PROYECTO AL sys.path ===
ROOT_DIR = Path(__file__).resolve().parent.parent  # .../gestion-docentes-app
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from db import get_db_connection


# =====================================================
# 1) Perfil del egresado + resultados de aprendizaje
# =====================================================

PERFIL_EGRESADO_MDU = """
[TODO: Reemplazar por el Perfil de Egresado oficial de la Maestría en Docencia Universitaria.]
""".strip()

RESULTADOS_APRENDIZAJE_MDU = """
[TODO: Reemplazar por Resultados de Aprendizaje oficiales del programa MDU.]
""".strip()


# =====================================================
# 2) Sumillas por asignatura (MDU)
# =====================================================

CURSOS_MDU = [
    # ==========================
    # PRIMER CICLO
    # ==========================
    {
        "codigo": "MDU_C1_PEDAGOGIA_UNIVERSITARIA",
        "asignatura": "PEDAGOGÍA UNIVERSITARIA",
        "sumilla": """
Asignatura de naturaleza teórico-práctica, cuyo propósito es analizar, desde una
perspectiva holística, los condicionantes de la acción educativa universitaria;
identificar el rol de los agentes implicados; y analizar el por qué y para qué de una
acción formativa de la universidad. Se orientará hacia una reflexión de la actuación
pedagógica que considera el contexto y su impacto en la historia personal de cada
sujeto. Se describen y analizan los diferentes enfoques pedagógicos. La apuesta es
por una pedagogía que reconozca la formación individual, pero y a su vez desde la
posibilidad de ser construido socialmente.
""".strip(),
    },
    {
        "codigo": "MDU_C1_PLANIF_GEST_CALIDAD_EDUCACION",
        "asignatura": "PLANIFICACIÓN Y GESTIÓN DE LA CALIDAD DE LA EDUCACIÓN",
        "sumilla": """
Asignatura de naturaleza teórico-práctica, cuyo propósito es presentar un panorama
general que la planificación educativa orientada a la gestión. Introduce en la
reflexión sobre los enfoques y conceptos sobre las nuevas tendencias y desafíos de
la planificación educativa en el marco de la democracia, la descentralización y la
autonomía. Brinda los lineamientos para establecer una postura política de gestión
de la institución educativa que atienda a las actuales exigencias y demandas de la
educación. Aborda la planificación estratégica. Proporciona las orientaciones para
una propuesta técnica en la formulación de planes y programas de mediano y largo
plazo. Aborda el liderazgo y la importancia del clima institucional que apunten
hacia el mejoramiento de la calidad del servicio en la institución educativa.
""".strip(),
    },
    {
        "codigo": "MDU_C1_METODOLOGIA_CIENTIFICA_INV",
        "asignatura": "METODOLOGÍA CIENTÍFICA DE LA INVESTIGACIÓN",
        "sumilla": """
Asignatura de naturaleza teórico-práctica, cuyo propósito es abordar los temas
centrales acerca de la teoría y práctica de los diferentes métodos de investigación,
tales como: Finalidad e importancia de la investigación en la generación de
conocimiento científico: su naturaleza, característica, niveles y tipos; con un
especial enfoque en los métodos cualitativos, cuantitativos y mixtos.
""".strip(),
    },
    {
        "codigo": "MDU_C1_EPISTEMOLOGIA",
        "asignatura": "EPISTEMOLOGÍA",
        "sumilla": """
Asignatura de naturaleza teórico-práctica, cuyo propósito es el estudio de la ciencia
pedagógica, ubicándola en el contexto de las otras disciplinas que también estudian
el fenómeno educativo. Dilucida su naturaleza epistemológica; asimismo alude a la
temática teleológica y axiológica de la educación, cuyos principios analiza, de igual
manera analiza la institución de la universidad, su caracterización del educando y
del educador como principales agentes educativos.
""".strip(),
    },

    # ==========================
    # SEGUNDO CICLO
    # ==========================
    {
        "codigo": "MDU_C2_PSICOLOGIA_APRENDIZAJE",
        "asignatura": "PSICOLOGÍA DEL APRENDIZAJE",
        "sumilla": """
Asignatura de naturaleza teórico-práctica, cuyo propósito es la comprensión de la
psicología del aprendizaje como herramienta activa en el proceso enseñanza
aprendizaje. Aborda las inteligencias múltiples, la motivación, la clasificación de
los aprendizajes, como: Conocimiento, Comprensión, Aplicación, Análisis,
Síntesis, Transferencia, Evaluación, Metacognición, en la enseñanza universitaria.
""".strip(),
    },
    {
        "codigo": "MDU_C2_ENFOQUES_ENS_APREND",
        "asignatura": "ENFOQUES DE ENSEÑANZA APRENDIZAJE",
        "sumilla": """
Asignatura de naturaleza teórico-práctica, cuyo propósito es conocer cómo
aprenden los alumnos, sus procesos de aprendizaje y a desarrollar en ellos, las
habilidades y adquisición de conocimientos para un desenvolvimiento crítico y
argumentativo que le permita transferir este conocimiento a las prácticas e
interacciones pedagógicas. Plantea los paradigmas contemporáneos más
consistentes sobre la relación entre la enseñanza y el aprendizaje en procesos de
educación formal. Se proyectan aportes para la reflexión sobre el currículo y sus
posibilidades de innovación.
""".strip(),
    },
    {
        "codigo": "MDU_C2_CURRICULO_COMPETENCIAS_SUP",
        "asignatura": "CURRÍCULO Y FORMACIÓN POR COMPETENCIAS EN LA EDUCACIÓN SUPERIOR",
        "sumilla": """
Asignatura de naturaleza teórico-práctica, cuyo propósito es estudiar las bases
conceptuales que definen la construcción del currículo al nivel universitario. En tal
sentido se aborda temas como la naturaleza, fuentes, estructura y tendencias
actuales. Sobre esta base se pretende plantear, creativamente, algunas propuestas
de un currículo moderno. El enfoque de un currículo por competencias permite
identificar de una manera más integral el término de calidad en la educación
universitaria, el cual adquiere relevancia cuando es contextualizado y responde a
las características y demandas de la sociedad en un momento histórico,
estableciendo criterios de eficacia, eficiencia y pertinencia.
""".strip(),
    },
    {
        "codigo": "MDU_C2_TESIS_I",
        "asignatura": "TESIS I",
        "sumilla": """
Asignatura de naturaleza teórico-práctica, cuyo propósito es orientar y asesorar en
la elaboración del diseño del proyecto de tesis de maestría. Se pone énfasis en el
planteamiento y formulación del problema de investigación; asimismo, en la
estructuración de las hipótesis, en la construcción del marco teórico y en las técnicas
de recopilación de datos. Al final, el estudiante aprobará el curso mediante la
presentación de su proyecto de investigación, diseñado de acuerdo con las
regulaciones y normas establecidas por la Escuela de Posgrado.
""".strip(),
    },

    # ==========================
    # TERCER CICLO
    # ==========================
    {
        "codigo": "MDU_C3_ESTRATEGIAS_ENS_APREND_I",
        "asignatura": "ESTRATEGIAS DE ENSEÑANZA APRENDIZAJE I",
        "sumilla": """
Asignatura de naturaleza teórico-práctica, cuyo propósito es destacar la función del
docente universitario como facilitador del aprendizaje, que, a través del manejo de
una didáctica universitaria, debe brindar una ayuda significativa al alumno en el
procesamiento de la información con vinculación a la práctica profesional. Se
plantea la enseñanza dentro del pensamiento complejo. Se analizan los factores o
componentes mediacionales y pedagógicos que comprende el estudio y
aplicabilidad de la Didáctica en el aula de clases.
""".strip(),
    },
    {
        "codigo": "MDU_C3_ESTRATEGIAS_ENS_APREND_II",
        "asignatura": "ESTRATEGIAS DE ENSEÑANZA APRENDIZAJE 2",
        "sumilla": """
Asignatura de naturaleza teórico-práctica, cuyo propósito es, en el marco de la
didáctica universitaria, establecer la relación entre los procesos de aprendizaje de
los estudiantes y los métodos de enseñanza de los profesores. Se muestran las
estrategias metodológicas activas y colaborativas. Las aplicaciones a las diferentes
profesiones. Se plantea la motivación y comunicación como ejes de una acción
educativa universitaria de calidad.
""".strip(),
    },
    # Alias común: II (por si el ERP viene con romano)
    {
        "codigo": "MDU_ALIAS_C3_ESTRATEGIAS_ENS_APREND_II_ROMANO",
        "asignatura": "ESTRATEGIAS DE ENSEÑANZA APRENDIZAJE II",
        "sumilla": """
Asignatura de naturaleza teórico-práctica, cuyo propósito es, en el marco de la
didáctica universitaria, establecer la relación entre los procesos de aprendizaje de
los estudiantes y los métodos de enseñanza de los profesores. Se muestran las
estrategias metodológicas activas y colaborativas. Las aplicaciones a las diferentes
profesiones. Se plantea la motivación y comunicación como ejes de una acción
educativa universitaria de calidad.
""".strip(),
    },

    {
        "codigo": "MDU_C3_EVALUACION_EN_EDUCACION",
        "asignatura": "EVALUACIÓN EN EDUCACIÓN",
        "sumilla": """
Asignatura de naturaleza teórico-práctica, cuyo propósito es examinar, para efectos
de evaluación, los componentes estructurales del proceso de enseñanza aprendizaje:
docente, alumno, contenido y la problemática de la relación entre método didáctico
y método del contenido a enseñar. Se plantea la naturaleza instrumental del sistema
de evaluación del aprendizaje, en la educación superior, como proceso y resultado;
asimismo, se analiza las técnicas de evaluación, los tipos de instrumentos de
evaluación. Se aborda la evaluación institucional y los procesos de acreditación.
""".strip(),
    },
    {
        "codigo": "MDU_C3_RECOLECCION_PROCESAMIENTO_DATOS",
        "asignatura": "RECOLECCIÓN Y PROCESAMIENTO DE DATOS",
        "sumilla": """
Asignatura de naturaleza teórico-práctica, cuyo propósito es brindar a los
estudiantes de posgrado una formación especializada en el manejo de datos en el
contexto de la investigación científica. Durante el curso, se abordarán los
principales aspectos de la recolección y el procesamiento de datos, incluyendo los
métodos de recolección de datos, la gestión y organización de bases de datos, la
limpieza y validación de datos, y la utilización de software especializado para el
análisis estadístico.
""".strip(),
    },

    # ==========================
    # CUARTO CICLO
    # ==========================
    {
        "codigo": "MDU_C4_PLANIF_APREND_SILABO_SESION",
        "asignatura": "PLANIFICACIÓN DE LOS APRENDIZAJES: SILABO Y SESION DE CLASE",
        "sumilla": """
Asignatura de naturaleza teórico-práctica, cuyo propósito es la elaboración del
silabo como un servicio pedagógico universitario de calidad y que responda a la
política institucional. Se espera que cada alumno se aproxime a darle al sílabo su
propio estilo de acuerdo a las expectativas que tiene del curso y, sobre todo, de sus
alumnos. Plantea lineamientos para la elaboración de las sesiones de clase
considerando los factores asociados que garantizarán una buena gestión de la
enseñanza para lograr aprendizajes significativos para los alumnos.
""".strip(),
    },
    {
        "codigo": "MDU_C4_DISENO_PROYECTOS_EDUCATIVOS",
        "asignatura": "DISEÑO DE PROYECTOS EDUCATIVOS",
        "sumilla": """
Asignatura de naturaleza teórico-práctica, cuyo propósito es analizar las bases
teóricas conceptuales y metodológicas que sustentan la elaboración y evaluación de
proyectos educativos en el marco de la planificación a fin de incorporar en el léxico
profesional del futuro maestro, la terminología y la secuencia formalizada de la
elaboración y evaluación de proyectos educativos. Asimismo, orienta la
formulación de proyectos educativos en el contexto del desarrollo nacional y sus
componentes geopolíticos, económicos, sociales, políticos y culturales, y
transporte.
""".strip(),
    },
    {
        "codigo": "MDU_C4_POLITICA_LEGISLACION_EDUCATIVA",
        "asignatura": "POLÍTICA Y LEGISLACIÓN EDUCATIVA",
        "sumilla": """
Asignatura de naturaleza teórico-práctica, cuyo propósito es enfatizar la capacidad
de análisis de los maestristas en los principales instrumentos legales, que norman el
proceso educativo en el Perú. Permite que cuenten con las habilidades y
herramientas necesarias para manejar situaciones que impliquen la aplicación de
dispositivos y normas administrativas referidas a la actividad educativa.
Comprende: el ordenamiento jurídico y el análisis de la Constitución Política del
Perú. Análisis de la ley general de educación, la estructura del sistema educativo
peruano y la gestión del sistema educativo; análisis de las principales normas
relacionadas al régimen universitario.
""".strip(),
    },
    {
        "codigo": "MDU_C4_TESIS_II",
        "asignatura": "TESIS II",
        "sumilla": """
Asignatura de naturaleza teórico-práctica, cuyo propósito es avanzar con el
asesoramiento personalizado en la ejecución del Proyecto de Tesis, elaborado en el
Taller I, con especial cuidado en las diversas estrategias relativas al proceso de
investigación. En este sentido, el profesor revisa el diseño metodológico y orienta
el trabajo de campo. La aprobación del curso se alcanza con la aprobación de un
informe preliminar de los avances de la investigación.
""".strip(),
    },
]


def main():
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 1) Buscar programa "Maestría en Docencia Universitaria"
    # Tomará la primera promoción que matchée.
    prog = cur.execute(
        """
        SELECT id, nombre_corto
        FROM programa_academico
        WHERE tipo = 'MAESTRIA'
          AND nombre_corto LIKE '%Docencia Universitaria%'
        ORDER BY id
        LIMIT 1
        """
    ).fetchone()

    if not prog:
        raise SystemExit(
            "No se encontró la Maestría en Docencia Universitaria en programa_academico.\n"
            "Verifica el campo nombre_corto."
        )

    programa_id = prog["id"]
    print(f"Usando programa_id = {programa_id} ({prog['nombre_corto']})")

    # 2) Upsert en silabo_programa_config
    # Ajusta 'plantilla_archivo' al nombre real del docx en plantillas_silabo/.
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
            nombre_programa         = excluded.nombre_programa,
            plantilla_archivo       = excluded.plantilla_archivo,
            numero_creditos         = excluded.numero_creditos,
            horas_teoricas          = excluded.horas_teoricas,
            horas_practicas         = excluded.horas_practicas,
            modalidad_default       = excluded.modalidad_default,
            horario_texto           = excluded.horario_texto,
            inicio_semestre         = excluded.inicio_semestre,
            fin_semestre            = excluded.fin_semestre,
            perfil_egresado         = excluded.perfil_egresado,
            resultados_aprendizaje  = excluded.resultados_aprendizaje,
            updated_at              = datetime('now')
        ;
        """,
        (
            programa_id,
            "MAESTRÍA EN DOCENCIA UNIVERSITARIA",
            "maestria_docencia_universitaria_silabo.docx",  # <-- AJUSTA a tu plantilla real
            4,      # créditos por defecto
            40,     # horas teóricas
            48,     # horas prácticas
            "DISTANCIA",  # modalidad por defecto
            "Según programación oficial EPG",
            "1 de agosto de 2025",
            "31 de diciembre de 2025",
            PERFIL_EGRESADO_MDU,
            RESULTADOS_APRENDIZAJE_MDU,
        ),
    )

    # 3) Insertar / actualizar sumillas en silabo_curso_base
    for curso in CURSOS_MDU:
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

    conn.commit()
    print(f"Se actualizaron {len(CURSOS_MDU)} sumillas para la Maestría en Docencia Universitaria.")


if __name__ == "__main__":
    main()
