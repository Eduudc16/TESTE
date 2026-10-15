"""Leitor de requisito em português: a IA devolve um JSON e o Python valida e monta a Unidade.

O regex do Informix vira a alternativa para quando o .txt é código.
"""

import json
import re

from ia import prompts
from motor import tipos
from motor.unidade import Unidade, Variavel, numero, vazio


def _sim(valor):
    return valor is True or str(valor).strip().lower() in ("true", "sim", "1")


def unidade_de_json(texto):
    """JSON da IA → Unidade. Erros de formato viram ValueError com mensagem em português."""
    texto = re.sub(r"^```(?:json)?\s*|\s*```$", "", (texto or "").strip())
    try:
        dados = json.loads(texto)
    except json.JSONDecodeError as erro:
        raise ValueError(f"A IA não devolveu um JSON válido ({erro}). Tente de novo.") from None
    if not isinstance(dados, dict) or not dados.get("entradas"):
        raise ValueError("O JSON da IA não tem a lista de entradas.")

    entradas = []
    for item in dados["entradas"]:
        nome = str(item.get("nome") or "").strip().lower()
        if not nome:
            raise ValueError("Uma das entradas veio sem nome.")
        entradas.append(Variavel(nome, tipos.normalizar(str(item.get("tipo") or "")), _sim(item.get("trata_nulo")),
                                 numero(item.get("minimo")), numero(item.get("maximo"))))
    saida = None
    dados_saida = dados.get("saida")
    if isinstance(dados_saida, dict) and not vazio(dados_saida.get("nome")) and not vazio(dados_saida.get("tipo")):
        saida = Variavel(str(dados_saida["nome"]).strip().lower(), tipos.normalizar(str(dados_saida["tipo"])))
    duvidas = [f"Dúvida apontada pela IA: {duvida}" for duvida in dados.get("duvidas") or []]
    return Unidade(nome=str(dados.get("nome") or "requisito"), entradas=entradas, saida=saida,
                   formula=None if vazio(dados.get("formula")) else str(dados["formula"]).strip(),
                   origem="requisito em português (IA → JSON)",
                   observacoes=["Interpretado pela IA: confira a tabela antes de analisar."] + duvidas)


def interpretar(requisito, perguntar):
    """perguntar(prompt) devolve o texto JSON da IA; a chamada em si fica na página."""
    return unidade_de_json(perguntar(prompts.interpretar(requisito)))
