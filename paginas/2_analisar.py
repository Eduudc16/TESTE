"""Página 2 — Analisar: ε e domínio, PCE, AVL e oráculo, tudo calculado pelo motor em Python."""

import pandas as pd
import streamlit as st

from motor import particao
from motor.tipos import mostrar
from paginas import graficos

estado = st.session_state
unidade = estado.get("unidade")

st.header("📐 2 · Analisar")
if unidade is None:
    st.info("Primeiro leia uma unidade na página Ler.")
    st.page_link("paginas/1_ler.py", label="Ir para Ler", icon="📄")
    st.stop()

st.caption(f"Unidade: **{unidade.nome}** · lida por {unidade.origem}")

classes = particao.classes_de_equivalencia(unidade)
casos = particao.casos_pce(unidade, classes)
for numero, caso in enumerate(casos, start=1):
    caso.id = f"CT{numero:02d}"
    caso.classes = particao.classificar(unidade, classes, caso.valores)


def representante(classe):
    if not classe.alcancavel:
        return "não alcançável com uma entrada no extremo"
    if isinstance(classe.representante, dict):
        return ", ".join(f"{nome}={mostrar(valor)}" for nome, valor in classe.representante.items())
    return mostrar(classe.representante)


aba_epsilon, aba_pce = st.tabs(["ε e domínio", "PCE"])

with aba_epsilon:
    st.markdown("**ε é a menor variação que o tipo representa.** Ele é calculado pelo Python a partir do tipo, "
                "nunca pela IA.")
    st.dataframe(pd.DataFrame(unidade.linhas_dominio()), hide_index=True)

with aba_pce:
    st.markdown("**Particionamento em Classes de Equivalência:** para cada entrada, a classe válida, abaixo, "
                "acima e NULL; para a saída, dentro do tipo ou estouro. Cada classe tem um representante.")
    st.dataframe(pd.DataFrame([{
        "Classe": classe.id, "Variável": classe.alvo, "Descrição": classe.descricao,
        "Válida": "✅" if classe.valida else "❌", "Representante": representante(classe)} for classe in classes]),
        hide_index=True)
    st.markdown("**Cobertura:** quantos casos de teste exercitam cada classe.")
    st.altair_chart(graficos.cobertura(particao.cobertura(classes, casos)))
    st.markdown("**Casos da PCE:** valores típicos para as classes válidas e um caso por classe inválida.")
    st.dataframe(pd.DataFrame([{"Caso": caso.id, "Descrição": caso.descricao,
                                **{nome: mostrar(valor) for nome, valor in caso.valores.items()},
                                "Classes": ", ".join(caso.classes)} for caso in casos]), hide_index=True)
