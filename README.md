# 🧪 TestingStudio Web

Auditor web de testes de software — Projeto Integrador de **Teste de Software I** (ementa 62371).
Sprint 1: teste de **caixa-preta** (PCE + AVL com ε).

Você entrega um `.txt` (código Informix-4GL ou requisito em português), a IA ajuda a entender e o
**Python** aplica o teste de caixa-preta com matemática exata. **A IA nunca calcula ε, classes ou limites.**

## Como rodar

1. Instale as dependências:

   ```bash
   python -m pip install -r requirements.txt
   ```

2. Crie a chave grátis em <https://aistudio.google.com/apikey>, copie `.streamlit/secrets.toml.example`
   para `.streamlit/secrets.toml` e cole a chave **entre aspas**:

   ```toml
   GEMINI_API_KEY = "AIza..."
   ```

   O `secrets.toml` está no `.gitignore`: a chave nunca vai para o repositório.

3. Rode a aplicação (abre em <http://localhost:8501>):

   ```bash
   python -m streamlit run app.py
   ```

4. Rode os testes do gabarito:

   ```bash
   python -m pytest
   ```

Sem chave, o motor (ε, PCE, AVL e oráculo) funciona normalmente; só a IA fica desligada, e o requisito
pode ser preenchido à mão. Se você mudar um `.py` e nada mudar na tela, reinicie o servidor: o Streamlit
nem sempre recarrega os módulos importados.

## Fluxo

| Página | O que faz |
|---|---|
| 📄 **Ler** | Upload ou exemplo; decodifica `utf-8-sig` → `cp1252` → `latin-1`; lê o código por regex ou o requisito pela IA (JSON); mostra a unidade numa tabela editável; a IA explica a unidade |
| 📐 **Analisar** | Abas ε e domínio · PCE (com gráfico de cobertura) · AVL (com régua das fronteiras) · casos de teste com resultado esperado; baixa CSV e testes pytest |
| 🤖 **Revisar** | Perguntas para o analista e revisão dos casos pela IA |

A barra lateral mostra de onde veio a chave (`secrets.toml`, variável de ambiente ou digitada) e se a
conexão funcionou. Chave recusada desliga a IA; Google lento não.

## Estrutura

```text
app.py                    navegação entre as páginas e barra lateral da chave
paginas/                  1_ler.py · 2_analisar.py · 3_revisar.py · graficos.py · comum.py
motor/                    tipos.py (ε e domínio) · formula.py (ast, sem eval) · unidade.py
                          particao.py (PCE) · limites.py (AVL) · oraculo.py · suite.py · exportar.py
leitores/                 arquivo.py (codificação) · informix.py (regex) · requisito.py (IA → JSON)
ia/                       chave.py (origem da chave) · cliente.py (tempo limite e modelos reserva) · prompts.py
tests/                    test_motor.py (gabarito) · test_ia.py (sem internet)
exemplos/                 CAD0001 do professor, versão do manual e um requisito em português
```

## Decisões registradas

- **Arredondamento da saída:** a especificação não diz. Padrão: meio para cima (`ROUND_HALF_UP`); a tela
  deixa trocar para meio para o par, e o caso de empate vira pergunta para o analista.
- **Valores típicos:** 50, 51, 52… — diferentes por variável, porque valores iguais mascaram a troca de
  um parâmetro por outro.
- **Representante inválido:** a meia largura além do limite; a fronteira exata é trabalho da AVL.
- **NULL:** é classe válida quando o código troca NULL por 0.
- **CHAR(n):** tamanho mínimo 1 (campo obrigatório).
- **Regras de negócio** (ex.: `IF p_val1 < 0 THEN RETURN -1`) estreitam a faixa do tipo e viram fronteiras.

## Gabarito (CAD0001 do professor)

15 classes, 8 fronteiras e 34 casos. Todas as linhas do gabarito do guia estão em `tests/test_motor.py`:

| p_val1 | p_val2 | p_val3 | Esperado |
|---|---|---|---|
| 50.00 | 51.00 | 52.00 | ✅ 2602.00 |
| NULL | NULL | NULL | ✅ 0.00 |
| 9999999999.99 | 51.00 | 52.00 | ⚠️ estouro (510000000051.49) |
| 50.00 | 51.00 | 9999997449.99 | ✅ 9999999999.99 — fronteira exata da saída |
| 50.00 | 51.00 | 9999997450.00 | ⚠️ estouro (10000000000.00) |
| 10000000000.00 | 51.00 | 52.00 | ❌ rejeitar |
| 0.01 | 0.50 | 0.00 | ❓ exato 0.0050: 0.01 meio para cima, 0.00 meio para o par |

O arquivo `cad0001_item_calculo.txt` do professor **não tem** a regra `valores < 0 → RETURN -1` que aparece
no manual. A versão do manual está em `exemplos/cad0001_manual.txt`; com ela, a fronteira mínima de cada
entrada passa a ser 0.00.

## O que esta versão faz diferente (seção 7 do guia)

- 🧭 Páginas com `st.navigation` em vez de rolagem.
- 📏 Régua das fronteiras com X − ε, X e X + ε, como no slide do manual.
- 🗣️ Requisito primeiro: a IA lê o enunciado e devolve JSON; o regex do Informix é a alternativa.
- 🐍 Exportar para pytest: um `.py` com `@pytest.mark.parametrize` de todos os casos.
- 📊 Cobertura das classes num gráfico de barras.

## Checklist de entrega

- [x] `python -m streamlit run app.py` abre sem erro
- [x] chave no `secrets.toml` com aspas e fora do Git
- [x] barra lateral mostra de onde veio a chave e se conectou
- [x] o `.txt` aparece na caixa de texto, com acentos certos
- [x] ε calculado pelo Python, nunca pela IA
- [x] PCE, AVL e casos de teste com resultado esperado
- [x] o gabarito confere (`python -m pytest`)
- [x] a IA explica, interpreta e revisa — e erro vira mensagem amigável
- [x] README dizendo como rodar
- [ ] commit e push antes do fim da aula, com o e-mail certo (`git config user.email` local)

## Referências

- DELAMARO, M. E.; MALDONADO, J. C.; JINO, M. *Introdução ao Teste de Software*. Rio de Janeiro: Elsevier, 2007.
- Manual da disciplina: *TestingStudio Web — Kickoff* (Laboratório de Teste de Software I, ementa 62371).
- Streamlit: <https://docs.streamlit.io> · Gemini API: <https://ai.google.dev/gemini-api/docs>
