# Third-party notices

## GUI chess-piece images - public-domain Livius set

The twelve PNGs in `src/gui/assets/pieces/` use **Livius**, an original design
by **Martin Sedlák (kmar), 2026**. They replace the previously unverified images.

- Source repository: https://github.com/kmar/chess_svg_piece_sets
- Exact revision: `af40ea51e87eddee1ae7ee35ae312893a1271233`
- Original artwork: https://github.com/kmar/chess_svg_piece_sets/tree/af40ea51e87eddee1ae7ee35ae312893a1271233/livius
- Exact license/dedication: https://github.com/kmar/chess_svg_piece_sets/blob/af40ea51e87eddee1ae7ee35ae312893a1271233/livius/LICENSE
- Upstream statement: https://github.com/kmar/chess_svg_piece_sets/blob/af40ea51e87eddee1ae7ee35ae312893a1271233/README.md

**License: public-domain dedication.** The author describes the sets as
"CC0/public domain"; the actual supplied LICENSE is a public-domain dedication,
not the standard CC0 1.0 legal-code text. We preserve that exact dedication rather
than substitute or claim a different license. It explicitly allows reproduction,
distribution, modification and commercial/non-commercial exploitation.
No attribution condition is stated; the author credit is retained voluntarily.

Unmodified SVGs, the upstream dedication and README, and SHA-256 provenance are
bundled in `src/gui/assets/pieces/livius/`. The artwork was rasterized to transparent
256 x 256 PNGs with resvg-py 0.5.0; lowercase upstream names map to the existing
`wK/wQ/wR/wB/wN/wP` and `bK/bQ/bR/bB/bN/bP` PNG filenames. No shape/color edits
were made. resvg-py is an offline conversion tool, not a GUI dependency.
The native window icon uses the replacement `wN.png`; refreshed screenshots depict
these same public-domain pieces. No Chess.com or Chess24 artwork is bundled.
Missing assets no longer trigger the old unverified artwork download.

The project [MIT LICENSE](LICENSE) applies to ChessAI source code and associated
project documentation. It does **not** override third-party licenses or dedications;
Livius artwork remains under its own public-domain dedication.

## GUI sounds

`src/gui/gui.py` contains a sine-wave WAV generator and definitions for the
three bundled sounds (`move.wav`, `capture.wav`, `check.wav`). No external sound
download is referenced. All three bundled WAVs were reproduced byte-for-byte from
that generator during the final audit. No external sound attribution requirement
is established by repository evidence; the project MIT license applies to ChessAI-owned generator code.

## Fonts and generated visual effects

The GUI uses installed system fonts (`Segoe UI` and `Segoe UI Symbol`), with
Tk's platform font substitution available. No font files are redistributed.
Gradients, borders and controls are rendered by GUI code, without external textures.

## Stockfish

The downloaded `stockfish/` distribution and executables are ignored and are
not part of the recommended staged files. Users supply their own executable
for optional analysis/calibration; see `benchmarks/elo/README.md`.
ChessAI's MIT LICENSE does not license Stockfish.

## Training data and dependencies

The ML guides identify the Lichess evaluations export as the training data source.
Raw exports, NPZ datasets and checkpoints are excluded; small recorded metadata,
metrics and histories are retained for provenance. See `ml/README.md` and
`ml/README_V2.md`. Their source/license statements are historical repository
documentation, not a new independent licensing verification.

Python dependencies are installed separately using the requirement files;
their own licenses apply. No third-party package distribution is bundled.

ChessAI source is MIT licensed. Third-party assets and dependencies retain their
own licenses and obligations; the project MIT grant does not relicense them.
