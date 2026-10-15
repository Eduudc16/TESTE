"""Gráficos da página Analisar (Altair, que já vem com o Streamlit)."""

import altair as alt
import pandas as pd

from motor.tipos import mostrar

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


def regua(fronteira):
    """Régua da fronteira com X − ε, X e X + ε, como no slide do manual."""
    pontos = fronteira.pontos
    dados = pd.DataFrame([{
        "Posição": ponto.posicao, "Ponto": ponto.rotulo, "Valor": mostrar(ponto.valor),
        "Resultado": "" if ponto.resultado is None else mostrar(ponto.resultado),
        "Situação": "Válida" if ponto.valido else "Inválida",
        "Rótulo": f"{ponto.rotulo}\n{mostrar(ponto.valor)}"} for ponto in pontos])

    # a faixa colorida muda de lado entre o último ponto válido e o primeiro inválido (ou o contrário)
    limite = next(((a.posicao + b.posicao) / 2 for a, b in zip(pontos, pontos[1:]) if a.valido != b.valido), None)
    lados = [{"de": -1.8, "ate": 1.8 if limite is None else limite, "Situação": dados["Situação"].iloc[0]}]
    if limite is not None:
        lados.append({"de": limite, "ate": 1.8, "Situação": dados["Situação"].iloc[-1]})

    escala = alt.Scale(domain=[-1.8, 1.8])
    eixo = alt.Axis(values=[-1, 0, 1], labelExpr="datum.value == 0 ? 'X' : datum.value < 0 ? 'X − ε' : 'X + ε'",
                    title=None, grid=False)

    def x(campo):  # todas as camadas usam o mesmo eixo
        return alt.X(campo, scale=escala, axis=eixo)

    faixas = alt.Chart(pd.DataFrame(lados)).mark_rect(opacity=0.12).encode(
        x=x("de:Q"), x2="ate:Q", color=alt.Color("Situação:N", scale=CORES, legend=None))
    fronteira_x = alt.Chart(pd.DataFrame({"Posição": [0.0]})).mark_rule(strokeDash=[4, 4], color=TINTA).encode(
        x=x("Posição:Q"), y=alt.value(82), y2=alt.value(170))
    marcas = alt.Chart(dados).mark_point(size=220, filled=True, opacity=1).encode(
        x=x("Posição:Q"), y=alt.value(100), color=alt.Color("Situação:N", scale=CORES, legend=alt.Legend(
            title=None, orient="top")), shape=alt.Shape("Situação:N", scale=FORMAS, legend=None),
        tooltip=["Ponto", "Valor", "Resultado", "Situação"])
    rotulos = alt.Chart(dados).mark_text(lineBreak="\n", dy=-36, fontSize=12, color=TINTA).encode(
        x=x("Posição:Q"), y=alt.value(100), text="Rótulo:N")
    return alt.layer(faixas, fronteira_x, marcas, rotulos).properties(height=170)
