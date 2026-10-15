"""De onde vem a API Key do Gemini: secrets.toml, variável de ambiente ou digitada na tela.

Nada aqui depende do Streamlit, para poder ser testado com pytest.
"""

from pathlib import Path

NOME = "GEMINI_API_KEY"


def eh_modelo(valor):
    """True para chave vazia ou texto de exemplo (COLE_SUA_CHAVE_AQUI, AIza...).

    O Streamlit copia o secrets.toml para as variáveis de ambiente, então o texto-modelo
    precisa ser ignorado nas duas origens.
    """
    texto = (valor or "").strip()
    maiusculo = texto.upper()
    return (len(texto) < 20 or " " in texto or texto.endswith("...")
            or "COLE" in maiusculo or "SUA_CHAVE" in maiusculo)


def _ler_toml(texto):
    try:
        import tomllib  # Python 3.11+
        return tomllib.loads(texto)
    except ModuleNotFoundError:
        import toml  # já vem com o Streamlit
        return toml.loads(texto)


def validar_secrets(caminho):
    """Confere o secrets.toml e devolve um aviso em texto, ou None se não houver problema.

    Com o arquivo malformado (por exemplo, a chave sem aspas) o Streamlit age como se ele
    não existisse, sem avisar ninguém; por isso a conferência é feita aqui.
    """
    caminho = Path(caminho)
    if not caminho.is_file():
        return None
    try:
        dados = _ler_toml(caminho.read_text(encoding="utf-8-sig"))
    except Exception as erro:
        return (f"O arquivo `{caminho}` está inválido e o Streamlit vai ignorá-lo. "
                f'Confira se a chave está entre aspas: `{NOME} = "AIza..."`. Detalhe: {erro}')
    if NOME not in dados:
        return f'O arquivo `{caminho}` não tem a linha `{NOME} = "..."`.'
    if eh_modelo(str(dados[NOME])):
        return f"O arquivo `{caminho}` ainda tem o texto de exemplo: cole a sua chave entre as aspas."
    return None


def obter_chave(valor_secrets, ambiente):
    """Escolhe a chave na ordem secrets.toml → variável de ambiente.

    Devolve (chave, origem); ("", "") quando nenhuma das duas tem uma chave de verdade.
    """
    if not eh_modelo(valor_secrets):
        return valor_secrets.strip(), "secrets.toml"
    valor_ambiente = ambiente.get(NOME, "")
    if not eh_modelo(valor_ambiente):
        return valor_ambiente.strip(), "variável de ambiente"
    return "", ""
