"""Página 2 — Analisar: ε e domínio, PCE, AVL e oráculo, tudo calculado pelo motor em Python."""

import pandas as pd
import streamlit as st

from motor import exportar, limites, oraculo, particao, suite
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
regras = list(oraculo.REGRAS)
regra = st.radio("Arredondamento da saída (a especificação não define — escolha e registre)", regras,
                 index=regras.index(estado.get("regra", oraculo.REGRA_PADRAO)), horizontal=True)
estado["regra"] = regra

resultado = suite.montar(unidade, regra)
estado["suite"] = resultado
casos = resultado.casos

colunas = st.columns(3)
colunas[0].metric("Classes de equivalência", len(resultado.classes))
colunas[1].metric("Fronteiras", len(resultado.fronteiras))
colunas[2].metric("Casos de teste", len(casos))
NOMES = {"ok": ("aceito", "aceitos"), "rejeitar": ("rejeitado", "rejeitados"),
         "estouro": ("estouro", "estouros"), "pergunta": ("pergunta", "perguntas")}
contagem = {situacao: sum(c.resultado.situacao == situacao for c in casos) for situacao in oraculo.SIMBOLOS}
st.markdown("**Esperados:** " + " · ".join(f"{oraculo.SIMBOLOS[s]} {n} {NOMES[s][n != 1]}"
                                           for s, n in contagem.items() if n))


def altura(linhas):
    """Altura que mostra a tabela inteira, sem barra de rolagem interna (35 px por linha)."""
    return 38 + 35 * linhas


def representante(classe):
    if not classe.alcancavel:
        return "não alcançável com uma entrada no extremo"
    if isinstance(classe.representante, dict):
        return ", ".join(f"{nome}={mostrar(valor)}" for nome, valor in classe.representante.items())
    return mostrar(classe.representante)


def tabela_de_casos(tecnica=None):
    linhas = suite.linhas_de_casos([caso for caso in casos if tecnica in (None, caso.tecnica)])
    st.dataframe(pd.DataFrame(linhas), hide_index=True, height=altura(len(linhas)))


aba_epsilon, aba_pce, aba_avl, aba_casos = st.tabs(["ε e domínio", "PCE", "AVL", "Casos de teste"])

with aba_epsilon:
    st.markdown("**ε é a menor variação que o tipo representa.** Ele é calculado pelo Python a partir do tipo, "
                "nunca pela IA.")
    st.dataframe(pd.DataFrame(unidade.linhas_dominio()), hide_index=True)

with aba_pce:
    st.markdown("**Particionamento em Classes de Equivalência:** para cada entrada, a classe válida, abaixo, "
                "acima e NULL; para a saída, dentro do tipo ou estouro. Cada classe tem um representante.")
    st.dataframe(pd.DataFrame([{
        "Classe": classe.id, "Variável": classe.alvo, "Descrição": classe.descricao,
        "Válida": "✅" if classe.valida else "❌", "Representante": representante(classe)}
        for classe in resultado.classes]), hide_index=True, height=altura(len(resultado.classes)))
    st.markdown("**Cobertura:** quantos casos de teste (PCE e AVL) exercitam cada classe.")
    st.altair_chart(graficos.cobertura(particao.cobertura(resultado.classes, casos)))
    st.markdown("**Casos da PCE:** valores típicos para as classes válidas e um caso por classe inválida.")
    tabela_de_casos("PCE")

with aba_avl:
    st.markdown("**Análise do Valor Limite:** em cada fronteira X, os pontos X − ε, X e X + ε, variando uma "
                "entrada por vez. Na saída, o Python resolve qual valor de entrada leva o resultado à fronteira.")
    st.dataframe(pd.DataFrame([limites.linha(fronteira) for fronteira in resultado.fronteiras]), hide_index=True,
                 height=altura(len(resultado.fronteiras)))
    por_id = {fronteira.id: fronteira for fronteira in resultado.fronteiras if fronteira.pontos}
    escolhida = st.selectbox("Régua da fronteira", list(por_id),
                             format_func=lambda id_: f"{id_} · {por_id[id_].alvo} {por_id[id_].lado} "
                                                     f"(X = {mostrar(por_id[id_].x)})")
    if escolhida:
        st.altair_chart(graficos.regua(por_id[escolhida]))
        st.caption(por_id[escolhida].nota)
    st.markdown("**Casos da AVL**")
    tabela_de_casos("AVL")

with aba_casos:
    st.markdown("**Oráculo:** entrada inválida → ❌ rejeitar; válida → a regra calculada com `Decimal`, "
                "arredondada para a escala da saída; ⚠️ quando o resultado não cabe no tipo; ❓ quando a "
                "especificação não responde.")
    tabela_de_casos()
    coluna_csv, coluna_pytest = st.columns(2)
    coluna_csv.download_button("⬇️ Baixar CSV (Excel)", exportar.csv_bytes(casos), f"casos_{unidade.nome}.csv",
                               "text/csv", help="Separado por ponto e vírgula, em UTF-8 com BOM: abre certinho no Excel.")
    funcao = exportar.identificador(unidade.nome)
    coluna_pytest.download_button("🐍 Baixar testes pytest", exportar.pytest_py(unidade, casos, regra),
                                  f"test_{funcao}.py", "text/x-python",
                                  help="Um @pytest.mark.parametrize com todos os casos e o resultado esperado.")

if resultado.achados:
    st.subheader("❓ Perguntas para o analista")
    st.markdown("\n".join(f"- {achado}" for achado in resultado.achados))
