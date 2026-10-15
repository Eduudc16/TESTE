"""Gabarito do guia (seção 5) em testes automáticos. Rode com: python -m pytest"""

import math
from decimal import Decimal
from pathlib import Path

import pytest

from leitores import informix
from leitores.arquivo import decodificar, ler_arquivo
from motor import limites, particao, tipos
from motor.formula import Formula

EXEMPLOS = Path(__file__).parent.parent / "exemplos"
D = Decimal


# --- Etapa 4: ε e faixa de cada tipo -------------------------------------------------------

@pytest.mark.parametrize("tipo, epsilon, maximo, avl_no_maximo, dentro", [
    ("DECIMAL(12,2)", D("0.01"), D("9999999999.99"),
     (D("9999999999.98"), D("9999999999.99"), D("10000000000.00")), (True, True, False)),
    ("DECIMAL(5,1)", D("0.1"), D("9999.9"), (D("9999.8"), D("9999.9"), D("10000.0")), (True, True, False)),
    ("INTEGER", 1, 2147483647, (2147483646, 2147483647, 2147483648), (True, True, False)),
    ("SMALLINT", 1, 32767, (32766, 32767, 32768), (True, True, False)),
    ("CHAR(40)", 1, 40, (39, 40, 41), (True, True, False)),
])
def test_tipos_exatos(tipo, epsilon, maximo, avl_no_maximo, dentro):
    dominio = tipos.dominio(tipo)
    assert dominio.epsilon == epsilon
    assert dominio.maximo == maximo
    assert dominio.minimo == (1 if dominio.familia == "texto" else -maximo)
    assert dominio.vizinhos(dominio.maximo) == avl_no_maximo
    assert tuple(dominio.contem(v) for v in avl_no_maximo) == dentro


def test_avl_do_maximo_decimal_mantem_a_escala():
    abaixo, x, acima = tipos.dominio("DECIMAL(12,2)").vizinhos(D("9999999999.99"))
    assert [tipos.mostrar(v) for v in (abaixo, x, acima)] == ["9999999999.98", "9999999999.99", "10000000000.00"]


def test_float():
    dominio = tipos.dominio("FLOAT")
    assert dominio.epsilon == math.ulp(1.0) == 2.220446049250313e-16
    assert dominio.maximo == 1.7976931348623157e308
    abaixo, x, acima = dominio.vizinhos(dominio.maximo)
    assert abaixo == math.nextafter(dominio.maximo, -math.inf)
    assert acima == math.inf and not dominio.contem(acima)


def test_epsilon_decimal_12_2():
    assert tipos.epsilon("DECIMAL", 12, 2) == D("0.01")
    assert tipos.epsilon("INTEGER") == 1


def test_decimal_grande_nao_perde_digitos():
    dominio = tipos.dominio("DECIMAL(32,2)")
    assert tipos.mostrar(dominio.vizinhos(dominio.maximo)[2]) == "1" + "0" * 30 + ".00"


@pytest.mark.parametrize("escrito, normalizado", [
    ("dec(12,2)", "DECIMAL(12,2)"), ("NUMERIC(5,1)", "DECIMAL(5,1)"), ("MONEY", "MONEY(16,2)"),
    ("int", "INTEGER"), ("SERIAL", "INTEGER"), ("INT8", "BIGINT"), ("CHAR(02)", "CHAR(2)"),
    ("VARCHAR(40)", "CHAR(40)"), ("double precision", "FLOAT"),
])
def test_sinonimos(escrito, normalizado):
    assert tipos.normalizar(escrito) == normalizado


@pytest.mark.parametrize("tipo", ["DECIMAL", "DECIMAL(12)", "DATE", "DECIMAL(40,2)", "xyz("])
def test_tipos_recusados(tipo):
    with pytest.raises(ValueError):
        tipos.dominio(tipo)


def test_armadilha_classica_float():
    assert 0.1 + 0.2 != 0.3
    assert D("0.1") + D("0.2") == D("0.3")


# --- fórmula interpretada com ast (sem eval) ------------------------------------------------

def test_formula_calcula_com_decimal():
    formula = Formula("(p_val1 * p_val2) + p_val3")
    assert formula.nomes == ["p_val1", "p_val2", "p_val3"]
    assert formula.avaliar({"p_val1": D("50.00"), "p_val2": D("51.00"), "p_val3": D("52.00")}) == D("2602.00")
    assert formula.produtos() == [("p_val1", "p_val2")]


@pytest.mark.parametrize("perigosa", ["__import__('os').system('dir')", "a ** b", "abs(a)", "a.b", "'texto'"])
def test_formula_recusa_o_que_nao_e_conta(perigosa):
    with pytest.raises(ValueError):
        Formula(perigosa)


# --- Etapa 3 e 4: leitura do .txt e do código Informix ---------------------------------------

def test_decodificar_ansi_e_utf8():
    assert decodificar("Cálculo".encode("cp1252")) == ("Cálculo", "cp1252")
    assert decodificar("﻿Fictício\r\n".encode("utf-8")) == ("Fictício\n", "utf-8-sig")


def test_exemplo_com_acentos():
    texto, _ = ler_arquivo(EXEMPLOS / "cad0001_item_calculo.txt")
    assert "Cálculo" in texto and "Fictício" in texto


def test_ler_cad0001_do_professor():
    texto, _ = ler_arquivo(EXEMPLOS / "cad0001_item_calculo.txt")
    assert "cad0001_calcula_valor" in informix.listar_funcoes(texto)
    unidade = informix.ler(texto)
    assert unidade.nome == "cad0001_calcula_valor"
    assert [(v.nome, v.tipo, v.trata_nulo, v.minimo) for v in unidade.entradas] == [
        ("p_val1", "DECIMAL(12,2)", True, None), ("p_val2", "DECIMAL(12,2)", True, None),
        ("p_val3", "DECIMAL(12,2)", True, None)]
    assert (unidade.saida.nome, unidade.saida.tipo) == ("l_val_calculado", "DECIMAL(12,2)")
    assert unidade.formula == "(p_val1 * p_val2) + p_val3"
    assert unidade.problemas() == []


