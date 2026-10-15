"""Gráficos da página Analisar (Altair, que já vem com o Streamlit)."""

import altair as alt
import pandas as pd

# Cores de status (válido / inválido); o rótulo e a forma do marcador também dizem a situação.
CORES = alt.Scale(domain=["Válida", "Inválida"], range=["#0ca30c", "#d03b3b"])
FORMAS = alt.Scale(domain=["Válida", "Inválida"], range=["circle", "diamond"])
TINTA = "#898781"  # cinza neutro para textos e linhas: legível no tema claro e no escuro


def cobertura(linhas):
    """Barras: quantos casos de teste cobrem cada classe de equivalência."""
    dados = pd.DataFrame(linhas)
    dados["Situação"] = dados["Válida"].map({True: "Válida", False: "Inválida"})
    base = alt.Chart(dados).encode(
        x=alt.X("Classe:N", sort=list(dados["Classe"]), title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("Casos:Q", title="Casos que cobrem a classe", axis=alt.Axis(tickMinStep=1)),
        tooltip=["Classe", "Descrição", "Situação", "Casos"])
    barras = base.mark_bar(size=24, cornerRadiusEnd=4).encode(
        color=alt.Color("Situação:N", scale=CORES, legend=alt.Legend(title=None, orient="top")))
    rotulos = base.mark_text(dy=-8, color=TINTA).encode(text="Casos:Q")
    return (barras + rotulos).properties(height=260)
