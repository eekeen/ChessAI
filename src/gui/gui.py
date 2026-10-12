import math
import os
import random
import struct
import subprocess
import threading
import tkinter as tk
import wave

from tkinter import messagebox, ttk, font as tkfont

try:
    from PIL import Image, ImageTk

    PIL_AVAILABLE = True

except ImportError:
    PIL_AVAILABLE = False


try:
    import winsound

except ImportError:
    winsound = None


# ============================================================
# WINDOW
# ============================================================

WINDOW_WIDTH = 1600
WINDOW_HEIGHT = 900

BOARD_SIZE = 800
SQUARE_SIZE = BOARD_SIZE // 8


# ============================================================
# SOUND
# ============================================================

# Raw amplitude of generated WAV files.
#
# 0.04 = intentionally quiet.
#
# Try 0.02 if you want it even quieter.

SOUND_VOLUME = 0.04


# ============================================================
# COLORS
# ============================================================

BACKGROUND = "#11161D"

MENU_BACKGROUND = "#11161D"
MENU_CARD = "#171D24"

PANEL_BACKGROUND = "#171D24"

HISTORY_BACKGROUND = "#151B21"

TEXT_COLOR = "#F3F5F7"

SECONDARY_TEXT = "#BFC7D1"

BUTTON_COLOR = "#458D35"
BUTTON_ACTIVE = "#54A13F"
ACCENT = "#7BD14D"
BORDER_COLOR = "#353E48"
INPUT_BACKGROUND = "#20262E"
FONT_FAMILY = "Segoe UI"

WATERMARK_COLOR = "#1C2830"


LIGHT_SQUARE = "#EEEED2"

DARK_SQUARE = "#769656"


LAST_MOVE_LIGHT = "#F5F682"

LAST_MOVE_DARK = "#BACA44"


SELECTED_LIGHT = "#F7EC6E"

SELECTED_DARK = "#ECED83"


CHECK_SQUARE = "#E45B5B"


LEGAL_DOT = "#59614F"

LEGAL_CAPTURE = "#59614F"


# ============================================================
# DIFFICULTIES
#
# The C++ controller performs the actual Elo weakening.
#
# These values mainly control the strongest search available
# to the profile.
#
# The displayed Elo values are still targets until calibrated
# through games.
# ============================================================

DIFFICULTIES = {

    500: {
        "name":
            "Beginner",

        "time":
            100,

        "depth":
            2,
    },


    1000: {
        "name":
            "Casual",

        "time":
            250,

        "depth":
            3,
    },


    1500: {
        "name":
            "Club",

        "time":
            650,

        "depth":
            4,
    },


    2000: {
        "name":
            "Expert",

        "time":
            1500,

        "depth":
            7,
    },
}


# ============================================================
# PIECES
# ============================================================

PIECE_FILES = {

    "K":
        "wK",

    "Q":
        "wQ",

    "R":
        "wR",

    "B":
        "wB",

    "N":
        "wN",

    "P":
        "wP",


    "k":
        "bK",

    "q":
        "bQ",

    "r":
        "bR",

    "b":
        "bB",

    "n":
        "bN",

    "p":
        "bP",
}


UNICODE_PIECES = {

    "K":
        "♔",

    "Q":
        "♕",

    "R":
        "♖",

    "B":
        "♗",

    "N":
        "♘",

    "P":
        "♙",


    "k":
        "♚",

    "q":
        "♛",

    "r":
        "♜",

    "b":
        "♝",

    "n":
        "♞",

    "p":
        "♟",
}


# ============================================================
# ENGINE
# ============================================================

class ChessEngine:

    def __init__(self):

        self.project_root = (
            self.find_project_root()
        )


        possible_paths = [

            os.path.join(
                self.project_root,
                "build",
                "Release",
                "ChessAI.exe"
            ),


            os.path.join(
                self.project_root,
                "build",
                "Debug",
                "ChessAI.exe"
            ),
        ]


        self.engine_path = None


        for path in possible_paths:

            if os.path.exists(
                path
            ):

                self.engine_path = (
                    path
                )

                break


        if self.engine_path is None:

            raise FileNotFoundError(

                "Could not find ChessAI.exe.\n\n"

                +

                "\n".join(
                    possible_paths
                )
            )


        creation_flags = 0


        if os.name == "nt":

            creation_flags = (
                subprocess.CREATE_NO_WINDOW
            )


        self.process = (
            subprocess.Popen(

                [
                    self.engine_path
                ],

                stdin=
                    subprocess.PIPE,

                stdout=
                    subprocess.PIPE,

                stderr=
                    subprocess.PIPE,

                text=True,

                bufsize=1,

                creationflags=
                    creation_flags
            )
        )


        response = (
            self.process
            .stdout
            .readline()
            .strip()
        )


        if response != "ready":

            raise RuntimeError(

                "Engine did not respond "
                "with 'ready'.\n"

                f"Received: {response}"
            )


    # ========================================================
    # PROJECT ROOT
    # ========================================================

    def find_project_root(
        self
    ):

        current = (
            os.path.abspath(

                os.path.dirname(
                    __file__
                )
            )
        )


        while True:

            cmake = os.path.join(

                current,

                "CMakeLists.txt"
            )


            if os.path.exists(
                cmake
            ):

                return current


            parent = (
                os.path.dirname(
                    current
                )
            )


            if parent == current:

                raise FileNotFoundError(

                    "Could not find "
                    "ChessAI project root."
                )


            current = parent


    # ========================================================
    # COMMAND
    # ========================================================

    def command(
        self,
        command
    ):

        if (
            self.process.poll()
            is not None
        ):

            raise RuntimeError(

                "ChessAI engine "
                "is not running."
            )


        self.process.stdin.write(

            command +
            "\n"
        )


        self.process.stdin.flush()


        return (

            self.process
            .stdout
            .readline()
            .strip()
        )


    # ========================================================
    # PROTOCOL HELPERS
    # ========================================================

    def new_game(
        self
    ):

        return self.command(
            "newgame"
        )


    def get_position(
        self
    ):

        response = (
            self.command(
                "position"
            )
        )


        if not response.startswith(
            "position "
        ):

            raise RuntimeError(

                "Unexpected engine "
                f"response: {response}"
            )


        return response.split(
            " ",
            1
        )[1]


    def get_state(
        self
    ):

        response = (
            self.command(
                "state"
            )
        )


        if not response.startswith(
            "state "
        ):

            return "unknown"


        return response.split(
            " ",
            1
        )[1]


    def get_legal_moves(
        self,
        square
    ):

        response = (
            self.command(

                f"legal "
                f"{square}"
            )
        )


        parts = (
            response.split()
        )


        if not parts:

            return []


        return parts[1:]


    def get_check(
        self
    ):

        return self.command(
            "check"
        )


    def make_move(
        self,
        move
    ):

        return self.command(

            f"move "
            f"{move}"
        )


    def engine_move(
        self,
        milliseconds,
        max_depth,
        elo
    ):

        return self.command(

            f"go "
            f"{milliseconds} "
            f"{max_depth} "
            f"{elo}"
        )


    # ========================================================
    # CLOSE
    # ========================================================

    def close(
        self
    ):

        if (
            self.process.poll()
            is None
        ):

            try:

                self.command(
                    "quit"
                )

            except Exception:

                pass


            try:

                self.process.terminate()

            except Exception:

                pass


