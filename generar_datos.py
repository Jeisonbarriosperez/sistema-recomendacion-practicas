"""
Genera los datos sintéticos del prototipo.

No existen datos reales de CECAR disponibles para el proyecto, así que se crean
datos ficticios pero coherentes con el lineamiento de práctica (programas,
convenios, cupos, prerrequisitos, MOOC y conflicto de interés).
Los nombres de personas y organizaciones son inventados.

Uso:  python generar_datos.py
Salida: datos/estudiantes.csv, datos/organizaciones.csv, datos/historial_practicas.csv
"""
from datetime import date, timedelta
from pathlib import Path
import random

import pandas as pd

SEMILLA = 2026          # misma semilla = mismos datos cada vez que se ejecute
CARPETA = Path(__file__).parent / "datos"
FECHA_REFERENCIA = date(2026, 11, 24)

HABILIDADES_POR_PROGRAMA = {
    "Ingeniería de Sistemas": ["Python", "Java", "Bases de datos", "Redes", "Desarrollo web",
                               "Soporte técnico", "Análisis de datos", "Ciberseguridad"],
    "Administración de Empresas": ["Gestión de proyectos", "Marketing", "Excel avanzado",
                                   "Atención al cliente", "Recursos humanos",
                                   "Planeación estratégica", "Análisis de datos", "Logística"],
    "Contaduría Pública": ["Contabilidad", "Excel avanzado", "Tributaria", "Auditoría",
                           "Nómina", "Software contable", "Costos", "Análisis financiero"],
    "Ingeniería Industrial": ["Logística", "Gestión de calidad", "Excel avanzado",
                              "Seguridad industrial", "Producción", "Gestión de proyectos",
                              "Análisis de datos", "Costos"],
}
PROGRAMAS = list(HABILIDADES_POR_PROGRAMA)
MUNICIPIOS = ["Sincelejo", "Sincelejo", "Sincelejo", "Corozal", "Sampués", "Tolú", "San Marcos"]
MODALIDADES = ["Presencial", "Híbrida", "Remota"]
SECTORES = ["Tecnología", "Comercio", "Salud", "Gobierno", "Financiero", "Manufactura", "Servicios"]

ORGANIZACIONES = [
    ("Soluciones Digitales del Caribe S.A.S.", "Tecnología", ["Ingeniería de Sistemas"]),
    ("Red Sabana Telecomunicaciones", "Tecnología", ["Ingeniería de Sistemas"]),
    ("CodeSur Software Lab", "Tecnología", ["Ingeniería de Sistemas"]),
    ("Clínica Santa Lucía del Sinú", "Salud", ["Ingeniería de Sistemas", "Administración de Empresas"]),
    ("Distribuidora La Sabana", "Comercio", ["Administración de Empresas", "Ingeniería Industrial"]),
    ("Supermercados El Golfo", "Comercio", ["Administración de Empresas", "Contaduría Pública"]),
    ("Cooperativa Agropecuaria de Sucre", "Servicios", ["Administración de Empresas", "Contaduría Pública"]),
    ("Contadores Asociados Morrosquillo", "Financiero", ["Contaduría Pública"]),
    ("Banco Cooperativo Sabanero", "Financiero", ["Contaduría Pública", "Administración de Empresas"]),
    ("Fondo de Empleados del Caribe", "Financiero", ["Contaduría Pública"]),
    ("Lácteos La Pradera", "Manufactura", ["Ingeniería Industrial"]),
    ("Arrocera San Marcos", "Manufactura", ["Ingeniería Industrial", "Contaduría Pública"]),
    ("Concretos y Prefabricados Sucre", "Manufactura", ["Ingeniería Industrial"]),
    ("Transportes Rápido Sabanero", "Servicios", ["Ingeniería Industrial", "Administración de Empresas"]),
    ("Hotel Brisas de Tolú", "Servicios", ["Administración de Empresas"]),
    ("Secretaría de Planeación Municipal", "Gobierno", ["Ingeniería de Sistemas", "Administración de Empresas"]),
    ("Instituto Departamental de Tránsito", "Gobierno", ["Ingeniería de Sistemas", "Contaduría Pública"]),
    ("Empresa de Servicios Públicos AguaClara", "Servicios", ["Ingeniería de Sistemas", "Ingeniería Industrial"]),
    ("Farmacias Vida Sana", "Salud", ["Administración de Empresas", "Contaduría Pública"]),
    ("Centro Médico Corozal", "Salud", ["Contaduría Pública", "Ingeniería de Sistemas"]),
    ("Agencia de Marketing Ola Creativa", "Servicios", ["Administración de Empresas"]),
    ("Taller Metalmecánico El Progreso", "Manufactura", ["Ingeniería Industrial"]),
    ("Data Insight Consultores", "Tecnología", ["Ingeniería de Sistemas", "Ingeniería Industrial"]),
    ("Almacenes Ferreteros del Sinú", "Comercio", ["Contaduría Pública", "Ingeniería Industrial"]),
    ("Universidad Virtual Costa Norte", "Servicios", ["Ingeniería de Sistemas", "Administración de Empresas"]),
]

