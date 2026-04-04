# img2ans

Convert images to ANSI art (`.ans` files) using half-block characters and the 16-color CGA palette.

![Example: catte003.gif rendered as ANSI art](catte003.gif)
*Cat artwork by Spiny of [Torment](https://www.spiny.org/torment/index.html)*

## How it works

Each character cell in a terminal using a VGA font is 8 pixels wide and 16 pixels tall -- roughly a 1:2 aspect ratio. `img2ans` exploits this by using the **upper-half-block character** (`▀`, CP437 `0xDF`) to encode **two vertical pixels per cell**: the foreground color paints the top half and the background color paints the bottom half. When both halves share the same color, a space (background only) is emitted instead.

This half-block technique gives an effective pixel resolution of `width` x `height*2` within a text grid of `width` columns by `height` rows.

Colors are quantized to the **standard 16-color CGA palette** using Euclidean distance in RGB space:

| Index | Color         | RGB           | Index | Color         | RGB           |
|-------|---------------|---------------|-------|---------------|---------------|
| 0     | Black         | `(0,0,0)`     | 8     | Dark Gray     | `(85,85,85)`  |
| 1     | Blue          | `(0,0,170)`   | 9     | Light Blue    | `(85,85,255)` |
| 2     | Green         | `(0,170,0)`   | 10    | Light Green   | `(85,255,85)` |
| 3     | Cyan          | `(0,170,170)` | 11    | Light Cyan    | `(85,255,255)`|
| 4     | Red           | `(170,0,0)`   | 12    | Light Red     | `(255,85,85)` |
| 5     | Magenta       | `(170,0,170)` | 13    | Light Magenta | `(255,85,255)`|
| 6     | Brown         | `(170,85,0)`  | 14    | Yellow        | `(255,255,85)`|
| 7     | Light Gray    | `(170,170,170)`| 15   | White         | `(255,255,255)`|

## Requirements

- Python 3.8+
- [Pillow](https://pypi.org/project/Pillow/)
- [NumPy](https://pypi.org/project/numpy/)

```
pip install Pillow numpy
```

## Usage

```
python img2ans.py <input> [-o OUTPUT] [-w WIDTH] [-t TITLE] [-a AUTHOR] [-g GROUP] [--no-ice] [-p PREVIEW]
```

### Arguments

| Argument | Description |
|---|---|
| `input` | Input image file. Any format Pillow can read (PNG, GIF, JPG, BMP, TIFF, WebP, ...). |
| `-o`, `--output` | Output `.ans` file path. If omitted, raw bytes are written to stdout. |
| `-w`, `--width` | Output width in columns. Default: **80**. |
| `-t`, `--title` | Title string stored in the SAUCE metadata record (max 35 chars). |
| `-a`, `--author` | Author string stored in SAUCE (max 20 chars). |
| `-g`, `--group` | Group/organization string stored in SAUCE (max 20 chars). |
| `--no-ice` | Disable iCE colors. Restricts backgrounds to the 8 dark colors (0-7), avoiding flashing output in viewers that interpret the blink attribute literally. See [iCE colors](#ice-colors) below. |
| `-p`, `--preview` | Save a PNG preview image showing how the ANSI art will look, rendered at 8x scale with nearest-neighbor interpolation. |

### Examples

Basic conversion at the default 80-column width:

```
python img2ans.py photo.png -o photo.ans
```

Wider output for high-detail images:

```
python img2ans.py landscape.jpg -o landscape.ans -w 160
```

Narrow output with SAUCE metadata:

```
python img2ans.py cat.gif -o cat.ans -w 40 -t "Cat" -a "myself" -g "MyGroup"
```

Safe for legacy viewers (no flashing):

```
python img2ans.py cat.gif -o cat.ans --no-ice
```

Generate a PNG preview alongside the `.ans` file:

```
python img2ans.py cat.gif -o cat.ans -p cat_preview.png
```

Pipe to stdout (e.g. to preview in a CP437-capable terminal):

```
python img2ans.py icon.png | iconv -f cp437 -t utf-8
```

## Output format

The generated `.ans` files follow standard ANSI art conventions:

- **Encoding:** CP437 (the IBM PC extended ASCII character set)
- **Color model:** 16-color CGA via SGR escape sequences (`ESC[...m`)
  - Foreground colors 0-7 use codes `30`-`37`; colors 8-15 add bold (`1;`)
  - Background colors 0-7 use codes `40`-`47`; colors 8-15 add blink (`5;`), interpreted as bright background in iCE color mode
- **iCE colors:** Enabled by default (TFlags bit 1). See [iCE colors](#ice-colors) below.
- **Line wrapping:** At the default width of 80, lines wrap implicitly with no CR/LF characters (matching the traditional BBS/ANSI art convention). At non-80 widths, explicit `CR+LF` line endings are inserted.
- **SAUCE record:** A standard 128-byte [SAUCE](https://www.acid.org/info/sauce/sauce.htm) metadata block is appended after an `EOF` (`0x1A`) marker. It records the title, author, group, creation date, canvas dimensions, iCE color flag, and font name (`IBM VGA`).

### iCE colors

In standard ANSI, SGR attribute `5` enables **blinking text**, limiting backgrounds to the 8 dark colors (indices 0-7). **iCE color** mode reinterprets the blink attribute as a bright background instead, unlocking all 16 colors for backgrounds. This is the default because it produces the best color fidelity.

However, many classic BBS terminals and ANSI viewers do not support iCE colors and will render the `5;` attribute as actual blinking, causing large portions of the image to flash. Use `--no-ice` to produce files compatible with these viewers.

When `--no-ice` is active, the renderer uses several strategies to avoid bright backgrounds:

- **Character flipping:** When the bottom pixel is dark and the top is bright, it uses `▄` (lower-half-block) instead of `▀` to swap which color lands in the foreground vs. background slot.
- **Full blocks:** When both pixels are the same bright color, it uses `█` (full-block) which only needs a foreground color.
- **Dark fallback:** When both pixels are different bright colors and neither can go in the background, the bottom color is demoted to its dark variant (index `& 7`).

The SAUCE TFlags field is set accordingly: bit 1 on for iCE, 0 for non-iCE.

### Escape sequence optimization

The renderer tracks the current foreground color, background color, bold, and blink state. It only emits SGR sequences when the state actually changes, and batches multiple attribute changes into a single `ESC[...m` sequence. A full reset (`ESC[0m`) is only emitted when transitioning from bold to non-bold or blink to non-blink, since those attributes cannot be turned off individually in standard ANSI.

## Viewing .ans files

`.ans` files are meant for CP437-compatible environments. Some options:

- **[PabloDraw](https://github.com/cwensley/pabloD)** -- Full-featured ANSI art editor/viewer (Windows, macOS, Linux)
- **[Moebius](https://blocktronics.github.io/moebius/)** -- Cross-platform ANSI art editor with iCE color support
- **[ansilove](https://github.com/ansilove/ansilove)** -- Command-line tool that renders `.ans` files to PNG
- **Terminal** -- Any terminal with CP437 font support; pipe through `iconv` or `chcp 437` on Windows

## Aspect ratio

The converter accounts for the VGA text-mode cell aspect ratio (8:16, or 1:2). When computing the output height from the input image dimensions, it applies a correction factor of `0.5` so that the rendered art appears with correct proportions in a standard VGA font. This means a square input image at 80 columns will produce roughly 40 text rows (80 pixel-rows in half-block representation).
