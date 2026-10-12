"""Construct the actual Tk menu with the real engine, without opening a visible window."""
import importlib.util
from pathlib import Path
import tkinter as tk
from unittest.mock import patch

source = Path(__file__).resolve().parents[1] / "src/gui/gui.py"
spec = importlib.util.spec_from_file_location("chess_gui", source)
gui = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gui)
root = tk.Tk()
root.withdraw()
app = None
try:
    # Asset I/O is unrelated to evaluator selection; no downloads or sound creation in this test.
    with patch.object(gui.ChessGUI, "load_piece_images"), patch.object(gui.ChessGUI, "create_sound_files"):
        app = gui.ChessGUI(root)
    root.update_idletasks()
    assert app.evaluator_choice.get() == "hybrid"
    assert app.engine.command("evalmode") == "evalmode hybrid"
    assert app.engine.command("hybridalpha") == "hybridalpha 0.25"
    assert "Hybrid alpha 0.25" in app.evaluator_model_text
    assert "v2-residual-3fb0a29e8514af8c" in app.evaluator_model_text
    assert app.engine.command("evalmodes") == "evalmodes classic ml hybrid"
    print("Actual Tk menu starts with Hybrid selected; real engine alpha 0.25 and all modes available")
finally:
    if app:
        app.engine.close()
    root.destroy()
