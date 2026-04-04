# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a collection of ANSI art files, not a software project. There is no build system, test suite, or package manager.

## File Formats

- **`.ans` files** — ANSI art using escape codes (ESC `[` sequences) and CP437 box-drawing/block characters. These are binary-like text files meant for display in terminals or ANSI art viewers, not for editing as plain text.
- **`.gif` files** — Rasterized versions of ANSI art pieces.

## Working with ANSI Art

- `.ans` files contain raw ANSI escape sequences and extended ASCII (CP437 encoding). Standard text tools may corrupt them — use hex editors or ANSI-aware editors.
- To view `.ans` files properly, use a terminal emulator with CP437/ANSI support or a dedicated viewer like PabloDraw or Moebius.
- The art includes metadata in the escape sequences (artist name, title, year) visible in the raw bytes.
