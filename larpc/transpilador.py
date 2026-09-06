"""Transpilador LarpC -> C.

Nao existe AST aqui, de proposito: o vocabulario do LarpC e uma troca 1:1
com o C, entao um lexer mais uma passada de reescrita de tokens da conta.
Erro de C de verdade (tipo errado, ponto e virgula faltando) escapa para o
compilador -- e o executor traduz a mensagem dele de volta para a linha do
.larp, porque o C gerado tem exatamente as mesmas linhas do fonte.
"""

import re

from .lexer import ErroDeLarp, tokenizar
from .vocabulario import (
    ASCII,
    CONTRABANDO,
    CONTROLE_C,
    MODIFICADORES,
    PALAVRAS,
    TIPOS,
)

# `pct_d` -> `%d`, `pct_2f` -> `%.2f` (precisao), `pct_w4d` -> `%4d`
# (largura, para alinhar coluna), `pct_pct` -> `%%`.
_RE_PCT = re.compile(r"pct_(pct|w[0-9]+l?[a-z]|[0-9]*l?[a-z])")
# `ascii_ponto` -> `.`. Os nomes mais longos primeiro, senao `ascii_abre`
# come o comeco de `ascii_abrechave`.
_RE_ASCII = re.compile(
    "ascii_(" + "|".join(sorted(ASCII, key=len, reverse=True)) + ")"
)
_RE_IDENT_C = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

_COLAR_ANTES = {")", "]", ",", ";", "++", "--", ".", "->"}
_COLAR_DEPOIS = {"(", "[", "!", "~", ".", "->"}

# Depois destes, um `-` ou `+` e sinal, nao operacao: sai `-1` e nao `- 1`.
_ANTES_DE_SINAL = {
    "(", "[", "{", ",", ";", "=", "==", "!=", "<", ">", "<=", ">=",
    "+", "-", "*", "/", "%", "&&", "||", "!", "?", ":",
    "+=", "-=", "*=", "/=", "%=", "return",
}

NOME_MAIN_DLL = "larpc_main_real"


class Resultado:
    """O C gerado mais o que o transpilador achou pelo caminho."""

    def __init__(self, codigo_c, avisos, tem_mainframe, mainframe_e_void):
        self.codigo_c = codigo_c
        self.avisos = avisos
        self.tem_mainframe = tem_mainframe
        self.mainframe_e_void = mainframe_e_void


class _Saida:
    __slots__ = ("texto", "linha", "colar_antes", "colar_depois")

    def __init__(self, texto, linha, colar_antes=False, colar_depois=False):
        self.texto = texto
        self.linha = linha
        self.colar_antes = colar_antes
        self.colar_depois = colar_depois


def decodificar_identificador(ident):
    """Traduz o identificador do swap para o texto que vai virar string C.

    Um underscore vira espaco. Dois ou mais viram quebra de linha (n
    underscores = n-1 quebras). `pct_d` e companhia viram especificador de
    formato, para caber printf formatado dentro da piada, e `ascii_ponto` e
    companhia viram os simbolos que nao cabem num identificador.
    """
    partes = []
    i = 0
    tamanho = len(ident)
    # Um escape termina uma palavra, entao `ascii_pontoascii_ponto` da `..`.
    # Sem isso nao daria para grudar dois simbolos sem um espaco no meio.
    apos_escape = False
    while i < tamanho:
        no_comeco_de_palavra = i == 0 or ident[i - 1] == "_" or apos_escape
        apos_escape = False
        if no_comeco_de_palavra and ident.startswith("pct_", i):
            casamento = _RE_PCT.match(ident, i)
            if casamento:
                spec = casamento.group(1)
                if spec == "pct":
                    partes.append("%%")
                elif spec[0] == "w":
                    partes.append("%" + spec[1:])
                elif spec[0].isdigit():
                    partes.append("%." + spec)
                else:
                    partes.append("%" + spec)
                i = casamento.end()
                apos_escape = True
                continue
        # `ascii_` vale em qualquer posicao, ao contrario de `pct_`: ninguem
        # escreve a palavra "ascii" no meio de uma frase por acaso, e sem
        # isso nao da para grudar simbolo em letra (`bordaascii_doispontos`).
        if ident.startswith("ascii_", i):
            casamento = _RE_ASCII.match(ident, i)
            if not casamento:
                raise ValueError(
                    "nao existe simbolo `ascii_%s`" % ident[i + 6:].split("_")[0]
                )
            partes.append(ASCII[casamento.group(1)])
            i = casamento.end()
            apos_escape = True
            continue
        if ident[i] == "_":
            fim = i
            while fim < tamanho and ident[fim] == "_":
                fim += 1
            quantidade = fim - i
            partes.append(" " if quantidade == 1 else "\\n" * (quantidade - 1))
            i = fim
            continue
        partes.append(ident[i])
        i += 1
    return "".join(partes)


