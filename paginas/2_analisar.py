"""Página 2 — Analisar: ε e domínio, PCE, AVL e oráculo, tudo calculado pelo motor em Python."""

import pandas as pd
import streamlit as st

estado = st.session_state
unidade = estado.get("unidade")

st.header("📐 2 · Analisar")
if unidade is None:
    st.info("Primeiro leia uma unidade na página Ler.")
    st.page_link("paginas/1_ler.py", label="Ir para Ler", icon="📄")
    st.stop()

st.caption(f"Unidade: **{unidade.nome}** · lida por {unidade.origem}")
aba_epsilon, = st.tabs(["ε e domínio"])

with aba_epsilon:
    st.markdown("**ε é a menor variação que o tipo representa.** Ele é calculado pelo Python a partir do tipo, "
                "nunca pela IA.")
    st.dataframe(pd.DataFrame(unidade.linhas_dominio()), hide_index=True)
