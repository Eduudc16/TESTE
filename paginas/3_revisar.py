"""Página 3 — Revisar: a IA comenta os casos gerados pelo motor; as perguntas ficam registradas."""

import streamlit as st

from ia import prompts
from motor import oraculo, suite
from paginas import comum

estado = st.session_state
unidade = estado.get("unidade")

st.header("🤖 3 · Revisar")
if unidade is None:
    st.info("Primeiro leia uma unidade na página Ler.")
    st.page_link("paginas/1_ler.py", label="Ir para Ler", icon="📄")
    st.stop()

resultado = suite.montar(unidade, estado.get("regra", oraculo.REGRA_PADRAO))
st.caption(f"Unidade **{unidade.nome}** · {len(resultado.casos)} casos · arredondamento: {resultado.regra}")

st.subheader("❓ Perguntas para o analista")
if resultado.achados:
    st.markdown("\n".join(f"- {achado}" for achado in resultado.achados))
else:
    st.markdown("Nenhuma pergunta em aberto.")

st.subheader("Revisão com a IA")
st.markdown("A IA recebe a unidade e os casos com o resultado esperado e aponta classes ou fronteiras que "
            "parecem faltar, esperados suspeitos e perguntas para o analista. Ela comenta; quem calcula é o Python.")
comum.resposta_guardada("revisao", prompts.revisar(resultado), "🤖 Revisar os casos com a IA")
if not comum.ia_ligada():
    st.caption("A IA está desligada: configure a chave na barra lateral para pedir a revisão.")