def transpilar(fonte, arquivo=None, alvo="exe"):
    """Traduz fonte LarpC para C. `alvo` e 'exe' ou 'dll'."""
    tokens = tokenizar(fonte, arquivo)
    saidas = []
    avisos = []
    estado = {"tem_appdata": False, "tem_mainframe": False, "mainframe_void": False}

    nome_do_main = "main" if alvo == "exe" else NOME_MAIN_DLL

    i = 0
    total = len(tokens)
    while i < total:
        tok = tokens[i]

        if tok.tipo == "FIM":
            break

        if tok.tipo == "APPDATA":
            i = _traduzir_appdata(tokens, i, saidas, estado, arquivo)
            continue

        if tok.tipo == "COMENTARIO":
            texto = tok.texto[len("nullsec"):]
            saidas.append(_Saida("//" + texto, tok.linha))
            i += 1
            continue

        # O swap tem que ser testado antes da traducao de palavra, porque
        # `based("printf")` e swap, nao o literal 1.
        consumidos = _tentar_swap(tokens, i, saidas, arquivo)
        if consumidos:
            i += consumidos
            continue

        if tok.tipo == "IDENT" and tok.texto == "payload":
            if not (i + 1 < total and tokens[i + 1].e("(")):
                raise ErroDeLarp(
                    "payload sozinho nao serve de nada: use payload(...) "
                    "logo depois do nome da funcao",
                    tok.linha,
                    tok.coluna,
                    arquivo,
                )
            i += 1  # o parentese seguinte e emitido normalmente
            continue

        if tok.tipo == "IDENT" and tok.texto == "mainframe":
            estado["tem_mainframe"] = True
            if i > 0 and tokens[i - 1].e("zeroday"):
                estado["mainframe_void"] = True
            _emitir(saidas, nome_do_main, tok.linha)
            i += 1
            continue

        if tok.tipo == "FORCE" or (tok.tipo == "IDENT" and tok.texto in PALAVRAS):
            chave = "--force" if tok.tipo == "FORCE" else tok.texto
            if chave == "sudo" and _abre_funcao_sem_payload(tokens, i):
                _emitir(saidas, "(", tok.linha, colar_antes=True, colar_depois=True)
                _emitir(saidas, "void", tok.linha)
                _emitir(saidas, ")", tok.linha, colar_antes=True)
            traducao = PALAVRAS[chave]
            # `doxx x` tem que sair `&x`, nao `& x`.
            cola_no_proximo = True if chave == "doxx" else None
            _emitir(saidas, traducao, tok.linha, colar_depois=cola_no_proximo)
            i += 1
            continue

        if tok.tipo == "IDENT" and tok.texto in CONTRABANDO:
            raise ErroDeLarp(
                "`%s` e C cru, e C cru fura o personagem. Aqui isso se escreve `%s`."
                % (tok.texto, CONTRABANDO[tok.texto]),
                tok.linha,
                tok.coluna,
                arquivo,
            )

        _emitir(saidas, tok.texto, tok.linha)
        i += 1

    if not estado["tem_appdata"]:
        avisos.append("cade seu include, bro? nenhum %appdata% neste arquivo.")
    if not estado["tem_mainframe"]:
        raise ErroDeLarp(
            "cade o mainframe? sem ele nao tem por onde comecar o programa.",
            tokens[-1].linha,
            1,
            arquivo,
        )

    codigo = _montar(saidas, fonte)
    if alvo == "dll":
        codigo += _rodape_dll(estado["mainframe_void"])

    return Resultado(codigo, avisos, estado["tem_mainframe"], estado["mainframe_void"])


def _emitir(saidas, texto, linha, colar_antes=None, colar_depois=None):
    """Emite um pedaco de C ja decidindo se ele cola no vizinho.

    Sem isso o C sai com `if ( x )` e `printf("oi" )`, que compila mas e feio
    de ler -- e o C gerado e feito para ser lido.
    """
    if colar_antes is None:
        colar_antes = texto in _COLAR_ANTES
    if colar_depois is None:
        colar_depois = texto in _COLAR_DEPOIS
    if texto in ("(", "[") and not colar_antes and saidas:
        anterior = saidas[-1]
        cola = anterior.texto not in CONTROLE_C and (
            _RE_IDENT_C.match(anterior.texto) or anterior.texto in (")", "]")
        )
        colar_antes = bool(cola)
    if texto in ("-", "+") and not colar_depois:
        vazio = not saidas
        colar_depois = vazio or saidas[-1].texto in _ANTES_DE_SINAL
    saidas.append(_Saida(texto, linha, colar_antes, colar_depois))


def _traduzir_appdata(tokens, i, saidas, estado, arquivo):
    tok = tokens[i]
    if tok.coluna != _primeira_coluna_da_linha(tokens, tok.linha):
        raise ErroDeLarp(
            "%appdata% precisa ser a primeira coisa da linha -- e diretiva, "
            "nao expressao.",
            tok.linha,
            tok.coluna,
            arquivo,
        )
    if i + 1 >= len(tokens):
        raise ErroDeLarp(
            "%appdata% sem nada depois: incluir o que?",
            tok.linha,
            tok.coluna,
            arquivo,
        )
    alvo = tokens[i + 1]
    if alvo.tipo == "IDENT":
        texto = "#include <%s.h>" % alvo.texto
    elif alvo.tipo == "STRING":
        texto = "#include %s" % alvo.texto
    else:
        raise ErroDeLarp(
            "depois de %appdata% vem o nome do header "
            "(ex: `%appdata% stdio`), nao " + repr(alvo.texto),
            alvo.linha,
            alvo.coluna,
            arquivo,
        )
    estado["tem_appdata"] = True
    saidas.append(_Saida(texto, tok.linha))
    return i + 2


