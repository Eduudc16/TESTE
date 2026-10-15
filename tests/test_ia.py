"""Testes da parte de IA sem internet: chave, erros, modelos reserva e o JSON do requisito."""

import json
from decimal import Decimal as D
from types import SimpleNamespace

import pytest

from ia import chave, cliente
from leitores import requisito

CHAVE_DE_TESTE = "AIzaSy" + "x" * 33  # valor inventado, só para os testes


# --- Etapa 2: de onde vem a chave ------------------------------------------------------------

@pytest.mark.parametrize("valor", [None, "", "COLE_SUA_CHAVE_AQUI", "AIza...", "sua_chave", "curta"])
def test_texto_modelo_e_ignorado(valor):
    assert chave.eh_modelo(valor)


def test_ordem_das_origens():
    assert chave.obter_chave(CHAVE_DE_TESTE, {}) == (CHAVE_DE_TESTE, "secrets.toml")
    assert chave.obter_chave("COLE_SUA_CHAVE_AQUI", {chave.NOME: CHAVE_DE_TESTE}) == (CHAVE_DE_TESTE,
                                                                                    "variável de ambiente")
    # o Streamlit copia o secrets.toml para o ambiente: o texto-modelo não vale em nenhuma das duas
    assert chave.obter_chave("COLE_SUA_CHAVE_AQUI", {chave.NOME: "COLE_SUA_CHAVE_AQUI"}) == ("", "")


def test_secrets_valido_nao_gera_aviso(tmp_path):
    arquivo = tmp_path / "secrets.toml"
    arquivo.write_text(f'GEMINI_API_KEY = "{CHAVE_DE_TESTE}"\n', encoding="utf-8")
    assert chave.validar_secrets(arquivo) is None
    assert chave.validar_secrets(tmp_path / "nao_existe.toml") is None


def test_secrets_sem_aspas_e_detectado(tmp_path):
    arquivo = tmp_path / "secrets.toml"
    arquivo.write_text(f"GEMINI_API_KEY = {CHAVE_DE_TESTE}\n", encoding="utf-8")
    assert "aspas" in chave.validar_secrets(arquivo)


def test_secrets_com_texto_modelo_e_detectado(tmp_path):
    arquivo = tmp_path / "secrets.toml"
    arquivo.write_text('GEMINI_API_KEY = "COLE_SUA_CHAVE_AQUI"\n', encoding="utf-8")
    assert "exemplo" in chave.validar_secrets(arquivo)


# --- Etapa 8: erros, tempo limite e modelos reserva -----------------------------------------

class ErroDaApi(Exception):
    def __init__(self, code, mensagem):
        super().__init__(mensagem)
        self.code = code


class ReadTimeout(Exception):
    pass


@pytest.mark.parametrize("erro, tipo", [
    (ErroDaApi(400, "API key not valid. Please pass a valid API key."), "chave"),
    (ErroDaApi(403, "PERMISSION_DENIED"), "chave"),
    (ErroDaApi(503, "The model is overloaded"), "indisponivel"),
    (ErroDaApi(504, "Deadline exceeded"), "indisponivel"),
    (ErroDaApi(429, "RESOURCE_EXHAUSTED"), "indisponivel"),
    (ErroDaApi(404, "models/gemini-x is not found"), "indisponivel"),
    (ReadTimeout("The read operation timed out"), "indisponivel"),
    (ValueError("outra coisa"), "outro"),
])
def test_classificar_erro(erro, tipo):
    assert cliente.classificar_erro(erro) == tipo


class ClienteFalso:
    """Imita o cliente do google-genai: cada chamada consome a próxima resposta da lista."""

    def __init__(self, respostas=(), modelos=()):
        self.respostas, self.chamados = list(respostas), []
        self.models = SimpleNamespace(generate_content=self._gerar, list=self._listar)
        self._modelos = modelos

    def _gerar(self, model, contents, config):
        self.chamados.append(model)
        resposta = self.respostas.pop(0)
        if isinstance(resposta, Exception):
            raise resposta
        return SimpleNamespace(text=resposta)

    def _listar(self, config=None):
        return [SimpleNamespace(name=f"models/{nome}", supported_actions=["generateContent"]) for nome in self._modelos]


