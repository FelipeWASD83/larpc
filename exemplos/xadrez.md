# Xadrez infinito

Xadrez num tabuleiro sem bordas, contra uma IA. Escrito inteiro em LarpC.

```bash
larpc exemplos/xadrez.larp
```

As peças começam exatamente onde começam no xadrez normal — colunas 1 a 8,
fileiras 1 a 8 — e dali em diante o mundo é aberto para os quatro lados.
Coordenada negativa é válida: uma torre pode ir para `-40, 12` e voltar.

## Como jogar

O jogo pergunta se você quer as brancas (1), as pretas (2), só assistir a IA
jogar contra ela mesma (3), ou rodar o auto-teste (4). Depois pergunta a força
da IA, de 1 a 4.

Um lance são **quatro números**: coluna e fileira de onde a peça está, coluna e
fileira para onde ela vai.

```
sua vez: x1 y1 x2 y2  (lances/desfazer/sair) 5 2 5 4
```

Isso é o peão do rei andando duas casas. Também dá para digitar:

- `lances` — lista todos os seus lances legais, no mesmo formato
- `desfazer` — volta o seu lance e o da IA
- `sair` — encerra

A tela mostra a janela onde as peças estão, com as coordenadas em volta. Se
alguma peça sair da janela, ela aparece listada embaixo como
`fora da tela: K -40 12` — no infinito a peça some da vista, não do jogo.

## O que muda por não existir borda

**Peão promove depois de andar 6 casas.** Não existe oitava fileira para chegar,
então a regra vira a distância que o peão andaria no tabuleiro normal — da
fileira 2 até a 8 são 6 casas — contada da casa onde ele nasceu. Um peão que
promove em `30, 26` promove pelo mesmo motivo que um peão promove em `e8`.

**Quem ficar só com o rei perde na hora.** Sem borda, o rei sempre tem casa de
fuga, e quem estivesse perdendo poderia simplesmente correr para sempre. Essa
regra é o que garante que a partida acaba.

**50 lances sem captura e sem peão dá empate**, como no xadrez. Quando as duas
regras dariam resultados diferentes, a do rei pelado decide primeiro.

**Mate ainda existe, mas exige cerco.** Encurralar rei contra a borda é como
quase todo mate funciona no xadrez normal, e aqui não tem borda. O auto-teste
monta um mate com três damas para provar que é possível.

Roque, en passant, xeque, cravada e afogamento continuam iguais.

## A área ativa

Uma torre num tabuleiro vazio infinito teria infinitos lances legais — não daria
nem para listar, quanto mais para a IA procurar. Então as peças só se movem
dentro da **área ativa**: a caixa que contém todas as peças em jogo, mais três
casas de folga. Ela cresce sozinha conforme o jogo se espalha.

Na prática isso é invisível: mover uma torre 300 casas para o vazio nunca é bom
lance. E resolve a fuga do rei de brinde — ele se afasta uma casa por lance,
enquanto a dama que o persegue anda vinte.

## A IA

Minimax com poda alfa-beta, ordenação de capturas primeiro e busca de
profundidade fixa. Stockfish não serviria: ele assume 8×8 empacotado em 64 bits,
e aqui o tabuleiro não tem tamanho.

A avaliação é material, mais duas coisas que só existem por causa do infinito:
peão adiantado vale mais (a promoção é por distância, então cada casa andada é
uma casa a menos), e peça perto do rei inimigo vale mais — com peso pequeno
durante o jogo e peso alto quando sobra pouca peça, que é quando o mate depende
inteiramente de fechar o cerco.

Força 1 responde na hora e joga mal. Força 4 leva alguns segundos por lance.

## Auto-teste

A opção 4 roda 27 conferências das regras por dentro, sem precisar digitar
lance nenhum: contagem de lances na posição inicial, simetria, `perft(2)`,
promoção por distância (inclusive longe do 8×8 original), roque em todas as
variações, en passant, mate sem borda, rei pelado, regra dos 50 e área ativa.
Também confere que desfazer um lance devolve a posição byte a byte — é o teste
que pega bug de estado, o mais fácil de introduzir sem perceber.

Ela roda junto com a suíte do projeto:

```bash
python -m unittest discover -s testes
```

## Detalhes de implementação

Sem `struct` no vocabulário do LarpC, as peças são **vetores paralelos**:
`px`, `py`, `ptipo`, `pcor`, `pviva`, `pmoveu`, `pavanco`, com 32 posições.
O rei branco é sempre a peça 4 e o preto sempre a 20, o que evita procurar
rei toda hora.

A busca precisa de uma lista de lances por nível de profundidade, então as
listas são vetores 2D `[8][512]` e a pilha de desfazer tem uma entrada por
nível. O `desfazer` do jogador é outra coisa: ele guarda a posição inteira
antes de cada lance, o que gasta mais memória mas não tem como sair errado.