NOMBRES = ["Andrea", "Luis", "Camila", "Santiago", "Valeria", "Mateo", "Daniela", "Sebastián",
           "Laura", "Juan", "María", "Carlos", "Paula", "Andrés", "Sofía", "Diego", "Natalia",
           "Felipe", "Juliana", "Kevin", "Mariana", "Jhon", "Isabella", "Esteban"]
APELLIDOS = ["Mercado", "Pérez", "Vergara", "Salgado", "Montes", "Ortega", "Benítez", "Arrieta",
             "Contreras", "Villalba", "Pacheco", "Romero", "Hoyos", "Tovar", "Cárdenas", "Meza",
             "Paternina", "Ruiz", "Sierra", "Álvarez"]


def generar_organizaciones(rng):
    filas = []
    for i, (nombre, sector, programas) in enumerate(ORGANIZACIONES, start=1):
        posibles = sorted({h for p in programas for h in HABILIDADES_POR_PROGRAMA[p]})
        cupos = rng.randint(1, 4)
        # unas pocas organizaciones quedan con el convenio vencido o sin cupos, como pasa en la realidad
        dias_convenio = rng.choice([-60, -15] + [rng.randint(90, 700) for _ in range(10)])
        filas.append({
            "id_org": f"ORG-{i:02d}",
            "nombre": nombre,
            "sector": sector,
            "municipio": rng.choice(MUNICIPIOS),
            "modalidad": rng.choices(MODALIDADES, weights=[6, 3, 1])[0],
            "programas_aceptados": ";".join(programas),
            "habilidades_requeridas": ";".join(rng.sample(posibles, 4)),
            "cupos_totales": cupos,
            "cupos_ocupados": cupos if rng.random() < 0.12 else rng.randint(0, cupos - 1),
            "convenio_vigente_hasta": (FECHA_REFERENCIA + timedelta(days=dias_convenio)).isoformat(),
        })
    return pd.DataFrame(filas)


def generar_estudiantes(rng, organizaciones, cantidad=80):
    filas = []
    for i in range(1, cantidad + 1):
        programa = rng.choice(PROGRAMAS)
        propias = rng.sample(HABILIDADES_POR_PROGRAMA[programa], rng.randint(3, 5))
        # algunas habilidades de otros programas, para que el perfil no sea perfecto
        otras = [h for p in PROGRAMAS if p != programa for h in HABILIDADES_POR_PROGRAMA[p]]
        habilidades = sorted(set(propias + rng.sample(otras, rng.randint(0, 2))))
        parientes = rng.choice(organizaciones["id_org"].tolist()) if rng.random() < 0.08 else ""
        filas.append({
            "id_estudiante": f"EST-{i:03d}",
            "nombre": f"{rng.choice(NOMBRES)} {rng.choice(APELLIDOS)} {rng.choice(APELLIDOS)}",
            "programa": programa,
            "semestre": rng.choice([8, 9, 9, 10]),
            "municipio": rng.choice(MUNICIPIOS),
            "habilidades": ";".join(habilidades),
            "modalidad_preferida": rng.choices(MODALIDADES + ["Indiferente"], weights=[4, 3, 1, 2])[0],
            "sector_interes": rng.choice(SECTORES),
            "prerrequisitos_academicos": "Sí" if rng.random() < 0.92 else "No",
            "mooc_habilidades_blandas": "Sí" if rng.random() < 0.88 else "No",
            "org_con_parientes": parientes,
        })
    return pd.DataFrame(filas)


def generar_historial(rng, organizaciones, cantidad=300):
    # cada organización tiene una "calidad" oculta que explica sus resultados pasados
    calidad = {org: rng.uniform(3.4, 4.7) for org in organizaciones["id_org"]}
    periodos = ["2024-1", "2024-2", "2025-1", "2025-2", "2026-1"]
    filas = []
    for i in range(1, cantidad + 1):
        org = organizaciones.sample(1, random_state=rng.randint(0, 10**6)).iloc[0]
        nota = min(5.0, max(2.5, rng.gauss(calidad[org["id_org"]], 0.35)))
        prob_cambio = 0.30 if calidad[org["id_org"]] < 3.8 else 0.06
        filas.append({
            "id_practica": f"PR-{i:04d}",
            "id_org": org["id_org"],
            "programa": rng.choice(org["programas_aceptados"].split(";")),
            "periodo": rng.choice(periodos),
            "nota_final": round(nota, 1),
            "cambio_de_sitio": "Sí" if rng.random() < prob_cambio else "No",
        })
    return pd.DataFrame(filas)


def main():
    rng = random.Random(SEMILLA)
    CARPETA.mkdir(exist_ok=True)
    organizaciones = generar_organizaciones(rng)
    estudiantes = generar_estudiantes(rng, organizaciones)
    historial = generar_historial(rng, organizaciones)

    organizaciones.to_csv(CARPETA / "organizaciones.csv", index=False, encoding="utf-8")
    estudiantes.to_csv(CARPETA / "estudiantes.csv", index=False, encoding="utf-8")
    historial.to_csv(CARPETA / "historial_practicas.csv", index=False, encoding="utf-8")
    print(f"{len(estudiantes)} estudiantes, {len(organizaciones)} organizaciones, "
          f"{len(historial)} prácticas históricas generadas en {CARPETA}")


if __name__ == "__main__":
    main()
