"""
Motor del sistema de recomendación de sitios de práctica.

Construimos este motor para apoyar al coordinador: él escoge un estudiante y el
sistema le devuelve las organizaciones más adecuadas, en cuatro pasos:
    1. Filtros:  reglas del lineamiento que deciden si una organización puede participar.
    2. Afinidad: cobertura de habilidades (qué parte de lo que pide la organización tiene el estudiante).
    3. Puntaje:  suma ponderada de cinco criterios (máximo 100 puntos).
    4. Explicación: puntos obtenidos en cada criterio y motivos de exclusión.

Uso por consola:  python recomendador.py EST-011
"""
from dataclasses import dataclass
from datetime import date
from pathlib import Path
import sys

import pandas as pd

CARPETA_DATOS = Path(__file__).parent / "datos"
FECHA_REFERENCIA = date(2026, 11, 24)   # con esta fecha revisamos si el convenio sigue vigente

# Pesos que definimos por defecto. Siempre deben sumar 100.
PESOS = {
    "afinidad": 40,      # cobertura de habilidades
    "desempeno": 25,     # cómo les ha ido a los practicantes anteriores en esa organización
    "cercania": 15,      # mismo municipio del estudiante
    "preferencias": 10,  # modalidad y sector de interés del estudiante
    "cupos": 10,         # cupos libres (menos competencia por el sitio)
}

NOMBRE_CRITERIO = {
    "afinidad": "Afinidad de habilidades",
    "desempeno": "Desempeño histórico",
    "cercania": "Cercanía",
    "preferencias": "Preferencias del estudiante",
    "cupos": "Cupos disponibles",
}


# ---------------------------------------------------------------- datos

@dataclass
class Datos:
    estudiantes: pd.DataFrame
    organizaciones: pd.DataFrame
    historial: pd.DataFrame


def a_lista(texto):
    """Convierte 'Python;Redes' en ['Python', 'Redes']. Los vacíos quedan como lista vacía."""
    if pd.isna(texto) or not str(texto).strip():
        return []
    return [parte.strip() for parte in str(texto).split(";") if parte.strip()]


def preparar_datos(estudiantes, organizaciones, historial):
    """Dejamos las tres tablas listas para el motor: tipos de dato, cupos libres y desempeño histórico."""
    estudiantes = estudiantes.fillna("").astype(str)
    organizaciones = organizaciones.fillna("").copy()
    historial = historial.copy()

    for col in ["cupos_totales", "cupos_ocupados"]:
        organizaciones[col] = organizaciones[col].astype(int)
    organizaciones["cupos_libres"] = organizaciones["cupos_totales"] - organizaciones["cupos_ocupados"]
    organizaciones["convenio_vigente_hasta"] = pd.to_datetime(organizaciones["convenio_vigente_hasta"]).dt.date
    historial["nota_final"] = historial["nota_final"].astype(float)

    organizaciones = organizaciones.merge(desempeno_por_organizacion(historial), on="id_org", how="left")
    return Datos(estudiantes, organizaciones, historial)


def cargar_datos(carpeta=CARPETA_DATOS):
    return preparar_datos(pd.read_csv(carpeta / "estudiantes.csv", dtype=str),
                          pd.read_csv(carpeta / "organizaciones.csv"),
                          pd.read_csv(carpeta / "historial_practicas.csv"))


def desempeno_por_organizacion(historial):
    """Resume el historial: cuántas prácticas, nota promedio y % de cambios de sitio por organización."""
    resumen = historial.assign(cambio=historial["cambio_de_sitio"].eq("Sí")).groupby("id_org").agg(
        practicas_previas=("id_practica", "count"),
        nota_promedio=("nota_final", "mean"),
        pct_cambio_sitio=("cambio", "mean"),
    ).reset_index()
    resumen["nota_promedio"] = resumen["nota_promedio"].round(2)
    resumen["pct_cambio_sitio"] = (resumen["pct_cambio_sitio"] * 100).round(1)
    return resumen


# ---------------------------------------------------------------- paso 1: filtros

def motivos_exclusion(estudiante, org, fecha=FECHA_REFERENCIA):
    """Revisamos las reglas del lineamiento y devolvemos las que la organización no cumple.
    Si la lista queda vacía, la organización puede participar en el ranking."""
    motivos = []
    if estudiante["programa"] not in a_lista(org["programas_aceptados"]):
        motivos.append(f"no recibe estudiantes de {estudiante['programa']}")
    if org["cupos_libres"] <= 0:
        motivos.append("no tiene cupos disponibles")
    if org["convenio_vigente_hasta"] < fecha:
        motivos.append(f"convenio vencido el {org['convenio_vigente_hasta']}")
    if estudiante["org_con_parientes"] == org["id_org"]:
        motivos.append("conflicto de interés: el estudiante tiene parientes en la organización")
    return motivos


