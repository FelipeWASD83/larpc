# LarpC

C de verdade, vestido de cosplay de hacker.

```
%appdata% stdio

script mainframe sudo
    i_use_arch_btw__("printf") opsec
    exfiltrate 0 opsec
--force
```

vira, no C gerado:

```c
#include <stdio.h>

int main(void) {
    printf("i use arch btw\n");
    return 0;
}
```

E aí compila e roda de verdade — o que executa é código de máquina, não
interpretador.

## Usando

```
larpc programa.larp            roda
larpc ver programa.larp        mostra o C gerado
larpc c programa.larp          salva o C num arquivo
larpc vocabulario              a tabela de palavras
```

O `larpc.bat` funciona de qualquer pasta. Precisa de Python e do Visual
Studio Build Tools 2022 com o workload de C++.

Exemplos prontos em `exemplos/`:

```
larpc exemplos\ola.larp
larpc exemplos\calculadora.larp
larpc exemplos\xadrez.larp
```

O `xadrez.larp` e um xadrez de tabuleiro infinito contra IA, escrito inteiro
em LarpC -- as regras, o minimax e a tela. Ver `exemplos/xadrez.md`.

## O truque do swap

O coração da linguagem: você escreve o texto como se fosse o nome da função,
e o nome da função entre aspas. O transpilador inverte.

```
total_pct_d_itens__("printf", n)     ->   printf("total %d itens\n", n)
```

Dentro do nome: `_` vira espaço, `__` vira quebra de linha, `pct_d` vira
`%d` (`pct_2f` vira `%.2f`, `pct_w4d` vira `%4d`) e `ascii_ponto` vira `.` —
esse último cobre todos os símbolos que não cabem num identificador, de
`ascii_espaco` a `ascii_abrechave`. `larpc vocabulario` lista tudo.

## As palavras

`sudo` `{` · `--force` `}` · `opsec` `;` · `probably` `if` · `cope` `else` ·
`script` `int` · `vibes` `float` · `npc` `char` · `zeroday` `void` ·
`mainframe` `main` · `exfiltrate` `return` · `doomscroll` `while` ·
`grindset` `for` · `unplug` `break` · `persist` `continue` ·
`trustmebro` `const` · `ghost` `static` · `based`/`cringe` `1`/`0` ·
`doxx` `&` · `payload(...)` parâmetros · `nullsec` comentário ·
`%appdata% stdio` `#include <stdio.h>`

`larpc vocabulario` imprime a lista completa.

Escrever C cru (`int`, `if`, `return`) dá erro de propósito — o personagem
não pode furar.

## Por que roda como DLL

O Smart App Control desta máquina bloqueia todo `.exe` compilado na hora,
mesmo os seus. Mas deixa passar DLL carregada por um processo assinado.
Então o programa vira DLL e o `python.exe` executa. O C que o `larpc ver`
mostra é portável e sem essa gambiarra — ela só existe no que vai para o
compilador. Detalhes no `CLAUDE.md`.

## Testes

```
python -m unittest discover -s testes
```
