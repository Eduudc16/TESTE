"""Leitor de código Informix-4GL (Logix) por expressões regulares → Unidade.

Encontra a função, os parâmetros e os tipos declarados (DEFINE), quem troca NULL por 0,
as regras que rejeitam valores (IF ... < 0 THEN RETURN -1), a fórmula do cálculo e a
variável devolvida no RETURN.
"""

import re
from decimal import Decimal

from motor import tipos
from motor.formula import Formula
from motor.unidade import Unidade, Variavel

_COMENTARIO = re.compile(r"\{[^}]*\}|--[^\n]*|#[^\n]*")
_FUNCAO = re.compile(r"^[ \t]*FUNCTION\s+(\w+)\s*\(([^)]*)\)(.*?)^[ \t]*END\s+FUNCTION\b", re.I | re.M | re.S)
_TIPO = (r"(DECIMAL|DEC|NUMERIC|MONEY|INTEGER|INT8|INT|SMALLINT|BIGINT|SERIAL8|SERIAL|CHARACTER|CHAR|"
         r"VARCHAR|NCHAR|FLOAT|DOUBLE\s+PRECISION)\b(\s*\(\s*\d+\s*(?:,\s*\d+\s*)?\))?")
_DECLARACAO = re.compile(r"\b(\w+(?:\s*,\s*\w+)*)\s+" + _TIPO, re.I)
_NULO = re.compile(r"\bIF\s+(\w+)\s+IS\s+NULL\s+THEN\s+LET\s+(\w+)\s*=\s*0(?:\.0*)?(?![\w.])", re.I)
_APELIDO = re.compile(r"\bLET\s+(\w+)\s*=\s*([A-Za-z_]\w*)[ \t]*(?=$|\bEND\b|\bELSE\b)", re.I | re.M)
_SE = re.compile(r"\bIF\b(.*?)\bTHEN\b(.*?)\bEND\s+IF\b", re.I | re.S)
_COMPARACAO = re.compile(r"(\w+)\s*(<=|>=|<>|!=|<|>)\s*(-?\d+(?:\.\d+)?)")
_LET = re.compile(r"\bLET\s+(\w+)\s*=\s*([^\n]+)", re.I)
_RETURN = re.compile(r"\bRETURN\s+([A-Za-z_]\w*)[ \t]*$", re.I | re.M)


def _sem_comentarios(fonte):
    return _COMENTARIO.sub("", fonte)


def listar_funcoes(fonte):
    return [encontrada.group(1) for encontrada in _FUNCAO.finditer(_sem_comentarios(fonte))]


def _declaracoes(texto):
    """{variável: tipo normalizado} de tudo o que foi declarado no texto (DEFINE e RECORD)."""
    declaradas = {}
    for nomes, tipo, tamanho in _DECLARACAO.findall(texto):
        tipo_texto = tipos.normalizar(re.sub(r"\s+", " ", tipo) + re.sub(r"\s+", "", tamanho or ""))
        for nome in re.split(r"\s*,\s*", nomes):
            declaradas.setdefault(nome.lower(), tipo_texto)
    return declaradas