def _tentar_swap(tokens, i, saidas, arquivo):
    """Reconhece o swap: `ident("funcao")` e `ident("funcao", args...)`.

    Devolve quantos tokens foram consumidos, ou 0 se nao for swap.
    """
    tok = tokens[i]
    if tok.tipo != "IDENT":
        return 0
    if i + 3 >= len(tokens):
        return 0
    if not tokens[i + 1].e("("):
        return 0
    alvo = tokens[i + 2]
    if alvo.tipo != "STRING":
        return 0
    fechamento = tokens[i + 3]
    if not (fechamento.e(")") or fechamento.e(",")):
        return 0

    nome_real = alvo.texto[1:-1]
    if not _RE_IDENT_C.match(nome_real):
        raise ErroDeLarp(
            "o que vai entre aspas e o nome da funcao de verdade, e "
            + repr(nome_real)
            + " nao e um nome valido.",
            alvo.linha,
            alvo.coluna,
            arquivo,
        )

    try:
        conteudo = decodificar_identificador(tok.texto)
    except ValueError as erro:
        raise ErroDeLarp(str(erro), tok.linha, tok.coluna, arquivo)

    _emitir(saidas, nome_real, tok.linha)
    _emitir(saidas, "(", tok.linha, colar_antes=True, colar_depois=True)
    _emitir(saidas, '"' + conteudo + '"', tok.linha)
    return 3  # o `)` ou `,` continua no fluxo normal


def _abre_funcao_sem_payload(tokens, i):
    """`script mainframe sudo` e funcao sem parametro: falta o `(void)`."""
    if i < 2:
        return False
    nome = tokens[i - 1]
    tipo = tokens[i - 2]
    if nome.tipo != "IDENT" or tipo.tipo != "IDENT":
        return False
    if tipo.texto in TIPOS:
        return True
    if tipo.texto in MODIFICADORES and i >= 3 and tokens[i - 3].texto in TIPOS:
        return True
    return False


def _primeira_coluna_da_linha(tokens, linha):
    for tok in tokens:
        if tok.linha == linha:
            return tok.coluna
    return 1


def _montar(saidas, fonte):
    """Junta as saidas respeitando as linhas originais do .larp.

    O C sai com o mesmo numero de linhas do fonte -- e por isso que erro do
    compilador aponta direto para a linha certa do .larp.
    """
    linhas_fonte = fonte.split("\n")
    total = len(linhas_fonte)
    baldes = [[] for _ in range(total + 2)]
    for saida in saidas:
        if saida.linha < len(baldes):
            baldes[saida.linha].append(saida)

    linhas_c = []
    for numero in range(1, total + 1):
        itens = baldes[numero]
        if not itens:
            linhas_c.append("")
            continue
        original = linhas_fonte[numero - 1]
        indentacao = original[: len(original) - len(original.lstrip())]
        partes = [itens[0].texto]
        for indice in range(1, len(itens)):
            anterior = itens[indice - 1]
            atual = itens[indice]
            if anterior.colar_depois or atual.colar_antes:
                partes.append(atual.texto)
            else:
                partes.append(" " + atual.texto)
        linhas_c.append(indentacao + "".join(partes))

    return "\n".join(linhas_c)


def _rodape_dll(mainframe_e_void):
    """Ponte para o executor.

    O Smart App Control do Windows barra .exe compilado na hora, entao o
    programa vira DLL e quem executa e o python.
    """
    if mainframe_e_void:
        chamada = "    " + NOME_MAIN_DLL + "();\n    codigo = 0;"
    else:
        chamada = "    codigo = " + NOME_MAIN_DLL + "();"
    return (
        "\n\n/* ---- ponte do larpc: o programa roda como DLL ---- */\n"
        "#include <stdio.h>\n"
        "__declspec(dllimport) unsigned int __stdcall GetConsoleOutputCP(void);\n"
        "__declspec(dllimport) int __stdcall SetConsoleOutputCP(unsigned int);\n"
        "__declspec(dllexport) int larpc_mainframe(void) {\n"
        "    unsigned int cp_antiga = GetConsoleOutputCP();\n"
        "    int codigo;\n"
        "    SetConsoleOutputCP(65001);\n"
        "    setvbuf(stdout, NULL, _IONBF, 0);\n"
        "    setvbuf(stderr, NULL, _IONBF, 0);\n"
        + chamada
        + "\n    if (cp_antiga) SetConsoleOutputCP(cp_antiga);\n"
        "    return codigo;\n}\n"
    )