# ============================================================
# GUI
# ============================================================

def rounded_rectangle(canvas, x1, y1, x2, y2, radius=10, **options):
    """A small, dependency-free rounded shape for dark desktop controls."""
    radius = min(radius, (x2 - x1) / 2, (y2 - y1) / 2)
    points = [x1 + radius, y1, x2 - radius, y1, x2, y1,
              x2, y1 + radius, x2, y2 - radius, x2, y2,
              x2 - radius, y2, x1 + radius, y2, x1, y2,
              x1, y2 - radius, x1, y1 + radius, x1, y1]
    return canvas.create_polygon(points, smooth=True, splinesteps=24, **options)


def button_gradient(canvas, width, height, top, bottom, radius=9):
    start = tuple(int(top[i:i + 2], 16) for i in (1, 3, 5))
    end = tuple(int(bottom[i:i + 2], 16) for i in (1, 3, 5))
    for y in range(2, max(2, height - 2), 2):
        ratio = y / max(1, height)
        rgb = tuple(round(a + (b - a) * ratio) for a, b in zip(start, end))
        dy = max(radius - y, y - (height - radius), 0)
        inset = radius - math.sqrt(max(0, radius * radius - dy * dy))
        canvas.create_rectangle(2 + inset, y, width - 3 - inset, min(height - 2, y + 2),
                                fill="#{:02x}{:02x}{:02x}".format(*rgb), outline="")


class RoundedPanel(tk.Canvas):
    def __init__(self, parent, color=PANEL_BACKGROUND, padding=20, **options):
        super().__init__(parent, bg=parent.cget("bg"), highlightthickness=0,
                         borderwidth=0, **options)
        self.color, self.padding = color, padding
        self.body = tk.Frame(self, bg=color)
        # Normal widget geometry avoids stale Canvas window clipping on Windows.
        self.body.place(x=padding, y=padding, relwidth=1, width=-2 * padding,
                         relheight=1, height=-2 * padding)
        self.bind("<Configure>", self._resize)

    def _resize(self, event):
        self.delete("surface")
        rounded_rectangle(self, 1, 1, event.width - 2, event.height - 2,
                          radius=20, fill=self.color, outline=BORDER_COLOR,
                          width=1, tags="surface")
        self.tag_lower("surface")


class RoundedButton(tk.Canvas):
    """Canvas styling with normal button state and keyboard activation."""
    def __init__(self, parent, text, command, primary=False, height=48,
                 font_size=12, bold=True, **options):
        super().__init__(parent, bg=parent.cget("bg"), highlightthickness=0,
                         borderwidth=0, height=height, width=100, takefocus=True,
                         cursor="hand2", **options)
        self.text, self.command, self.primary = text, command, primary
        self.font_size, self.state, self.hover = font_size, "normal", False
        self.bold = bold
        self.on_state_change = None
        self.bind("<Configure>", lambda event: self._paint())
        self.bind("<Enter>", lambda event: self._hover(True))
        self.bind("<Leave>", lambda event: self._hover(False))
        self.bind("<Button-1>", lambda event: self.invoke())
        self.bind("<Return>", lambda event: self.invoke())
        self.bind("<space>", lambda event: self.invoke())
        self.bind("<FocusIn>", lambda event: self._paint())
        self.bind("<FocusOut>", lambda event: self._paint())

    def _hover(self, hover):
        self.hover = hover
        self._paint()

    def _paint(self):
        self.delete("all")
        width, height = self.winfo_width(), self.winfo_height()
        fill = BUTTON_ACTIVE if self.primary and self.hover else BUTTON_COLOR if self.primary else INPUT_BACKGROUND
        if self.state == "disabled":
            fill = INPUT_BACKGROUND
        outline = ACCENT if self.primary or self.focus_get() == self else BORDER_COLOR
        rounded_rectangle(self, 1, 1, width - 2, height - 2, radius=9,
                          fill=fill, outline=outline, width=1)
        if self.primary and self.state != "disabled":
            button_gradient(self, width, height, "#55A341" if self.hover else "#4C9639",
                            "#458D35" if self.hover else "#3F8031")
        self.create_text(width / 2, height / 2, text=self.text,
                         fill=SECONDARY_TEXT if self.state == "disabled" else TEXT_COLOR,
                         font=(FONT_FAMILY, self.font_size, "bold" if self.bold else "normal"))

    def configure(self, cnf=None, **options):
        if cnf:
            options.update(cnf)
        state_changed = "state" in options
        for name in ("state", "text", "command"):
            if name in options:
                setattr(self, name, options.pop(name))
        if options:
            super().configure(**options)
        if hasattr(self, "text"):
            self._paint()
        if state_changed and getattr(self, "on_state_change", None):
            self.on_state_change(self.state)

    config = configure

    def invoke(self):
        if self.state != "disabled":
            self.focus_set()
            self.command()


class DarkDropdown(RoundedButton):
    def __init__(self, parent, variable, choices, command=None):
        self.variable, self.choices, self.on_change = variable, choices, command
        super().__init__(parent, "", self._open, height=44, font_size=11)
        self.menu = tk.Menu(self, tearoff=False, bg=INPUT_BACKGROUND,
                            fg=TEXT_COLOR, activebackground=BUTTON_COLOR,
                            activeforeground=TEXT_COLOR, relief="flat", borderwidth=1,
                            font=(FONT_FAMILY, 11))
        for value, label in choices:
            self.menu.add_radiobutton(label=label, variable=variable, value=value,
                                      command=self._changed, selectcolor=ACCENT)
        self.trace_id = variable.trace_add("write", lambda *args: self._paint())
        self.bind("<Destroy>", self._destroy_trace, add="+")
        self.bind("<Down>", lambda event: self.invoke())
        self.bind("<Alt-Down>", lambda event: self.invoke())

    def _destroy_trace(self, event):
        if event.widget == self:
            self.variable.trace_remove("write", self.trace_id)

    def _paint(self):
        super()._paint()
        self.delete("all")
        width, height = self.winfo_width(), self.winfo_height()
        rounded_rectangle(self, 1, 1, width - 2, height - 2, radius=9,
                          fill=INPUT_BACKGROUND,
                          outline=ACCENT if self.focus_get() == self else BORDER_COLOR)
        label = dict(self.choices).get(self.variable.get(), "Unavailable")
        font = tkfont.Font(family=FONT_FAMILY, size=12)
        full_label = label
        while label and font.measure(label) > max(1, width - 54):
            label = label[:-1]
        if label != full_label:
            label = label[:-1].rstrip() + "…"
        self.create_text(16, height / 2, text=label, anchor="w",
                         fill=SECONDARY_TEXT if self.state == "disabled" else TEXT_COLOR,
                         font=(FONT_FAMILY, 12))
        self.create_line(width - 28, height / 2 - 3, width - 22, height / 2 + 3,
                         width - 16, height / 2 - 3, fill=SECONDARY_TEXT, width=2)

    def _open(self):
        try:
            self.menu.tk_popup(self.winfo_rootx(), self.winfo_rooty() + self.winfo_height())
        finally:
            self.menu.grab_release()

    def _changed(self):
        if self.on_change:
            self.on_change()
        self._paint()


