#!/usr/bin/env python3
"""Convert an image file to ANSI art (.ans) using half-block characters.

Each character cell encodes two vertical pixels by using the upper-half-block
character (▀, CP437 0xDF) with foreground = top pixel color and background =
bottom pixel color.  This gives effective resolution of (columns × rows*2)
pixels within the 16-color CGA palette.

Output uses iCE color mode (16 background colors, no blink) and appends a
SAUCE metadata record.

Usage:
    python img2ans.py input.png                  # 80-col output to stdout
    python img2ans.py input.gif -o out.ans       # write to file
    python img2ans.py input.jpg -w 160           # 160-col wide
    python img2ans.py input.png -w 40 -t "Cool"  # 40-col with SAUCE title
    python img2ans.py input.png --full-block     # full blocks (stretched)
    python img2ans.py input.png --gradient       # gradient shading (░▒▓)
"""

import argparse
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image

# Standard CGA 16-color palette (RGB)
CGA_PALETTE = np.array([
    [0x00, 0x00, 0x00],  # 0  Black
    [0x00, 0x00, 0xAA],  # 1  Blue
    [0x00, 0xAA, 0x00],  # 2  Green
    [0x00, 0xAA, 0xAA],  # 3  Cyan
    [0xAA, 0x00, 0x00],  # 4  Red
    [0xAA, 0x00, 0xAA],  # 5  Magenta
    [0xAA, 0x55, 0x00],  # 6  Brown
    [0xAA, 0xAA, 0xAA],  # 7  Light Gray
    [0x55, 0x55, 0x55],  # 8  Dark Gray
    [0x55, 0x55, 0xFF],  # 9  Light Blue
    [0x55, 0xFF, 0x55],  # 10 Light Green
    [0x55, 0xFF, 0xFF],  # 11 Light Cyan
    [0xFF, 0x55, 0x55],  # 12 Light Red
    [0xFF, 0x55, 0xFF],  # 13 Light Magenta
    [0xFF, 0xFF, 0x55],  # 14 Yellow
    [0xFF, 0xFF, 0xFF],  # 15 White
], dtype=np.float64)

# ANSI SGR codes for CGA colors
#   FG: 0-7 → 30-37,  8-15 → 30-37 with bold (1;)
#   BG: 0-7 → 40-47,  8-15 → 40-47 with blink (5;)  [iCE mode interprets blink as bright bg]
FG_CODES = {
    0: "30", 1: "34", 2: "32", 3: "36", 4: "31", 5: "35", 6: "33", 7: "37",
    8: "1;30", 9: "1;34", 10: "1;32", 11: "1;36", 12: "1;31", 13: "1;35", 14: "1;33", 15: "1;37",
}
BG_CODES = {
    0: "40", 1: "44", 2: "42", 3: "46", 4: "41", 5: "45", 6: "43", 7: "47",
    8: "5;40", 9: "5;44", 10: "5;42", 11: "5;46", 12: "5;41", 13: "5;45", 14: "5;43", 15: "5;47",
}

UPPER_HALF_BLOCK = 0xDF  # ▀ in CP437
LOWER_HALF_BLOCK = 0xDC  # ▄ in CP437
FULL_BLOCK = 0xDB        # █ in CP437
LIGHT_SHADE = 0xB0       # ░ in CP437
MEDIUM_SHADE = 0xB1      # ▒ in CP437
DARK_SHADE = 0xB2        # ▓ in CP437
SPACE = 0x20

# Shade characters ordered by foreground coverage (0% → 100%)
SHADE_CHARS = [SPACE, LIGHT_SHADE, MEDIUM_SHADE, DARK_SHADE, FULL_BLOCK]
SHADE_WEIGHTS = np.array([0.0, 0.25, 0.5, 0.75, 1.0])  # fg weight per shade


def nearest_color(rgb):
    """Return index of the closest CGA color to an RGB triplet."""
    diffs = CGA_PALETTE - rgb
    dists = np.sum(diffs ** 2, axis=1)
    return int(np.argmin(dists))