def requisitos_estudiante(estudiante):
    """Requisitos del propio estudiante. Si no los cumple, no tiene sentido recomendarle ningún sitio."""
    faltantes = []
    if estudiante["prerrequisitos_academicos"] != "Sí":
        faltantes.append("no cumple los prerrequisitos académicos")
    if estudiante["mooc_habilidades_blandas"] != "Sí":
        faltantes.append("no ha aprobado el MOOC de habilidades blandas")
    return faltantes


# ---------------------------------------------------------------- paso 2: afinidad

def cobertura(habilidades_estudiante, habilidades_requeridas):
    """Medimos qué parte de las habilidades que pide la organización tiene el estudiante.
    Va de 0 (ninguna) a 1 (todas). Escogimos esta medida porque las habilidades extra del
    estudiante no lo perjudican, cosa que sí pasaba con Jaccard."""
    requeridas = set(habilidades_requeridas)
    if not requeridas:
        return 0.0
    return len(set(habilidades_estudiante) & requeridas) / len(requeridas)


def jaccard(a, b):
    """Alternativa que evaluamos y descartamos: habilidades en común / habilidades distintas entre los dos.
    La dejamos en el código para la comparación: castiga al estudiante que sabe más cosas."""
    a, b = set(a), set(b)
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


# ---------------------------------------------------------------- paso 3: puntaje

def proporcion_desempeno(org):
    """De 0 a 1. Tomamos la nota promedio (3.0 vale 0 y 5.0 vale 1) y descontamos los cambios de sitio.
    A una organización sin historial le damos un valor neutro (0.5) para no premiarla ni castigarla."""
    if pd.isna(org["nota_promedio"]):
        return 0.5
    nota = min(1.0, max(0.0, (org["nota_promedio"] - 3.0) / 2.0))
    sin_cambios = 1 - org["pct_cambio_sitio"] / 100
    return 0.7 * nota + 0.3 * sin_cambios


def proporcion_preferencias(estudiante, org):
    """Repartimos mitad modalidad y mitad sector. La modalidad híbrida la contamos como coincidencia parcial."""
    preferida = estudiante["modalidad_preferida"]
    if preferida in ("Indiferente", org["modalidad"]):
        modalidad = 1.0
    elif "Híbrida" in (preferida, org["modalidad"]):
        modalidad = 0.5
    else:
        modalidad = 0.0
    sector = 1.0 if estudiante["sector_interes"] == org["sector"] else 0.0
    return 0.5 * modalidad + 0.5 * sector


def calcular_puntos(estudiante, org, pesos=PESOS):
    """Cada regla da una proporción de 0 a 1 y la multiplicamos por el peso del criterio.
    Así, si cambian los pesos, las reglas siguen siendo las mismas."""
    proporciones = {
        "afinidad": cobertura(a_lista(estudiante["habilidades"]), a_lista(org["habilidades_requeridas"])),
        "desempeno": proporcion_desempeno(org),
        "cercania": 1.0 if estudiante["municipio"] == org["municipio"] else 0.4,
        "preferencias": proporcion_preferencias(estudiante, org),
        "cupos": min(org["cupos_libres"], 3) / 3,
    }
    return {criterio: round(pesos[criterio] * proporciones[criterio], 2) for criterio in pesos}


# ---------------------------------------------------------------- recomendación completa

@dataclass
class Resultado:
    estudiante: pd.Series
    ranking: pd.DataFrame       # organizaciones elegibles ordenadas por puntaje
    excluidas: pd.DataFrame     # organizaciones que no pasaron los filtros y por qué
    requisitos_faltantes: list  # si no está vacío, el estudiante no puede recibir recomendaciones


def recomendar(id_estudiante, datos, pesos=PESOS):
    if abs(sum(pesos.values()) - 100) > 0.01:
        raise ValueError(f"Los pesos deben sumar 100 y suman {sum(pesos.values())}")

    coincidencias = datos.estudiantes[datos.estudiantes["id_estudiante"] == id_estudiante]
    if coincidencias.empty:
        raise ValueError(f"No existe el estudiante {id_estudiante}")
    estudiante = coincidencias.iloc[0]

    faltantes = requisitos_estudiante(estudiante)
    if faltantes:
        return Resultado(estudiante, pd.DataFrame(), pd.DataFrame(), faltantes)

    elegibles, excluidas = [], []
    for _, org in datos.organizaciones.iterrows():
        motivos = motivos_exclusion(estudiante, org)
        if motivos:
            excluidas.append({"id_org": org["id_org"], "nombre": org["nombre"], "motivo": "; ".join(motivos)})
            continue
        puntos = calcular_puntos(estudiante, org, pesos)
        elegibles.append({**org.to_dict(), **{f"p_{c}": v for c, v in puntos.items()},
                          "puntaje": round(sum(puntos.values()), 2)})

    ranking = pd.DataFrame(elegibles)
    if not ranking.empty:
        ranking = ranking.sort_values("puntaje", ascending=False).reset_index(drop=True)
        ranking.index += 1   # posición 1, 2, 3...
    return Resultado(estudiante, ranking, pd.DataFrame(excluidas), [])


