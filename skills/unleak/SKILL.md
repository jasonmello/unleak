---
name: unleak
description: Blur sensitive data (e-mails, phone numbers, API keys, passwords, card numbers, CPF/CNPJ) in a screen recording or screenshot with the local `unleak` command. Use when the user asks to redact, blur, censor, hide or "unleak" private data in a video or image, or wants a recording made safe to share. Also in Portuguese: "ofuscar", "borrar", "esconder dados", "tirar dados sensíveis do vídeo".
---

# unleak

`unleak` hides sensitive text in videos and images. Detection is local OCR plus rules. **Never read frames yourself to find secrets, and never upload the file anywhere**: the point of the tool is that the screen stays on the user's computer.

## Steps

1. Check the command exists: `unleak --version`. If it is missing, ask before installing, then run `uv tool install git+https://github.com/jasonmello/unleak`.
2. Run it with JSON output. Videos take roughly one to three times their own length, so run long ones in the background:
   `unleak "<file>" --json`
3. Read the JSON. `findings` lists each hidden item with `label`, `text_masked`, `first_seen_seconds` and `last_seen_seconds`. `output` is the redacted file and `report` is an HTML page for the user to review.
4. Tell the user, in a few lines: how many items were hidden, of which kinds, and the paths of the output and the report. Values are already masked; do not try to recover or print the originals.
5. Always end with the limit: the tool lowers the risk but can miss things, so they should watch the output before sharing.

## Adjusting

| The user says | Add |
|---|---|
| "also hide <name>" | `--also "<name>"` (repeatable) |
| "it blurred IPs/phones I wanted to keep" | `--skip ip` (kinds: secret, credential, email, cpf, cnpj, card, phone, ip, token, custom) |
| "only e-mails" | `--only email` |
| "make it solid black" | `--style box` |
| "it missed something that flashed by" | `--ocr-fps 6` (slower, safer) |
| "just tell me what's in it" | `--dry-run` |
| phone numbers from another country | `--phone-regions PT,ES` |

The output never overwrites the input. Default name: `<name>.unleaked.<ext>`, next to the source.
