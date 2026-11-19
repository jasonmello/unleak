# Design

Tirado do código: `src/unleak/report.py` (relatório) e `src/unleak/cli.py` (mensagens). Mudou lá, mude aqui.

## Princípios
- **Honesto antes de tranquilizador.** Toda saída lembra que a ferramenta reduz o risco e não elimina.
- **Nunca mostrar o que foi escondido.** Texto sempre mascarado (`mask`), miniaturas sempre do vídeo já borrado.
- **Um arquivo, sem rede.** O relatório é um HTML único, com CSS embutido e imagens em base64. Sem fonte externa, sem script.

## Cores (variáveis CSS do relatório)
| Token | Claro | Escuro | Uso |
|---|---|---|---|
| `--bg` | `#f6f5f1` | `#151412` | fundo da página |
| `--card` | `#ffffff` | `#1e1d1a` | cartão de cada item |
| `--ink` | `#1c1b19` | `#f1efe9` | texto |
| `--muted` | `#6b6862` | `#a19d94` | texto secundário, tempos |
| `--line` | `#e3e0d8` | `#33312c` | bordas e divisórias |
| `--accent` | `#c2410c` | `#fb923c` | barra do aviso de limite |

O tema escuro segue `prefers-color-scheme`. Na miniatura, a área escondida leva contorno vermelho de 2 px (BGR 60, 60, 235, em `_thumbnail` de `src/unleak/pipeline.py`).

## Tipografia
- Texto: fonte do sistema (`ui-sans-serif, system-ui`), 15 px, entrelinha 1.5.
- Título: 26 px. Números de destaque: 22 px, com algarismos tabulares.
- Valor mascarado: monoespaçada do sistema, 13 px.

## Espaço e componentes
- Coluna única de até 880 px, com 16 px de margem lateral.
- Faixa de números (itens escondidos, duração, frames lidos) entre duas linhas.
- Aviso de limite: parágrafo com barra de 3 px à esquerda, sem caixa.
- Item: cartão com raio de 10 px e borda de 1 px; tipo, valor mascarado, intervalo de tempo e miniatura.
- Área escondida no vídeo e na imagem: borrão com 20% de cinza por cima (`redact` em `src/unleak/regions.py`), para continuar visível em fundo claro ou escuro.
- Sem movimento: o relatório é estático.

## Voz
- Inglês simples no produto (CLI, relatório, README). Português em `README.pt-BR.md` e nos docs internos.
- Frases curtas, verbo direto: "3 items hidden", "Check the output before you share it."
- Diga o que aconteceu e o que a pessoa faz a seguir. Sem exclamação, sem promessa de segurança total.
- Erros começam com `unleak:` e dizem como resolver.
- Tempos no formato `m:ss.s`.

## Conteúdo
- Exemplos e imagens usam só dados falsos, e dizem isso.
- O nome do tipo mostrado à pessoa vem de `LABELS` em `src/unleak/report.py`.
