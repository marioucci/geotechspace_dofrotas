# === app_rotas.py ===
import sqlite3
import pandas as pd
import folium
from folium.plugins import Geocoder, MarkerCluster, LocateControl, MousePosition, Draw, MeasureControl
import streamlit as st
from streamlit_folium import st_folium

# =========================================================
# CONFIGURAÇÃO DA PÁGINA
# =========================================================
st.set_page_config(layout="wide")
st.title("🌐 Análise de Rotas DOF - IBAMA")

# =========================================================
# BANCO DE DADOS
# =========================================================
banco_dados = 'db_dadosabertosIBAMA.db'
tabela = 'autorizacoes_dof_RO_2018'

# =========================================================
# SIDEBAR - FILTROS
# =========================================================
st.sidebar.header("🔎 Filtros")

# 🔎 Busca CPF/CNPJ
filtro_cpfcnpj = st.sidebar.text_input(
    "Buscar CPF/CNPJ (Origem ou Destino)",
    placeholder="Digite parte do CPF/CNPJ"
)

# 📦 Filtro produto
def carregar_produtos():
    con = sqlite3.connect(banco_dados)
    query = f"SELECT DISTINCT produto FROM {tabela} ORDER BY produto"
    produtos = pd.read_sql_query(query, con)
    con.close()
    return produtos['produto'].dropna().tolist()

lista_produtos = carregar_produtos()

produto_selecionado = st.sidebar.selectbox(
    "Filtrar por Produto",
    ["Todos"] + lista_produtos
)

# 🔢 Limite de registros
limite = st.sidebar.slider(
    "Quantidade de registros",
    min_value=100,
    max_value=5000,
    value=100,
    step=100
)

# =========================================================
# QUERY DINÂMICA
# =========================================================
def carregar_dados():
    con = sqlite3.connect(banco_dados)

    query = f"""
    SELECT 
        lat_origem, long_origem, lat_destino, long_destino,
        municipio_origem, mun_destino, produto, volume, unidade,
        valor, nome_razaosocial, cpfcnpj,
        nom_razao_destinatario, cpfcnpj_destinatario,
        nom_patio_destino
    FROM {tabela}
    WHERE lat_origem IS NOT NULL AND long_origem IS NOT NULL
      AND lat_destino IS NOT NULL AND long_destino IS NOT NULL
      AND lat_origem != '' AND long_origem != ''
      AND lat_destino != '' AND long_destino != ''
    """

    # 🔎 Filtro CPF/CNPJ
    if filtro_cpfcnpj:
        query += f"""
        AND (
            cpfcnpj LIKE '%{filtro_cpfcnpj}%'
            OR cpfcnpj_destinatario LIKE '%{filtro_cpfcnpj}%'
        )
        """

    # 📦 Filtro produto
    if produto_selecionado != "Todos":
        query += f" AND produto = '{produto_selecionado}'"

    query += f" LIMIT {limite}"

    df = pd.read_sql_query(query, con)
    con.close()

    return df

df = carregar_dados()

st.write(f"📊 Registros encontrados: {len(df)}")

# =========================================================
# FUNÇÃO DE CONVERSÃO
# =========================================================
def to_float(valor):
    try:
        return float(str(valor).replace(',', '.'))
    except:
        return None

# =========================================================
# MAPA
# =========================================================
mapa = folium.Map(location=[-15.77, -47.55], zoom_start=4, control_scale=True)

#folium.TileLayer(tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
#                 attr='Google', name='Google Satellite Hybrid',
#                 overlay=True, control=True).add_to(mapa)

Geocoder(collapsed=True, position="topleft", add_marker=False).add_to(mapa)

LocateControl().add_to(mapa)

Draw(export=True, filename='data.geojson', position='topleft').add_to(mapa)

MeasureControl(position='topright').add_to(mapa)

MousePosition(position='topright',
              separator=' | ',
              prefix="Mouse:",
              lat_formatter="function(num) {return L.Util.formatNum(num, 3) + ' º ';};",
              lng_formatter="function(num) {return L.Util.formatNum(num, 3) + ' º ';};").add_to(mapa)

#Loop
for _, linha in df.iterrows():

    lat_origem = to_float(linha['lat_origem'])
    long_origem = to_float(linha['long_origem'])
    lat_destino = to_float(linha['lat_destino'])
    long_destino = to_float(linha['long_destino'])

    if None in [lat_origem, long_origem, lat_destino, long_destino]:
        continue

    origem = [lat_origem, long_origem]
    destino = [lat_destino, long_destino]

    # Linha
    folium.PolyLine(
        [origem, destino],
        color='blue',
        weight=2,
        opacity=0.5
    ).add_to(mapa)

    # Popup origem
    popup_origem = (
        f"<b>Origem</b><br>"
        f"{linha['nome_razaosocial']}<br>"
        f"{linha['cpfcnpj']}<br>"
        f"{linha['municipio_origem']}<br>"
        f"{linha['produto']} - {linha['volume']} {linha['unidade']}"
    )

    # Popup destino
    popup_destino = (
        f"<b>Destino</b><br>"
        f"{linha['nom_razao_destinatario']}<br>"
        f"{linha['cpfcnpj_destinatario']}<br>"
        f"{linha['mun_destino']}<br>"
        f"{linha['nom_patio_destino']}<br>"
        f"{linha['produto']} - {linha['volume']} {linha['unidade']}"
    )

    # Marcadores
    folium.CircleMarker(
        location=origem,
        radius=8,
        color='green',
        fill=True,
        fill_color='green',
        popup=popup_origem
    ).add_to(mapa)

    folium.CircleMarker(
        location=destino,
        radius=4,
        color='red',
        fill=True,
        fill_color='red',
        popup=popup_destino
    ).add_to(mapa)

# =========================================================
# EXIBIÇÃO DO MAPA
# =========================================================
st.subheader("🗺️ Mapa de Rotas")

st_folium(mapa, width=1200, height=600)

# =========================================================
# TABELA (EXPLORAÇÃO)
# =========================================================
st.subheader("📋 Dados")

st.dataframe(df)
