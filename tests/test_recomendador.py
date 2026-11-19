"""
Pruebas del motor de recomendación.

Cada prueba comprueba una regla o un comportamiento del sistema. Las primeras usan
casos armados a mano un estudiante y una organización de ejemplo para que el
resultado esperado se pueda calcular sin computador. Las últimas usan los datos
del prototipo para revisar el sistema completo.

comando de pruebas:  python -m pytest -v
"""
from datetime import date
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import recomendador as motor  # noqa: E402


def estudiante_ejemplo(**cambios):
    datos = {
        "id_estudiante": "EST-T01", "nombre": "Estudiante de prueba", "programa": "Contaduría Pública",
        "semestre": "9", "municipio": "Sincelejo", "habilidades": "Contabilidad;Tributaria;Auditoría",
        "modalidad_preferida": "Presencial", "sector_interes": "Financiero",
        "prerrequisitos_academicos": "Sí", "mooc_habilidades_blandas": "Sí", "org_con_parientes": "",
    }
    datos.update(cambios)
    return pd.Series(datos)


def organizacion_ejemplo(**cambios):
    datos = {
        "id_org": "ORG-T01", "nombre": "Organización de prueba", "sector": "Financiero",
        "municipio": "Sincelejo", "modalidad": "Presencial", "programas_aceptados": "Contaduría Pública",
        "habilidades_requeridas": "Contabilidad;Tributaria;Auditoría;Nómina",
        "cupos_totales": 2, "cupos_ocupados": 0, "cupos_libres": 2,
        "convenio_vigente_hasta": date(2027, 6, 30),
        "practicas_previas": 10, "nota_promedio": 4.0, "pct_cambio_sitio": 10.0,
    }
    datos.update(cambios)
    return pd.Series(datos)


@pytest.fixture(scope="module")
def datos():
    return motor.cargar_datos()


# ------------------------------------------------------------ P1 a P4: reglas del lineamiento

def test_p1_organizacion_que_no_recibe_el_programa_queda_excluida():
    org = organizacion_ejemplo(programas_aceptados="Ingeniería de Sistemas")
    motivos = motor.motivos_exclusion(estudiante_ejemplo(), org)
    assert motivos == ["no recibe estudiantes de Contaduría Pública"]


def test_p2_convenio_vencido_queda_excluido():
    org = organizacion_ejemplo(convenio_vigente_hasta=date(2026, 10, 1))
    motivos = motor.motivos_exclusion(estudiante_ejemplo(), org)
    assert motivos == ["convenio vencido el 2026-10-01"]


def test_p3_organizacion_sin_cupos_queda_excluida():
    org = organizacion_ejemplo(cupos_ocupados=2, cupos_libres=0)
    assert motor.motivos_exclusion(estudiante_ejemplo(), org) == ["no tiene cupos disponibles"]


def test_p4_conflicto_de_interes_excluye_la_organizacion():
    est = estudiante_ejemplo(org_con_parientes="ORG-T01")
    motivos = motor.motivos_exclusion(est, organizacion_ejemplo())
    assert motivos == ["conflicto de interés: el estudiante tiene parientes en la organización"]


def test_p4b_organizacion_que_cumple_todo_es_elegible():
    assert motor.motivos_exclusion(estudiante_ejemplo(), organizacion_ejemplo()) == []


# ------------------------------------------------------------ P5: requisitos del estudiante

def test_p5_estudiante_sin_mooc_no_recibe_recomendaciones(datos):
    resultado = motor.recomendar("EST-002", datos)      # EST-002 no ha aprobado el MOOC
    assert resultado.requisitos_faltantes == ["no ha aprobado el MOOC de habilidades blandas"]
    assert resultado.ranking.empty


# ------------------------------------------------------------ P6: afinidad

