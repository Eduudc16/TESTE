"""A regra da unidade (ex.: (p_val1 * p_val2) + p_val3) interpretada com o módulo ast.

Nada de eval(): eval executaria qualquer código escrito no .txt. Aqui a fórmula vira uma
árvore e só são aceitos números, nomes de variáveis, parênteses e + − × ÷.
"""

import ast
import operator
from decimal import Decimal

from motor import exato

_OPERACOES = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv}


class Formula:
    def __init__(self, texto):
        self.texto = (texto or "").strip()
        try:
            raiz = ast.parse(self.texto, mode="eval").body
        except SyntaxError as erro:
            raise ValueError(f"Fórmula inválida: {self.texto!r}") from erro
        _validar(raiz)
        self._raiz = raiz
        self.nomes = sorted({no.id for no in ast.walk(raiz) if isinstance(no, ast.Name)})

    @exato
    def avaliar(self, valores):
        """Calcula com Decimal, sem arredondar. Divisão por zero levanta ZeroDivisionError."""
        return _calcular(self._raiz, valores)

    def produtos(self):
        """Pares de variáveis multiplicadas entre si, ex.: [('p_val1', 'p_val2')]."""
        return [(no.left.id, no.right.id) for no in ast.walk(self._raiz)
                if isinstance(no, ast.BinOp) and isinstance(no.op, ast.Mult)
                and isinstance(no.left, ast.Name) and isinstance(no.right, ast.Name)]


def _validar(no):
    if isinstance(no, ast.BinOp) and type(no.op) in _OPERACOES:
        _validar(no.left)
        _validar(no.right)
    elif isinstance(no, ast.UnaryOp) and isinstance(no.op, (ast.USub, ast.UAdd)):
        _validar(no.operand)
    elif isinstance(no, ast.Name) or (isinstance(no, ast.Constant) and type(no.value) in (int, float)):
        return
    else:
        raise ValueError("A fórmula só aceita números, nomes de variáveis, parênteses e + − × ÷ "
                         f"(encontrado: {ast.unparse(no)}).")


def _calcular(no, valores):
    if isinstance(no, ast.BinOp):
        return _OPERACOES[type(no.op)](_calcular(no.left, valores), _calcular(no.right, valores))
    if isinstance(no, ast.UnaryOp):
        valor = _calcular(no.operand, valores)
        return -valor if isinstance(no.op, ast.USub) else +valor
    if isinstance(no, ast.Name):
        if no.id not in valores:
            raise ValueError(f"Falta o valor de {no.id} para calcular a fórmula.")
        return valores[no.id]
    return Decimal(str(no.value))  # str() evita levar o erro do float para o Decimal
