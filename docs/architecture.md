# Architecture

## The path of a video
`src/unleak/cli.py` builds the options and calls `process` in `src/unleak/pipeline.py`. An image goes to `process_image` (one OCR pass, one blur). A video goes to `process_video`:

1. `src/unleak/video.py` reads BGR frames through the ffmpeg binary bundled with the `imageio-ffmpeg` package, always at a constant frame rate so the audio stays in sync.
2. Each frame is shrunk to 320 px wide in grey (`_small`) and compared with the last frame that went through OCR (`_changed`). Still screen: the frame is written right away with the current boxes, no OCR.
3. Screen changed: the frame joins the `held` queue. Once `1 / ocr_fps` has passed since the last OCR, `ocr_pass` runs.
4. `ocr_pass` reads the frame (`detect` in `src/unleak/regions.py`), combines it with the previous pass and only then writes the queued frames.

## Why frames are held back
OCR runs a few times per second at most. If every frame were written immediately, text that shows up between two passes would stay visible until the next pass. By holding frames, the ones in between get the boxes of **both passes** (`between`), so text is already hidden on the first frame where it appears.

## What keeps the cost low
- **Changed strip** (`_changed_rows`): if the change covers up to 40% of the height (typing, a blinking cursor), OCR reads only that strip and the other regions are reused.
- **Sticky regions** (`carry_over`): if OCR did not find a region again but its pixels have not changed (`still_there`), it stays. This stops the blur from flickering.
- **Pixel tracking** (`locate`): for a region that appeared or vanished between two passes, each held frame looks for its pixels nearby (`cv2.matchTemplate`). Only if that fails does the frame go through OCR.
- **Moving pairs** (`between`): a region of the same kind and size in both passes has the path between its two positions covered.

Regions are compared by kind, size and distance, never by their text: OCR rarely reads a long key the same way twice.

## Detectors
`scan` in `src/unleak/detectors/__init__.py` runs each detector on a line of text and merges overlapping spans. OCR often drops spaces ("CPF529.982.247-25"), so no pattern uses `\b`; they use "not preceded by a digit" instead. The position of a span on screen is estimated from its share of the characters in the line, with padding on both sides.

## Blur
`redact` shrinks the area to a single row of cells (each about two characters wide) and enlarges it again. The detail is thrown away first, so there is nothing to reverse. `--style box` paints a solid rectangle.

## Known limits
- Text that appears and disappears entirely between two passes, while the screen is moving, can get through.
- A secret typed character by character is only recognised once the pattern is complete; earlier frames have already been written.
- A secret wrapped onto two lines: the second half is only caught if it qualifies as `token` (32 or more mixed characters).