# ---------------------------------------------------------------- paso 4: explicación

def detalle_puntaje(estudiante, org_fila, pesos=PESOS):
    """Armamos la explicación de cada punto: una fila por criterio con el detalle, los puntos y el máximo."""
    habilidades_est = set(a_lista(estudiante["habilidades"]))
    habilidades_org = set(a_lista(org_fila["habilidades_requeridas"]))
    comunes = sorted(habilidades_est & habilidades_org)
    faltan = sorted(habilidades_org - habilidades_est)

    afinidad = f"Tiene {len(comunes)} de las {len(habilidades_org)} habilidades que pide la organización"
    if comunes:
        afinidad += f": {', '.join(comunes)}"
    if faltan:
        afinidad += f". Le faltan {', '.join(faltan)}"

    if pd.isna(org_fila["nota_promedio"]):
        desempeno = "La organización no tiene prácticas anteriores; se usa un valor neutro"
    else:
        desempeno = (f"Nota promedio de {org_fila['nota_promedio']:.2f} en {int(org_fila['practicas_previas'])} "
                     f"prácticas anteriores, con {org_fila['pct_cambio_sitio']:.1f} % de cambios de sitio")

    if estudiante["municipio"] == org_fila["municipio"]:
        cercania = f"Los dos están en {org_fila['municipio']}"
    else:
        cercania = f"El estudiante vive en {estudiante['municipio']} y la organización está en {org_fila['municipio']}"

    preferencias = (f"Prefiere modalidad {estudiante['modalidad_preferida'].lower()} y la organización ofrece "
                    f"{org_fila['modalidad'].lower()}. Le interesa el sector {estudiante['sector_interes'].lower()} "
                    f"y la organización es del sector {org_fila['sector'].lower()}")

    libres = int(org_fila["cupos_libres"])
    cupos = f"{libres} cupo libre" if libres == 1 else f"{libres} cupos libres"

    detalles = {"afinidad": afinidad, "desempeno": desempeno, "cercania": cercania,
                "preferencias": preferencias, "cupos": cupos}
    return [{"criterio": c, "nombre": NOMBRE_CRITERIO[c], "detalle": detalles[c],
             "puntos": float(org_fila[f"p_{c}"]), "maximo": float(pesos[c])} for c in pesos]


def explicar(estudiante, org_fila, pesos=PESOS):
    """Versión en texto de detalle_puntaje, para la consola."""
    lineas = [f"{d['nombre']}: {d['puntos']:.1f} de {d['maximo']:.4g}. {d['detalle']}."
              for d in detalle_puntaje(estudiante, org_fila, pesos)]
    lineas.append(f"Puntaje total: {org_fila['puntaje']:.2f} de 100")
    return lineas


# ---------------------------------------------------------------- consola

def main():
    id_estudiante = sys.argv[1] if len(sys.argv) > 1 else "EST-011"
    datos = cargar_datos()
    resultado = recomendar(id_estudiante, datos)
    est = resultado.estudiante
    print(f"\nEstudiante: {est['nombre']} ({est['id_estudiante']}), {est['programa']}, {est['municipio']}")
    print(f"Habilidades: {est['habilidades'].replace(';', ', ')}\n")

    if resultado.requisitos_faltantes:
        print("No se pueden generar recomendaciones: " + "; ".join(resultado.requisitos_faltantes))
        return
    if resultado.ranking.empty:
        print("Ninguna organización cumple las restricciones para este estudiante.")
    else:
        print(resultado.ranking[["nombre", "municipio", "p_afinidad", "p_desempeno", "p_cercania",
                                 "p_preferencias", "p_cupos", "puntaje"]].head(5).to_string())
        print("\nRECOMENDACIÓN:", resultado.ranking.iloc[0]["nombre"])
        for linea in explicar(est, resultado.ranking.iloc[0]):
            print("  -", linea)
    print(f"\nOrganizaciones excluidas: {len(resultado.excluidas)}")
    print(resultado.excluidas.to_string(index=False))


if __name__ == "__main__":
    main()
