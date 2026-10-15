"""Junta o motor: classes (PCE), fronteiras (AVL), casos com resultado esperado e achados."""

from dataclasses import dataclass

from motor import limites, oraculo, particao
from motor.tipos import mostrar


@dataclass
class Suite:
    unidade: object
    regra: str
    classes: list
    fronteiras: list
    casos: list
    achados: list


def montar(unidade, regra=oraculo.REGRA_PADRAO):
    classes = particao.classes_de_equivalencia(unidade)
    lista_fronteiras = limites.fronteiras(unidade)
    casos = particao.casos_pce(unidade, classes) + limites.casos_avl(unidade, lista_fronteiras)
    arredondamento = oraculo.caso_de_arredondamento(unidade, regra)
    if arredondamento:
        casos.append(arredondamento)
    for numero, caso in enumerate(casos, start=1):
        caso.id = f"CT{numero:02d}"
        caso.classes = particao.classificar(unidade, classes, caso.valores)
        caso.resultado = oraculo.esperado(unidade, caso.valores, regra)
    return Suite(unidade, regra, classes, lista_fronteiras, casos, achados(unidade, classes, casos, regra))


def achados(unidade, classes, casos, regra):
    """Perguntas para o analista: o que a especificação não responde."""
    lista = []
    perguntas = [caso.id for caso in casos if caso.resultado.situacao == "pergunta"]
    if perguntas:
        lista.append(f"A especificação não diz como arredondar a saída ({', '.join(perguntas)}). "
                     f"Regra adotada: {regra}. Pergunte ao analista qual vale.")
    estouros = [caso for caso in casos if caso.resultado.situacao == "estouro"]
    if estouros:
        exemplo = estouros[0]
        lista.append(f"A saída {unidade.saida.nome} pode estourar {unidade.saida.tipo} (ex.: {exemplo.id} = "
                     f"{mostrar(exemplo.resultado.valor)}). A especificação não diz o que fazer: rejeitar a "
                     "entrada, truncar ou devolver erro?")
    nulos = [variavel.nome for variavel in unidade.entradas if variavel.trata_nulo]
    if nulos:
        lista.append(f"NULL vira 0 em {', '.join(nulos)}: confirme que é isso que a regra de negócio quer "
                     "(o manual chama o nulo de classe inválida).")
    for classe in classes:
        if not classe.alcancavel:
            lista.append(f"{classe.id} ({classe.descricao}) não é alcançável com uma entrada no extremo.")
    return lista


def linhas_de_casos(casos):
    """Casos no formato de tabela (tela e CSV)."""
    return [{"Caso": caso.id, "Técnica": caso.tecnica, "Descrição": caso.descricao,
             **{nome: mostrar(valor) for nome, valor in caso.valores.items()},
             "Esperado": caso.resultado.texto(), "Classes": ", ".join(caso.classes)} for caso in casos]
