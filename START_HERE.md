# ANSI (img2ans): start here

`img2ans`: a Python 3 command-line tool that converts any image to ANSI art (`.ans`, CP437, 16-colour CGA palette, SAUCE record) using half-block, full-block or shade characters. A small finished tool, plus some sample art.

| | |
|---|---|
| GitHub | https://github.com/kieranhj/img2ans (public). Note the folder is called `ANSI`, the repo `img2ans` |
| Local path | D:\misc\mine\ANSI (moved from C:\Users\khcon\OneDrive\Projects\ANSI on 2026-11-21) |
| Branch | `master`; other branches: `wip/2026-11-tidy` |
| Last commit | 2026-04-05: Add --gradient option for shade-character color blending |

## What's in here
- `img2ans.py`: the whole tool (options: `-w` width, `-t/-a/-g` SAUCE, `--no-ice`, `--full-block`, `--gradient`, `-p` PNG preview).
- `catte003.gif`, `deadline_cat_012.ans`: committed sample art (cat by Spiny of Torment).
- README.md: full documentation. CLAUDE.md: describes the repo as an ANSI art collection (out of date: it predates the tool).
- Untracked test outputs: `catte_long.*`, `catte_test.*`, `parrot*.ans/png`, `parrot_in.png`, and `progress.md` (session notes).

## Build and run
- `make`: nothing to compile; runs `img2ans.py --help` (checks Pillow and NumPy are installed) and prints an example command. `make help` lists targets.
- Needs Python 3.8+ with `pip install Pillow numpy`.
- Example: `py -3 img2ans.py catte003.gif -o cat.ans -w 80 -p cat.png`. View `.ans` in PabloDraw or Moebius.

## Local changes
- Uncommitted: the untracked test outputs and `progress.md` listed above, plus `__pycache__/` and `.claude/` (no `.gitignore` in the repo).
- `wip/2026-11-tidy` (pushed): snapshot of those untracked files (9 files incl. `progress.md`) from the 2026-11 tidy.

## Status and next steps
- `progress.md` says the tool is feature-complete. Its cleanup list: add a `.gitignore` (test outputs, `.claude/`, `__pycache__/`), delete the `catte_test.*` outputs.
- Backlog from `progress.md`: dithering, animated GIF input, batch conversion, preview `--scale`. (Shade-character mode is done: `--gradient`.)
- CLAUDE.md could be updated to describe the tool.

## See also
- README.md, progress.md (untracked), CLAUDE.md.