class StatusLabel(tk.Label):
    def __init__(self, parent, app, **options):
        self.app = app
        super().__init__(parent, **options)

    def configure(self, cnf=None, **options):
        if cnf:
            options.update(cnf)
        if options.get("text") == "Your move":
            options["text"] = "Your move (White)" if self.app.player_is_white else "Your move (Black)"
        if "text" in options:
            options["fg"] = SECONDARY_TEXT if "thinking" in options["text"] else ACCENT
            self.app.set_controls_enabled(not self.app.engine_thinking)
        return super().configure(**options)

    config = configure


class SearchInfo(tk.Label):
    def __init__(self, parent, app):
        self.app = app
        super().__init__(parent, text="")

    def configure(self, cnf=None, **options):
        if cnf:
            options.update(cnf)
        if "text" in options:
            self.app.show_search_info(options["text"])
        return super().configure(**options)

    config = configure


class Tooltip:
    def __init__(self, widget, text):
        self.widget, self.text, self.window, self.timer = widget, text, None, None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<Destroy>", self._hide, add="+")

    def _schedule(self, event):
        self.timer = self.widget.after(500, self._show)

    def _show(self):
        self.timer = None
        text = self.text() if callable(self.text) else self.text
        if not text:
            return
        self.window = tk.Toplevel(self.widget)
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.geometry(f"+{self.widget.winfo_rootx()}+{self.widget.winfo_rooty() + self.widget.winfo_height() + 6}")
        tk.Label(self.window, text=text, justify="left", bg=INPUT_BACKGROUND,
                 fg=TEXT_COLOR, padx=12, pady=10, font=(FONT_FAMILY, 10),
                 relief="solid", borderwidth=1).pack()

    def _hide(self, event=None):
        if self.timer:
            self.widget.after_cancel(self.timer)
            self.timer = None
        if self.window:
            self.window.destroy()
            self.window = None


class GradientBackdrop(tk.Canvas):
    def __init__(self, parent):
        super().__init__(parent, bg=BACKGROUND, highlightthickness=0, borderwidth=0)
        self.bind("<Configure>", self._paint)
        self.source = None
        if PIL_AVAILABLE:
            self.source = Image.new("RGB", (200, 120))
            pixels = self.source.load()
            for y in range(120):
                for x in range(200):
                    cool = math.exp(-((x - 35) ** 2 / 10000 + (y - 15) ** 2 / 3000))
                    green = math.exp(-((x - 165) ** 2 / 6500 + (y - 100) ** 2 / 2000))
                    pixels[x, y] = (int(15 + cool * 3 + green * 2),
                                    int(20 + cool * 5 + green * 6),
                                    int(26 + cool * 7 + green * 2))

    def _paint(self, event):
        self.delete("background")
        if self.source:
            self.photo = ImageTk.PhotoImage(self.source.resize((event.width, event.height), Image.BILINEAR))
            self.create_image(0, 0, image=self.photo, anchor="nw", tags="background")
        else:
            for y in range(0, event.height, 16):
                shade = int(20 + 5 * y / max(1, event.height))
                self.create_rectangle(0, y, event.width, y + 16,
                                      fill=f"#11{shade:02x}1d",
                                      outline="", tags="background")
        self.tag_lower("background")


