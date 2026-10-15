"""Página 1 — Ler o .txt: código Informix-4GL ou requisito em português."""

from pathlib import Path

import streamlit as st

from leitores.arquivo import decodificar, ler_arquivo

EXEMPLOS = Path(__file__).parent.parent / "exemplos"
estado = st.session_state
estado.setdefault("fonte", "")
estado.setdefault("origem", "")


def usar_exemplo(nome):
    estado["fonte"], codificacao = ler_arquivo(EXEMPLOS / nome)
    estado["origem"] = f"exemplo {nome} ({codificacao})"


def guardar_edicao():
    # a caixa de texto é apagada ao trocar de página; o texto fica guardado em "fonte"
    estado["fonte"] = estado["caixa_fonte"]


st.header("📄 1 · Ler o .txt")
st.caption("Envie o código-fonte (Informix-4GL) ou um requisito escrito em português.")

coluna_arquivo, coluna_exemplos = st.columns([2, 1])
with coluna_arquivo:
    arquivo = st.file_uploader("Arquivo .txt", type=["txt", "4gl"])
    # só lê quando o arquivo é novo: senão cada clique jogaria fora o que você editou
    if arquivo is not None and estado.get("arquivo_id") != arquivo.file_id:
        estado["fonte"], codificacao = decodificar(arquivo.getvalue())
        estado["origem"] = f"{arquivo.name} ({codificacao})"
        estado["arquivo_id"] = arquivo.file_id
with coluna_exemplos:
    st.markdown("**Exemplos**")
    st.button("CAD0001 — código do professor", on_click=usar_exemplo, args=("cad0001_item_calculo.txt",))
    st.button("CAD0001 — versão do manual", on_click=usar_exemplo, args=("cad0001_manual.txt",))
    st.button("Requisito em português", on_click=usar_exemplo, args=("requisito_cad0001.txt",))

estado["caixa_fonte"] = estado["fonte"]
st.text_area("Conteúdo (você pode editar)", key="caixa_fonte", on_change=guardar_edicao, height=320)
if estado["origem"]:
    st.caption(f"Lido de: {estado['origem']}")
