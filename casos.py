import streamlit as st
import pandas as pd
import plotly.express as px

# =========================================================
# CONFIGURAÇÃO DA PÁGINA
# =========================================================
st.set_page_config(layout="wide")
st.title("📊 Dashboard - Leishmaniose")

# =========================================================
# LEITURA DOS DADOS
# =========================================================
@st.cache_data
def carregar_dados():
    df = pd.read_parquet("leishmaniose_mega_tratada.parquet")

    df["dt_notific"] = pd.to_datetime(df["dt_notific"], errors="coerce")
    df["ano"] = df["dt_notific"].dt.year
    df["casos"] = 1

    referencia_municipios = (
        df.dropna(subset=["nome_municipio"])
        .drop_duplicates(subset=["id_municip"])
        [["id_municip", "nome_municipio"]]
    )

    df = df.drop(columns=["nome_municipio"]).merge(
        referencia_municipios,
        on="id_municip",
        how="left"
    )

    return df


# >>> AQUI
df = carregar_dados()



# =========================================================
# FILTROS
# =========================================================
st.sidebar.header("Filtros")

ano = st.sidebar.selectbox(
    "Selecione o Ano",
    sorted(df["ano"].dropna().unique())
)

estado = st.sidebar.multiselect(
    "Selecione o Estado",
    sorted(df["uf"].dropna().unique())
)

df_filtro = df[df["ano"] == ano]

if estado:
    df_filtro = df_filtro[df_filtro["uf"].isin(estado)]

st.sidebar.markdown("---")
st.sidebar.write("Registros filtrados:", df_filtro.shape[0])

if df_filtro.empty:
    st.warning("⚠️ Não há dados para os filtros selecionados.")
    st.stop()
# =========================================================
# INDICADORES
# =========================================================
total_casos = df_filtro["casos"].sum()
total_estados = df_filtro["uf"].nunique()
total_municipios = df_filtro["id_municip"].nunique()

col1, col2, col3 = st.columns(3)

col1.metric("Total de Casos", f"{total_casos:,}".replace(",", "."))
col2.metric("Estados com Casos", total_estados)
col3.metric("Municípios com Casos", total_municipios)

st.markdown("---")

# =========================================================
# CASOS POR ESTADO
# =========================================================
st.subheader("📍 Casos por Estado")

casos_estado = (
    df_filtro
    .groupby("uf")["casos"]
    .sum()
    .reset_index()
    .sort_values("casos", ascending=False)
)

fig_estado = px.bar(
    casos_estado,
    x="uf",
    y="casos",
    text="casos",
    title="Casos por Estado",
    labels={"uf": "Estado", "casos": "Número de Casos"}
)

fig_estado.update_layout(xaxis_tickangle=-45)

st.plotly_chart(fig_estado, use_container_width=True)

# =========================================================
# TOP 20 MUNICÍPIOS
# =========================================================
st.subheader("🏙️ Top 20 Municípios com Mais Casos")

casos_municipio = (
    df_filtro
    .dropna(subset=["nome_municipio"])   # garante nome válido
    .groupby(["nome_municipio", "uf"], as_index=False)["casos"]
    .sum()
    .sort_values("casos", ascending=False)
    .head(20)
)

if casos_municipio.empty:
    st.warning("Sem dados de município para esse ano.")
else:
    fig_municipio = px.bar(
        casos_municipio,
        x="nome_municipio",
        y="casos",
        color="uf",
        text="casos",
        title="Top 20 Municípios com Mais Casos"
    )

    fig_municipio.update_layout(
        xaxis_title="Município",
        yaxis_title="Casos",
        xaxis_tickangle=-45
    )

    st.plotly_chart(fig_municipio, use_container_width=True)

# =========================================================
# MAPA GEOESPACIAL
# =========================================================
st.subheader("🗺️ Distribuição Geográfica dos Casos")

casos_mapa = (
    df_filtro
    .groupby("id_municip")["casos"]
    .sum()
    .reset_index()
)

geo_base = (
    df[["id_municip", "nome_municipio", "uf", "lat_locali", "long_local"]]
    .drop_duplicates(subset=["id_municip"])
)

casos_mapa = casos_mapa.merge(
    geo_base,
    on="id_municip",
    how="left"
)

casos_mapa = casos_mapa.dropna(subset=["lat_locali", "long_local"])

if casos_mapa.empty:
    st.warning("Sem coordenadas disponíveis para esse ano.")
else:
    sizeref = 2.0 * casos_mapa["casos"].max() / (40**2)

    fig_mapa = px.scatter_mapbox(
        casos_mapa,
        lat="lat_locali",
        lon="long_local",
        size="casos",
        color="casos",
        color_continuous_scale="YlOrRd",
        hover_name="nome_municipio",
        hover_data={
            "uf": True,
            "casos": True,
            "lat_locali": False,
            "long_local": False
        },
        zoom=4,
        size_max=40,
        title="Intensidade de Casos por Município"
    )

    fig_mapa.update_traces(
        marker=dict(
            opacity=0.75,
            sizemode="area",
            sizeref=sizeref
        )
    )

    fig_mapa.update_layout(
        mapbox_style="open-street-map",
        margin=dict(r=0, t=50, l=0, b=0),
        coloraxis_colorbar=dict(title="Número de Casos")
    )

    st.plotly_chart(fig_mapa, use_container_width=True)

# =========================================================
# RELAÇÃO COM VARIÁVEIS SOCIOAMBIENTAIS
# =========================================================
st.subheader("📈 Relação Casos x Variáveis Ambientais e Socioeconômicas")

casos_variaveis = (
    df_filtro
    .groupby("id_municip")["casos"]
    .sum()
    .reset_index()
)

base_estrutural = (
    df[["id_municip", "uf", "precipitacao_mensal", "saneamento_basico", "idh", "renda_media"]]
    .drop_duplicates(subset=["id_municip"])
)

casos_variaveis = casos_variaveis.merge(
    base_estrutural,
    on="id_municip",
    how="left"
)

variavel = st.selectbox(
    "Selecione a variável para analisar",
    ["precipitacao_mensal", "saneamento_basico", "idh", "renda_media"]
)

casos_variaveis = casos_variaveis.dropna(subset=[variavel])

if casos_variaveis.empty:
    st.warning("Sem dados disponíveis para essa variável.")
else:
    fig_disp = px.scatter(
        casos_variaveis,
        x=variavel,
        y="casos",
        color="uf",
        size="casos",
        trendline="ols",
        title=f"Casos x {variavel}"
    )

    st.plotly_chart(fig_disp, use_container_width=True)
