# Arquitetura

## Caminho de um vídeo
`src/unleak/cli.py` monta as opções e chama `process` em `src/unleak/pipeline.py`. Imagem vai para `process_image` (um OCR, um borrão). Vídeo vai para `process_video`:

1. `src/unleak/video.py` lê os frames em BGR pelo ffmpeg que vem no pacote `imageio-ffmpeg`, sempre em taxa de quadros constante, para o áudio não sair de sincronia.
2. Cada frame é reduzido para 320 px de largura em cinza (`_small`) e comparado com o último frame lido por OCR (`_changed`). Tela parada: o frame é escrito na hora com as caixas atuais, sem OCR.
3. Tela mudou: o frame entra na fila `held`. Quando já passou `1 / ocr_fps` desde o último OCR, roda `ocr_pass`.
4. `ocr_pass` lê o frame (`detect` em `src/unleak/regions.py`), junta com o passe anterior e só então escreve os frames da fila.

## Por que segurar frames
O OCR roda no máximo algumas vezes por segundo. Se cada frame fosse escrito na hora, o texto que aparece entre dois passes ficaria visível até o passe seguinte. Segurando, os frames do intervalo recebem as caixas **dos dois passes** (`between`), e o texto já sai borrado no primeiro frame em que aparece.

## O que mantém o custo baixo
- **Faixa alterada** (`_changed_rows`): se a mudança ocupa até 40% da altura (digitação, cursor piscando), o OCR lê só aquela faixa e o resto das regiões é reaproveitado.
- **Região persistente** (`carry_over`): se o OCR não reencontrou uma região mas os pixels dela não mudaram (`still_there`), ela continua. Evita o borrão piscar.
- **Rastreio por pixels** (`locate`): para região que apareceu ou sumiu entre dois passes, cada frame da fila procura os pixels dela por perto (`cv2.matchTemplate`). Só se não achar é que o frame passa por OCR.
- **Pares em movimento** (`between`): região do mesmo tipo e tamanho nos dois passes tem o caminho entre as duas posições coberto.

As regiões são comparadas por tipo, tamanho e distância, nunca pelo texto: o OCR raramente lê uma chave longa igual duas vezes.

## Detectores
`scan` em `src/unleak/detectors/__init__.py` roda cada detector na linha de texto e funde os trechos sobrepostos. O OCR costuma comer espaços ("CPF529.982.247-25"), então nenhum padrão usa `\b`; usam "não precedido de dígito". A posição do trecho na tela é estimada pela proporção de caracteres na linha, com folga para os lados.

## Borrão
`redact` reduz a área a uma fileira de células (cada uma com cerca de dois caracteres de largura) e amplia de volta. O detalhe é descartado antes, então não há o que reverter. `--style box` pinta um retângulo sólido.

## Limites conhecidos
- Texto que aparece e some inteiro entre dois passes, com a tela em movimento, pode passar.
- Segredo digitado letra por letra só é reconhecido quando o padrão fecha; os frames anteriores já foram escritos.
- Segredo quebrado em duas linhas: a segunda metade só é pega se cair em `token` (32 ou mais caracteres misturados).
