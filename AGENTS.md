# unleak

CLI em Python que borra dados sensíveis (e-mail, telefone, chaves de API, senhas, CPF/CNPJ, cartão) em gravações de tela e prints. Roda tudo local: OCR (RapidOCR) + regras. Público: quem programa e quem usa IA, em macOS, Windows e Linux.

## Onde está cada coisa
| O quê | Onde |
|---|---|
| Linha de comando e opções | `src/unleak/cli.py` |
| Laço do vídeo (quando ler, o que segurar) | `src/unleak/pipeline.py` |
| OCR, caixas, rastreio e borrão | `src/unleak/regions.py` |
| Leitura e gravação de vídeo (ffmpeg) | `src/unleak/video.py` |
| Detectores de texto | `src/unleak/detectors/` |
| Relatório HTML e JSON | `src/unleak/report.py` |
| Skill para Claude Code e Codex | `skills/unleak/SKILL.md` |
| Testes | `tests/` |

## Comandos
- Instalar: `uv sync`
- Testes: `uv run pytest -q` (o de ponta a ponta leva cerca de 1 minuto)
- Conferir docs: `uv run python scripts/check_docs.py`
- Rodar: `uv run unleak arquivo.mp4`

## Regras que não se quebram
- **Nada sai do computador.** Sem chamada de rede, sem LLM na detecção, sem telemetria.
- **Na dúvida, borra.** Falso positivo é aceitável; vazamento não.
- O relatório e o JSON nunca mostram o valor escondido, só a versão mascarada (`mask` em `src/unleak/report.py`).
- A saída nunca sobrescreve a entrada.
- Dados de exemplo e de teste são sempre falsos.
- Detector novo entra com teste do que pega e do que não pode pegar.
- Git e GitHub: skill `fluxo-github`.

## Não verificado
- Windows e Linux: só o macOS (Apple Silicon) foi testado à mão. O CI cobre os três, mas ainda não rodou.
- Gravação de tela real: os testes usam vídeos sintéticos.
- Publicação no PyPI: ainda não feita; a instalação é pelo Git.

## Antes de X, leia Y
| Antes de | Leia |
|---|---|
| Mexer no laço do vídeo, no rastreio ou no desempenho | `docs/arquitetura.md` |
| Mudar uma escolha já feita (bibliotecas, borrão, nome) | `docs/decisoes.md` |
| Mexer no relatório HTML, nas mensagens da CLI ou nos READMEs | `DESIGN.md` |
