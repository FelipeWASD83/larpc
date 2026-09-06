# CLAUDE.md — larpc

Instruções para qualquer sessão aberta nesta pasta. Vale mais que o
`CLAUDE.md` da raiz. O que o Felipe disser na conversa vale mais que os dois.

---

## 1. O que é

**LarpC é C de verdade com o vocabulário trocado por gíria de gente que finge
entender de segurança.** O `.larp` é transpilado para C, compilado pelo
compilador da Microsoft e executado. Não é interpretador, não é emulação: o
que roda é código de máquina compilado a partir do C gerado.

O nome brinca com os dois sentidos de "LARP": o antigo (*Live Action Role
Play*, encenar um personagem) e o atual de internet (fingir domínio que não
se tem). Escrever nessa linguagem é as duas coisas ao mesmo tempo.

**A piada só funciona se o C por baixo for real.** Nada de "quase C", nada de
subconjunto que finge compilar. Se uma construção não cabe no vocabulário, o
certo é ampliar o vocabulário — não afrouxar a transpilação.

---

## 2. A decisão que explica a arquitetura

**Esta máquina não roda `.exe` compilado na hora.** O Smart App Control do
Windows 11 está ligado (`HKLM\SYSTEM\CurrentControlSet\Control\CI\Policy`,
`VerifiedAndReputablePolicyState = 1`) e barra qualquer executável sem
assinatura — inclusive os que o próprio usuário compila. Testado: um
`hello world` compilado pelo `cl` local morre com *"Uma política de Controle
de Aplicativo bloqueou este arquivo"*.

Consequências, todas verificadas nesta máquina em 06/09/2026:

- **Instalar gcc/MinGW não resolve** — o `gcc.exe` baixado seria barrado do
  mesmo jeito. O `cl` da Microsoft só funciona porque é assinado por ela.
- **DLL passa.** Uma DLL não assinada carregada por um processo assinado
  (`python.exe`) executa normalmente: `printf` sai no console, `scanf` lê o
  stdin, o valor de retorno chega no Python.
- **Por isso o programa LarpC roda como DLL**, não como `.exe`. O
  `mainframe` vira `larpc_main_real` e o transpilador anexa uma ponte
  `larpc_mainframe` exportada, que o `executor.py` carrega com `ctypes`.

Desligar o Smart App Control resolveria — mas é **irreversível** (só volta
reinstalando o Windows) e é decisão do Felipe, não da sessão. Ele optou pela
DLL. **Não proponha desligar de novo sem ele levantar o assunto.**

O modo `larpc ver` / `larpc c` emite C **portável**, com `main` normal e sem
nada de Windows: é o C que ele pode levar para qualquer lugar. O truque da
DLL só aparece no alvo `dll`.

---

## 3. Como rodar

```
larpc programa.larp          compila e executa (igual a `larpc rodar`)
larpc ver programa.larp      mostra o C gerado, sem compilar
larpc c programa.larp -o x.c salva o C gerado
larpc vocabulario            imprime a tabela de palavras
```

O `larpc.bat` funciona de qualquer pasta. Sem ele:
`python -m larpc programa.larp` de dentro desta pasta.

Testes: `python -m unittest discover -s testes` na raiz do projeto. Os testes
de ponta a ponta compilam de verdade (~5s no primeiro, ~0.2s depois, por
causa do cache) e se pulam sozinhos numa máquina sem `cl`.

**Não existe entrada no `.claude/launch.json` da raiz e não deve existir:**
isso aqui é CLI, não servidor web. Não há preview para subir.

---

## 4. Como o código está dividido

| Arquivo | O que faz |
|---|---|
| `larpc/lexer.py` | quebra o `.larp` em tokens com linha e coluna |
| `larpc/vocabulario.py` | **o dicionário**. Mexeu aqui, mexeu na linguagem |
| `larpc/transpilador.py` | reescreve os tokens em C |
| `larpc/msvc.py` | acha o `cl`, guarda o ambiente do `vcvars` em cache |
| `larpc/executor.py` | compila a DLL, carrega com `ctypes`, traduz erro |
| `larpc/cli.py` | linha de comando |
| `_build/` | C gerado, `.dll`, `.obj` e cache do ambiente. Fora do git |