def test_troca_de_modelo_quando_o_primeiro_esta_sobrecarregado():
    falso = ClienteFalso([ErroDaApi(503, "overloaded"), ReadTimeout("timed out"), "resposta"])
    texto, modelo = cliente.gerar(falso, "prompt", ["a", "b", "c"])
    assert (texto, modelo, falso.chamados) == ("resposta", "c", ["a", "b", "c"])


def test_chave_recusada_para_na_hora():
    falso = ClienteFalso([ErroDaApi(400, "API key not valid"), "nunca chega aqui"])
    with pytest.raises(cliente.ErroIA) as erro:
        cliente.gerar(falso, "prompt", ["a", "b"])
    assert erro.value.tipo == "chave" and falso.chamados == ["a"]


def test_todos_os_modelos_falham_com_mensagem_amigavel():
    falso = ClienteFalso([ErroDaApi(503, "overloaded")] * 3)
    with pytest.raises(cliente.ErroIA) as erro:
        cliente.gerar(falso, "prompt", ["a", "b", "c"])
    assert erro.value.tipo == "indisponivel" and "Tente de novo" in str(erro.value)


def test_testar_chave_lista_os_modelos():
    teste = cliente.testar_chave(CHAVE_DE_TESTE, ClienteFalso(modelos=["gemini-2.5-flash", "gemini-3.5-flash"]))
    assert teste["situacao"] == "conectado"
    assert cliente.escolher_modelos(teste["modelos"]) == ["gemini-3.5-flash", "gemini-2.5-flash"]
    assert cliente.escolher_modelos([]) == list(cliente.MODELOS_PADRAO)


def test_google_lento_nao_desliga_a_ia():
    class ClienteLento(ClienteFalso):
        def _listar(self, config=None):
            raise ReadTimeout("timed out")

    assert cliente.testar_chave(CHAVE_DE_TESTE, ClienteLento())["situacao"] == "instavel"


# --- Etapa 8: requisito em português → JSON → Unidade ----------------------------------------

JSON_CAD0001 = {
    "nome": "cad0001_calcula_valor",
    "entradas": [{"nome": f"p_val{n}", "tipo": "DECIMAL(12,2)", "minimo": None, "maximo": None, "trata_nulo": True}
                 for n in (1, 2, 3)],
    "saida": {"nome": "val_calculado", "tipo": "DECIMAL(12,2)"},
    "formula": "(p_val1 * p_val2) + p_val3",
    "duvidas": ["Como arredondar o resultado?"],
}


def test_requisito_vira_unidade():
    unidade = requisito.unidade_de_json(json.dumps(JSON_CAD0001))
    assert [(v.nome, v.tipo, v.trata_nulo) for v in unidade.entradas] == [
        ("p_val1", "DECIMAL(12,2)", True), ("p_val2", "DECIMAL(12,2)", True), ("p_val3", "DECIMAL(12,2)", True)]
    assert unidade.formula == "(p_val1 * p_val2) + p_val3" and unidade.problemas() == []
    assert any("arredondar" in observacao for observacao in unidade.observacoes)


def test_requisito_com_regra_e_crases_do_markdown():
    dados = dict(JSON_CAD0001, entradas=[{"nome": "p_val1", "tipo": "dec(12,2)", "minimo": "0", "trata_nulo": "false"}],
                 formula="p_val1 * 2", saida=None)
    unidade = requisito.interpretar("texto", lambda prompt: "```json\n" + json.dumps(dados) + "\n```")
    variavel = unidade.entradas[0]
    assert (variavel.tipo, variavel.minimo, variavel.trata_nulo, unidade.saida) == ("DECIMAL(12,2)", D("0"), False, None)


@pytest.mark.parametrize("texto", ["isto não é json", "{}", '{"entradas": [{"tipo": "INTEGER"}]}'])
def test_requisito_invalido(texto):
    with pytest.raises(ValueError):
        requisito.unidade_de_json(texto)
