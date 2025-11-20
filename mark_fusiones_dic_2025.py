#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "docentes.db"

# Definimos las fusiones de diciembre 2025
# Cada fusión:
#   - group: identificador de grupo
#   - principal: (programa, asignatura)
#   - secundarios: lista de (programa, asignatura)
FUSIONES = [
    {
        "group": "FUSION_DCSALUD4_DPIS3_TESIS1_DIC2025",
        "principal": (
            "Doctorado en Ciencias de la Salud 4ta Promoción a Distancia",
            "SEMINARIO DE TESIS I",
        ),
        "secundarios": [
            (
                "Doctorado en Psicología 3ra Promoción a Distancia",
                "SEMINARIO DE TESIS I",
            )
        ],
    },
    {
        "group": "FUSION_MAN3_MCONT4_TESIS1_DIC2025",
        "principal": (
            "Maestría en Administración de Negocios 3ra Promoción a Distancia",
            "TESIS I",
        ),
        "secundarios": [
            (
                "Maestría en Contabilidad mención en Auditoría y Control Interno 4ta Promoción a Distancia",
                "TESIS I",
            )
        ],
    },
]


def buscar_curso(cur, periodo_id, programa, asignatura):
    row = cur.execute(
        """
        SELECT
          cp.id,
          cp.fusion_grupo,
          cp.fusion_principal
        FROM curso_programado cp
        JOIN programa_academico pa ON pa.id = cp.programa_id
        WHERE cp.periodo_id = ?
          AND pa.nombre_corto = ?
          AND cp.asignatura = ?
        """,
        (periodo_id, programa, asignatura),
    ).fetchone()
    return row


def main():
    print(f"Usando base de datos: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    periodo_row = cur.execute(
        "SELECT id, anio, mes, etiqueta FROM periodo WHERE anio = 2025 AND mes = 12"
    ).fetchone()

    if not periodo_row:
        print("❌ No se encontró el período Diciembre 2025 en la tabla periodo.")
        conn.close()
        return

    periodo_id = periodo_row["id"]
    print(f"Periodo Diciembre 2025 ID: {periodo_id}")

    total_actualizados = 0

    for fusion in FUSIONES:
        group = fusion["group"]
        principal_prog, principal_asig = fusion["principal"]
        secundarios = fusion["secundarios"]

        print(f"\n=== Configurando fusión: {group} ===")

        # Principal
        principal_row = buscar_curso(
            cur, periodo_id, principal_prog, principal_asig
        )
        if not principal_row:
            print(
                f"❌ No se encontró curso principal: '{principal_prog}' - '{principal_asig}'"
            )
        else:
            cur.execute(
                """
                UPDATE curso_programado
                SET fusion_grupo = ?, fusion_principal = 1
                WHERE id = ?
                """,
                (group, principal_row["id"]),
            )
            print(
                f"✅ Principal id={principal_row['id']} "
                f"('{principal_prog}' - '{principal_asig}') marcado con fusion_grupo='{group}', fusion_principal=1"
            )
            total_actualizados += 1

        # Secundarios
        for prog, asig in secundarios:
            row = buscar_curso(cur, periodo_id, prog, asig)
            if not row:
                print(f"❌ No se encontró curso secundario: '{prog}' - '{asig}'")
                continue

            cur.execute(
                """
                UPDATE curso_programado
                SET fusion_grupo = ?, fusion_principal = 0
                WHERE id = ?
                """,
                (group, row["id"]),
            )
            print(
                f"✅ Secundario id={row['id']} "
                f"('{prog}' - '{asig}') marcado con fusion_grupo='{group}', fusion_principal=0"
            )
            total_actualizados += 1

    conn.commit()
    conn.close()

    print(f"\n===== RESUMEN FUSIONES =====")
    print(f"Registros actualizados: {total_actualizados}")


if __name__ == "__main__":
    main()
