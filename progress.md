# Progress

## Current Status

The img2ans tool is feature-complete and working. The git repo has been initialised with two clean commits. There are a couple of untracked test output files that should be cleaned up.

## Completed Work

- **`img2ans.py`** — New file. Python script that converts any Pillow-readable image to `.ans` ANSI art using half-block characters (`▀`/`▄`/`█`) and the 16-color CGA palette. Features:
  - Configurable output width (`-w`)
  - SAUCE metadata record with title/author/group (`-t`, `-a`, `-g`)
  - iCE color mode (default) with `--no-ice` flag for legacy viewer compatibility
  - PNG preview output (`-p`) with correct VGA aspect ratio
  - Optimised escape sequence output (only emits SGR changes when color state changes)
  - Implicit 80-column wrapping (explicit CRLF for non-80 widths)
- **`README.md`** — New file. Comprehensive documentation covering usage, arguments, output format, iCE color explanation, viewing tools, and aspect ratio handling. Includes credit for cat artwork to Spiny of Torment.
- **`CLAUDE.md`** — New file. Brief guidance for Claude Code describing the repo as an ANSI art collection with notes on file formats and tooling.
- **`catte003.gif`** and **`deadline_cat_012.ans`** — Pre-existing art files, committed as-is.
- **iCE / no-iCE modes verified** — Confirmed against Moebius editor documentation. No-iCE mode never emits `5;` (blink), uses character flipping (`▄`), full blocks (`█`), and dark-variant fallback to keep backgrounds in 0-7 range.
- **Preview aspect ratio fixed** — Initial implementation double-applied the cell aspect correction; fixed to uniform scaling since `quantize_image` already compensates.

## Cleanup Needed

- **`catte_test.ans`** and **`catte_test.png`** — Untracked test output files in the project root. Should be deleted or added to `.gitignore`.
- **`.claude/`** — Untracked directory (Claude Code local settings). Should be added to `.gitignore`.

## Immediate Next Steps

1. Create a `.gitignore` to exclude test outputs (`*.test.ans`, `*.test.png`, or specific filenames) and `.claude/`.
2. Delete `catte_test.ans` and `catte_test.png` if no longer needed.

## Longer-term Backlog

- Dithering support (Floyd-Steinberg or ordered) for smoother gradients in the 16-color palette.
- Shade character mode (`░▒▓█`) as an alternative to half-block rendering, matching the style used in `deadline_cat_012.ans`.
- Animated GIF support (render each frame to a separate `.ans` or produce an ANSI animation sequence).
- Batch conversion (multiple input files).
- `--scale` option for the preview PNG.

## Key Notes

- The `quantize_image` function applies a 0.5 vertical correction for the 8x16 VGA cell aspect ratio. Any preview or rendering code should NOT apply additional aspect correction — this was the cause of the squashed preview bug.
- The `BG_CODES` and `FG_CODES` dicts at module level are defined but not used by the renderer (which builds SGR codes inline). They exist as documentation/reference. Don't remove them thinking they're dead code without checking.
- The `nearest_color` function is also unused by the main pipeline (vectorised lookup is used instead) but is kept as a utility.
- `.ans` files are binary (CP437 + escape sequences). Standard text tools and git text diffs will mangle them.