def test_ler_cad0001_do_manual_com_regra_de_negocio():
    texto, _ = ler_arquivo(EXEMPLOS / "cad0001_manual.txt")
    unidade = informix.ler(texto)
    assert [(v.nome, v.tipo, v.trata_nulo, v.minimo) for v in unidade.entradas] == [
        ("val_param1", "DECIMAL(12,2)", True, D("0")), ("val_param2", "DECIMAL(12,2)", True, D("0")),
        ("val_param3", "DECIMAL(12,2)", True, D("0"))]
    assert unidade.formula == "(val_param1 * val_param2) + val_param3"
    assert unidade.entradas[0].faixa == (D("0.00"), D("9999999999.99"))
    assert tipos.mostrar(unidade.entradas[0].faixa[0]) == "0.00"


def test_regra_com_menor_ou_igual_soma_epsilon():
    fonte = """FUNCTION f(a)
    DEFINE a DECIMAL(5,1)
    IF a <= 0 THEN RETURN -1 END IF
    RETURN a
END FUNCTION"""
    assert informix.ler(fonte).entradas[0].minimo == D("0.1")


# --- Etapa 5: PCE ---------------------------------------------------------------------------

def unidade_cad0001():
    texto, _ = ler_arquivo(EXEMPLOS / "cad0001_item_calculo.txt")
    return informix.ler(texto)


def test_valores_tipicos_diferentes_por_variavel():
    assert particao.tipicos(unidade_cad0001()) == {"p_val1": D("50.00"), "p_val2": D("51.00"), "p_val3": D("52.00")}


def test_classes_do_cad0001():
    classes = particao.classes_de_equivalencia(unidade_cad0001())
    assert [classe.id for classe in classes] == [f"CE{n}" for n in range(1, 16)]
    assert [(c.tipo, c.valida) for c in classes[:4]] == [
        ("dentro", True), ("abaixo", False), ("acima", False), ("nulo", True)]
    assert classes[1].representante == D("-19999999999.98")   # meia largura abaixo do mínimo
    assert classes[2].representante == D("19999999999.98")
    assert [c.tipo for c in classes[12:]] == ["saida_dentro", "saida_acima", "saida_abaixo"]
    assert classes[13].representante == {"p_val1": D("9999999999.99"), "p_val2": D("51.00"), "p_val3": D("52.00")}


def test_casos_pce_cobrem_tudo_com_uma_invalida_por_caso():
    unidade = unidade_cad0001()
    classes = particao.classes_de_equivalencia(unidade)
    casos = particao.casos_pce(unidade, classes)
    for caso in casos:
        caso.classes = particao.classificar(unidade, classes, caso.valores)
    invalidas = {classe.id for classe in classes if not classe.valida}
    assert all(len(set(caso.classes) & invalidas) <= 1 for caso in casos)
    assert {id_ for caso in casos for id_ in caso.classes} == {classe.id for classe in classes}
    assert {"p_val1": None, "p_val2": None, "p_val3": None} in [caso.valores for caso in casos]


# --- Etapa 6: AVL ---------------------------------------------------------------------------

def test_oito_fronteiras_e_avl_no_maximo_da_entrada():
    fronteiras = limites.fronteiras(unidade_cad0001())
    assert len(fronteiras) == 8
    assert limites.linha(fronteiras[1])["Pontos"] == "9999999999.98 ✅ · 9999999999.99 ✅ · 10000000000.00 ❌"
    assert limites.linha(fronteiras[0])["Pontos"] == "-10000000000.00 ❌ · -9999999999.99 ✅ · -9999999999.98 ✅"


def test_avl_no_maximo_da_saida_e_exata():
    unidade = unidade_cad0001()
    variavel, x, multiplo = limites.resolver_saida(unidade, D("9999999999.99"))
    assert (variavel.nome, x, multiplo) == ("p_val3", D("9999997449.99"), True)
    maximo = limites.fronteiras(unidade)[7]
    assert [tipos.mostrar(p.valor) for p in maximo.pontos] == ["9999997449.98", "9999997449.99", "9999997450.00"]
    assert [p.valido for p in maximo.pontos] == [True, True, False]
    assert maximo.pontos[1].resultado == D("9999999999.99")


def test_avl_no_minimo_da_saida_testa_os_dois_vizinhos():
    minimo = limites.fronteiras(unidade_cad0001())[6]
    assert minimo.variavel == "p_val1"  # p_val3 precisaria sair da faixa do tipo
    assert [tipos.mostrar(p.valor) for p in minimo.pontos] == ["-196078432.40", "-196078432.39"]
    assert [p.valido for p in minimo.pontos] == [False, True]


def test_regra_do_manual_vira_fronteira_em_zero():
    texto, _ = ler_arquivo(EXEMPLOS / "cad0001_manual.txt")
    fronteira = limites.fronteiras(informix.ler(texto))[0]
    assert limites.linha(fronteira)["Pontos"] == "-0.01 ❌ · 0.00 ✅ · 0.01 ✅"


def test_casos_avl():
    unidade = unidade_cad0001()
    casos = limites.casos_avl(unidade, limites.fronteiras(unidade))
    assert len(casos) == 6 * 3 + 2 + 3
    assert {"p_val1": D("50.00"), "p_val2": D("51.00"), "p_val3": D("9999997449.99")} in [c.valores for c in casos]
