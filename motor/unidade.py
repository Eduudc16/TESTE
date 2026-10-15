"""O modelo comum aos dois leitores (Informix e requisito): entradas, saída e regra da unidade."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from motor import tipos
from motor.formula import Formula

COLUNAS = ("Nome", "Tipo", "Mínimo (regra)", "Máximo (regra)", "NULL vira 0")


def vazio(valor):
    """Célula vazia: None, '', NaN do pandas ou <NA> do st.data_editor — tratado num lugar só."""
    if valor is None:
        return True
    if isinstance(valor, float) and math.isnan(valor):
        return True
    return str(valor).strip().lower() in ("", "nan", "<na>", "none", "null")


def numero(valor):
    """Texto da tabela → Decimal (aceita vírgula decimal); vazio → None."""
    if vazio(valor):
        return None
    texto = str(valor).strip().replace(" ", "")
    if "," in texto:  # 1.234,56 → 1234.56
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return Decimal(texto)
    except InvalidOperation:
        raise ValueError(f"Número inválido: {valor!r}") from None


@dataclass
class Variavel:
    nome: str
    tipo: str
    trata_nulo: bool = False          # o código troca NULL por 0?
    minimo: Decimal | None = None     # regra de negócio que estreita a faixa do tipo
    maximo: Decimal | None = None

    @property
    def dominio(self):
        return tipos.dominio(self.tipo)

    @property
    def faixa(self):
        """(mínimo, máximo) aceitos: a faixa do tipo estreitada pelas regras de negócio."""
        dominio = self.dominio
        if dominio.familia == "texto":
            return dominio.minimo, dominio.maximo
        minimo = dominio.minimo if self.minimo is None else max(dominio.minimo, self.minimo)
        maximo = dominio.maximo if self.maximo is None else min(dominio.maximo, self.maximo)
        return minimo, maximo

    def medida(self, valor):
        """O que é comparado com a faixa: o valor, ou o tamanho do texto em CHAR."""
        return len(valor) if self.dominio.familia == "texto" else valor

    def aceita(self, valor):
        if valor is None:
            return self.trata_nulo
        minimo, maximo = self.faixa
        return minimo <= self.medida(valor) <= maximo


@dataclass
class Caso:
    id: str
    tecnica: str              # "PCE", "AVL" ou "Achado"
    descricao: str
    valores: dict             # entrada → valor (None = NULL)
    classes: list = field(default_factory=list)
    resultado: object = None  # oraculo.Resultado


@dataclass
class Unidade:
    nome: str
    entradas: list
    saida: Variavel | None = None
    formula: str | None = None
    origem: str = ""
    observacoes: list = field(default_factory=list)

    def entrada(self, nome):
        return next(v for v in self.entradas if v.nome == nome)

    @property
    def tem_regra_de_saida(self):
        """Há fórmula e uma saída de tipo exato: dá para fazer PCE e AVL na saída."""
        return bool(self.formula) and self.saida is not None and self.saida.dominio.familia == "exato"

    def calcular(self, valores):
        """Valor exato da fórmula (sem arredondar), com NULL valendo 0."""
        numeros = {nome: Decimal(0) if valor is None else Decimal(repr(valor)) if isinstance(valor, float)
                   else valor for nome, valor in valores.items()}
        return Formula(self.formula).avaliar(numeros)

    def problemas(self):
        """O que impede a análise (tipo inválido, fórmula com nome desconhecido...)."""
        erros = []
        nomes = [v.nome for v in self.entradas]
        if not nomes:
            erros.append("A unidade não tem entradas.")
        if len(set(nomes)) != len(nomes):
            erros.append("Há entradas com o mesmo nome.")
        for variavel in self.entradas + ([self.saida] if self.saida else []):
            try:
                variavel.dominio
            except ValueError as erro:
                erros.append(f"{variavel.nome}: {erro}")
        if self.formula and not erros:
            try:
                formula = Formula(self.formula)
            except ValueError as erro:
                return erros + [str(erro)]
            desconhecidos = set(formula.nomes) - set(nomes)
            if desconhecidos:
                erros.append(f"A fórmula usa nomes que não são entradas: {', '.join(sorted(desconhecidos))}.")
            textos = [v.nome for v in self.entradas if v.nome in formula.nomes and v.dominio.familia == "texto"]
            if textos:
                erros.append(f"A fórmula não pode fazer contas com texto: {', '.join(textos)}.")
            if self.saida and self.saida.dominio.familia == "texto":
                erros.append("A saída de uma fórmula precisa ser numérica.")
        return erros

    def linhas_entradas(self):
        """Entradas no formato da tabela editável da página Ler."""
        return [{"Nome": v.nome, "Tipo": v.tipo,
                 "Mínimo (regra)": "" if v.minimo is None else tipos.mostrar(v.minimo),
                 "Máximo (regra)": "" if v.maximo is None else tipos.mostrar(v.maximo),
                 "NULL vira 0": v.trata_nulo} for v in self.entradas]

    def linhas_dominio(self):
        """Tabela do ε: tipo, faixa aceita e o porquê de cada ε."""
        linhas = []
        for papel, variavel in [("entrada", v) for v in self.entradas] + [("saída", self.saida)]:
            if variavel is None:
                continue
            dominio = variavel.dominio
            minimo, maximo = variavel.faixa
            medida = " (tamanho)" if dominio.familia == "texto" else ""
            linhas.append({
                "Variável": variavel.nome, "Papel": papel, "Tipo": dominio.tipo,
                "ε": "1 caractere" if dominio.familia == "texto" else tipos.mostrar(dominio.epsilon),
                "Mínimo": tipos.mostrar(minimo) + medida, "Máximo": tipos.mostrar(maximo) + medida,
                "NULL vira 0": "sim" if variavel.trata_nulo else ("—" if papel == "saída" else "não"),
                "Por quê": dominio.por_que})
        return linhas


def unidade_de_tabela(nome, linhas, saida_nome, saida_tipo, formula, origem="", observacoes=()):
    """Reconstrói a Unidade a partir do que foi editado na tela."""
    entradas = [Variavel(nome=str(linha["Nome"]).strip().lower(), tipo=tipos.normalizar(str(linha["Tipo"])),
                         trata_nulo=not vazio(linha.get("NULL vira 0")) and bool(linha.get("NULL vira 0")),
                         minimo=numero(linha.get("Mínimo (regra)")), maximo=numero(linha.get("Máximo (regra)")))
                for linha in linhas if not vazio(linha.get("Nome")) and not vazio(linha.get("Tipo"))]
    saida = None
    if not vazio(saida_nome) and not vazio(saida_tipo):
        saida = Variavel(str(saida_nome).strip().lower(), tipos.normalizar(str(saida_tipo)))
    return Unidade(nome=nome, entradas=entradas, saida=saida,
                   formula=None if vazio(formula) else str(formula).strip(),
                   origem=origem, observacoes=list(observacoes))