def ler(fonte, funcao=None):
    """Lê a função de cálculo (ou a função indicada) e devolve a Unidade."""
    texto = _sem_comentarios(fonte)
    funcoes = list(_FUNCAO.finditer(texto))
    if not funcoes:
        raise ValueError("Não encontrei nenhuma FUNCTION ... END FUNCTION no texto.")
    if funcao:
        alvo = next((f for f in funcoes if f.group(1).lower() == funcao.lower()), None)
        if alvo is None:
            raise ValueError(f"A função {funcao} não está no texto.")
    else:  # a função de cálculo; senão, a primeira que recebe parâmetros
        alvo = next((f for f in funcoes if "calcul" in f.group(1).lower()), None) \
            or next((f for f in funcoes if f.group(2).strip()), funcoes[0])
    nome, lista, corpo = alvo.groups()
    parametros = [p.strip().lower() for p in lista.split(",") if p.strip()]
    tipos_funcao, tipos_programa = _declaracoes(corpo), _declaracoes(texto)
    observacoes = [f"Função {nome}({', '.join(parametros)})."]

    # variável local que copia um parâmetro: IF val_param1 IS NULL ... ELSE LET p_val1 = val_param1
    apelidos = {local.lower(): origem.lower() for local, origem in _APELIDO.findall(corpo)
                if origem.lower() in parametros and local.lower() not in parametros}

    def parametro_de(variavel):
        variavel = variavel.lower()
        return variavel if variavel in parametros else apelidos.get(variavel)

    entradas = []
    for parametro in parametros:
        locais = [local for local, origem in apelidos.items() if origem == parametro]
        tipo = tipos_funcao.get(parametro) or next((tipos_funcao[l] for l in locais if l in tipos_funcao), None) \
            or tipos_programa.get(parametro)
        if tipo is None:
            tipo = next(iter(tipos_funcao.values()), "DECIMAL(12,2)")
            observacoes.append(f"O tipo de {parametro} não foi declarado: assumido {tipo}.")
        entradas.append(Variavel(parametro, tipo))
    por_nome = {variavel.nome: variavel for variavel in entradas}

    for variavel_if, variavel_let in _NULO.findall(corpo):
        parametro = parametro_de(variavel_if) or parametro_de(variavel_let)
        if parametro:
            por_nome[parametro].trata_nulo = True
    nulos = [v.nome for v in entradas if v.trata_nulo]
    if nulos:
        observacoes.append(f"NULL vira 0 em: {', '.join(nulos)}.")

    # regras de negócio: um IF que compara com um número e devolve (RETURN) rejeita o valor
    for condicao, bloco in _SE.findall(corpo):
        if not re.search(r"\bRETURN\b", bloco, re.I):
            continue
        for variavel, operador, limite in _COMPARACAO.findall(condicao):
            parametro = parametro_de(variavel)
            if parametro is None:
                continue
            alvo_regra, limite = por_nome[parametro], Decimal(limite)
            passo = alvo_regra.dominio.epsilon if alvo_regra.dominio.familia == "exato" else 0
            if operador == "<":      # rejeita < X  → válido a partir de X
                alvo_regra.minimo = limite
            elif operador == "<=":   # rejeita <= X → válido a partir de X + ε
                alvo_regra.minimo = limite + passo
            elif operador == ">":
                alvo_regra.maximo = limite
            elif operador == ">=":
                alvo_regra.maximo = limite - passo
            else:
                observacoes.append(f"Regra de igualdade ignorada: {variavel} {operador} {limite}.")
                continue
            observacoes.append(f"Regra encontrada: {variavel} {operador} {limite} é rejeitado (RETURN).")

    # saída: a última variável devolvida; fórmula: o LET com conta que a calcula
    retornos = [r.lower() for r in _RETURN.findall(corpo)]
    saida_nome = retornos[-1] if retornos else None
    formula = None
    candidatas = [(a.lower(), e) for a, e in _LET.findall(corpo) if re.search(r"[*/+\-]", e)]
    candidatas.sort(key=lambda par: par[0] != saida_nome)  # primeiro a que calcula a saída
    for _, expressao in candidatas:
        traduzida = re.sub(r"[A-Za-z_]\w*", lambda m: apelidos.get(m.group(0).lower(), m.group(0).lower()),
                           re.split(r"\bEND\b|\bELSE\b", expressao, flags=re.I)[0]).strip()
        try:
            nomes = Formula(traduzida).nomes
        except ValueError:
            continue
        if nomes and set(nomes) <= set(parametros):
            formula = traduzida
            break
    if formula:
        observacoes.append(f"Regra (fórmula): {formula}.")
    else:
        observacoes.append("Não encontrei a fórmula do cálculo: escreva-a na tabela, se houver.")

    saida = None
    tipo_saida = (tipos_funcao.get(saida_nome) or tipos_programa.get(saida_nome)) if saida_nome else None
    if saida_nome and tipo_saida:
        saida = Variavel(saida_nome, tipo_saida)
        observacoes.append(f"Saída: {saida_nome} {tipo_saida}.")
    elif saida_nome:
        observacoes.append(f"O tipo da saída {saida_nome} não foi declarado: sem AVL na saída.")

    return Unidade(nome=nome, entradas=entradas, saida=saida, formula=formula,
                   origem="Informix-4GL (regex)", observacoes=observacoes)
