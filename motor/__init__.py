"""Motor de teste em Python puro: ε, PCE, AVL e oráculo. A IA nunca calcula nada aqui."""

from decimal import Context, localcontext
from functools import wraps


def exato(funcao):
    """Executa a função com 80 dígitos de precisão decimal.

    O padrão do Python é 28 dígitos, pouco para DECIMAL(32,x) e para os produtos que estouram
    a saída. O contexto decimal vale só para a thread atual, por isso é aplicado em cada função.
    """
    @wraps(funcao)
    def com_precisao(*args, **kwargs):
        with localcontext(Context(prec=80)):
            return funcao(*args, **kwargs)
    return com_precisao
