"""Leitura do .txt: fontes do Logix costumam vir em ANSI (cp1252), não em UTF-8."""

from pathlib import Path

# utf-8-sig aceita UTF-8 com e sem BOM; latin-1 nunca falha, por isso fica por último
CODIFICACOES = ("utf-8-sig", "cp1252", "latin-1")


def decodificar(conteudo):
    """Bytes do arquivo → (texto, codificação usada). Lido como UTF-8, um ANSI vira 'CÃ¡lculo'."""
    for codificacao in CODIFICACOES:
        try:
            texto = conteudo.decode(codificacao)
            return texto.replace("\r\n", "\n").replace("\r", "\n"), codificacao
        except UnicodeDecodeError:
            continue
    raise AssertionError("latin-1 decodifica qualquer sequência de bytes")


def ler_arquivo(caminho):
    """Lê um .txt do disco → (texto, codificação usada)."""
    return decodificar(Path(caminho).read_bytes())
