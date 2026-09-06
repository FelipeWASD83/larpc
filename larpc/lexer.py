"""Lexer do LarpC.

Quebra o fonte em tokens guardando a linha e a coluna de cada um. O
transpilador depende disso para emitir C com o mesmo numero de linhas do
.larp original -- e assim traduzir erro do compilador de volta para a linha
que o cara escreveu.
"""

import re

# Ordem importa: '--force' antes de '--', '%appdata%' antes de '%',
# 'nullsec' antes de identificador comum.
_ESPECIFICACAO = [
    ("APPDATA", r"%appdata%"),
    ("COMENTARIO", r"nullsec(?![A-Za-z0-9_])[^\n]*"),
    ("FORCE", r"--force(?![A-Za-z0-9_])"),
    ("STRING", r'"(?:[^"\\\n]|\\.)*"'),
    ("CARACTERE", r"'(?:[^'\\\n]|\\.)*'"),
    ("NUMERO", r"(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?[fFuUlL]*"),
    ("IDENT", r"[A-Za-z_][A-Za-z0-9_]*"),
    ("ESPACO", r"[ \t\r]+"),
    ("QUEBRA", r"\n"),
    (
        "SIMBOLO",
        r"->|\+\+|--|<<=|>>=|<<|>>|<=|>=|==|!=|&&|\|\||\+=|-=|\*=|/=|%=|&=|\|=|\^=|"
        r"[-+*/%=<>!&|^~?:;,.()\[\]{}]",
    ),
]

_REGEX = re.compile(
    "|".join("(?P<%s>%s)" % (nome, padrao) for nome, padrao in _ESPECIFICACAO)
)


class ErroDeLarp(Exception):
    """Erro de sintaxe do LarpC, com posicao no fonte."""

    def __init__(self, mensagem, linha, coluna=1, arquivo=None):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.linha = linha
        self.coluna = coluna
        self.arquivo = arquivo

    def __str__(self):
        onde = self.arquivo or "<larp>"
        return "%s:%d:%d: %s" % (onde, self.linha, self.coluna, self.mensagem)


class Token:
    __slots__ = ("tipo", "texto", "linha", "coluna")

    def __init__(self, tipo, texto, linha, coluna):
        self.tipo = tipo
        self.texto = texto
        self.linha = linha
        self.coluna = coluna

    def e(self, texto):
        return self.texto == texto

    def __repr__(self):
        return "Token(%s, %r, l%d)" % (self.tipo, self.texto, self.linha)


def tokenizar(fonte, arquivo=None):
    """Devolve a lista de tokens do fonte, sem espacos e sem quebras de linha.

    A linha de cada token fica guardada no proprio token, entao a quebra de
    linha nao precisa virar token.
    """
    tokens = []
    linha = 1
    inicio_da_linha = 0
    pos = 0
    tamanho = len(fonte)

    while pos < tamanho:
        casamento = _REGEX.match(fonte, pos)
        if casamento is None:
            coluna = pos - inicio_da_linha + 1
            raise ErroDeLarp(
                "caractere que nao existe no vocabulario: %r" % fonte[pos],
                linha,
                coluna,
                arquivo,
            )

        tipo = casamento.lastgroup
        texto = casamento.group()

        if tipo == "QUEBRA":
            linha += 1
            inicio_da_linha = casamento.end()
        elif tipo != "ESPACO":
            coluna = pos - inicio_da_linha + 1
            tokens.append(Token(tipo, texto, linha, coluna))

        pos = casamento.end()

    tokens.append(Token("FIM", "", linha, 1))
    return tokens