def quantize_image(img, width, full_block=False):
    """Resize and quantize an image to the CGA palette.

    Returns a 2D array of palette indices with shape (height, width),
    where height is even (padded if needed) in half-block mode, or
    any value in full-block mode.
    """
    # Compute height preserving aspect ratio.  Each character cell is
    # roughly 8×16 px in a VGA font, so one cell = 2 vertical pixels
    # in half-block mode.  We correct for the 1:2 cell aspect ratio.
    orig_w, orig_h = img.size
    cell_aspect = 8 / 16  # width / height of a VGA character cell
    if full_block:
        pixel_height = int(round(width * (orig_h / orig_w) * cell_aspect))
        if pixel_height < 1:
            pixel_height = 1
    else:
        pixel_height = int(round(width * (orig_h / orig_w) * cell_aspect)) * 2
        if pixel_height < 2:
            pixel_height = 2

    img = img.convert("RGB").resize((width, pixel_height), Image.LANCZOS)
    pixels = np.array(img, dtype=np.float64)

    # Vectorised nearest-colour lookup
    # Shape: (H, W, 1, 3) vs (16, 3) → (H, W, 16)
    diffs = pixels[:, :, np.newaxis, :] - CGA_PALETTE[np.newaxis, np.newaxis, :, :]
    dists = np.sum(diffs ** 2, axis=3)
    indices = np.argmin(dists, axis=2).astype(np.uint8)

    return indices