def test_p6_cobertura_no_castiga_habilidades_extra_y_jaccard_si():
    requeridas = ["Contabilidad", "Tributaria", "Auditoría", "Nómina"]
    estudiante_a = ["Contabilidad", "Tributaria", "Auditoría"]
    estudiante_b = estudiante_a + ["Excel avanzado", "Costos", "Python"]   # sabe lo mismo y algo más

    assert motor.cobertura(estudiante_a, requeridas) == 0.75
    assert motor.cobertura(estudiante_b, requeridas) == 0.75
    assert motor.jaccard(estudiante_a, requeridas) == 0.75
    assert round(motor.jaccard(estudiante_b, requeridas), 2) == 0.43      # Jaccard le baja la nota


# ------------------------------------------------------------ P7: puntaje

def test_p7_puntaje_calculado_a_mano():
    """Caso armado para calcularlo sin computador:
    afinidad 3 de 4 = 0.75 x 40 = 30; desempeño 0.7 x 0.5 + 0.3 x 0.9 = 0.62 x 25 = 15.5;
    mismo municipio = 15; modalidad y sector coinciden = 10; 2 cupos = 2/3 x 10 = 6.67. Total 77.17."""
    puntos = motor.calcular_puntos(estudiante_ejemplo(), organizacion_ejemplo())
    assert puntos == {"afinidad": 30.0, "desempeno": 15.5, "cercania": 15.0, "preferencias": 10.0, "cupos": 6.67}
    assert round(sum(puntos.values()), 2) == 77.17


def test_p7b_organizacion_sin_historial_recibe_valor_neutro():
    org = organizacion_ejemplo(practicas_previas=float("nan"), nota_promedio=float("nan"), pct_cambio_sitio=float("nan"))
    assert motor.calcular_puntos(estudiante_ejemplo(), org)["desempeno"] == 12.5     # 0.5 x 25


def test_p7c_pesos_que_no_suman_100_se_rechazan(datos):
    pesos_malos = dict(motor.PESOS, cercania=30)       # suman 115
    with pytest.raises(ValueError, match="deben sumar 100"):
        motor.recomendar("EST-011", datos, pesos_malos)


def test_p7d_ningun_puntaje_supera_100(datos):
    for id_est in datos.estudiantes["id_estudiante"]:
        resultado = motor.recomendar(id_est, datos)
        if not resultado.ranking.empty:
            assert resultado.ranking["puntaje"].between(0, 100).all()


# ------------------------------------------------------------ P8: cambio de pesos

def test_p8_cambiar_los_pesos_cambia_la_recomendacion(datos):
    original = motor.recomendar("EST-011", datos)
    pesos_cercania = dict(motor.PESOS, afinidad=15, cercania=40)
    modificado = motor.recomendar("EST-011", datos, pesos_cercania)
    assert original.ranking.iloc[0]["nombre"] == "Secretaría de Planeación Municipal"
    assert modificado.ranking.iloc[0]["nombre"] == "Agencia de Marketing Ola Creativa"


# ------------------------------------------------------------ P9: caso sin sitios elegibles

def test_p9_estudiante_sin_organizaciones_elegibles(datos):
    """Simulamos un programa que ninguna organización recibe."""
    simulado = motor.Datos(datos.estudiantes.copy(), datos.organizaciones, datos.historial)
    simulado.estudiantes.loc[simulado.estudiantes["id_estudiante"] == "EST-011", "programa"] = "Medicina"
    resultado = motor.recomendar("EST-011", simulado)
    assert resultado.ranking.empty
    assert len(resultado.excluidas) == len(datos.organizaciones)


# ------------------------------------------------------------ P10: explicación

def test_p10_la_explicacion_suma_lo_mismo_que_el_puntaje(datos):
    resultado = motor.recomendar("EST-011", datos)
    primero = resultado.ranking.iloc[0]
    detalle = motor.detalle_puntaje(resultado.estudiante, primero)
    assert round(sum(d["puntos"] for d in detalle), 2) == primero["puntaje"]
    assert "Tiene 2 de las 4 habilidades" in detalle[0]["detalle"]


def test_p11_estudiante_inexistente_da_error_claro(datos):
    with pytest.raises(ValueError, match="No existe el estudiante EST-999"):
        motor.recomendar("EST-999", datos)
