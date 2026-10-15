"""Etapa 4 — Tipos de dado: ε (a menor variação que o tipo representa) e a faixa do tipo.

Tipos exatos usam decimal.Decimal, nunca float:
    0.1 + 0.2                        → 0.30000000000000004  (float)
    Decimal("0.1") + Decimal("0.2")  → Decimal('0.3')       (exato)
"""

import math
import re
import sys
from dataclasses import dataclass
from decimal import Decimal

from motor import exato

# No Informix o menor valor de cada inteiro é reservado para o NULL: a faixa é simétrica.
INTEIROS = {"SMALLINT": 32767, "INTEGER": 2147483647, "BIGINT": 9223372036854775807}
SINONIMOS = {"INT": "INTEGER", "SERIAL": "INTEGER", "INT8": "BIGINT", "SERIAL8": "BIGINT",
             "BIGSERIAL": "BIGINT", "DEC": "DECIMAL", "NUMERIC": "DECIMAL", "CHARACTER": "CHAR",
             "VARCHAR": "CHAR", "NCHAR": "CHAR", "NVARCHAR": "CHAR", "DOUBLE PRECISION": "FLOAT",
             "DOUBLE": "FLOAT"}
_TEXTO_DO_TIPO = re.compile(r"^\s*([A-Za-z]+\d*(?:\s+PRECISION)?)\s*(?:\(\s*(\d+)\s*(?:,\s*(\d+)\s*)?\))?\s*$",
                            re.IGNORECASE)
_SOBRESCRITO = str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹")


@dataclass(frozen=True)
class Dominio:
    """O que um tipo aceita. Em CHAR a medida é o tamanho do texto, não o valor."""
    tipo: str          # nome normalizado, ex.: DECIMAL(12,2)
    familia: str       # "exato", "float" ou "texto"
    epsilon: object    # Decimal (exato), ulp de 1.0 (float) ou 1 caractere (texto)
    minimo: object
    maximo: object
    escala: int = 0

    def contem(self, medida):
        return self.minimo <= medida <= self.maximo

    @exato
    def vizinhos(self, x):
        """(X − ε, X, X + ε): os três pontos da AVL em torno da fronteira X."""
        if self.familia == "float":
            return math.nextafter(x, -math.inf), x, math.nextafter(x, math.inf)
        return x - self.epsilon, x, x + self.epsilon

    def epsilon_em(self, x):
        """ε no ponto X: constante nos tipos exatos; no FLOAT é a distância até o próximo float."""
        return math.ulp(x) if self.familia == "float" else self.epsilon

    @property
    def por_que(self):
        if self.familia == "texto":
            return "a fronteira é o tamanho do texto: ε = 1 caractere"
        if self.familia == "float":
            return f"ε muda com X: é a distância até o próximo float (math.ulp); em 1.0 vale {math.ulp(1.0)!r}"
        if self.escala == 0:
            return "não existe valor inteiro entre X e X + 1"
        potencia = "10" + str(-self.escala).translate(_SOBRESCRITO)
        casas = "1 casa decimal" if self.escala == 1 else f"{self.escala} casas decimais"
        return f"{self.tipo} guarda {casas}: ε = {potencia} = {mostrar(self.epsilon)}"


@exato
def dominio(texto):
    """Texto do tipo (ex.: 'DECIMAL(12,2)', 'INTEGER', 'CHAR(40)', 'FLOAT') → Dominio."""
    encontrado = _TEXTO_DO_TIPO.match(texto or "")
    if not encontrado:
        raise ValueError(f"Tipo não reconhecido: {texto!r}")
    nome = re.sub(r"\s+", " ", encontrado.group(1).upper())
    nome = SINONIMOS.get(nome, nome)
    precisao = int(encontrado.group(2)) if encontrado.group(2) else None
    escala = int(encontrado.group(3)) if encontrado.group(3) else None

    if nome in INTEIROS:
        limite = Decimal(INTEIROS[nome])
        return Dominio(nome, "exato", Decimal(1), -limite, limite)
    if nome in ("DECIMAL", "MONEY"):
        if nome == "MONEY":  # MONEY sem argumentos é MONEY(16,2)
            precisao, escala = precisao or 16, 2 if escala is None else escala
        if precisao is None or escala is None:
            raise ValueError("DECIMAL sem escala é ponto flutuante no Informix: informe DECIMAL(p,s), "
                             "por exemplo DECIMAL(12,2).")
        if not 1 <= precisao <= 32 or escala > precisao:
            raise ValueError(f"{nome}({precisao},{escala}) inválido: precisão de 1 a 32 e escala até a precisão.")
        eps = Decimal(1).scaleb(-escala)
        maximo = Decimal(10) ** (precisao - escala) - eps  # DECIMAL(12,2) → 9999999999.99
        return Dominio(f"{nome}({precisao},{escala})", "exato", eps, -maximo, maximo, escala)
    if nome == "CHAR":
        tamanho = precisao or 1
        # tamanho mínimo 1 é uma escolha (campo obrigatório); ajuste se a regra permitir vazio
        return Dominio(f"CHAR({tamanho})", "texto", 1, 1, tamanho)
    if nome == "FLOAT":
        return Dominio("FLOAT", "float", math.ulp(1.0), -sys.float_info.max, sys.float_info.max)
    raise ValueError(f"O tipo {nome} ainda não é suportado. Use DECIMAL(p,s), MONEY, INTEGER, SMALLINT, "
                     "BIGINT, CHAR(n) ou FLOAT.")


def epsilon(tipo, precisao=None, escala=None):
    """ε do tipo. Ex.: epsilon("DECIMAL", 12, 2) == Decimal("0.01"); epsilon("INTEGER") == 1."""
    if precisao is not None:
        tipo = f"{tipo}({precisao})" if escala is None else f"{tipo}({precisao},{escala})"
    return dominio(tipo).epsilon


def normalizar(texto):
    """'dec(12,2)' → 'DECIMAL(12,2)'. Tipos desconhecidos voltam como foram escritos."""
    try:
        return dominio(texto).tipo
    except ValueError:
        return (texto or "").strip().upper()


def mostrar(valor):
    """Valor em texto para as tabelas: Decimal sem notação científica, NULL e textos longos."""
    if valor is None:
        return "NULL"
    if isinstance(valor, Decimal):
        return format(valor, "f")
    if isinstance(valor, float):
        return repr(valor)
    if isinstance(valor, str):
        return f'"{valor}"' if len(valor) <= 12 else f"texto de {len(valor)} caracteres"
    return str(valor)
