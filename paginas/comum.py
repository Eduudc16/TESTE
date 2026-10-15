"""Peças de tela usadas por mais de uma página."""

import hashlib

import streamlit as st

from ia import cliente, prompts


def ia_ligada():
    return st.session_state.get("ia", {}).get("ligada", False)


def chamar_ia(prompt, json=False):
    """Chama o Gemini e devolve (texto, modelo); em erro, mostra uma mensagem amigável e devolve None."""
    ia = st.session_state.get("ia", {})
    if not ia.get("ligada"):
        st.warning("A IA está desligada: coloque a chave em `.streamlit/secrets.toml` ou na barra lateral.")
        return None
    try:
        with st.spinner("Consultando o Gemini (tempo limite de 45 s por modelo)..."):
            return cliente.perguntar(ia["chave"], prompt, ia["modelos"], sistema=prompts.SISTEMA, json=json)
    except cliente.ErroIA as erro:
        st.error(str(erro))
        return None


def resposta_guardada(nome, prompt, rotulo, ajuda=""):
    """Botão que pede uma resposta em texto à IA e a mantém na tela enquanto o prompt não mudar."""
    assinatura = hashlib.sha1(prompt.encode()).hexdigest()
    if st.button(rotulo, help=ajuda, disabled=not ia_ligada()):
        resposta = chamar_ia(prompt)
        if resposta:
            st.session_state[nome] = (assinatura, *resposta)
    guardada = st.session_state.get(nome)
    if guardada and guardada[0] == assinatura:
        st.markdown(guardada[1])
        st.caption(f"Resposta de {guardada[2]} — revise antes de usar: a IA é parceira, não oráculo.")
