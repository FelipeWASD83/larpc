"""O dicionario do LarpC: cada palavra do cosplay e o C que ela vira.

Isto aqui e a fonte de verdade do vocabulario. Mexeu aqui, mexeu na
linguagem -- e o README e o CLAUDE.md do projeto precisam acompanhar.
"""

# Palavra LarpC -> texto C. Troca direta, sem contexto.
PALAVRAS = {
    "sudo": "{",
    "--force": "}",
    "opsec": ";",
    "probably": "if",
    "cope": "else",
    "zeroday": "void",
    "exfiltrate": "return",
    "script": "int",
    "persist": "continue",
    "unplug": "break",
    "trustmebro": "const",
    "doomscroll": "while",
    "grindset": "for",
    "npc": "char",
    "vibes": "float",
    "based": "1",
    "cringe": "0",
    "ghost": "static",
    "doxx": "&",
}

# Simbolos que nao cabem num identificador, para usar dentro do nome do swap:
# `ascii_ponto` vira `.`. Sem isso nao da para desenhar nada em texto -- foi
# o xadrez que cobrou, porque tabuleiro precisa de ponto, barra e tubo.
ASCII = {
    "espaco": " ",
    "ponto": ".",
    "virgula": ",",
    "doispontos": ":",
    "pontoevirgula": ";",
    "mais": "+",
    "menos": "-",
    "vezes": "*",
    "barra": "/",
    "contrabarra": "\\\\",
    "igual": "=",
    "maior": ">",
    "menor": "<",
    "hash": "#",
    "tubo": "|",
    "til": "~",
    "circunflexo": "^",
    "abre": "(",
    "fecha": ")",
    "abrecolchete": "[",
    "fechacolchete": "]",
    "abrechave": "{",
    "fechachave": "}",
    "aspas": '\\"',
    "apostrofo": "'",
    "exclamacao": "!",
    "interrogacao": "?",
    "arroba": "@",
    "cifrao": "$",
    "ecomercial": "&",
    "sublinhado": "_",
    "tab": "\\t",
}

# Palavras que precisam de tratamento com contexto, tratadas no transpilador:
#   mainframe   -> main (ou larpc_main_real, quando o alvo e DLL)
#   payload(    -> (          lista de parametros
#   %appdata% x -> #include <x.h>
#   nullsec ... -> // ...
#   ident("f")  -> f("ident")  o swap
PALAVRAS_COM_CONTEXTO = ("mainframe", "payload")

# Tipos que podem abrir uma definicao de funcao. Serve para descobrir que
# `script mainframe sudo` e uma funcao sem parametros e precisa de `(void)`.
TIPOS = {"script", "vibes", "npc", "zeroday"}

# Modificadores que podem vir antes do tipo numa definicao de funcao.
MODIFICADORES = {"ghost", "trustmebro"}

# Palavras C de controle: depois delas o `(` leva espaco, para o C gerado
# sair `if (x)` e nao `if(x)`.
CONTROLE_C = {"if", "for", "while", "switch", "return", "else", "do"}

# Palavras que o LarpC recusa: sao C cru, e escrever C cru aqui e furar o
# personagem. A mensagem de erro diz o termo certo.
CONTRABANDO = {
    "int": "script",
    "char": "npc",
    "float": "vibes",
    "void": "zeroday",
    "return": "exfiltrate",
    "if": "probably",
    "else": "cope",
    "while": "doomscroll",
    "for": "grindset",
    "break": "unplug",
    "continue": "persist",
    "const": "trustmebro",
    "static": "ghost",
    "main": "mainframe",
    "true": "based",
    "false": "cringe",
}
