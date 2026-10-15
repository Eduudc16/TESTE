"""Página 1 — Ler o .txt: código Informix-4GL ou requisito em português."""

import hashlib
from pathlib import Path

import pandas as pd
import streamlit as st

from leitores import informix
from leitores.arquivo import decodificar, ler_arquivo
from motor.unidade import COLUNAS, unidade_de_tabela

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


def editar(base):
    """Mostra a unidade lida para conferência e edição e guarda a versão final para as outras páginas."""
    assinatura = hashlib.sha1(f"{base.origem}|{base.nome}|{estado['fonte']}".encode()).hexdigest()[:10]
    guardada = estado.get("unidade_editada")
    inicial = guardada[1] if guardada and guardada[0] == assinatura else base
    chave_tabela = f"entradas_{assinatura}"
    if chave_tabela not in estado:  # primeira vez, ou de volta de outra página: parte da versão guardada
        estado[f"inicial_{assinatura}"] = pd.DataFrame(inicial.linhas_entradas(), columns=COLUNAS)

    st.markdown("**Entradas** — confira o que foi lido; dá para corrigir direto na tabela.")
    tabela = st.data_editor(
        estado[f"inicial_{assinatura}"], key=chave_tabela, num_rows="dynamic", hide_index=True,
        column_config={
            "Tipo": st.column_config.TextColumn(help="Ex.: DECIMAL(12,2), INTEGER, SMALLINT, CHAR(40), FLOAT"),
            "Mínimo (regra)": st.column_config.TextColumn(help="Regra de negócio: menor valor aceito (vazio = o do tipo)"),
            "Máximo (regra)": st.column_config.TextColumn(help="Regra de negócio: maior valor aceito (vazio = o do tipo)"),
            "NULL vira 0": st.column_config.CheckboxColumn(help="O código troca NULL por 0?"),
        })
    coluna_saida, coluna_tipo, coluna_formula = st.columns([1, 1, 2])
    saida_nome = coluna_saida.text_input("Saída", inicial.saida.nome if inicial.saida else "",
                                         key=f"saida_{assinatura}")
    saida_tipo = coluna_tipo.text_input("Tipo da saída", inicial.saida.tipo if inicial.saida else "",
                                        key=f"tipo_saida_{assinatura}")
    formula = coluna_formula.text_input("Regra (fórmula com + − × ÷)", inicial.formula or "",
                                        key=f"formula_{assinatura}")
    try:
        unidade = unidade_de_tabela(base.nome, tabela.to_dict("records"), saida_nome, saida_tipo, formula,
                                    base.origem, base.observacoes)
        problemas = unidade.problemas()
    except ValueError as erro:
        unidade, problemas = None, [str(erro)]

    with st.expander("O que o leitor encontrou"):
        st.markdown("\n".join(f"- {observacao}" for observacao in base.observacoes))
    if problemas:
        for problema in problemas:
            st.error(problema)
        estado.pop("unidade", None)
        return None
    estado["unidade"] = unidade
    estado["unidade_editada"] = (assinatura, unidade)
    st.success(f"Unidade **{unidade.nome}** pronta: {len(unidade.entradas)} entradas"
               + (f", saída {unidade.saida.nome} {unidade.saida.tipo}." if unidade.saida else "."))
    st.page_link("paginas/2_analisar.py", label="Analisar: ε, PCE, AVL e oráculo", icon="📐")
    return unidade


st.subheader("Unidade em teste")
if not estado["fonte"].strip():
    st.info("Envie um arquivo .txt ou escolha um exemplo.")
    st.stop()

funcoes = informix.listar_funcoes(estado["fonte"])
if not funcoes:
    st.warning("Não encontrei FUNCTION ... END FUNCTION neste texto.")
    st.stop()
padrao = next((i for i, nome in enumerate(funcoes) if "calcul" in nome.lower()), 0)
funcao = st.selectbox("Função analisada", funcoes, index=padrao)
try:
    editar(informix.ler(estado["fonte"], funcao))
except ValueError as erro:
    st.error(str(erro))
