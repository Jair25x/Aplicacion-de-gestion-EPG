# utils_programas.py
import re

# Orden lógico de facultades para los reportes
FACULTY_ORDER = [
    "Ciencias y Humanidades",
    "Ciencias de la Salud",
    "Ingenierías y Arquitectura",
    "Ciencias Económicas y Contables",
    "Derecho y Ciencia Política",
]


def nombre_simple_facultad(nombre: str) -> str:
    if not nombre:
        return ""
    nombre = re.sub(r"(?i)^facultad\s+de\s+", "", nombre).strip()
    return nombre


def facultad_sort_key(nombre: str):
    simple = nombre_simple_facultad(nombre)
    try:
        idx = FACULTY_ORDER.index(simple)
    except ValueError:
        idx = len(FACULTY_ORDER)
    return (idx, simple.lower())


def programa_sort_key(programa_base: str):
    if not programa_base:
        return (3, "")
    low = programa_base.lower()
    if low.startswith("doctorado"):
        return (0, low)
    if low.startswith("maestr"):
        return (1, low)
    return (2, low)


def normalizar_programa_base(nombre_programa: str, tipo_programa: str) -> str:
    """
    Devuelve el nombre base del programa sin 'Xra Promoción ...'
    y agrupa ciertas maestrías por familias (Derecho, Ing. Civil, etc.).
    """
    if not nombre_programa:
        return ""

    base = re.sub(
        r"\s+\d+\S*\s+Promoción.*$",
        "",
        nombre_programa,
        flags=re.IGNORECASE,
    ).strip()

    # Unificar familia de Maestrías en Derecho
    if re.match(r"(?i)^maestr[ií]a\s+en\s+derecho\b", base):
        return "Maestría en Derecho"

    # Unificar familia de Maestrías en Ingeniería Civil
    if re.match(r"(?i)^maestr[ií]a\s+en\s+ingenier[ií]a\s+civil\b", base):
        return "Maestría en Ingeniería Civil"

    return base


def agrupar_por_facultad_y_programa_base(rows):
    """
    Agrupa filas de cursos por:
      facultad -> programa_base
    donde programa_base es la versión normalizada del nombre del programa.
    """
    grouped = {}
    for r in rows:
        facultad = r["facultad"]
        tipo_prog = (r["tipo_programa"] or "").upper()
        programa = r["programa"] or ""

        programa_base = normalizar_programa_base(programa, tipo_prog)

        if facultad not in grouped:
            grouped[facultad] = {}
        if programa_base not in grouped[facultad]:
            grouped[facultad][programa_base] = []

        grouped[facultad][programa_base].append(r)

    return grouped