def quantize_image_gradient(img, width, ice=True):
    """Resize and quantize using gradient shading for higher color fidelity.

    Uses shade characters (░▒▓) to blend between two CGA colors per cell,
    giving 5 blend levels × 16×16 color pairs = effectively ~1280 tones.

    Returns (fg_indices, bg_indices, shade_indices) each with shape (H, W).
    """
    orig_w, orig_h = img.size
    cell_aspect = 8 / 16
    pixel_height = int(round(width * (orig_h / orig_w) * cell_aspect))
    if pixel_height < 1:
        pixel_height = 1

    img = img.convert("RGB").resize((width, pixel_height), Image.LANCZOS)
    pixels = np.array(img, dtype=np.float64)

    n_colors = 16
    max_bg = n_colors if ice else 8
    n_shades = len(SHADE_WEIGHTS)

    # Precompute effective RGB for every (fg, bg, shade) combination
    # Shape: (n_colors, max_bg, n_shades, 3)
    fg_rgb = CGA_PALETTE[:n_colors]                          # (16, 3)
    bg_rgb = CGA_PALETTE[:max_bg]                            # (max_bg, 3)
    # outer products with shade weights
    # effective = w * fg + (1-w) * bg
    effective = (SHADE_WEIGHTS[np.newaxis, np.newaxis, :, np.newaxis]
                 * fg_rgb[:, np.newaxis, np.newaxis, :]
                 + (1 - SHADE_WEIGHTS)[np.newaxis, np.newaxis, :, np.newaxis]
                 * bg_rgb[np.newaxis, :, np.newaxis, :])
    # Flatten to (N, 3) for distance computation
    n_combos = n_colors * max_bg * n_shades
    effective_flat = effective.reshape(n_combos, 3)

    # For each pixel find the nearest combo
    # pixels: (H, W, 3), effective_flat: (N, 3)
    diffs = pixels[:, :, np.newaxis, :] - effective_flat[np.newaxis, np.newaxis, :, :]
    dists = np.sum(diffs ** 2, axis=3)
    best = np.argmin(dists, axis=2)

    # Decode flat index back to (fg, bg, shade)
    fg_indices = (best // (max_bg * n_shades)).astype(np.uint8)
    bg_indices = ((best // n_shades) % max_bg).astype(np.uint8)
    shade_indices = (best % n_shades).astype(np.uint8)

    return fg_indices, bg_indices, shade_indices


def _pick_cell(top, bot, ice):
    """Choose character, foreground, and background for a cell pair.

    Returns (char_byte, fg_index, bg_index).

    In iCE mode any of the 16 colors can appear in either slot.  Without
    iCE, backgrounds are restricted to 0-7 (the blink attribute would
    cause flashing instead of a bright background).  The function picks
    between ▀ and ▄ to keep a dark color in the background slot when
    possible, and falls back to the dark variant (index & 7) when both
    colors are bright.
    """
    if top == bot:
        if not ice and top >= 8:
            # Both bright & same — full block needs only fg (any color ok)
            return FULL_BLOCK, top, 0
        return SPACE, top, top  # fg is don't-care but passed through

    if ice:
        return UPPER_HALF_BLOCK, top, bot

    # Non-iCE: background must be 0-7.
    if bot < 8:
        # Bottom is dark → ▀  fg=top, bg=bottom
        return UPPER_HALF_BLOCK, top, bot
    if top < 8:
        # Top is dark → ▄  fg=bottom, bg=top
        return LOWER_HALF_BLOCK, bot, top
    # Both bright — demote the less-visible one (bottom) to its dark variant
    return UPPER_HALF_BLOCK, top, bot % 8


def _render_gradient(fg_indices, bg_indices, shade_indices, width, ice=True):
    """Render gradient-shaded cells using shade characters with fg+bg colors."""
    height = fg_indices.shape[0]
    buf = bytearray()
    cur_fg = -1
    cur_bg = -1
    cur_bold = False
    cur_blink = False

    for row in range(height):
        for col in range(width):
            need_fg = int(fg_indices[row, col])
            need_bg = int(bg_indices[row, col])
            shade = int(shade_indices[row, col])
            char = SHADE_CHARS[shade]

            parts = []
            want_bold = need_fg >= 8 if char != SPACE else cur_bold
            want_blink = need_bg >= 8  # only reachable when ice=True

            need_reset = (cur_bold and not want_bold) or (cur_blink and not want_blink)

            if need_reset:
                parts.append("0")
                cur_fg = -1
                cur_bg = -1
                cur_bold = False
                cur_blink = False

            if want_bold and not cur_bold:
                parts.append("1")
                cur_bold = True
            if want_blink and not cur_blink:
                parts.append("5")
                cur_blink = True

            fg_base = need_fg % 8
            fg_sgr = str(30 + [0, 4, 2, 6, 1, 5, 3, 7][fg_base])
            if char != SPACE and (need_fg != cur_fg or need_reset):
                parts.append(fg_sgr)
                cur_fg = need_fg

            bg_base = need_bg % 8
            bg_sgr = str(40 + [0, 4, 2, 6, 1, 5, 3, 7][bg_base])
            if need_bg != cur_bg or need_reset:
                parts.append(bg_sgr)
                cur_bg = need_bg

            if parts:
                buf.extend(b"\x1b[" + ";".join(parts).encode("ascii") + b"m")

            buf.append(char)

        if width != 80:
            buf.extend(b"\r\n")

    return bytes(buf)


def _render_full_block(indices, width):
    """Render each pixel as a full-block character with foreground color only."""
    height = indices.shape[0]
    buf = bytearray()
    cur_fg = -1
    cur_bold = False

    for row in range(height):
        for col in range(width):
            color = int(indices[row, col])
            want_bold = color >= 8
            parts = []

            need_reset = cur_bold and not want_bold
            if need_reset:
                parts.append("0")
                cur_fg = -1
                cur_bold = False

            if want_bold and not cur_bold:
                parts.append("1")
                cur_bold = True

            if color != cur_fg or need_reset:
                fg_base = color % 8
                fg_sgr = str(30 + [0, 4, 2, 6, 1, 5, 3, 7][fg_base])
                parts.append(fg_sgr)
                cur_fg = color

            if parts:
                buf.extend(b"\x1b[" + ";".join(parts).encode("ascii") + b"m")

            buf.append(FULL_BLOCK)

        if width != 80:
            buf.extend(b"\r\n")

    return bytes(buf)


def render_ansi(indices, width, ice=True, full_block=False):
    """Render a palette-index grid into raw ANSI bytes (CP437 + escape seqs).

    When *full_block* is True, each pixel gets its own character cell using
    a full-block character (█) with only foreground color.  This produces
    vertically stretched output but avoids half-block rendering.

    Otherwise, processes rows in pairs (top, bottom).  For each column the
    best character + fg/bg combination is chosen:
      - Both same color  → space with that bg (or full-block with that fg)
      - Different colors → ▀ or ▄ half-block with appropriate fg/bg

    When *ice* is False, background colors are limited to 0-7 so that the
    blink attribute is never emitted (avoiding flashing in legacy viewers).
    """
    height = indices.shape[0]
    buf = bytearray()
    cur_fg = -1
    cur_bg = -1
    cur_bold = False
    cur_blink = False

    if full_block:
        return _render_full_block(indices, width)

    for row in range(0, height, 2):
        for col in range(width):
            top = int(indices[row, col])
            bot = int(indices[row + 1, col]) if row + 1 < height else 0

            char, need_fg, need_bg = _pick_cell(top, bot, ice)

            # Build SGR sequence only if color changed
            parts = []
            want_bold = need_fg >= 8 if char != SPACE else cur_bold
            want_blink = need_bg >= 8  # only reachable when ice=True

            # Determine if we need a reset (going from bold→no-bold or blink→no-blink)
            need_reset = (cur_bold and not want_bold) or (cur_blink and not want_blink)

            if need_reset:
                parts.append("0")
                cur_fg = -1
                cur_bg = -1
                cur_bold = False
                cur_blink = False

            if want_bold and not cur_bold:
                parts.append("1")
                cur_bold = True
            if want_blink and not cur_blink:
                parts.append("5")
                cur_blink = True

            # Foreground (base code, without bold prefix since bold is separate)
            fg_base = need_fg % 8
            fg_sgr = str(30 + [0, 4, 2, 6, 1, 5, 3, 7][fg_base])
            if char != SPACE and (need_fg != cur_fg or need_reset):
                parts.append(fg_sgr)
                cur_fg = need_fg

            # Background (base code, without blink prefix)
            bg_base = need_bg % 8
            bg_sgr = str(40 + [0, 4, 2, 6, 1, 5, 3, 7][bg_base])
            if need_bg != cur_bg or need_reset:
                parts.append(bg_sgr)
                cur_bg = need_bg

            if parts:
                buf.extend(b"\x1b[" + ";".join(parts).encode("ascii") + b"m")

            buf.append(char)

        # No CRLF — implicit 80-col wrapping (matches the reference file style)
        # But if width != 80, we need explicit line breaks
        if width != 80:
            buf.extend(b"\r\n")

    return bytes(buf)


def make_sauce(title="", author="", group="", width=80, height=0, ice=True):
    """Build a 128-byte SAUCE record + EOF marker."""
    from datetime import date
    today = date.today().strftime("%Y%m%d")

    sauce = bytearray(128)
    sauce[0:7] = b"SAUCE00"
    sauce[7:42] = title.encode("ascii", errors="replace").ljust(35, b"\x00")
    sauce[42:62] = author.encode("ascii", errors="replace").ljust(20, b"\x00")
    sauce[62:82] = group.encode("ascii", errors="replace").ljust(20, b"\x00")
    sauce[82:90] = today.encode("ascii")
    # FileSize filled later by caller
    sauce[94] = 1   # DataType: Character
    sauce[95] = 1   # FileType: ANSi
    struct.pack_into("<H", sauce, 96, width)   # TInfo1 = width
    struct.pack_into("<H", sauce, 98, height)  # TInfo2 = height (in rows)
    sauce[105] = 2 if ice else 0  # TFlags: bit 1 = iCE colors
    sauce[106:128] = b"IBM VGA\x00" + b"\x00" * 14  # TInfoS font name

    return sauce


def render_preview(indices, scale=8, full_block=False):
    """Render the quantized pixel grid to an RGB image.

    Each pixel in *indices* maps to a CGA palette color.  The image is
    scaled by *scale* using nearest-neighbor interpolation.  In half-block
    mode the cell aspect ratio correction is already applied during
    quantization.  In full-block mode each pixel occupies a full 8×16
    character cell, so the vertical scale is doubled to match.
    """
    palette_u8 = CGA_PALETTE.astype(np.uint8)
    rgb = palette_u8[indices]  # (H, W, 3)
    img = Image.fromarray(rgb)
    y_scale = scale * 2 if full_block else scale
    img = img.resize((indices.shape[1] * scale, indices.shape[0] * y_scale),
                     Image.NEAREST)
    return img


def render_preview_gradient(fg_indices, bg_indices, shade_indices, scale=8):
    """Render a gradient-shaded pixel grid to an RGB preview image.

    Each character cell is rendered at *scale* × *scale*×2 pixels with a
    stipple pattern that matches the shade character:
      - space  → all background
      - ░      → 25% foreground (sparse dots)
      - ▒      → 50% foreground (checkerboard)
      - ▓      → 75% foreground (dense dots)
      - █      → all foreground
    """
    palette_u8 = CGA_PALETTE.astype(np.uint8)
    h, w = fg_indices.shape
    cw = scale          # cell width in preview pixels
    ch = scale * 2      # cell height (2:1 aspect for full-height chars)

    # Build per-pixel stipple masks for each shade level within one cell
    # yx grid within a cell
    cy, cx = np.mgrid[0:ch, 0:cw]
    shade_masks = np.zeros((5, ch, cw), dtype=bool)
    # shade 0 (space):   all False  → all bg
    # shade 1 (░ 25%):   every other pixel in every other row
    shade_masks[1] = (cy % 2 == 0) & (cx % 2 == 0)
    # shade 2 (▒ 50%):   checkerboard
    shade_masks[2] = (cx + cy) % 2 == 0
    # shade 3 (▓ 75%):   inverse of 25% pattern
    shade_masks[3] = ~shade_masks[1]
    # shade 4 (█ full):  all True → all fg
    shade_masks[4] = True

    out = np.zeros((h * ch, w * cw, 3), dtype=np.uint8)

    for row in range(h):
        for col in range(w):
            fg = palette_u8[fg_indices[row, col]]
            bg = palette_u8[bg_indices[row, col]]
            mask = shade_masks[shade_indices[row, col]]  # (ch, cw)
            cell = np.where(mask[:, :, np.newaxis], fg, bg)
            out[row * ch:(row + 1) * ch, col * cw:(col + 1) * cw] = cell

    return Image.fromarray(out)


def convert(input_path, output=None, width=80, title="", author="", group="",
            ice=True, preview=None, full_block=False, gradient=False):
    img = Image.open(input_path)

    if gradient:
        fg_idx, bg_idx, shade_idx = quantize_image_gradient(img, width, ice=ice)
        rows = fg_idx.shape[0]
        art_data = _render_gradient(fg_idx, bg_idx, shade_idx, width, ice=ice)
    else:
        indices = quantize_image(img, width, full_block=full_block)
        rows = indices.shape[0] if full_block else indices.shape[0] // 2
        art_data = render_ansi(indices, width, ice=ice, full_block=full_block)

    # Build SAUCE
    sauce = make_sauce(title=title, author=author, group=group,
                       width=width, height=rows, ice=ice)
    # Set file size in SAUCE (size of art data, before EOF marker)
    struct.pack_into("<I", sauce, 90, len(art_data))

    full = art_data + b"\x1a" + bytes(sauce)

    if output:
        Path(output).write_bytes(full)
        print(f"Wrote {len(full)} bytes to {output}  ({width}x{rows})", file=sys.stderr)
    else:
        sys.stdout.buffer.write(full)

    if preview:
        if gradient:
            preview_img = render_preview_gradient(fg_idx, bg_idx, shade_idx)
        else:
            preview_img = render_preview(indices, full_block=full_block)
        preview_img.save(preview)
        print(f"Preview saved to {preview}  ({preview_img.size[0]}x{preview_img.size[1]} px)",
              file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Convert an image to ANSI art (.ans) with half-block characters.")
    parser.add_argument("input", help="Input image file (PNG, GIF, JPG, BMP, …)")
    parser.add_argument("-o", "--output", help="Output .ans file (default: stdout)")
    parser.add_argument("-w", "--width", type=int, default=80,
                        help="Output width in columns (default: 80)")
    parser.add_argument("-t", "--title", default="", help="SAUCE title")
    parser.add_argument("-a", "--author", default="", help="SAUCE author")
    parser.add_argument("-g", "--group", default="", help="SAUCE group")
    parser.add_argument("--no-ice", action="store_true",
                        help="Disable iCE colors (restrict backgrounds to dark "
                             "colors 0-7 to avoid flashing in legacy viewers)")
    parser.add_argument("--full-block", action="store_true",
                        help="Use full block characters (one cell per pixel) "
                             "instead of half-blocks.  Output is vertically "
                             "stretched but avoids half-block rendering.")
    parser.add_argument("--gradient", action="store_true",
                        help="Use gradient shading with shade characters "
                             "(░▒▓) to blend between CGA colors.  Gives "
                             "much higher effective color fidelity at the "
                             "cost of a stippled/dithered appearance.")
    parser.add_argument("-p", "--preview", metavar="FILE",
                        help="Save a PNG preview of the ANSI art")
    args = parser.parse_args()

    convert(args.input, args.output, args.width, args.title, args.author,
            args.group, ice=not args.no_ice, preview=args.preview,
            full_block=args.full_block, gradient=args.gradient)


if __name__ == "__main__":
    main()
