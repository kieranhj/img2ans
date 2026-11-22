# Wrapper so that `make` works from PowerShell / Windows Terminal.
# img2ans is a single Python script: nothing to compile. The default target
# checks that it runs (Pillow + NumPy installed) and prints its usage.
# GNU make runs recipes with cmd.exe here (no sh on PATH).

PYTHON = py -3

.PHONY: all check help
all: check

check:
	@$(PYTHON) img2ans.py --help
	@echo.
	@echo Nothing to build: run img2ans.py directly, e.g.  py -3 img2ans.py catte003.gif -o out.ans -p out.png
	@echo See START_HERE.md and README.md.

help:
	@echo make        - check img2ans.py runs and print its usage
	@echo make help   - this list
