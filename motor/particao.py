"""Etapa 5 — PCE: Particionamento em Classes de Equivalência.

Cada entrada tem 1 classe válida (dentro da faixa), 2 inválidas (abaixo e acima) e a classe
NULL (válida se o código troca NULL por 0). A saída também tem domínio: um resultado que
estoura o tipo é uma classe inválida.
"""

import math
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from motor import exato
from motor.tipos import mostrar
from motor.unidade import Caso


@dataclass
class Classe:
    id: str
    alvo: str              # nome da entrada (ou da saída)
    tipo: str              # dentro, abaixo, acima, nulo, saida_dentro, saida_acima, saida_abaixo
    descricao: str
    valida: bool
    representante: object = None   # valor da entrada, ou {entrada: valor} nas classes da saída
    alcancavel: bool = True


@exato
def tipicos(unidade):
    """Um valor típico por entrada: longe das fronteiras e diferente entre as variáveis.

    Valores iguais mascaram defeitos: com p_val2 = p_val3, trocar um pelo outro no código
    não mudaria nenhum resultado.
    """
    valores = {}
    for posicao, variavel in enumerate(unidade.entradas):
        dominio = variavel.dominio
        minimo, maximo = variavel.faixa
        if dominio.familia == "texto":
            valores[variavel.nome] = "x" * max(minimo, min(maximo, maximo // 2 + posicao))
            continue
        if dominio.familia == "float":
            candidato = 50.0 + posicao
        else:
            candidato = Decimal(50 + posicao).quantize(dominio.epsilon)
        if not minimo <= candidato <= maximo:  # uma regra de negócio tirou o 50 da faixa: usa o meio
            candidato = minimo + (maximo - minimo) / 2 + posicao * dominio.epsilon_em(minimo)
            if dominio.familia == "exato":
                candidato = candidato.quantize(dominio.epsilon, ROUND_HALF_UP)
        valores[variavel.nome] = candidato
    return valores


@exato
def fora_da_faixa(variavel):
    """(abaixo, acima): bem fora da faixa, a meia largura além de cada limite.
    A fronteira exata é trabalho da AVL."""
    dominio = variavel.dominio
    minimo, maximo = variavel.faixa
    if dominio.familia == "texto":
        return "x" * (minimo - 1), "x" * (maximo + max(1, (maximo - minimo) // 2))
    if dominio.familia == "float":
        return -math.inf, math.inf
    meia_largura = ((maximo - minimo) / 2).quantize(dominio.epsilon, ROUND_HALF_UP)
    return minimo - meia_largura, maximo + meia_largura


def _faixa_em_texto(variavel):
    minimo, maximo = variavel.faixa
    if variavel.dominio.familia == "texto":
        return f"tamanho de {minimo} a {maximo}"
    return f"{mostrar(minimo)} ≤ {variavel.nome} ≤ {mostrar(maximo)}"


@exato
def _procurar_saida(unidade, base, condicao):
    """Entradas que levam a saída para fora da faixa: uma entrada no extremo, as outras típicas."""
    for variavel in unidade.entradas:
        if variavel.dominio.familia == "texto":
            continue
        for extremo in reversed(variavel.faixa):
            valores = dict(base, **{variavel.nome: extremo})
            if condicao(unidade.calcular(valores)):
                return valores
    return None


def classes_de_equivalencia(unidade):
    """Todas as classes, numeradas CE1, CE2, ... com um representante cada."""
    classes = []

    def nova(alvo, tipo, descricao, valida, representante, alcancavel=True):
        classes.append(Classe(f"CE{len(classes) + 1}", alvo, tipo, descricao, valida, representante, alcancavel))

    tipico = tipicos(unidade)
    for variavel in unidade.entradas:
        minimo, maximo = variavel.faixa
        abaixo, acima = fora_da_faixa(variavel)
        tamanho = " (tamanho)" if variavel.dominio.familia == "texto" else ""
        nova(variavel.nome, "dentro", _faixa_em_texto(variavel), True, tipico[variavel.nome])
        nova(variavel.nome, "abaixo", f"{variavel.nome}{tamanho} < {mostrar(minimo)}", False, abaixo)
        nova(variavel.nome, "acima", f"{variavel.nome}{tamanho} > {mostrar(maximo)}", False, acima)
        nova(variavel.nome, "nulo", "NULL (vira 0)" if variavel.trata_nulo else "NULL (não tratado no código)",
             variavel.trata_nulo, None)

    if unidade.tem_regra_de_saida:
        saida = unidade.saida
        minimo, maximo = saida.faixa
        nova(saida.nome, "saida_dentro", _faixa_em_texto(saida), True, dict(tipico))
        for tipo, sinal, condicao in (("saida_acima", f"> {mostrar(maximo)}", lambda y: y > maximo),
                                      ("saida_abaixo", f"< {mostrar(minimo)}", lambda y: y < minimo)):
            representante = _procurar_saida(unidade, tipico, condicao)
            nova(saida.nome, tipo, f"resultado {sinal} (estouro do tipo)", False, representante,
                 alcancavel=representante is not None)
    return classes


def casos_pce(unidade, classes):
    """Casos válidos cobrem o máximo de classes válidas; cada caso inválido cobre UMA classe
    inválida (duas juntas podem mascarar o defeito)."""
    tipico = tipicos(unidade)
    casos = [Caso("", "PCE", "Valores típicos (cobre as classes válidas)", dict(tipico))]
    nulas = [classe.alvo for classe in classes if classe.tipo == "nulo" and classe.valida]
    if nulas:
        casos.append(Caso("", "PCE", "NULL em todas as entradas que aceitam NULL",
                          dict(tipico, **{nome: None for nome in nulas})))
    for classe in classes:
        if classe.valida or not classe.alcancavel:
            continue
        if classe.tipo.startswith("saida"):
            valores = dict(classe.representante)
        else:
            valores = dict(tipico, **{classe.alvo: classe.representante})
        casos.append(Caso("", "PCE", f"{classe.id}: {classe.descricao}", valores))
    return casos


@exato
def classificar(unidade, classes, valores):
    """IDs das classes que um caso exercita: uma por entrada e, se as entradas valem, a da saída."""
    ids, entradas_validas = [], True
    for variavel in unidade.entradas:
        valor = valores.get(variavel.nome)
        if valor is None:
            tipo = "nulo"
        else:
            medida, (minimo, maximo) = variavel.medida(valor), variavel.faixa
            tipo = "abaixo" if medida < minimo else "acima" if medida > maximo else "dentro"
        entradas_validas &= variavel.aceita(valor)
        ids += [classe.id for classe in classes if classe.alvo == variavel.nome and classe.tipo == tipo]
    if entradas_validas and unidade.tem_regra_de_saida:
        resultado = unidade.calcular(valores)
        minimo, maximo = unidade.saida.faixa
        tipo = "saida_abaixo" if resultado < minimo else "saida_acima" if resultado > maximo else "saida_dentro"
        ids += [classe.id for classe in classes if classe.tipo == tipo]
    return ids


def cobertura(classes, casos):
    """Quantos casos cobrem cada classe (para o gráfico de barras)."""
    return [{"Classe": classe.id, "Descrição": f"{classe.alvo}: {classe.descricao}", "Válida": classe.valida,
             "Casos": sum(classe.id in caso.classes for caso in casos)} for classe in classes]
