"""
Interfaz web del sistema de recomendación de sitios de práctica.
Ejecutar:  streamlit run app.py
"""
from html import escape

import pandas as pd
import streamlit as st

import recomendador as motor

st.set_page_config(page_title="Recomendación de sitios de práctica", layout="wide")

# Para los cinco criterios escogimos una sola familia de tonos, del más importante al menos importante.
COLOR_CRITERIO = {
    "afinidad": "#16425B",
    "desempeno": "#2F6F8A",
    "cercania": "#5A9BB0",
    "preferencias": "#8FBCCB",
    "cupos": "#C4DCE3",
}

ESTILOS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;500;600;700&display=swap');

.stApp { font-family: 'Public Sans', sans-serif; }
.block-container { padding-top: 2.2rem; max-width: 1180px; }
h1, h2, h3 { color: #16425B; letter-spacing: -0.01em; }

.encabezado { border-bottom: 1px solid #D5DDE2; padding-bottom: 1.1rem; margin-bottom: 1.4rem; }
.encabezado .titulo-app { font-size: 0.95rem; color: #5C6B74; margin: 0 0 0.9rem 0; }
.encabezado .nombre { font-size: 2rem; font-weight: 700; color: #16425B; line-height: 1.15; margin: 0; }
.encabezado .datos { display: flex; flex-wrap: wrap; gap: 0.4rem 2rem; margin-top: 0.7rem; color: #1F2B33; }
.encabezado .datos span b { font-weight: 600; color: #5C6B74; margin-right: 0.35rem; }
.habilidades { margin-top: 0.8rem; display: flex; flex-wrap: wrap; gap: 0.4rem; }
.habilidad { background: #E8EDF0; color: #1F2B33; border-radius: 4px; padding: 0.15rem 0.55rem; font-size: 0.88rem; }

.ficha { background: #FFFFFF; border: 1px solid #D5DDE2; border-left: 5px solid #B9832F;
         border-radius: 6px; padding: 1.4rem 1.6rem; margin-bottom: 1.6rem; }
.ficha .sello { color: #8A6020; font-weight: 600; font-size: 0.9rem; margin-bottom: 0.35rem; }
.fila-titulo { display: flex; justify-content: space-between; align-items: baseline; gap: 1rem; }
.fila-titulo .org { font-size: 1.45rem; font-weight: 700; color: #1F2B33; margin: 0; }
.fila-titulo .puntaje { font-size: 1.9rem; font-weight: 700; color: #16425B; white-space: nowrap; }
.fila-titulo .puntaje small { font-size: 0.95rem; font-weight: 500; color: #5C6B74; }
.lugar { color: #5C6B74; margin: 0.2rem 0 0.9rem 0; }

.barra { display: flex; height: 14px; width: 100%; background: #EEF2F4; border-radius: 3px; overflow: hidden; }
.barra div { height: 100%; }
.leyenda { display: flex; flex-wrap: wrap; gap: 0.3rem 1.2rem; font-size: 0.85rem; color: #5C6B74; margin: 0.6rem 0 1.4rem 0; }
.leyenda i { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 0.35rem; vertical-align: -1px; }

table.detalle { width: 100%; border-collapse: collapse; margin-top: 0.4rem; border: none; }
table.detalle th, table.detalle td { border-left: none; border-right: none; border-top: none; }
table.detalle th { text-align: left; font-weight: 600; color: #5C6B74; font-size: 0.88rem; padding: 0.45rem 0.6rem; border-bottom: 1px solid #D5DDE2; }
table.detalle td { padding: 0.6rem; border-bottom: 1px solid #EEF2F4; vertical-align: top; line-height: 1.45; }
table.detalle td.pts { white-space: nowrap; text-align: right; font-weight: 600; color: #16425B; }
table.detalle tr.total td { border-bottom: none; font-weight: 700; }

.alterna { background: #FFFFFF; border: 1px solid #D5DDE2; border-radius: 6px; padding: 1rem 1.3rem 1.2rem 1.3rem; margin-bottom: 0.5rem; }
.alterna .fila-titulo .org { font-size: 1.1rem; }
.alterna .fila-titulo .puntaje { font-size: 1.3rem; }

.aviso { background: #FBF4E6; border: 1px solid #E8D3A6; color: #5E4310; border-radius: 6px; padding: 0.8rem 1rem; margin: 0.4rem 0 1.2rem 0; }
.bloqueo { background: #FFFFFF; border: 1px solid #D5DDE2; border-left: 5px solid #9B3B2E; border-radius: 6px; padding: 1.2rem 1.4rem; }
.bloqueo p { margin: 0.2rem 0; }
</style>
"""


@st.cache_data
def obtener_datos():
    return motor.cargar_datos()


def restablecer_pesos():
    for criterio, valor in motor.PESOS.items():
        st.session_state[f"peso_{criterio}"] = valor


def normalizar(pesos):
    """Si los controles no suman 100, ajustamos los pesos manteniendo la proporción que eligió el coordinador."""
    total = sum(pesos.values())
    if total == 0:
        return dict(motor.PESOS)
    return {c: v * 100 / total for c, v in pesos.items()}


# ---------------------------------------------------------------- piezas HTML

def html_barra(detalle):
    """Dibujamos una barra partida en los cinco criterios: el largo de cada tramo son los puntos obtenidos."""
    tramos = "".join(
        f'<div style="width:{d["puntos"]}%; background:{COLOR_CRITERIO[d["criterio"]]}" '
        f'title="{escape(d["nombre"])}: {d["puntos"]:.1f} de {d["maximo"]:.4g}"></div>'
        for d in detalle)
    return f'<div class="barra" role="img" aria-label="Composición del puntaje">{tramos}</div>'


def html_leyenda():
    items = "".join(f'<span><i style="background:{COLOR_CRITERIO[c]}"></i>{escape(motor.NOMBRE_CRITERIO[c])}</span>'
                    for c in motor.PESOS)
    return f'<div class="leyenda">{items}</div>'


def html_tabla_detalle(detalle, total):
    filas = "".join(
        f'<tr><td><b>{escape(d["nombre"])}</b></td><td>{escape(d["detalle"])}</td>'
        f'<td class="pts">{d["puntos"]:.1f} de {d["maximo"]:.4g}</td></tr>'
        for d in detalle)
    return (f'<table class="detalle"><tr><th>Criterio</th><th>Qué se encontró</th><th style="text-align:right">Puntos</th></tr>'
            f'{filas}<tr class="total"><td>Total</td><td></td><td class="pts">{total:.1f} de 100</td></tr></table>')


def html_titulo_org(org):
    return (f'<div class="fila-titulo"><p class="org">{escape(org["nombre"])}</p>'
            f'<span class="puntaje">{org["puntaje"]:.1f}<small> de 100</small></span></div>'
            f'<p class="lugar">{escape(org["sector"])}, {escape(org["municipio"])}. Modalidad {escape(org["modalidad"].lower())}.</p>')


# ---------------------------------------------------------------- página

st.markdown(ESTILOS, unsafe_allow_html=True)
datos = obtener_datos()

with st.sidebar:
    st.subheader("Estudiante")
    opciones = datos.estudiantes["id_estudiante"] + "  " + datos.estudiantes["nombre"]
    elegido = st.selectbox("Busque por código o nombre", opciones,
                           index=int(opciones.str.startswith("EST-011").idxmax()))
    id_estudiante = elegido.split("  ")[0]

    st.subheader("Importancia de cada criterio")
    st.caption("Mueva los controles para ver cómo cambia la recomendación. "
               "Si no suman 100, se ajustan en la misma proporción.")
    for criterio, valor in motor.PESOS.items():
        st.session_state.setdefault(f"peso_{criterio}", valor)
    pesos_usuario = {c: st.slider(motor.NOMBRE_CRITERIO[c], 0, 60, step=5, key=f"peso_{c}")
                     for c in motor.PESOS}
    pesos = normalizar(pesos_usuario)
    suma = sum(pesos_usuario.values())
    if suma != 100:
        st.caption(f"Los controles suman {suma}. Pesos aplicados: "
                   + ", ".join(f"{motor.NOMBRE_CRITERIO[c].lower()} {v:.1f}" for c, v in pesos.items()) + ".")
    st.button("Volver a los pesos originales", on_click=restablecer_pesos, width="stretch")

resultado = motor.recomendar(id_estudiante, datos, pesos)
est = resultado.estudiante

habilidades = "".join(f'<span class="habilidad">{escape(h)}</span>' for h in motor.a_lista(est["habilidades"]))
st.markdown(f"""
<div class="encabezado">
  <p class="titulo-app">Recomendación de sitios de práctica</p>
  <p class="nombre">{escape(est['nombre'])}</p>
  <div class="datos">
    <span><b>Código</b>{escape(est['id_estudiante'])}</span>
    <span><b>Programa</b>{escape(est['programa'])}</span>
    <span><b>Municipio</b>{escape(est['municipio'])}</span>
    <span><b>Modalidad preferida</b>{escape(est['modalidad_preferida'])}</span>
    <span><b>Sector de interés</b>{escape(est['sector_interes'])}</span>
  </div>
  <div class="habilidades">{habilidades}</div>
</div>""", unsafe_allow_html=True)

if resultado.requisitos_faltantes:
    motivos = "".join(f"<p>El estudiante {escape(m)}.</p>" for m in resultado.requisitos_faltantes)
    st.markdown(f'<div class="bloqueo"><p><b>Todavía no se le puede recomendar un sitio.</b></p>{motivos}'
                f'<p>Cuando cumpla estos requisitos aparecerán sus recomendaciones.</p></div>', unsafe_allow_html=True)
    st.stop()

if resultado.ranking.empty:
    st.markdown('<div class="bloqueo"><p><b>Ninguna organización cumple las reglas para este estudiante.</b></p>'
                '<p>Revise abajo por qué se descartó cada una.</p></div>', unsafe_allow_html=True)
    st.dataframe(resultado.excluidas, hide_index=True, width="stretch")
    st.stop()

ranking = resultado.ranking
tab_rec, tab_todos, tab_desc, tab_metodo = st.tabs([
    "Recomendación",
    f"Todos los sitios elegibles ({len(ranking)})",
    f"Sitios descartados ({len(resultado.excluidas)})",
    "Cómo se calcula",
])

with tab_rec:
    primero = ranking.iloc[0]
    detalle = motor.detalle_puntaje(est, primero, pesos)
    st.markdown(f"""
<div class="ficha">
  <div class="sello">Sitio recomendado</div>
  {html_titulo_org(primero)}
  {html_barra(detalle)}
  {html_leyenda()}
  {html_tabla_detalle(detalle, primero['puntaje'])}
</div>""", unsafe_allow_html=True)

    if len(ranking) > 1:
        diferencia = primero["puntaje"] - ranking.iloc[1]["puntaje"]
        if diferencia < 3:
            st.markdown(f'<div class="aviso">El segundo sitio quedó a solo {diferencia:.1f} puntos. '
                        'Conviene revisar las dos opciones antes de asignar.</div>', unsafe_allow_html=True)

        st.subheader("Otras opciones")
        for _, org in ranking.iloc[1:3].iterrows():
            detalle_org = motor.detalle_puntaje(est, org, pesos)
            st.markdown(f'<div class="alterna">{html_titulo_org(org)}{html_barra(detalle_org)}</div>',
                        unsafe_allow_html=True)
            with st.expander(f"Ver el detalle de {org['nombre']}"):
                st.markdown(html_tabla_detalle(detalle_org, org["puntaje"]), unsafe_allow_html=True)

with tab_todos:
    tabla = ranking[["nombre", "municipio", "modalidad"] + [f"p_{c}" for c in motor.PESOS] + ["puntaje"]].copy()
    tabla.insert(0, "posición", ranking.index)
    st.dataframe(
        tabla, hide_index=True, width="stretch",
        column_config={
            "nombre": "Organización",
            **{f"p_{c}": st.column_config.NumberColumn(motor.NOMBRE_CRITERIO[c], format="%.1f") for c in motor.PESOS},
            "puntaje": st.column_config.ProgressColumn("Puntaje", min_value=0, max_value=100, format="%.1f"),
        })

with tab_desc:
    st.caption("Organizaciones que no cumplen las reglas del lineamiento de práctica para este estudiante.")
    st.dataframe(resultado.excluidas.rename(columns={"id_org": "código", "nombre": "organización"}),
                 hide_index=True, width="stretch")

with tab_metodo:
    st.markdown("""
#### 1. Reglas del lineamiento
Primero se revisa que el estudiante cumpla los prerrequisitos académicos y haya aprobado el MOOC de
habilidades blandas. Después se descarta toda organización que no reciba su programa, que no tenga cupos,
que tenga el convenio vencido o donde el estudiante tenga parientes.

#### 2. Afinidad de habilidades
De las habilidades que pide la organización, se cuenta cuántas tiene el estudiante. Si pide 4 y el
estudiante tiene 3, la afinidad es del 75 %. Las habilidades adicionales del estudiante no le restan.

#### 3. Puntaje de 0 a 100
Cada criterio da un porcentaje que se multiplica por su importancia:

| Criterio | Importancia | Cómo se mide |
|---|---|---|
| Afinidad de habilidades | 40 | Habilidades que tiene de las que pide la organización |
| Desempeño histórico | 25 | Nota promedio de practicantes anteriores (3.0 vale 0 y 5.0 vale 100 %), con descuento por cambios de sitio |
| Cercanía | 15 | Mismo municipio vale 100 %, otro municipio 40 % |
| Preferencias del estudiante | 10 | La mitad por modalidad y la mitad por sector |
| Cupos disponibles | 10 | Más cupos libres, menos competencia por el sitio (máximo 3) |

#### 4. Quién decide
El puntaje ordena las opciones; no es una probabilidad de éxito. La asignación final la hace el coordinador.
""")
    st.caption("Prototipo académico de CECAR. Los datos de estudiantes y organizaciones son ficticios.")
