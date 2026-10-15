"""Etapa 9 — Exporta os casos: CSV para o Excel e um arquivo de testes pytest."""

import csv
import io
import keyword
import re
from decimal import Decimal

from motor.tipos import mostrar


def _para_excel(valor):
    """Números com vírgula decimal, como o Excel em português espera."""
    texto = mostrar(valor)
    return texto.replace(".", ",") if isinstance(valor, (Decimal, float)) else texto


def csv_bytes(casos):
    """CSV separado por ';' e em utf-8-sig: abre certinho no Excel, com acentos."""
    saida = io.StringIO()
    escritor = csv.writer(saida, delimiter=";", lineterminator="\r\n")
    nomes = list(casos[0].valores) if casos else []
    escritor.writerow(["Caso", "Técnica", "Descrição", *nomes, "Situação", "Valor esperado", "Esperado",
                       "Classes"])
    for caso in casos:
        resultado = caso.resultado
        escritor.writerow([caso.id, caso.tecnica, caso.descricao,
                           *(_para_excel(caso.valores[nome]) for nome in nomes), resultado.situacao,
                           "" if resultado.valor is None else _para_excel(resultado.valor), resultado.texto(),
                           " ".join(caso.classes)])
    return saida.getvalue().encode("utf-8-sig")


def identificador(nome):
    """Nome válido em Python para a função e os parâmetros do teste gerado."""
    texto = re.sub(r"\W", "_", nome.strip()) or "unidade"
    return f"f_{texto}" if keyword.iskeyword(texto) or texto[0].isdigit() else texto


def _em_python(valor):
    if valor is None:
        return "None"
    if isinstance(valor, Decimal):
        return f'Decimal("{mostrar(valor)}")'
    if isinstance(valor, float):
        return f'float("{valor!r}")'
    if isinstance(valor, str) and len(valor) > 12 and set(valor) == {"x"}:
        return f'"x" * {len(valor)}'
    return repr(valor)


def pytest_py(unidade, casos, regra):
    """Um test_<unidade>.py com @pytest.mark.parametrize de todos os casos."""
    funcao = identificador(unidade.nome)
    parametros = ", ".join(identificador(variavel.nome) for variavel in unidade.entradas)
    linhas = []
    for caso in casos:
        resultado = caso.resultado
        esperado = {"rejeitar": "REJEITAR", "estouro": "ESTOURO"}.get(resultado.situacao) \
            or ("ACEITA" if resultado.valor is None else _em_python(resultado.valor))
        entradas = ", ".join(_em_python(caso.valores[variavel.nome]) for variavel in unidade.entradas)
        comentario = f"  # ❓ {resultado.motivo}" if resultado.situacao == "pergunta" else ""
        linhas.append(f'    pytest.param({entradas}, {esperado}, id="{caso.id}"),{comentario}')
    corpo = "\n".join(linhas)
    return f'''"""Casos de teste de caixa-preta gerados pelo TestingStudio Web para {unidade.nome}.

Arredondamento adotado: {regra}.
Para rodar: implemente {funcao}() abaixo (a tradução da unidade para Python) e execute
    python -m pytest test_{funcao}.py
"""

from decimal import Decimal

import pytest

REJEITAR = "rejeitar"  # a unidade deve recusar a entrada
ESTOURO = "estouro"    # o resultado não cabe no tipo da saída
ACEITA = "aceita"      # entrada aceita, sem valor calculado


def {funcao}({parametros}):
    raise NotImplementedError("traduza {unidade.nome} para Python e devolva o valor, REJEITAR ou ESTOURO")


CASOS = [
{corpo}
]


@pytest.mark.parametrize("{parametros}, esperado", CASOS)
def test_{funcao}({parametros}, esperado):
    assert {funcao}({parametros}) == esperado
'''
