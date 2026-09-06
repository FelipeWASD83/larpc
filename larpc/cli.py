"""Linha de comando do larpc."""

import argparse
import os
import sys

from .executor import (
    FalhaDeCompilacao,
    formatar_erro_de_larp,
    gerar_c,
    rodar,
)
from .lexer import ErroDeLarp
from .msvc import SemCompilador
from .vocabulario import CONTRABANDO, PALAVRAS

COMANDOS = ("rodar", "ver", "c", "vocabulario")


def montar_parser():
    parser = argparse.ArgumentParser(
        prog="larpc",
        description="LarpC: C de verdade, vestido de cosplay de hacker.",
        epilog="sem comando nenhum, `larpc programa.larp` roda o programa.",
    )
    sub = parser.add_subparsers(dest="comando", required=True)

    rodar_cmd = sub.add_parser("rodar", help="compila e executa o programa")
    rodar_cmd.add_argument("arquivo")

    ver_cmd = sub.add_parser("ver", help="mostra o C gerado, sem compilar")
    ver_cmd.add_argument("arquivo")

    c_cmd = sub.add_parser("c", help="salva o C gerado num arquivo")
    c_cmd.add_argument("arquivo")
    c_cmd.add_argument(
        "-o", "--saida", help="caminho do .c (padrao: ao lado do .larp)"
    )

    sub.add_parser("vocabulario", help="imprime a tabela de palavras")
    return parser


def _com_comando_implicito(argumentos):
    """`larpc programa.larp` vale por `larpc rodar programa.larp`."""
    if argumentos and argumentos[0] not in COMANDOS:
        if not argumentos[0].startswith("-"):
            return ["rodar"] + list(argumentos)
    return list(argumentos)


def principal(argumentos=None):
    if argumentos is None:
        argumentos = sys.argv[1:]
    parser = montar_parser()
    if not argumentos:
        parser.print_help()
        return 2
    args = parser.parse_args(_com_comando_implicito(argumentos))

    if args.comando == "vocabulario":
        return _mostrar_vocabulario()

    caminho = args.arquivo
    if not os.path.isfile(caminho):
        print("nao achei o arquivo: " + caminho, file=sys.stderr)
        return 2

    try:
        if args.comando == "rodar":
            return rodar(caminho)
        if args.comando == "ver":
            print(gerar_c(caminho, alvo="exe").codigo_c)
            return 0
        if args.comando == "c":
            saida = args.saida or os.path.splitext(caminho)[0] + ".c"
            resultado = gerar_c(caminho, alvo="exe")
            with open(saida, "w", encoding="utf-8", newline="\n") as arquivo:
                arquivo.write(resultado.codigo_c)
            for aviso in resultado.avisos:
                print("aviso: " + aviso, file=sys.stderr)
            print("C gerado em " + saida)
            return 0
    except ErroDeLarp as erro:
        print(formatar_erro_de_larp(erro), file=sys.stderr)
        return 1
    except FalhaDeCompilacao as erro:
        print(str(erro), file=sys.stderr)
        return 1
    except SemCompilador as erro:
        print(str(erro), file=sys.stderr)
        return 3

    parser.print_help()
    return 2


def _mostrar_vocabulario():
    linhas = [(palavra, PALAVRAS[palavra]) for palavra in sorted(PALAVRAS)]
    linhas += [
        ("mainframe", "main"),
        ("payload(...)", "(...)"),
        ("%appdata% x", "#include <x.h>"),
        ("nullsec ...", "// ..."),
        ('nome("funcao")', 'funcao("nome")'),
    ]
    print("%-16s %s" % ("larpc", "C"))
    print("-" * 36)
    for palavra, virada in linhas:
        print("%-16s %s" % (palavra, virada))
    print()
    print("dentro do nome do swap:")
    print("%-16s %s" % ("_", "espaco"))
    print("%-16s %s" % ("__", "quebra de linha"))
    print("%-16s %s" % ("pct_d", "%d (pct_2f vira %.2f, pct_pct vira %%)"))
    print()
    print("C cru que o larpc recusa, e o termo que ele quer no lugar:")
    for cru in sorted(CONTRABANDO):
        print("  %-10s -> %s" % (cru, CONTRABANDO[cru]))
    return 0
