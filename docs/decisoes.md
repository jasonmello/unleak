# Decisões

| Data | Decisão | Motivo |
|---|---|---|
| 2026-11-19 | Nome `unleak` | `hush` já existia no PyPI; `unleak` estava livre no PyPI e sem projeto relevante no GitHub. |
| 2026-11-19 | v1 processa o vídeo depois de gravado; ao vivo fica para depois (filtro do OBS) | Borrar durante a gravação em Mac e Windows é bem mais difícil; o pós-processamento já resolve a dor. |
| 2026-11-19 | Detecção sem LLM: OCR local + regras | LLM por frame seria lento e caro e mandaria a tela para a nuvem. O agente (Claude Code, Codex) só chama a CLI. |
| 2026-11-19 | Sem interface gráfica no v1; o relatório HTML é a tela de revisão | Menor caminho até algo útil. App de arrastar e soltar só se houver tração. |
| 2026-11-19 | `imageio-ffmpeg` em vez de PyAV | PyAV e OpenCV trazem cada um a sua cópia das bibliotecas do ffmpeg e o macOS imprime avisos de classe duplicada a cada execução. O binário do ffmpeg evita isso e dispensa instalar ffmpeg. |
| 2026-11-19 | Saída em taxa de quadros constante | Gravações de tela costumam ter taxa variável; fixar a taxa mantém o áudio em sincronia ao passar frames crus pelo ffmpeg. |
| 2026-11-19 | RapidOCR (ONNX) como OCR único | Roda igual em macOS, Windows e Linux, sem GPU e sem baixar modelo na primeira execução. Apple Vision fica como otimização futura. |
| 2026-11-19 | Borrão reduz a área a poucas células antes de ampliar | Desfoque gaussiano e mosaico fino podem ser revertidos; aqui o detalhe é descartado. |
| 2026-11-19 | Relatório e JSON mostram só o valor mascarado e miniaturas do vídeo já borrado | O relatório costuma ser compartilhado junto; não pode virar outro vazamento. |
| 2026-11-19 | Regiões pareadas por tipo, tamanho e distância | O teste de ponta a ponta mostrou que parear pelo texto falha: o OCR lê a mesma chave de formas diferentes. |
