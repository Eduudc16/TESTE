"""Cliente do Gemini com tempo limite, modelos reserva e erros traduzidos para o usuário.

Os modelos mais novos vivem sobrecarregados (503/504) e, sem tempo limite, uma chamada pode
ficar girando por minutos. Por isso cada chamada tem limite e, se um modelo falhar por
lentidão, sobrecarga ou por não existir, tenta-se o próximo da lista.
"""

MODELOS_PADRAO = ("gemini-3.5-flash", "gemini-2.5-flash", "gemini-flash-latest")
TEMPO_LIMITE_MS = 45_000
TEMPO_TESTE_MS = 10_000

MENSAGENS = {
    "chave": "O Google recusou a chave. Confira o valor no `.streamlit/secrets.toml`.",
    "indisponivel": "O Google está lento ou sobrecarregado agora. Tente de novo em instantes.",
    "biblioteca": "Falta a biblioteca do Gemini. No terminal: `python -m pip install google-genai`",
}


class ErroIA(Exception):
    """Erro da IA já com uma mensagem amigável; `tipo` é 'chave', 'indisponivel' ou 'outro'."""

    def __init__(self, mensagem, tipo="outro"):
        super().__init__(mensagem)
        self.tipo = tipo


def biblioteca_instalada():
    try:
        from google import genai  # noqa: F401
        return True
    except ImportError:
        return False


def classificar_erro(erro):
    """'chave' (chave recusada), 'indisponivel' (lento, sobrecarregado, modelo inexistente) ou 'outro'."""
    codigo = getattr(erro, "code", None)
    texto = f"{type(erro).__name__} {erro}".lower()
    if codigo in (401, 403) or "api_key_invalid" in texto or (codigo == 400 and "api key" in texto):
        return "chave"
    if (codigo in (404, 408, 429) or (isinstance(codigo, int) and codigo >= 500)
            or "timeout" in texto or "timed out" in texto or "connect" in texto):
        return "indisponivel"
    return "outro"


def criar_cliente(chave, tempo_limite_ms=TEMPO_LIMITE_MS):
    from google import genai
    from google.genai import types
    return genai.Client(api_key=chave, http_options=types.HttpOptions(timeout=tempo_limite_ms))


def testar_chave(chave, cliente=None):
    """Lista os modelos para conferir a chave.

    Devolve {'situacao', 'mensagem', 'modelos'}, com situacao 'conectado', 'recusada' ou
    'instavel'. Em 'instavel' (Google lento) a IA continua ligada: só a chave recusada desliga.
    """
    try:
        cliente = cliente or criar_cliente(chave, TEMPO_TESTE_MS)
        modelos = sorted(
            m.name.removeprefix("models/") for m in cliente.models.list(config={"page_size": 100})
            if "generateContent" in (getattr(m, "supported_actions", None) or ["generateContent"]))
        return {"situacao": "conectado", "mensagem": f"Conectado ({len(modelos)} modelos disponíveis)",
                "modelos": modelos}
    except ImportError:
        return {"situacao": "recusada", "mensagem": MENSAGENS["biblioteca"], "modelos": []}
    except Exception as erro:
        if classificar_erro(erro) == "chave":
            return {"situacao": "recusada", "mensagem": MENSAGENS["chave"], "modelos": []}
        return {"situacao": "instavel", "modelos": [],
                "mensagem": "Não deu para confirmar a chave agora (Google lento). A IA continua ligada."}


def escolher_modelos(disponiveis, preferidos=MODELOS_PADRAO):
    """Ordem de tentativa: os preferidos que existem na conta; sem a lista, todos os preferidos."""
    escolhidos = [m for m in preferidos if m in (disponiveis or [])]
    return escolhidos or list(preferidos)


def gerar(cliente, prompt, modelos, sistema=None, json=False):
    """Pede uma resposta, trocando de modelo em caso de lentidão ou sobrecarga.

    Devolve (texto, modelo_usado). Erros viram ErroIA com mensagem amigável.
    """
    config = {"temperature": 0.2, "system_instruction": sistema}
    if json:
        config["response_mime_type"] = "application/json"
    for modelo in modelos:
        try:
            resposta = cliente.models.generate_content(model=modelo, contents=prompt, config=config)
            return (resposta.text or "").strip(), modelo
        except Exception as erro:
            tipo = classificar_erro(erro)
            if tipo == "chave":
                raise ErroIA(MENSAGENS["chave"], "chave") from erro
            if tipo == "outro":
                raise ErroIA(f"A IA devolveu um erro inesperado: {erro}") from erro
    raise ErroIA(MENSAGENS["indisponivel"], "indisponivel")


def perguntar(chave, prompt, modelos, sistema=None, json=False):
    """Atalho para as páginas: cria o cliente e chama gerar()."""
    try:
        cliente = criar_cliente(chave)
    except ImportError as erro:
        raise ErroIA(MENSAGENS["biblioteca"]) from erro
    return gerar(cliente, prompt, modelos, sistema=sistema, json=json)