class ChessGUI:

    def __init__(
        self,
        root
    ):

        self.root = root


        self.root.title(
            "ChessAI"
        )


        self.root.geometry(

            f"{WINDOW_WIDTH}"
            f"x"
            f"{WINDOW_HEIGHT}"
        )


        self.root.configure(
            bg=BACKGROUND
        )


        self.root.resizable(True, True)
        self.root.minsize(1100, 720)


        # ====================================================
        # ENGINE
        # ====================================================

        try:

            self.engine = (
                ChessEngine()
            )


        except Exception as error:

            messagebox.showerror(

                "ChessAI",

                str(
                    error
                )
            )


            self.root.destroy()

            return


        # ====================================================
        # GAME STATE
        # ====================================================

        self.position = (
            "." * 64
        )


        self.player_is_white = (
            True
        )


        self.selected_square = (
            None
        )


        self.legal_moves = []


        self.legal_targets = {}


        self.last_move = None


        self.check_king_index = (
            None
        )


        self.engine_thinking = (
            False
        )


        self.move_history = []


        self.difficulty = 1000


        self.piece_images = {}


        self.sound_files = {}


        # ====================================================
        # LOAD ASSETS
        # ====================================================

        self.load_piece_images()

        if "N" in self.piece_images:
            self.root.iconphoto(True, self.piece_images["N"])
        self.root.after_idle(self._style_native_titlebar)


        self.create_sound_files()


        # ====================================================
        # MENU
        # ====================================================

        self.show_main_menu()


        self.root.protocol(

            "WM_DELETE_WINDOW",

            self.on_close
        )


    # ========================================================
    # CLEAR WINDOW
    # ========================================================

    def clear_window(
        self
    ):

        for widget in (
            self.root
            .winfo_children()
        ):

            widget.destroy()


    # ========================================================
    # MAIN MENU
    # ========================================================

    def show_main_menu(self):
        if self.engine_thinking:
            return
        self.side_choice = tk.StringVar(value="white")
        self.difficulty_choice = tk.IntVar(value=1000)
        self.available_modes = self.engine.command("evalmodes").split()[1:]
        current_mode = self.engine.command("evalmode").split()[-1]
        hybrid_alpha = self.engine.command("hybridalpha").split()[-1]
        self.evaluator_model_text = f"{self.engine.command('model').removeprefix('model ')} | Hybrid alpha {hybrid_alpha}"
        self.evaluator_choice = tk.StringVar(value=current_mode)
        self.board_flipped = False
        self._build_layout(setup=True)
        self.refresh_position()
        self.status_label.config(text="Ready to play")



    # ========================================================
    # START GAME
    # ========================================================

    def start_game(
        self
    ):

        side = (
            self.side_choice
            .get()
        )


        if side == "random":

            self.player_is_white = (
                random.choice(
                    [
                        True,
                        False
                    ]
                )
            )


        else:

            self.player_is_white = (

                side ==
                "white"
            )


        self.difficulty = (
            self.difficulty_choice
            .get()
        )


        self.engine.new_game()

        response = self.engine.command(f"evalmode {self.evaluator_choice.get()}")
        if response != "ok":
            messagebox.showerror("Evaluator", response)
            return


        self.selected_square = (
            None
        )


        self.legal_moves = []


        self.legal_targets = {}


        self.last_move = None


        self.check_king_index = (
            None
        )


        self.engine_thinking = (
            False
        )


        self.move_history = []


        self.build_game_view()


        self.refresh_position()


        self.update_history()


        self.update_check_status()


        if self.player_is_white:

            self.status_label.config(
                text="Your move"
            )


        else:

            self.start_engine_move()


    # ========================================================
    # GAME VIEW
    # ========================================================

    def build_game_view(self):
        self.board_flipped = not self.player_is_white
        self._build_layout(setup=False)



    # ========================================================
    # LOAD PIECE IMAGES
    # ========================================================

    def _build_layout(self, setup):
        self.clear_window()
        self._setup = setup
        self._current_mode = self.engine.command("evalmode").split()[-1]
        self.square_size = SQUARE_SIZE
        self.backdrop = GradientBackdrop(self.root)
        self.backdrop.pack(fill="both", expand=True)
        self.main_frame = tk.Frame(self.backdrop, bg=BACKGROUND)
        self.main_frame.place(x=20, y=18)
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.columnconfigure(1, weight=0)
        self.main_frame.rowconfigure(0, weight=1)
        self.board_area = tk.Frame(self.main_frame, bg=BACKGROUND)
        self.board_area.grid(row=0, column=0, sticky="nsew", padx=(0, 28))
        self.board_area.bind("<Configure>", self._resize_board)
        self.board_frame = tk.Frame(self.board_area, bg=BACKGROUND)
        self.board_frame.place(relx=.5, rely=.5, anchor="center")
        self.rank_canvas = tk.Canvas(self.board_frame, width=28, height=BOARD_SIZE,
                                     bg=BACKGROUND, highlightthickness=0)
        self.rank_canvas.grid(row=0, column=0)
        self.board_canvas = tk.Canvas(self.board_frame, width=BOARD_SIZE, height=BOARD_SIZE,
                                      bg=BACKGROUND, highlightthickness=0, cursor="hand2")
        self.board_canvas.grid(row=0, column=1)
        self.board_canvas.bind("<Button-1>", self.on_board_click)
        self.file_canvas = tk.Canvas(self.board_frame, width=BOARD_SIZE, height=28,
                                     bg=BACKGROUND, highlightthickness=0)
        self.file_canvas.grid(row=1, column=1)
        self.sidebar_surface = RoundedPanel(self.main_frame, width=520, padding=28)
        self.sidebar_surface.grid(row=0, column=1, sticky="nsew")
        self.side_panel = self.sidebar_surface.body
        self.side_panel.columnconfigure(0, weight=1)
        self.side_panel.rowconfigure(5, weight=1)

        header = tk.Frame(self.side_panel, bg=PANEL_BACKGROUND)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 18))
        self._label(header, "ChessAI", 32, bold=True).pack(anchor="w")
        self._label(header, "C++ Chess Engine", 15, color=SECONDARY_TEXT).pack(anchor="w", pady=(0, 2))

        controls = tk.Frame(self.side_panel, bg=PANEL_BACKGROUND)
        controls.grid(row=1, column=0, sticky="ew", pady=(0, 18))
        controls.columnconfigure(0, weight=1, uniform="controls")
        controls.columnconfigure(1, weight=1, uniform="controls")
        sides = tk.Frame(controls, bg=PANEL_BACKGROUND)
        self.side_area = sides
        sides.grid(row=0, column=0, sticky="ew", padx=(0, 12))
        heading = tk.Frame(sides, bg=PANEL_BACKGROUND)
        heading.pack(fill="x", pady=(0, 6))
        self._label(heading, "Side", 12).pack(side="left")
        self.random_side_label = self._label(heading, "Random", 9, color=SECONDARY_TEXT)
        self.random_side_label.pack(side="right")
        self.random_side_label.configure(cursor="hand2")
        self.random_side_label.bind("<Button-1>", self._choose_random_side)
        Tooltip(self.random_side_label, "Randomly choose your side when starting a New Game.")
        segment = tk.Frame(sides, bg=PANEL_BACKGROUND)
        segment.pack(fill="x")
        segment.columnconfigure(0, weight=1, uniform="sides")
        segment.columnconfigure(1, weight=1, uniform="sides")
        self.side_buttons = []
        for column, value in enumerate(("white", "black")):
            button = RoundedButton(segment, "", lambda side=value: self._choose_side(side),
                                   height=44, font_size=11, bold=False)
            button.grid(row=0, column=column, sticky="ew", padx=(0, 2) if column == 0 else (2, 0))
            self.side_buttons.append(button)
            Tooltip(button, "Side selection applies to New Game.")
        self._paint_side_choices()
        difficulty = tk.Frame(controls, bg=PANEL_BACKGROUND)
        self.difficulty_area = difficulty
        difficulty.grid(row=0, column=1, sticky="ew", padx=(12, 0))
        self._label(difficulty, "Difficulty", 12).pack(anchor="w", pady=(0, 6))
        # Display names only: the original ratings/time/depth profiles are unchanged.
        self.difficulty_dropdown = DarkDropdown(difficulty, self.difficulty_choice,
                                                [(500, "Beginner"), (1000, "Medium"),
                                                 (1500, "Club"), (2000, "Expert")])
        self.difficulty_dropdown.pack(fill="x")
        Tooltip(self.difficulty_dropdown, "Applies to New Game. Medium is the existing Casual profile.\nDifficulty labels are not calibrated human Elo ratings.")

        evaluator = tk.Frame(self.side_panel, bg=PANEL_BACKGROUND)
        evaluator.grid(row=2, column=0, sticky="ew", pady=(0, 18))
        self._label(evaluator, "Evaluator", 12).pack(anchor="w", pady=(0, 6))
        labels = {"classic": "Classic (Handcrafted)", "ml": "ML (Direct Neural Evaluation)",
                  "hybrid": "Hybrid (Opening + Middlegame + Endgame)"}
        self.evaluator_dropdown = DarkDropdown(evaluator, self.evaluator_choice,
                                               [(mode, labels[mode]) for mode in ("classic", "ml", "hybrid")
                                                if mode in self.available_modes])
        self.evaluator_dropdown.pack(fill="x")
        self.evaluator_tooltip = Tooltip(self.evaluator_dropdown, lambda: f"{labels[self.evaluator_choice.get()]}\n{self.evaluator_model_text}\nSelection applies to New Game.")

        self.status_surface = RoundedPanel(self.side_panel, color="#1C2229", padding=16, height=92)
        self.status_surface.grid(row=3, column=0, sticky="ew", pady=(0, 18))
        status = self.status_surface.body
        status.columnconfigure(0, weight=1)
        self._label(status, "Game Status", 11, color=SECONDARY_TEXT).grid(row=0, column=0, sticky="w")
        self.status_label = StatusLabel(status, self, text="Your move", bg="#1C2229",
                                        fg=ACCENT, font=(FONT_FAMILY, 13, "bold"), anchor="w")
        self.status_label.grid(row=1, column=0, sticky="w", pady=(2, 0))
        self.eval_label = self._label(status, "Eval: —", 11, color=ACCENT)
        self.eval_label.grid(row=0, column=1, sticky="e", padx=(10, 0))
        self.depth_label = self._label(status, "Depth: —", 11, color=SECONDARY_TEXT)
        self.depth_label.grid(row=1, column=1, sticky="e", padx=(10, 0))
        self.engine_info = SearchInfo(status, self)
        for widget in (self.status_surface, self.status_label, self.eval_label, self.depth_label):
            Tooltip(widget, lambda: "Eval is current static evaluation in pawns, White-relative.\nDepth is from the last engine search.\n" + self.engine_info.cget("text"))

        self._label(self.side_panel, "Moves", 12, color=SECONDARY_TEXT).grid(row=4, column=0, sticky="w", pady=(0, 6))
        self.history_surface = RoundedPanel(self.side_panel, color=HISTORY_BACKGROUND, padding=10)
        self.history_surface.grid(row=5, column=0, sticky="nsew")
        history = self.history_surface.body
        history.columnconfigure(0, weight=1)
        history.rowconfigure(0, weight=1)
        self._style_history()
        self.history_tree = ttk.Treeview(history, columns=("number", "white", "black"),
                                         show="", selectmode="browse", style="ChessAI.Treeview", height=4)
        self.history_tree.column("number", width=44, minwidth=36, stretch=False)
        self.history_tree.column("white", width=120, minwidth=90, stretch=True)
        self.history_tree.column("black", width=120, minwidth=90, stretch=True)
        self.history_tree.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(history, orient="vertical", command=self.history_tree.yview,
                                   style="ChessAI.Vertical.TScrollbar")
        scrollbar.grid(row=0, column=1, sticky="ns", padx=(6, 0))
        self.history_tree.configure(yscrollcommand=scrollbar.set)

        actions = tk.Frame(self.side_panel, bg=PANEL_BACKGROUND)
        actions.grid(row=6, column=0, sticky="ew", pady=(20, 0))
        actions.columnconfigure(0, weight=1, uniform="actions")
        actions.columnconfigure(1, weight=1, uniform="actions")
        self.new_game_button = RoundedButton(actions, "▶   New Game", self._request_new_game,
                                             primary=True, height=60, font_size=14)
        self.new_game_button.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.new_game_button.on_state_change = lambda state: self.set_controls_enabled(state != "disabled")
        self.flip_button = RoundedButton(actions, "⇄   Flip Board", self.flip_board, height=60, font_size=14)
        self.flip_button.grid(row=0, column=1, sticky="ew", padx=(10, 0))
        self.backdrop.bind("<Configure>", self._resize_layout, add="+")
        self.draw_board()
        if not setup:
            self.update_history()


    @staticmethod
    def _label(parent, text, size, bold=False, color=TEXT_COLOR):
        return tk.Label(parent, text=text, bg=parent.cget("bg"), fg=color,
                         font=(FONT_FAMILY, size, "bold" if bold else "normal"), anchor="w")


    def _style_history(self):
        style = ttk.Style(self.root)
        # 'clam' supplies portable styling; no native white fields leak into the theme.
        if style.theme_use() != "clam":
            style.theme_use("clam")
        style.configure("ChessAI.Treeview", background=HISTORY_BACKGROUND,
                         fieldbackground=HISTORY_BACKGROUND, foreground=TEXT_COLOR,
                         borderwidth=0, relief="flat", rowheight=30, font=(FONT_FAMILY, 11))
        style.layout("ChessAI.Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
        style.map("ChessAI.Treeview", background=[("selected", "#303841")],
                   foreground=[("selected", TEXT_COLOR)])
        style.configure("ChessAI.Vertical.TScrollbar", background="#4B535E",
                         troughcolor=HISTORY_BACKGROUND, bordercolor=HISTORY_BACKGROUND,
                         arrowcolor=SECONDARY_TEXT, lightcolor="#4B535E", darkcolor="#4B535E",
                         gripcount=0, width=14, borderwidth=0)
        style.map("ChessAI.Vertical.TScrollbar", background=[("active", "#65717E")])


    def _resize_layout(self, event):
        panel_width = max(370, min(580, int((event.width - 40) * .35)))
        height = max(1, event.height - 36)
        # Center the board+panel as a unit; preserve the reference's narrow gap.
        width = min(event.width - 40, height - 28 + 28 + 28 + panel_width)
        self.main_frame.place_configure(x=(event.width - width) / 2, y=18,
                                         width=max(1, width), height=height)
        self.sidebar_surface.configure(width=panel_width)
        compact = panel_width < 460
        self._compact = compact
        self._paint_side_choices()
        self.status_label.configure(wraplength=max(150, panel_width - 220),
                                     font=(FONT_FAMILY, 11 if compact else 13, "bold"))
        for button in (self.new_game_button, self.flip_button):
            button.font_size = 11 if compact else 14
            button.config()
        if getattr(self, "_resize_redraw_id", None):
            self.root.after_cancel(self._resize_redraw_id)
        self._resize_redraw_id = self.root.after(80, self._redraw_layout)

    def _redraw_layout(self):
        """Invalidate child surfaces after a resize (older Windows Tk needs this)."""
        self._resize_redraw_id = None
        def expose(widget):
            if widget.winfo_ismapped():
                widget.event_generate("<Expose>")
            for child in widget.winfo_children():
                expose(child)
        expose(self.main_frame)

    def _style_native_titlebar(self):
        """Use Windows' dark native chrome when supported; keep normal OS controls."""
        if os.name != "nt":
            return
        try:
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.WinDLL("user32")
            user32.GetParent.argtypes = [wintypes.HWND]
            user32.GetParent.restype = wintypes.HWND
            handle = user32.GetParent(self.root.winfo_id())
            dwm = ctypes.WinDLL("dwmapi")
            dwm.DwmSetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD,
                                                 ctypes.c_void_p, wintypes.DWORD]
            dark = ctypes.c_int(1)
            for attribute in (20, 19):
                if dwm.DwmSetWindowAttribute(handle, attribute, ctypes.byref(dark),
                                             ctypes.sizeof(dark)) == 0:
                    break
        except (OSError, AttributeError):
            pass


    def _resize_board(self, event):
        size = max(32, int(min(event.width - 28, event.height - 28) // 8))
        if size == self.square_size:
            return
        self.square_size = size
        board = size * 8
        self.board_canvas.configure(width=board, height=board)
        self.rank_canvas.configure(height=board)
        self.file_canvas.configure(width=board)
        self._scale_piece_images()
        self.draw_board()


    def _scale_piece_images(self):
        if not self.piece_images:
            return
        if not hasattr(self, "_piece_originals"):
            self._piece_originals = {}
            directory = os.path.join(os.path.dirname(__file__), "assets", "pieces")
            for piece, name in PIECE_FILES.items():
                filename = os.path.join(directory, name + ".png")
                if PIL_AVAILABLE:
                    with Image.open(filename) as image:
                        self._piece_originals[piece] = image.convert("RGBA")
                else:
                    self._piece_originals[piece] = tk.PhotoImage(file=filename)
        target = max(24, int(self.square_size * .94))
        for piece, image in self._piece_originals.items():
            if PIL_AVAILABLE:
                self.piece_images[piece] = ImageTk.PhotoImage(image.resize((target, target), Image.LANCZOS))
            else:
                factor = max(1, math.ceil(max(image.width(), image.height()) / target))
                self.piece_images[piece] = image.subsample(factor, factor)


    def _choose_side(self, side):
        if not self.engine_thinking:
            self.side_choice.set(side)
            self._paint_side_choices()


    def _choose_random_side(self, event=None):
        self._choose_side("random")


    def _paint_side_choices(self):
        choice = self.side_choice.get()
        for button, side in zip(self.side_buttons, ("white", "black")):
            button.primary = side == choice
            suffix = "" if getattr(self, "_compact", False) else " (You)" if side == choice else " (AI)"
            button.config(text=side.title() + suffix)
        self.random_side_label.config(fg=ACCENT if choice == "random" else SECONDARY_TEXT)


    def set_controls_enabled(self, enabled):
        state = "normal" if enabled else "disabled"
        for control in [*getattr(self, "side_buttons", []),
                        getattr(self, "difficulty_dropdown", None),
                        getattr(self, "evaluator_dropdown", None)]:
            if control and control.winfo_exists():
                control.config(state=state)


    def _request_new_game(self):
        if not self.engine_thinking:
            self.start_game()


    def flip_board(self):
        self.board_flipped = not self.board_flipped
        self.draw_board()


    def _refresh_evaluation(self):
        if self.engine_thinking:
            return
        parts = self.engine.command("evaluate").split()[1:]
        values = dict(zip(parts[::2], parts[1::2]))
        try:
            score = float(values[self._current_mode]) / 100
        except (KeyError, ValueError):
            self.eval_label.config(text="Eval: —", fg=SECONDARY_TEXT)
        else:
            self.eval_label.config(text=f"Eval: {score:+.2f}",
                                   fg=ACCENT if score >= 0 else "#EAA894")


    def show_search_info(self, text):
        depth = next((line.removeprefix("Depth: ") for line in text.splitlines()
                      if line.startswith("Depth: ")), "—")
        self.depth_label.config(text=f"Depth: {depth}")


    def load_piece_images(
        self
    ):

        assets_directory = (
            os.path.join(

                os.path.dirname(
                    __file__
                ),

                "assets",

                "pieces"
            )
        )


        os.makedirs(

            assets_directory,

            exist_ok=True
        )


        try:

            for (
                board_character,
                piece_name

            ) in PIECE_FILES.items():


                filename = (

                    piece_name +
                    ".png"
                )


                local_path = (
                    os.path.join(

                        assets_directory,

                        filename
                    )
                )


                if not os.path.exists(
                    local_path
                ):

                    raise FileNotFoundError(
                        "Bundled piece asset missing: " + local_path
                    )


                if PIL_AVAILABLE:

                    image = (
                        Image.open(
                            local_path
                        )
                        .convert(
                            "RGBA"
                        )
                    )


                    target_size = int(

                        SQUARE_SIZE *
                        0.94
                    )


                    image = image.resize(

                        (
                            target_size,
                            target_size
                        ),

                        Image.LANCZOS
                    )


                    photo = (
                        ImageTk.PhotoImage(
                            image
                        )
                    )


                else:

                    photo = (
                        tk.PhotoImage(
                            file=
                                local_path
                        )
                    )


                    maximum = max(

                        photo.width(),

                        photo.height()
                    )


                    target = int(

                        SQUARE_SIZE *
                        0.94
                    )


                    if maximum > target:

                        factor = (
                            math.ceil(

                                maximum /
                                target
                            )
                        )


                        photo = (
                            photo.subsample(

                                factor,
                                factor
                            )
                        )


                self.piece_images[
                    board_character
                ] = photo


        except Exception as error:

            self.piece_images = {}


            print(

                "Piece image error:",

                error
            )


    # ========================================================
    # SOUND FILES
    # ========================================================

    def create_sound_files(
        self
    ):

        if winsound is None:

            return


        sounds_directory = (
            os.path.join(

                os.path.dirname(
                    __file__
                ),

                "assets",

                "sounds"
            )
        )


        os.makedirs(

            sounds_directory,

            exist_ok=True
        )


        definitions = {

            "move": [
                (
                    500,
                    55
                )
            ],


            "capture": [

                (
                    390,
                    45
                ),

                (
                    290,
                    60
                )
            ],


            "check": [

                (
                    680,
                    55
                ),

                (
                    880,
                    75
                )
            ],
        }


        for (
            name,
            notes

        ) in definitions.items():


            path = os.path.join(

                sounds_directory,

                f"{name}.wav"
            )


            self.generate_sound_file(

                path,
                notes
            )


            self.sound_files[
                name
            ] = path


    # ========================================================
    # GENERATE LOW-VOLUME WAV
    # ========================================================

    def generate_sound_file(
        self,
        path,
        notes
    ):

        sample_rate = 44100


        maximum_amplitude = int(

            32767 *
            SOUND_VOLUME
        )


        frames = []


        for (
            frequency,
            duration_ms

        ) in notes:


            sample_count = int(

                sample_rate *

                duration_ms /

                1000
            )


            fade_samples = min(

                int(
                    sample_rate *
                    0.008
                ),

                max(
                    1,
                    sample_count // 2
                )
            )


            for sample in range(
                sample_count
            ):


                time_value = (

                    sample /
                    sample_rate
                )


                envelope = 1.0


                if (
                    sample <
                    fade_samples
                ):

                    envelope = (

                        sample /
                        fade_samples
                    )


                elif (
                    sample >
                    sample_count -
                    fade_samples
                ):

                    envelope = (

                        (
                            sample_count -
                            sample
                        )
                        /
                        fade_samples
                    )


                value = int(

                    maximum_amplitude *

                    envelope *

                    math.sin(

                        2.0 *

                        math.pi *

                        frequency *

                        time_value
                    )
                )


                frames.append(

                    struct.pack(

                        "<h",

                        value
                    )
                )


        with wave.open(
            path,
            "wb"
        ) as wav_file:


            wav_file.setnchannels(
                1
            )


            wav_file.setsampwidth(
                2
            )


            wav_file.setframerate(
                sample_rate
            )


            wav_file.writeframes(

                b"".join(
                    frames
                )
            )


    # ========================================================
    # POSITION
    # ========================================================

    def refresh_position(self):
        self.position = self.engine.get_position()
        self.draw_board()
        self._refresh_evaluation()



    # ========================================================
    # BOARD ORIENTATION
    # ========================================================

    def display_to_board_index(self, display_index):
        return 63 - display_index if self.board_flipped else display_index



    # ========================================================
    # DRAW BOARD
    # ========================================================

    def draw_board(self):
        if not hasattr(self, "board_canvas") or not self.board_canvas.winfo_exists():
            return
        canvas, size = self.board_canvas, self.square_size
        canvas.delete("all")
        for row in range(8):
            for column in range(8):
                index = self.display_to_board_index(row * 8 + column)
                x, y = column * size, row * size
                light = (row + column) % 2 == 0
                color = LIGHT_SQUARE if light else DARK_SQUARE
                if self.last_move is not None and index in self.last_move:
                    color = LAST_MOVE_LIGHT if light else LAST_MOVE_DARK
                if index == self.selected_square:
                    color = SELECTED_LIGHT if light else SELECTED_DARK
                if index == self.check_king_index:
                    color = CHECK_SQUARE
                canvas.create_rectangle(x, y, x + size, y + size, fill=color, outline="")
                piece = self.position[index]
                if piece != ".":
                    if piece in self.piece_images:
                        canvas.create_image(x + size / 2, y + size / 2,
                                            image=self.piece_images[piece])
                    else:
                        canvas.create_text(x + size / 2, y + size / 2,
                                           text=UNICODE_PIECES.get(piece, ""),
                                           font=("Segoe UI Symbol", max(20, int(size * .60))),
                                           fill="#171B20")
                if index in self.legal_targets:
                    if self.legal_targets[index]:
                        margin = max(5, size * .08)
                        canvas.create_oval(x + margin, y + margin, x + size - margin,
                                           y + size - margin, outline=LEGAL_CAPTURE,
                                           width=max(3, int(size * .055)))
                    else:
                        radius = size * .105
                        cx, cy = x + size / 2, y + size / 2
                        canvas.create_oval(cx - radius, cy - radius, cx + radius,
                                           cy + radius, fill=LEGAL_DOT, outline="")
        self.rank_canvas.delete("all")
        self.file_canvas.delete("all")
        font = (FONT_FAMILY, max(10, int(size * .14)))
        for index in range(8):
            rank = self.index_to_square(self.display_to_board_index(index * 8))[1]
            file = self.index_to_square(self.display_to_board_index(56 + index))[0]
            self.rank_canvas.create_text(14, (index + .5) * size, text=rank,
                                         fill=SECONDARY_TEXT, font=font)
            self.file_canvas.create_text((index + .5) * size, 14, text=file,
                                         fill=SECONDARY_TEXT, font=font)



    # ========================================================
    # IS PLAYER PIECE
    # ========================================================

    def is_player_piece(
        self,
        piece
    ):

        if piece == ".":

            return False


        if self.player_is_white:

            return (
                piece.isupper()
            )


        return (
            piece.islower()
        )


    # ========================================================
    # SELECT PIECE
    # ========================================================

    def select_square(
        self,
        board_index
    ):

        self.selected_square = (
            board_index
        )


        square = (
            self.index_to_square(
                board_index
            )
        )


        self.legal_moves = (
            self.engine
            .get_legal_moves(
                square
            )
        )


        self.legal_targets = {}


        moving_piece = (
            self.position[
                board_index
            ]
        )


        from_file = (
            square[0]
        )


        for move in (
            self.legal_moves
        ):

            if len(move) < 4:

                continue


            target_square = (
                move[2:4]
            )


            target_index = (
                self.square_to_index(
                    target_square
                )
            )


            target_piece = (
                self.position[
                    target_index
                ]
            )


            capture = (

                target_piece != "."
            )


            # En passant
            if (
                moving_piece.lower()
                ==
                "p"

                and

                from_file
                !=
                target_square[0]
            ):

                capture = True


            self.legal_targets[
                target_index
            ] = capture


        self.draw_board()


    # ========================================================
    # BOARD CLICK
    # ========================================================

    def on_board_click(
        self,
        event
    ):

        if self.engine_thinking or self._setup:

            return


        column = (

            event.x //
            self.square_size
        )


        row = (

            event.y //
            self.square_size
        )


        if not (

            0 <= column < 8

            and

            0 <= row < 8
        ):

            return


        display_index = (

            row * 8 +
            column
        )


        board_index = (
            self.display_to_board_index(

                display_index
            )
        )


        clicked_piece = (
            self.position[
                board_index
            ]
        )


        # ====================================================
        # NOTHING SELECTED
        # ====================================================

        if (
            self.selected_square
            is None
        ):

            if self.is_player_piece(
                clicked_piece
            ):

                self.select_square(
                    board_index
                )


            return


        # ====================================================
        # SAME PIECE
        # ====================================================

        if (
            board_index ==
            self.selected_square
        ):

            self.clear_selection()

            return


        # ====================================================
        # ANOTHER OWN PIECE
        # ====================================================

        if self.is_player_piece(
            clicked_piece
        ):

            self.select_square(
                board_index
            )

            return


        # ====================================================
        # ILLEGAL TARGET
        # ====================================================

        if (
            board_index
            not in
            self.legal_targets
        ):

            self.clear_selection()

            return


        self.make_selected_move(
            board_index
        )


    # ========================================================
    # CLEAR SELECTION
    # ========================================================

    def clear_selection(
        self
    ):

        self.selected_square = (
            None
        )


        self.legal_moves = []


        self.legal_targets = {}


        self.draw_board()


    # ========================================================
    # PLAYER MOVE
    # ========================================================

    def make_selected_move(
        self,
        target_index
    ):

        from_index = (
            self.selected_square
        )


        moving_piece = (
            self.position[
                from_index
            ]
        )


        from_square = (
            self.index_to_square(
                from_index
            )
        )


        to_square = (
            self.index_to_square(
                target_index
            )
        )


        move = (

            from_square +
            to_square
        )


        # ====================================================
        # PROMOTION
        # ====================================================

        if (

            moving_piece == "P"

            and

            to_square[1] == "8"

        ) or (

            moving_piece == "p"

            and

            to_square[1] == "1"
        ):

            promotion = (
                self.choose_promotion(

                    moving_piece
                    .isupper()
                )
            )


            if promotion is None:

                self.clear_selection()

                return


            move += promotion


        self.clear_selection()


        response = (
            self.engine
            .make_move(
                move
            )
        )


        if not response.startswith(
            "ok"
        ):

            self.status_label.config(

                text=
                    "Illegal move"
            )

            return


        parts = (
            response.split()
        )


        capture = False


        if "capture" in parts:

            capture_index = (
                parts.index(
                    "capture"
                )
            )


            if (
                capture_index + 1
                <
                len(parts)
            ):

                capture = (

                    parts[
                        capture_index + 1
                    ]
                    ==
                    "1"
                )


        self.last_move = (

            from_index,
            target_index
        )


        self.move_history.append(
            move
        )


        self.refresh_position()


        self.update_history()


        in_check = (
            self.update_check_status()
        )


        game_over = (
            self.check_game_state()
        )


        if in_check:

            self.play_sound(
                "check"
            )


        elif capture:

            self.play_sound(
                "capture"
            )


        else:

            self.play_sound(
                "move"
            )


        if game_over:

            return


        self.start_engine_move()


    # ========================================================
    # PROMOTION
    # ========================================================

    def choose_promotion(
        self,
        white
    ):

        dialog = (
            tk.Toplevel(
                self.root
            )
        )


        dialog.title(
            "Promotion"
        )


        dialog.configure(
            bg=
                PANEL_BACKGROUND
        )


        dialog.resizable(
            False,
            False
        )


        dialog.transient(
            self.root
        )


        dialog.grab_set()


        tk.Label(

            dialog,

            text=
                "Choose promotion",

            font=(
                "Segoe UI",
                13,
                "bold"
            ),

            bg=
                PANEL_BACKGROUND,

            fg=
                TEXT_COLOR

        ).pack(

            pady=(
                15,
                8
            )
        )


        frame = tk.Frame(

            dialog,

            bg=
                PANEL_BACKGROUND
        )


        frame.pack(

            padx=15,

            pady=(
                0,
                15
            )
        )


        result = {

            "piece":
                None
        }


        def choose(
            piece
        ):

            result["piece"] = (
                piece
            )

            dialog.destroy()


        for promotion in [

            "q",
            "r",
            "b",
            "n"

        ]:

            image_key = (

                promotion.upper()

                if white

                else promotion
            )


            arguments = {

                "command":

                    lambda
                    p=promotion:
                    choose(p),


                "bg":

                    LIGHT_SQUARE,


                "activebackground":

                    LAST_MOVE_LIGHT,


                "relief":

                    "flat",


                "cursor":

                    "hand2",
            }


            if (
                image_key
                in
                self.piece_images
            ):

                arguments[
                    "image"
                ] = (

                    self.piece_images[
                        image_key
                    ]
                )


            else:

                arguments[
                    "text"
                ] = (

                    UNICODE_PIECES[
                        image_key
                    ]
                )


            tk.Button(

                frame,

                **arguments

            ).pack(

                side="left",

                padx=3
            )


        dialog.wait_window()


        return (
            result["piece"]
        )


    # ========================================================
    # START ENGINE MOVE
    # ========================================================

    def start_engine_move(
        self
    ):

        self.engine_thinking = (
            True
        )


        self.status_label.config(

            text=(

                f"ChessAI "
                f"({self.difficulty}) "
                f"is thinking..."
            )
        )


        self.new_game_button.config(

            state=
                "disabled"
        )


        profile = (

            DIFFICULTIES[
                self.difficulty
            ]
        )


        thread = (
            threading.Thread(

                target=
                    self.run_engine_move,

                args=(

                    profile[
                        "time"
                    ],

                    profile[
                        "depth"
                    ]
                ),

                daemon=True
            )
        )


        thread.start()


    # ========================================================
    # ENGINE THREAD
    # ========================================================

    def run_engine_move(
        self,
        milliseconds,
        depth
    ):

        try:

            response = (
                self.engine
                .engine_move(

                    milliseconds,

                    depth,

                    self.difficulty
                )
            )


            self.root.after(

                0,

                lambda:
                self.handle_engine_response(

                    response
                )
            )


        except Exception as error:

            message = (
                str(
                    error
                )
            )


            self.root.after(

                0,

                lambda:
                self.handle_engine_error(

                    message
                )
            )


    # ========================================================
    # ENGINE ERROR
    # ========================================================

    def handle_engine_error(
        self,
        error
    ):

        self.engine_thinking = (
            False
        )


        self.new_game_button.config(

            state=
                "normal"
        )


        messagebox.showerror(

            "Engine Error",

            error
        )


    # ========================================================
    # ENGINE RESPONSE
    # ========================================================

    def handle_engine_response(
        self,
        response
    ):

        self.engine_thinking = (
            False
        )


        self.new_game_button.config(

            state=
                "normal"
        )


        if not response.startswith(
            "bestmove "
        ):

            self.status_label.config(

                text=
                    "Engine could not move"
            )

            return


        parts = (
            response.split()
        )


        move = (
            parts[1]
        )


        from_index = (
            self.square_to_index(

                move[0:2]
            )
        )


        to_index = (
            self.square_to_index(

                move[2:4]
            )
        )


        self.last_move = (

            from_index,
            to_index
        )


        self.move_history.append(
            move
        )


        data = {}


        index = 2


        while (
            index + 1
            <
            len(parts)
        ):

            data[
                parts[index]
            ] = (

                parts[
                    index + 1
                ]
            )


            index += 2


        capture = (

            data.get(
                "capture",
                "0"
            )
            ==
            "1"
        )


        from_book = (

            data.get(
                "book",
                "0"
            )
            ==
            "1"
        )


        if from_book:

            source_text = (
                "Opening book"
            )


        else:

            source_text = (
                "Search"
            )


        self.engine_info.config(

            text=(

                f"Evaluation: "
                f"{data.get('score', '?')} cp\n"

                f"Depth: "
                f"{data.get('depth', '?')}\n"

                f"Nodes: "
                f"{data.get('nodes', '?')}\n"

                f"TT hits: "
                f"{data.get('tthits', '?')}\n"

                f"Time: "
                f"{data.get('time', '?')} ms\n"

                f"Source: "
                f"{source_text}"
            )
        )


        self.refresh_position()


        self.update_history()


        in_check = (
            self.update_check_status()
        )


        game_over = (
            self.check_game_state()
        )


        if in_check:

            self.play_sound(
                "check"
            )


        elif capture:

            self.play_sound(
                "capture"
            )


        else:

            self.play_sound(
                "move"
            )


        if not game_over:

            self.status_label.config(

                text=
                    "Your move"
            )


    # ========================================================
    # CHECK
    # ========================================================

    def update_check_status(
        self
    ):

        response = (
            self.engine
            .get_check()
        )


        parts = (
            response.split()
        )


        in_check = (

            len(parts) >= 3

            and

            parts[0]
            ==
            "check"

            and

            parts[1]
            ==
            "1"
        )


        if in_check:

            self.check_king_index = (
                self.square_to_index(

                    parts[2]
                )
            )


        else:

            self.check_king_index = (
                None
            )


        self.draw_board()


        return in_check


    # ========================================================
    # PLAY SOUND
    # ========================================================

    def play_sound(
        self,
        sound_type
    ):

        if winsound is None:

            return


        path = (
            self.sound_files.get(

                sound_type
            )
        )


        if path is None:

            return


        try:

            winsound.PlaySound(

                path,

                winsound.SND_FILENAME
                |
                winsound.SND_ASYNC
            )


        except Exception:

            pass


    # ========================================================
    # MOVE HISTORY
    # ========================================================

    def update_history(self):
        self.history_tree.delete(*self.history_tree.get_children())
        for index in range(0, len(self.move_history), 2):
            white = self.move_history[index]
            black = self.move_history[index + 1] if index + 1 < len(self.move_history) else ""
            item = self.history_tree.insert("", "end", values=(f"{index // 2 + 1}.", white, black))
        if self.move_history:
            self.history_tree.selection_set(item)
            self.history_tree.see(item)



    # ========================================================
    # GAME STATE
    # ========================================================

    def check_game_state(
        self
    ):

        state = (
            self.engine
            .get_state()
        )


        messages = {

            "white_wins":

                "Checkmate — "
                "White wins!",


            "black_wins":

                "Checkmate — "
                "Black wins!",


            "stalemate":

                "Draw — "
                "Stalemate",


            "draw_fifty_move":

                "Draw — "
                "Fifty-move rule",


            "draw_repetition":

                "Draw — "
                "Threefold repetition",


            "draw_insufficient_material":

                "Draw — "
                "Insufficient material",
        }


        if state not in messages:

            return False


        message = (
            messages[
                state
            ]
        )


        self.status_label.config(

            text=
                message
        )


        messagebox.showinfo(

            "Game Over",

            message
        )


        return True


    # ========================================================
    # INDEX -> CHESS SQUARE
    # ========================================================

    def index_to_square(
        self,
        index
    ):

        row = (

            index //
            8
        )


        column = (

            index %
            8
        )


        file_name = chr(

            ord("a")
            +
            column
        )


        rank_name = str(

            8 -
            row
        )


        return (

            file_name +
            rank_name
        )


    # ========================================================
    # CHESS SQUARE -> INDEX
    # ========================================================

    def square_to_index(
        self,
        square
    ):

        column = (

            ord(
                square[0]
            )
            -
            ord("a")
        )


        row = (

            8 -
            int(
                square[1]
            )
        )


        return (

            row * 8 +
            column
        )


    # ========================================================
    # CLOSE
    # ========================================================

    def on_close(
        self
    ):

        self.engine.close()


        self.root.destroy()


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    root = tk.Tk()


    app = ChessGUI(
        root
    )


    root.mainloop()
