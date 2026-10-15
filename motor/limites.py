"""Etapa 6 — AVL: Análise do Valor Limite.

Defeitos moram nas fronteiras. Em cada fronteira X testam-se X − ε, X e X + ε, variando
uma entrada por vez (as outras ficam no valor típico) — nas entradas e na saída.

AVL na saída: se a regra é linear numa entrada (saída = a·x + b), calcula-se b = f(0) e
a = f(1) − f(0), confere-se f(2) − f(1) = a e resolve-se x = (Y − b) / a para Y = mínimo e
máximo da saída. Se x não for múltiplo de ε, testam-se os dois múltiplos vizinhos.
"""

from dataclasses import dataclass, field
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal

from motor import exato
from motor.formula import Formula
from motor.particao import tipicos
from motor.tipos import mostrar
from motor.unidade import Caso


@dataclass
class Ponto:
    rotulo: str             # "X − ε", "X", "X + ε" (ou "abaixo de x" e "acima de x" se x não é múltiplo de ε)
    valor: object           # valor da entrada que varia
    valido: bool            # a entrada é aceita e (na saída) o resultado cabe no tipo?
    posicao: float          # distância até a fronteira, em ε (para a régua)
    resultado: object = None


@dataclass
class Fronteira:
    id: str
    alvo: str               # entrada (ou saída) que tem a fronteira
    lado: str               # "mínimo" ou "máximo"
    x: object               # valor da fronteira
    variavel: str           # entrada que varia nos casos
    pontos: list = field(default_factory=list)
    nota: str = ""


def _fronteiras_das_entradas(unidade):
    fronteiras = []
    for variavel in unidade.entradas:
        dominio = variavel.dominio
        for lado, x in zip(("mínimo", "máximo"), variavel.faixa):
            pontos = []
            for posicao, (rotulo, medida) in enumerate(zip(("X − ε", "X", "X + ε"), dominio.vizinhos(x)), start=-1):
                if dominio.familia == "texto":
                    if medida < 0:
                        continue
                    valor = "x" * medida
                else:
                    valor = medida
                pontos.append(Ponto(rotulo, valor, variavel.aceita(valor), float(posicao)))
            medida = " (tamanho)" if dominio.familia == "texto" else ""
            fronteiras.append(Fronteira("", variavel.nome, lado, x, variavel.nome, pontos,
                                        f"ε = {'1 caractere' if medida else mostrar(dominio.epsilon_em(x))}"))
    return fronteiras


@exato
def resolver_saida(unidade, y):
    """Entrada e valor x que levam a saída exatamente a Y (as outras entradas ficam típicas).

    Devolve (variável, x, x_é_múltiplo_de_ε) ou None. Prefere uma solução exata.
    """
    base = tipicos(unidade)
    nomes = Formula(unidade.formula).nomes
    candidatos = []
    for variavel in unidade.entradas:
        if variavel.nome not in nomes or variavel.dominio.familia != "exato":
            continue

        def f(valor, nome=variavel.nome):
            return unidade.calcular(dict(base, **{nome: Decimal(valor)}))

        b = f(0)
        a = f(1) - b
        if a == 0 or f(2) - f(1) != a:  # não é linear nesta entrada
            continue
        x = (y - b) / a
        minimo, maximo = variavel.faixa
        if minimo <= x <= maximo:
            eps = variavel.dominio.epsilon
            candidatos.append((variavel, x, x == x.quantize(eps)))
    return next((c for c in candidatos if c[2]), candidatos[0] if candidatos else None)


@exato
def _fronteiras_da_saida(unidade):
    saida = unidade.saida
    minimo, maximo = saida.faixa
    base = tipicos(unidade)
    fronteiras = []
    for lado, y in (("mínimo", minimo), ("máximo", maximo)):
        solucao = resolver_saida(unidade, y)
        if solucao is None:
            fronteiras.append(Fronteira("", saida.nome, lado, y, "—", [],
                                        "nenhuma entrada sozinha leva a saída até aqui"))
            continue
        variavel, x, multiplo = solucao
        eps = variavel.dominio.epsilon
        if multiplo:
            valores = (("x − ε", x - eps), ("x", x), ("x + ε", x + eps))
        else:
            valores = (("abaixo de x", x.quantize(eps, ROUND_FLOOR)), ("acima de x", x.quantize(eps, ROUND_CEILING)))
        pontos = []
        for rotulo, valor in valores:
            resultado = unidade.calcular(dict(base, **{variavel.nome: valor}))
            pontos.append(Ponto(rotulo, valor, variavel.aceita(valor) and minimo <= resultado <= maximo,
                                float((valor - x) / eps), resultado))
        if multiplo:
            nota = f"{variavel.nome} = (Y − b) / a = {mostrar(x)}"
        else:
            nota = (f"{variavel.nome} = (Y − b) / a ≈ {mostrar(x.quantize(eps.scaleb(-4)))}, que não é múltiplo "
                    "de ε: testados os dois vizinhos")
        fronteiras.append(Fronteira("", saida.nome, lado, y, variavel.nome, pontos, nota))
    return fronteiras


def fronteiras(unidade):
    """Todas as fronteiras (entradas e saída), numeradas F1, F2, ..."""
    todas = _fronteiras_das_entradas(unidade)
    if unidade.tem_regra_de_saida:
        todas += _fronteiras_da_saida(unidade)
    for numero, fronteira in enumerate(todas, start=1):
        fronteira.id = f"F{numero}"
    return todas


def casos_avl(unidade, lista_de_fronteiras):
    """Um caso por ponto: só a entrada da fronteira muda; as outras ficam típicas."""
    base = tipicos(unidade)
    return [Caso("", "AVL", f"{fronteira.id} ({fronteira.alvo} {fronteira.lado}): {ponto.rotulo}",
                 dict(base, **{fronteira.variavel: ponto.valor}))
            for fronteira in lista_de_fronteiras for ponto in fronteira.pontos]


def linha(fronteira):
    """A fronteira no formato do gabarito: 9999999999.98 ✅ · 9999999999.99 ✅ · 10000000000.00 ❌"""
    return {"Fronteira": fronteira.id, "Alvo": fronteira.alvo, "Lado": fronteira.lado,
            "X": mostrar(fronteira.x), "Varia": fronteira.variavel,
            "Pontos": " · ".join(f"{mostrar(p.valor)} {'✅' if p.valido else '❌'}" for p in fronteira.pontos),
            "Nota": fronteira.nota}
