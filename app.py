"""TestingStudio Web — auditor de testes de software (Sprint 1: caixa-preta).

Este arquivo só monta a navegação entre as páginas e a barra lateral da chave do Gemini;
cada página fica em paginas/.
Executar:  python -m streamlit run app.py
"""

import os
from pathlib import Path

import streamlit as st

from ia import chave as chaves
from ia import cliente

PASTA = Path(__file__).parent

st.set_page_config(page_title="TestingStudio Web", page_icon="🧪", layout="wide")

pagina = st.navigation([
    st.Page("paginas/1_ler.py", title="Ler", icon="📄", default=True),
    st.Page("paginas/2_analisar.py", title="Analisar", icon="📐"),
    st.Page("paginas/3_revisar.py", title="Revisar", icon="🤖"),
])


@st.cache_data(ttl=600, show_spinner="Testando a chave do Gemini...")
def testar_chave(chave):
    # guardado por 10 minutos: um Google lento não trava a tela a cada clique
    return cliente.testar_chave(chave)


def chave_do_secrets():
    try:
        return st.secrets.get(chaves.NOME)
    except Exception:  # sem secrets.toml (ou inválido: o aviso aparece na barra lateral)
        return None


with st.sidebar:
    st.title("🧪 TestingStudio Web")
    st.caption("Teste de Software I · Sprint 1 · Caixa-preta")
    st.markdown("1. **Ler** o `.txt` (código ou requisito)\n"
                "2. **Analisar**: ε, PCE, AVL e oráculo\n"
                "3. **Revisar** os casos com a IA")

    st.subheader("🔑 Gemini")
    for arquivo in (PASTA / ".streamlit" / "secrets.toml", Path.home() / ".streamlit" / "secrets.toml"):
        aviso = chaves.validar_secrets(arquivo)
        if aviso:
            st.warning(aviso)

    valor, origem = chaves.obter_chave(chave_do_secrets(), os.environ)
    if not valor:
        digitada = st.text_input("API Key (não fica salva):", type="password", key="chave_digitada",
                                 help="Melhor: coloque a chave em .streamlit/secrets.toml, entre aspas.")
        if not chaves.eh_modelo(digitada):
            valor, origem = digitada.strip(), "digitada nesta sessão"

    ia = {"ligada": False, "chave": "", "modelos": []}
    if not valor:
        st.info("Sem chave: a IA fica desligada. O motor (ε, PCE, AVL e oráculo) funciona sem ela.")
    elif not cliente.biblioteca_instalada():
        st.error(cliente.MENSAGENS["biblioteca"])
    else:
        teste = testar_chave(valor)
        st.caption(f"Chave vinda de: **{origem}**")
        if teste["situacao"] == "conectado":
            st.success(teste["mensagem"], icon="✅")
        elif teste["situacao"] == "recusada":
            st.error(teste["mensagem"], icon="⛔")
        else:
            st.warning(teste["mensagem"], icon="⏳")
        ia = {"ligada": teste["situacao"] != "recusada", "chave": valor,
              "modelos": cliente.escolher_modelos(teste["modelos"])}
    st.session_state["ia"] = ia

pagina.run()
