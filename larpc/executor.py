"""Transpila, compila e executa um programa LarpC.

O programa vira uma DLL e quem executa e o proprio python. O motivo esta
documentado no CLAUDE.md do projeto: o Smart App Control desta maquina
bloqueia qualquer .exe compilado na hora, mas deixa passar DLL carregada por
um processo assinado -- e o python.exe e assinado.
"""

import ctypes
import hashlib
import os
import re
import sys

from .lexer import ErroDeLarp
from .msvc import compilar_dll
from .transpilador import transpilar

RAIZ_DO_PROJETO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTA_DE_BUILD = os.path.join(RAIZ_DO_PROJETO, "_build")

_RE_DIAGNOSTICO = re.compile(
    r"^(?P<arquivo>.+?)\((?P<linha>\d+)\)\s*:\s*"
    r"(?P<nivel>fatal error|error|warning)\s+(?P<codigo>[A-Z]+\d+)\s*:\s*"
    r"(?P<mensagem>.*)$"
)


class FalhaDeCompilacao(Exception):
    """O C gerado nao compilou."""


def ler(caminho):
    """Le o .larp tolerando BOM e arquivo salvo em ANSI pelo Bloco de Notas."""
    with open(caminho, "rb") as arquivo:
        dados = arquivo.read()
    for codec in ("utf-8-sig", "cp1252"):
        try:
            return dados.decode(codec)
        except UnicodeDecodeError:
            continue
    return dados.decode("utf-8", errors="replace")


def gerar_c(caminho_larp, alvo="exe"):
    """Devolve o Resultado do transpilador para um arquivo .larp."""
    fonte = ler(caminho_larp)
    return transpilar(fonte, arquivo=os.path.basename(caminho_larp), alvo=alvo)


def compilar(caminho_larp, mostrar_avisos=True):
    """Transpila e compila. Devolve o caminho da DLL pronta para carregar."""
    nome = os.path.splitext(os.path.basename(caminho_larp))[0]
    resultado = gerar_c(caminho_larp, alvo="dll")

    if mostrar_avisos:
        for aviso in resultado.avisos:
            print("aviso: " + aviso, file=sys.stderr)

    digest = hashlib.sha256(resultado.codigo_c.encode("utf-8")).hexdigest()[:10]
    os.makedirs(PASTA_DE_BUILD, exist_ok=True)
    caminho_c = os.path.join(PASTA_DE_BUILD, "%s-%s.c" % (nome, digest))
    caminho_dll = os.path.join(PASTA_DE_BUILD, "%s-%s.dll" % (nome, digest))

    if os.path.isfile(caminho_dll) and os.path.isfile(caminho_c):
        return caminho_dll

    _limpar_versoes_antigas(nome, digest)

    # BOM para o MSVC nao ter duvida de que o arquivo e UTF-8.
    with open(caminho_c, "w", encoding="utf-8-sig", newline="\n") as arquivo:
        arquivo.write(resultado.codigo_c)

    deu_certo, saida = compilar_dll(caminho_c, caminho_dll, PASTA_DE_BUILD)
    if not deu_certo or not os.path.isfile(caminho_dll):
        raise FalhaDeCompilacao(
            traduzir_diagnosticos(saida, os.path.basename(caminho_larp), nome, digest)
        )

    avisos = traduzir_diagnosticos(
        saida, os.path.basename(caminho_larp), nome, digest, so_avisos=True
    )
    if avisos and mostrar_avisos:
        print(avisos, file=sys.stderr)

    return caminho_dll


def rodar(caminho_larp, mostrar_avisos=True):
    """Compila e executa. Devolve o codigo de saida do programa."""
    caminho_dll = compilar(caminho_larp, mostrar_avisos=mostrar_avisos)
    sys.stdout.flush()
    sys.stderr.flush()
    biblioteca = ctypes.CDLL(caminho_dll)
    ponto_de_entrada = biblioteca.larpc_mainframe
    ponto_de_entrada.restype = ctypes.c_int
    ponto_de_entrada.argtypes = []
    return ponto_de_entrada()


def traduzir_diagnosticos(saida, nome_larp, nome, digest, so_avisos=False):
    """Reescreve o berro do MSVC apontando para o .larp, no tom da casa.

    O C gerado tem exatamente as mesmas linhas do .larp, entao o numero que
    o compilador reporta ja e o numero certo -- so o nome do arquivo muda.
    """
    linhas_uteis = []
    nome_do_c = "%s-%s.c" % (nome, digest)
    for linha in saida.splitlines():
        limpa = linha.strip()
        if not limpa or limpa == nome_do_c:
            continue
        casamento = _RE_DIAGNOSTICO.match(limpa)
        if casamento:
            nivel = casamento.group("nivel")
            if so_avisos and nivel != "warning":
                continue
            if not so_avisos and nivel == "warning":
                continue
            rotulo = "aviso" if nivel == "warning" else "erro"
            linhas_uteis.append(
                "  %s %s:%s: %s [%s]"
                % (
                    rotulo,
                    nome_larp,
                    casamento.group("linha"),
                    casamento.group("mensagem"),
                    casamento.group("codigo"),
                )
            )
        elif not so_avisos and "LNK" in limpa:
            linhas_uteis.append("  erro de link: " + limpa)

    if not linhas_uteis:
        if so_avisos:
            return ""
        return "seu opsec falhou e nem deu para saber onde:\n" + saida.strip()

    if so_avisos:
        cabecalho = "seu opsec ta vazando (o C compilou, mas reclamou):"
    else:
        cabecalho = "seu opsec falhou:"
    return cabecalho + "\n" + "\n".join(linhas_uteis)


def formatar_erro_de_larp(erro):
    """Mensagem de erro do transpilador, no tom da linguagem."""
    if not isinstance(erro, ErroDeLarp):
        return str(erro)
    return "seu opsec falhou:\n  erro %s:%d:%d: %s" % (
        erro.arquivo or "<larp>",
        erro.linha,
        erro.coluna,
        erro.mensagem,
    )


def _limpar_versoes_antigas(nome, digest_atual):
    """Apaga builds antigos do mesmo programa. DLL travada e ignorada."""
    if not os.path.isdir(PASTA_DE_BUILD):
        return
    prefixo = nome + "-"
    for arquivo in os.listdir(PASTA_DE_BUILD):
        if not arquivo.startswith(prefixo):
            continue
        if digest_atual in arquivo:
            continue
        if not arquivo.endswith((".c", ".dll", ".obj", ".lib", ".exp")):
            continue
        try:
            os.remove(os.path.join(PASTA_DE_BUILD, arquivo))
        except OSError:
            pass
