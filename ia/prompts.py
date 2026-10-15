"""Os três usos da IA: explicar a unidade, interpretar um requisito (em JSON) e revisar os casos.

A IA nunca calcula ε, classes ou limites: isso é do motor em Python.
"""

from motor.tipos import mostrar

SISTEMA = (
    "Você é parceiro de pareamento de um estudante de Teste de Software I (teste de caixa-preta, como em "
    "Delamaro, Maldonado e Jino, 2007). Responda em português do Brasil, em Markdown simples. Não use LaTeX: "
    "escreva nomes de variáveis e valores entre crases, como `p_val1`. Não calcule ε, classes de equivalência "
    "nem valores-limite: isso é feito pelo motor em Python; você explica, interpreta e revisa."
)


def resumo(unidade):
    """A unidade como o Python a entendeu, em poucas linhas."""
    linhas = [f"Unidade: {unidade.nome}"]
    for variavel in unidade.entradas:
        minimo, maximo = variavel.faixa
        linhas.append(f"- entrada {variavel.nome}: {variavel.tipo}, aceita de {mostrar(minimo)} a {mostrar(maximo)}"
                      f"{', NULL vira 0' if variavel.trata_nulo else ', NULL não tratado'}")
    if unidade.saida:
        linhas.append(f"- saída {unidade.saida.nome}: {unidade.saida.tipo}")
    linhas.append(f"- regra: {unidade.formula or '(sem fórmula)'}")
    return "\n".join(linhas)


def explicar(fonte, unidade):
    return f"""Explique esta unidade para quem vai testá-la como caixa-preta:
1. o que ela faz, em 2 ou 3 frases;
2. as entradas, a saída e o que acontece com NULL;
3. as regras de negócio que limitam os valores;
4. o que a especificação não deixa claro.
Seja breve (até 12 linhas).

Leitura feita pelo Python:
{resumo(unidade)}

Texto enviado:
```
{fonte}
```"""


def interpretar(requisito):
    return f"""Leia o requisito abaixo e devolva SOMENTE um JSON neste formato:
{{
  "nome": "nome curto da unidade",
  "entradas": [
    {{"nome": "p_val1", "tipo": "DECIMAL(12,2)", "minimo": null, "maximo": null, "trata_nulo": true}}
  ],
  "saida": {{"nome": "valor_calculado", "tipo": "DECIMAL(12,2)"}},
  "formula": "(p_val1 * p_val2) + p_val3",
  "duvidas": ["o que o requisito não deixa claro"]
}}

Regras:
- tipo: DECIMAL(p,s), MONEY(p,s), INTEGER, SMALLINT, BIGINT, CHAR(n) ou FLOAT. Se o requisito não disser,
  use o tipo mais provável e registre isso em "duvidas".
- minimo e maximo: só regras de negócio escritas no requisito (ex.: "não pode ser negativo" → "minimo": "0").
  Escreva os números como texto. Sem regra, use null.
- trata_nulo: true só se o requisito disser o que fazer com valor nulo ou ausente.
- formula: só + - * / e parênteses, com os nomes das entradas; null se não houver cálculo.
- saida: null se não houver valor calculado.
- Não calcule ε, classes nem limites.

Requisito:
\"\"\"
{requisito}
\"\"\""""


def revisar(resultado):
    casos = "\n".join(
        f"{caso.id} | {caso.tecnica} | "
        + ", ".join(f"{nome}={mostrar(valor)}" for nome, valor in caso.valores.items())
        + f" | {caso.resultado.texto()}" for caso in resultado.casos)
    achados = "\n".join(f"- {achado}" for achado in resultado.achados) or "- nenhuma"
    return f"""Revise os casos de teste de caixa-preta que o motor em Python gerou para a unidade abaixo.
Responda com:
1. classes de equivalência ou fronteiras que parecem faltar;
2. resultados esperados que parecem errados, citando o ID do caso e o porquê;
3. perguntas para o analista;
4. uma conclusão de 2 linhas.
Não refaça as contas do ε nem das fronteiras: comente o que foi gerado.

{resumo(resultado.unidade)}
Regra de arredondamento adotada: {resultado.regra}

Casos (ID | técnica | entradas | esperado):
{casos}

Perguntas já registradas:
{achados}"""
