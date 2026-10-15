"""Etapa 7 — Oráculo: o resultado esperado vem da especificação, não de rodar o código.

Entrada inválida → rejeitar. Entrada válida → calcula a regra com Decimal, arredonda para a
escala da saída e confere se o resultado cabe no tipo (senão: estouro). Quando a especificação
não responde — por exemplo, para que lado arredondar um empate —, o caso vira pergunta para o
analista: é um achado legítimo do teste de caixa-preta.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal, InvalidOperation

from motor import exato
from motor.formula import Formula
from motor.tipos import mostrar
from motor.unidade import Caso

REGRAS = {"meio para cima": ROUND_HALF_UP, "meio para o par": ROUND_HALF_EVEN}
# A especificação do CAD0001 não diz como arredondar: esta é a escolha registrada.
REGRA_PADRAO = "meio para cima"
SIMBOLOS = {"ok": "✅", "rejeitar": "❌", "estouro": "⚠️", "pergunta": "❓"}


@dataclass(frozen=True)
class Resultado:
    situacao: str            # "ok", "rejeitar", "estouro" ou "pergunta"
    valor: object = None     # já arredondado para a escala da saída
    exato: object = None     # resultado da conta, sem arredondar
    motivo: str = ""

    @property
    def simbolo(self):
        return SIMBOLOS[self.situacao]

    def texto(self):
        if self.situacao == "rejeitar":
            return f"❌ rejeitar ({self.motivo})"
        if self.situacao == "estouro":
            return f"⚠️ estouro ({mostrar(self.valor)})"
        if self.situacao == "pergunta":
            return f"❓ {self.motivo}"
        return "✅ aceita" if self.valor is None else f"✅ {mostrar(self.valor)}"


@exato
def esperado(unidade, valores, regra=REGRA_PADRAO):
    """Resultado esperado de um caso segundo a especificação."""
    for variavel in unidade.entradas:
        valor = valores.get(variavel.nome)
        if not variavel.aceita(valor):
            motivo = f"{variavel.nome} NULL não tratado" if valor is None else f"{variavel.nome} fora da faixa"
            return Resultado("rejeitar", motivo=motivo)
    if not unidade.formula:
        return Resultado("ok", motivo="entradas aceitas (não há regra de saída)")
    try:
        conta = unidade.calcular(valores)
    except (ZeroDivisionError, InvalidOperation):
        return Resultado("pergunta", motivo="divisão por zero: a especificação não diz o que fazer")
    saida = unidade.saida
    if saida is None or saida.dominio.familia != "exato":
        return Resultado("ok", conta, conta)

    eps = saida.dominio.epsilon
    valor = conta.quantize(eps, rounding=REGRAS[regra])
    minimo, maximo = saida.faixa
    if not minimo <= valor <= maximo:
        return Resultado("estouro", valor, conta, f"{mostrar(valor)} não cabe em {saida.tipo}")
    para_cima, para_o_par = conta.quantize(eps, ROUND_HALF_UP), conta.quantize(eps, ROUND_HALF_EVEN)
    if para_cima != para_o_par:
        return Resultado("pergunta", valor, conta,
                         f"exato {mostrar(conta)}: {mostrar(para_cima)} arredondando meio para cima, "
                         f"{mostrar(para_o_par)} meio para o par (adotado: {regra})")
    return Resultado("ok", valor, conta, "" if valor == conta else f"arredondado de {mostrar(conta)}")


@exato
def caso_de_arredondamento(unidade, regra=REGRA_PADRAO):
    """Um caso cujo resultado exato cai no meio entre dois múltiplos de ε da saída
    (ex.: 0.01 × 0.50 = 0.0050). Devolve None se a regra não tiver produto entre entradas."""
    if not unidade.tem_regra_de_saida:
        return None
    for nome_a, nome_b in Formula(unidade.formula).produtos():
        a, b = unidade.entrada(nome_a), unidade.entrada(nome_b)
        if a.dominio.familia != "exato" or b.dominio.escala < 1:
            continue
        valores = {}
        for variavel in unidade.entradas:  # zero onde for aceito, para isolar o produto
            zero = Decimal(0).quantize(variavel.dominio.epsilon) if variavel.dominio.familia == "exato" else None
            valores[variavel.nome] = zero if zero is not None and variavel.aceita(zero) else None
        valores[nome_a] = a.dominio.epsilon
        valores[nome_b] = Decimal("0.5").quantize(b.dominio.epsilon)
        if esperado(unidade, valores, regra).situacao == "pergunta":
            return Caso("", "Achado", f"Arredondamento: {nome_a} × {nome_b} cai no meio de dois centavos",
                        valores)
    return None