**Não há AST, de propósito.** O vocabulário é troca 1:1 com o C, então lexer
+ uma passada de reescrita resolve. Um parser completo de C seria muito
trabalho para nada. As únicas regras que precisam de contexto são o swap, o
`payload(...)`, o `%appdata%` e o `(void)` implícito.

**O C sai com exatamente o mesmo número de linhas do `.larp`.** Isso não é
estética: é o que faz o erro do compilador apontar para a linha certa do
fonte original sem precisar de tabela de mapeamento. **Qualquer mudança que
adicione ou remova linhas no meio do arquivo quebra isso** — a ponte da DLL
é anexada no fim justamente por causa disso.

---

## 5. O vocabulário

| LarpC | C | Observação |
|---|---|---|
| `sudo` | `{` | |
| `--force` | `}` | |
| `opsec` | `;` | |
| `probably` | `if` | |
| `cope` | `else` | `cope probably` = `else if` |
| `zeroday` | `void` | |
| `exfiltrate` | `return` | |
| `script` | `int` | |
| `mainframe` | `main` | |
| `persist` | `continue` | |
| `unplug` | `break` | |
| `trustmebro` | `const` | |
| `doomscroll` | `while` | |
| `grindset` | `for` | |
| `npc` | `char` | |
| `vibes` | `float` | |
| `based` / `cringe` | `1` / `0` | |
| `ghost` | `static` | |
| `payload(...)` | `(...)` | lista de parâmetros da função |
| `nullsec ...` | `// ...` | até o fim da linha |
| `%appdata% stdio` | `#include <stdio.h>` | tem que ser o começo da linha |
| `doxx x` | `&x` | **acrescentado**: doxxing é descobrir o endereço |

### O swap

`nome_com_underscore("funcao")` vira `funcao("nome com underscore")`.

Vale também com argumentos extras:
`total_pct_d__("printf", n)` vira `printf("total %d\n", n)`.

Regra que decide: **é swap quando os parênteses contêm exatamente uma
string**. `probably (x == 5)` não é swap. `based("printf")` é — palavra do
vocabulário perde para o swap, e vira texto.

Dentro do nome:

| escrito | vira |
|---|---|
| `_` | espaço |
| `__` | quebra de linha (n underscores = n−1 quebras) |
| `pct_d` | `%d` — qualquer especificador |
| `pct_2f` | `%.2f` — dígito na frente vira precisão |
| `pct_pct` | `%%` |

### C cru é recusado

Escrever `int`, `if`, `return` e companhia dá erro apontando o termo certo.
Isso é de propósito: **o personagem não pode furar**. A lista está em
`CONTRABANDO`, no `vocabulario.py`.

---

## 6. Buracos conhecidos

Nenhum destes é bug: são coisas que o design ainda não cobre. **Não "conserte"
por conta própria — cada um muda a linguagem e é decisão do Felipe.**

1. **Símbolo não cabe no nome do swap.** Não dá para imprimir `+ - * /` pelo
   swap, porque identificador não aceita esses caracteres. A `calculadora.larp`
   contorna com `pct_c` e literais `'+'`. Um prefixo de escape (`chr_mais`)
   resolveria.
2. **Chamada sem argumento nenhum** (`limpar()`) mostra o nome da função cru —
   não tem swap para disfarçar. Idem chamada só com números.
3. **Sem termo para `double`, `long`, ponteiro, `struct`, `switch`.** Passam
   como C cru, o que fura o personagem sem dar erro.
4. **Escape só de quebra de linha.** Não há como escrever tab ou aspas dentro
   do swap.
5. **O `.exe` continua bloqueado** — quem quiser um binário de verdade precisa
   compilar o C em outra máquina.

## 7. Roadmap (do documento de design)

1. ~~**Calculadora**~~ — feita, em `exemplos/calculadora.larp`.
2. **Jogo simples** (jogo da velha ou adivinhação) — próximo. Vai exigir
   `ghost`, vetor e provavelmente resolver o buraco 1 ou 2 acima.
3. **"Sistema operacional"** — ambiente de desktop simulado dentro do Windows.
   Isso exige chamar API do Windows de dentro do LarpC, e o swap de hoje
   (uma string por chamada) não escala para isso. É a etapa que vai obrigar a
   linguagem a crescer de verdade.
