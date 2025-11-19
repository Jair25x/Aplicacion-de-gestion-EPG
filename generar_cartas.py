# generar_cartas.py
# Utilidades para generación de cartas desde la BD

from datetime import date, datetime
import re
import unicodedata
from typing import Optional, Union, Tuple

# ============================
# 1) Fecha larga en español
# ============================

MESES_ES = [
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "setiembre",
    "octubre",
    "noviembre",
    "diciembre",
]


def fecha_larga_es(
    fecha: Optional[Union[date, datetime]] = None,
) -> Tuple[str, str]:
    """
    Devuelve una fecha larga en español y el año, por ejemplo:
        ("14 de noviembre de 2025", "2025")

    - Si no se pasa fecha, usa la fecha actual.
    - Si se pasa datetime, usa solo la parte de fecha.
    """
    if fecha is None:
        hoy = date.today()
    elif isinstance(fecha, datetime):
        hoy = fecha.date()
    elif isinstance(fecha, date):
        hoy = fecha
    else:
        # Fallback defensivo
        hoy = date.today()

    mes_nombre = MESES_ES[hoy.month - 1]
    fecha_larga = f"{hoy.day} de {mes_nombre} de {hoy.year}"
    return fecha_larga, str(hoy.year)


# ============================
# 2) Remuneración
# ============================

def _parse_monto(monto_str: Optional[str]) -> Optional[float]:
    """
    Convierte strings como:
      '5900'
      '5900.0'
      'S/. 5,900.00'
      's/ 5900'
    a float 5900.0

    Devuelve None si no se puede interpretar.
    """
    if not monto_str:
        return None

    s = str(monto_str).strip()

    if s in ("-", "--", ""):
        return None

    # Quitar prefijos de moneda y espacios
    for pref in ["S/.", "S/", "s/.", "s/"]:
        s = s.replace(pref, "")
    s = s.replace(" ", "")

    # Quitar separadores de miles
    s = s.replace(",", "")

    try:
        return float(s)
    except ValueError:
        return None


def calc_remuneracion(
    programa_texto: str,
    override: Optional[str] = None,
) -> str:
    """
    Lógica:

    - Si 'override' viene con valor (desde la BD), se usa ese monto.
      (ej. remuneracion_monto en curso_programado)
    - Si NO hay override:
        * Si el texto del programa contiene 'doctorado' => 5900.00
        * Si contiene 'maestría' o 'maestria' => 4140.00
        * En otro caso => 0.00

    Retorna SIEMPRE un string con separador de miles y 2 decimales:
      '5,900.00'
      '4,140.00'
      '0.00'
    """
    # 1) Intentar con override (valor de la BD)
    monto = _parse_monto(override)
    if monto is not None:
        return f"{monto:,.2f}"

    # 2) Lógica por tipo de programa
    t = (programa_texto or "").lower()

    if "doctorado" in t:
        monto = 5900.00
    elif "maestría" in t or "maestria" in t:
        monto = 4140.00
    else:
        monto = 0.0

    return f"{monto:,.2f}"


# ============================
# 3) Normalizar nombre de archivo
# ============================

def _strip_accents(text: str) -> str:
    """
    Elimina acentos y caracteres combinados.
    """
    text_norm = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text_norm if not unicodedata.combining(ch))


def limpiar_nombre_archivo(nombre: str) -> str:
    """
    Limpia un texto para usarlo como nombre de archivo:

    - Quita acentos
    - Quita caracteres no seguros
    - Reemplaza espacios por guiones bajos
    - Evita repeticiones de guiones bajos
    """
    if not nombre:
        return "archivo"

    nombre = nombre.strip()
    nombre = _strip_accents(nombre)

    # Dejar solo letras, números, espacios, guiones y puntos
    nombre = re.sub(r"[^A-Za-z0-9\.\- ]+", "", nombre)

    # Reemplazar espacios por guiones bajos
    nombre = nombre.replace(" ", "_")

    # Compactar guiones bajos repetidos
    nombre = re.sub(r"_+", "_", nombre)

    # Quitar guiones bajos iniciales/finales
    nombre = nombre.strip("_")

    return nombre or "archivo"


# ============================
# 4) Extraer título, paterno y nombre
# ============================

_TITULOS_INICIALES = {
    "DR", "DRA",
    "MG", "MGS", "MBA", "MSC",
    "LIC", "ING", "ARQ",
    "MEDICO", "MÉDICO", "PSIC",
    "ABOG", "ABOGADO", "ABOGADA",
}


def extraer_paterno_y_nombre(nombre_completo: str) -> Tuple[str, str]:
    """
    Versión simplificada que devuelve solo (paterno, nombre) y
    **descarta** títulos como DR., DRA., MG., etc.
    Se mantiene para compatibilidad con el script CLI anterior.
    """
    if not nombre_completo:
        return "DOCENTE", ""

    partes = nombre_completo.strip().split()

    # Quitar títulos al inicio (DR., DRA., MG., LIC., etc.)
    while partes:
        token = partes[0].upper().rstrip(".")
        if token in _TITULOS_INICIALES:
            partes.pop(0)
        else:
            break

    if not partes:
        return "DOCENTE", ""

    if len(partes) == 1:
        return partes[0].upper(), ""
    if len(partes) == 2:
        return partes[0].upper(), partes[1].upper()

    paterno = partes[0].upper()
    nombre = partes[-1].upper()
    return paterno, nombre


def extraer_titulo_paterno_nombre(nombre_completo: str) -> Tuple[str, str, str]:
    """
    Versión extendida para nombres tipo:
        'DRA. MIRIAM CLEDY ZARATE MUÑIZ'
        'Mg. Del Carpio Gamarra Manuel Jesus'
        'DR JUAN PEREZ LOPEZ'

    Devuelve:
        (titulo, paterno, nombre)

    Ejemplos:
      'DRA. MIRIAM CLEDY ZARATE MUÑIZ'  -> ('DRA', 'ZARATE', 'MIRIAM')
      'Mg. Del Carpio Gamarra Manuel Jesus' -> ('MG', 'GAMARRA', 'MANUEL')
      'MIRIAM CLEDY ZARATE MUÑIZ'      -> ('', 'ZARATE', 'MIRIAM')
    """
    if not nombre_completo:
        return "", "DOCENTE", ""

    partes = nombre_completo.strip().split()

    # 1) Extraer uno o más títulos iniciales
    titulos = []
    while partes:
        token_raw = partes[0]
        token_norm = token_raw.upper().rstrip(".")
        if token_norm in _TITULOS_INICIALES:
            titulos.append(token_norm)  # ej. "DRA", "MG"
            partes.pop(0)
        else:
            break

    titulo = " ".join(titulos)  # "DRA", "MG", "DR", etc.

    # 2) Si después de quitar títulos ya no queda nada
    if not partes:
        if not titulo:
            return "", "DOCENTE", ""
        return titulo, "DOCENTE", ""

    # 3) Calcular paterno y nombre a partir del resto
    if len(partes) == 1:
        paterno = partes[0].upper()
        nombre = ""
    elif len(partes) == 2:
        paterno = partes[0].upper()
        nombre = partes[1].upper()
    else:
        # Heurística: primer token = apellido paterno, último token = primer nombre
        paterno = partes[-2].upper()   # ej. 'ZARATE' en 'MIRIAM CLEDY ZARATE MUÑIZ'
        nombre = partes[-3].upper() if len(partes) >= 3 else partes[0].upper()

        # Si prefieres paterno primer token y nombre último, usa:
        # paterno = partes[0].upper()
        # nombre = partes[-1].upper()

    return titulo, paterno, nombre
