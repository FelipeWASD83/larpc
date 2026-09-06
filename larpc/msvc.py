"""Acha o compilador da Microsoft e compila o C gerado.

Aqui nao tem gcc: o unico compilador C desta maquina e o `cl` do Visual
Studio Build Tools 2022. E ele so serve porque `cl.exe` e assinado pela
Microsoft -- o Smart App Control barraria qualquer gcc baixado avulso, do
mesmo jeito que barra o .exe que o proprio cl produz.

O ambiente do `vcvars64.bat` demora uns segundos para montar, entao ele e
capturado uma vez e guardado em cache. Rodar um programa LarpC nao pode
custar dois segundos de batch toda vez.
"""

import json
import os
import shutil
import subprocess

_CAMINHOS_CONHECIDOS = [
    r"C:\Program Files\Microsoft Visual Studio\2022\BuildTools",
    r"C:\Program Files\Microsoft Visual Studio\2022\Community",
    r"C:\Program Files\Microsoft Visual Studio\2022\Professional",
    r"C:\Program Files\Microsoft Visual Studio\2022\Enterprise",
    r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools",
    r"C:\Program Files (x86)\Microsoft Visual Studio\2022\Community",
    r"C:\Program Files (x86)\Microsoft Visual Studio\2022\Professional",
    r"C:\Program Files (x86)\Microsoft Visual Studio\2022\Enterprise",
]

_VSWHERE = (
    r"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
)

_SUFIXO_VCVARS = r"VC\Auxiliary\Build\vcvars64.bat"


class SemCompilador(Exception):
    """Nao ha `cl` nesta maquina."""


def achar_vcvars():
    """Devolve o caminho do vcvars64.bat, ou levanta SemCompilador."""
    if os.path.isfile(_VSWHERE):
        try:
            saida = subprocess.run(
                [
                    _VSWHERE,
                    "-latest",
                    "-products",
                    "*",
                    "-requires",
                    "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
                    "-property",
                    "installationPath",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            raiz = saida.stdout.strip().splitlines()
            if raiz:
                candidato = os.path.join(raiz[0], _SUFIXO_VCVARS)
                if os.path.isfile(candidato):
                    return candidato
        except (OSError, subprocess.SubprocessError):
            pass

    for raiz in _CAMINHOS_CONHECIDOS:
        candidato = os.path.join(raiz, _SUFIXO_VCVARS)
        if os.path.isfile(candidato):
            return candidato

    raise SemCompilador(
        "nao achei o compilador da Microsoft (vcvars64.bat).\n"
        "instale o Visual Studio Build Tools 2022 com o workload "
        '"Desenvolvimento para desktop com C++".'
    )


def ambiente(pasta_de_cache):
    """Devolve o dicionario de ambiente com o `cl` no PATH, usando cache."""
    vcvars = achar_vcvars()
    assinatura = "%s|%d" % (vcvars, int(os.path.getmtime(vcvars)))
    arquivo_cache = os.path.join(pasta_de_cache, "msvc-env.json")

    if os.path.isfile(arquivo_cache):
        try:
            with open(arquivo_cache, "r", encoding="utf-8") as arquivo:
                guardado = json.load(arquivo)
            if guardado.get("assinatura") == assinatura:
                return guardado["ambiente"]
        except (OSError, ValueError, KeyError):
            pass

    capturado = _capturar_ambiente(vcvars)
    os.makedirs(pasta_de_cache, exist_ok=True)
    try:
        with open(arquivo_cache, "w", encoding="utf-8") as arquivo:
            json.dump(
                {"assinatura": assinatura, "ambiente": capturado},
                arquivo,
                indent=2,
            )
    except OSError:
        pass
    return capturado


def _capturar_ambiente(vcvars):
    # Comando vai como string, nao como lista: o quoting que o Python faz
    # para listas escapa aspas com barra, e o cmd nao entende barra.
    comando = 'cmd.exe /s /c ""%s" >nul 2>&1 && set"' % vcvars
    resultado = subprocess.run(
        comando,
        capture_output=True,
        timeout=180,
    )
    texto = _decodificar(resultado.stdout)
    capturado = {}
    for linha in texto.splitlines():
        if "=" in linha:
            chave, _, valor = linha.partition("=")
            capturado[chave] = valor
    if "PATH" not in capturado and "Path" not in capturado:
        raise SemCompilador(
            "o vcvars64.bat rodou mas nao devolveu ambiente nenhum:\n"
            + texto[-800:]
        )
    return capturado


def compilar_dll(caminho_c, caminho_dll, pasta_de_build):
    """Compila o .c como DLL. Devolve (deu_certo, saida_do_compilador).

    O `cl` roda com cwd na pasta de build e recebe so nomes de arquivo, sem
    caminho: a pasta deste projeto tem espaco no meio ("Claude Code") e
    argumento com espaco vira briga de aspas com o compilador.
    """
    env = ambiente(pasta_de_build)
    comando = [
        _achar_cl(env),
        "/nologo",
        "/W3",
        "/LD",
        "/utf-8",
        "/D_CRT_SECURE_NO_WARNINGS",
        os.path.basename(caminho_c),
        "/Fe:" + os.path.basename(caminho_dll),
    ]
    resultado = subprocess.run(
        comando,
        cwd=os.path.dirname(caminho_c),
        env=env,
        capture_output=True,
        timeout=180,
    )
    saida = _decodificar(resultado.stdout) + _decodificar(resultado.stderr)
    return resultado.returncode == 0, saida


def _achar_cl(env):
    """Caminho completo do cl.exe dentro do ambiente do vcvars.

    Precisa ser o caminho completo: o Windows procura o executavel no PATH
    do processo que chama, nao no `env` que a gente passa para o filho.
    """
    caminho = ""
    for chave, valor in env.items():
        if chave.upper() == "PATH":
            caminho = valor
            break
    achado = shutil.which("cl.exe", path=caminho)
    if not achado:
        raise SemCompilador(
            "o ambiente do Visual Studio carregou, mas nao tem cl.exe dentro "
            "dele. Falta o workload de C++ nos Build Tools."
        )
    return achado


def _decodificar(dados):
    if not dados:
        return ""
    for codec in ("utf-8", "oem", "cp1252"):
        try:
            return dados.decode(codec)
        except (UnicodeDecodeError, LookupError):
            continue
    return dados.decode("utf-8", errors="replace")
