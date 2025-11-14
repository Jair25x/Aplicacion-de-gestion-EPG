# add_docentes_octubre_2025.py

import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv
from init_db import parse_nombre  # reutilizamos tu lógica de nombres

# ============================
# Configuración de rutas / .env
# ============================
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

# Si existe DOCENTES_DB_PATH en el .env lo usamos,
# si no, se crea/usa docentes.db en esta carpeta.
DB_PATH = os.getenv("DOCENTES_DB_PATH", str(BASE_DIR / "docentes.db"))


def main():
    print(f"Usando base de datos: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # ============================
    # DOCENTES OCTUBRE 2025
    # ============================
    docentes_octubre = [
        # 1–43: Docentes locales
        ("40543399", "DRA. EDDY TELLO YARIN", "LOCAL"),
        ("23854868", "DR. EDWARDS JESÚS AGUIRRE ESPINOZA", "LOCAL"),
        ("23863492", "DR. ELIAS MELENDREZ VELASCO", "LOCAL"),
        ("08742823", "DR. JORGE LEONCIO RIVERA MUÑOZ", "LOCAL"),
        ("42495820", "DR. EDER ARTURO ACO CORRALES", "LOCAL"),

        ("23963570", "DRA. PATRICIA LUKSIC GIBAJA", "LOCAL"),
        ("40873367", "DRA. URSULA ISABEL ROMANI MIRANDA", "LOCAL"),

        ("41884386", "DR. GARETH DEL CASTILLO ESTRADA", "LOCAL"),
        ("18140940", "DRA. VHANYA OLENKA MALPICA RISCO", "LOCAL"),

        ("02424160", "DR. CIRO ABEL MESTAS VALERO", "LOCAL"),
        ("23842238", "DR. PABLO FIDEL GRAJEDA ANCCA", "LOCAL"),

        ("40767295", "DRA. CRAYLA ALFARO AUCCA", "LOCAL"),
        ("45924301", "DR. TEODORO HUARHUA CHIPANI", "LOCAL"),
        ("25310696", "DR. FELIO CALDERON LA TORRE", "LOCAL"),
        ("47025143", "DRA. KAREN MELISSA GARCES PORRAS", "LOCAL"),
        ("23867865", "DRA. VIOLETA EUGENIA ZAMALLOA ACURIO", "LOCAL"),

        ("41610570", "DR. ELVIS YURI MAMANI VARGAS", "LOCAL"),
        ("42204820", "MG. JACKELINE ALEJANDRA PELAEZ GAMARRA", "LOCAL"),
        ("41153481", "MTRA. YADIRA MATAMOROS HUAMAN", "LOCAL"),
        ("40718230", "MTRA. BETZABET EVELIN VILAVILA NORIEGA", "LOCAL"),
        ("24004480", "DRA. LIZET VARGAS VERA", "LOCAL"),
        ("24006901", "DR. ELIOT PEZO ZEGARRA", "LOCAL"),

        ("24485372", "DR. EBERT LOAIZA ROJAS", "LOCAL"),
        ("23933923", "DR. WALDO ENRIQUE CAMPAÑA MORRO", "LOCAL"),

        ("23818383", "MGT. RICARDO CASTRO PONCE DE LEON", "LOCAL"),
        ("23930110", "DR. JOSE LUIS VALENCIA VILA", "LOCAL"),
        ("72639015", "MTRO. ROY ANDY HUMPIRE CASTRO", "LOCAL"),

        ("23981474", "DRA. PAOLA ESTRADA SANCHEZ", "LOCAL"),
        ("23847092", "DR. RENNE WILFREDO PEREZ VILLAFUERTE", "LOCAL"),
        ("25199031", "DRA. ESTELA QUISPE RAMOS", "LOCAL"),

        ("10439164", "DR. LUIS MANUEL CASTILLO LUNA", "LOCAL"),
        ("40961651", "DR. JHONNY HERNAN TUPAYACHI SOTOMAYOR", "LOCAL"),
        ("23987320", "DRA. LILIANA CORONADO GAMARRA", "LOCAL"),
        ("10281126", "DR. ISAAC ENRIQUE CASTRO CUBA", "LOCAL"),

        ("28268722", "DR. SIDNEY ALEX BRAVO MELGAR", "LOCAL"),
        ("40856192", "MTRO. GILBERTO MENDOZA DEL MAESTRO", "LOCAL"),
        ("40846406", "MGT. ARACELÍ ACUÑA CHÁVEZ", "LOCAL"),
        ("23856768", "MTRA. BEGONIA VELASQUEZ CUENTAS", "LOCAL"),
        ("45827055", "MGT. YULIANO QUISPE ANDRADE", "LOCAL"),
        ("24713007", "DRA. DUNIA VICTORIA TERRAZAS GONZALES", "LOCAL"),
        ("45503490", "MTRO. ANGELLO MAURICIO RAMIREZ GUEVARA", "LOCAL"),
        ("07267102", "DR. RENZO GUILLERMO ORTIZ DIAZ", "LOCAL"),
        ("06273587", "MGT. ROMULO MARTÍN MORALES HERVIAS", "LOCAL"),

        # Ordinarios de octubre
        ("23913968", "DRA. HERMINIA CALLO SANCHEZ", "ORDINARIZADO"),
        ("07933864", "DRA. GLADIS EDITH ROJAS SALAS", "ORDINARIZADO"),
        ("23821151", "DR. JULIO TRINIDAD RIOS MAYORGA", "ORDINARIZADO"),
    ]

    insertados = 0
    ya_existian = 0

    for dni, nombre_completo, tipo_docente in docentes_octubre:
        # ¿Ya existe este DNI en la tabla docente?
        cursor.execute("SELECT id FROM docente WHERE dni = ?", (dni,))
        row = cursor.fetchone()
        if row:
            ya_existian += 1
            # Si quieres ver quién se saltó, descomenta:
            # print(f"[SKIP] DNI {dni} ya existe ({nombre_completo})")
            continue

        nombre_norm, nombres, apellidos = parse_nombre(nombre_completo)

        cursor.execute(
            """
            INSERT INTO docente
                (nombre_completo, nombres, apellidos, dni, tipo_docente, activo)
            VALUES (?, ?, ?, ?, ?, 1);
            """,
            (nombre_norm, nombres, apellidos, dni, tipo_docente),
        )
        insertados += 1

    conn.commit()
    conn.close()

    print(f"✅ Docentes nuevos insertados: {insertados}")
    print(f"ℹ️ Docentes ya existentes (mismo DNI, no se duplicaron): {ya_existian}")


if __name__ == "__main__":
    main()
