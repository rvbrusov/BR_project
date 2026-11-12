"""Автономный тест «Красно-чёрные числа».

Запуск: python red_black_numbers.py
Зависимости: только стандартная библиотека Python 3.10+.
"""

from __future__ import annotations

import csv
import json
import math
import random
import sys
import time
import tkinter as tk
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Callable


APP_TITLE = "Красно-чёрные числа"
RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
APP_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "red_black_data"
SETTINGS_FILE = DATA_DIR / "settings.json"
RESULTS_FILE = DATA_DIR / "results.json"
CSV_FILE = DATA_DIR / "results.csv"

BG = "#f3f0d6"
CARD = "#ece7c9"
INK = "#111111"
MUTED = "#5a5a5a"
BLUE = "#42d95b"
BLUE_HOVER = "#35b74a"
RED = "#cf2437"
GREEN = "#2eaf69"
GRID = "#9b967f"
BACK = "#d7cfaa"
BACK_HOVER = "#bfb585"
FIELD = "#fffdf1"
TEST_BG = "#f6f0d8"


@dataclass(frozen=True)
class Cell:
    number: int
    kind: str


@dataclass
class Norm:
    cycle: float = 1.50
    allowed_errors: int = 8
    range_cycle: float = 1.50
    range_allowed_errors: int = 3


DEFAULT_SETTINGS = {
    "participant": "",
    "stage_1": asdict(Norm()),
    "stage_2": asdict(Norm(cycle=1.80, range_cycle=1.80)),
    "stage_3": asdict(Norm(cycle=2.10, range_cycle=2.10)),
}


STAGES = {
    1: (6, ("black", "red")),
    2: (8, ("black", "red", "white_red")),
    3: (9, ("black", "red", "white_red", "white_black")),
}


def target_sequence(stage: int) -> list[Cell]:
    """Возвращает порядок кликов согласно описанию методики."""
    _, kinds = STAGES[stage]
    result: list[Cell] = []
    for n in range(1, 18):
        descending = 18 - n  # 17..1
        result.append(Cell(n, "black"))
        result.append(Cell(descending, "red"))
        if "white_red" in kinds:
            result.append(Cell(n, "white_red"))
        if "white_black" in kinds:
            result.append(Cell(descending, "white_black"))
    return result


def _layout_penalty(cells: list[Cell | None], side: int) -> int:
    """Soft spatial limits leave local chance variation without large blocks.

    Adjacent means sharing an edge, except the first pair and the two blanks
    in stage 1, which must also avoid diagonal contact. No alternating pattern
    or fixed position is imposed. Lower scores are better; zero meets all limits.
    """
    penalty = 0
    colors = [None if c is None else ('red' if c.kind in ('red', 'white_red') else 'black') for c in cells]
    sizes = [None if c is None else ('small' if c.number <= 8 else 'large') for c in cells]
    for categories in (colors, sizes):
        # Five identical categories in a straight line and solid 3x3 blocks.
        for row in range(side):
            for col in range(side):
                start = row * side + col
                value = categories[start]
                if value is None:
                    continue
                for height, width in ((1, 5), (5, 1), (3, 3)):
                    if row + height <= side and col + width <= side:
                        if all(categories[(row + dy) * side + col + dx] == value
                               for dy in range(height) for dx in range(width)):
                            penalty += 1
    # Prevent segregation into left/right or upper/lower halves for each kind.
    for kind in {cell.kind for cell in cells if cell is not None}:
        indices = [i for i, cell in enumerate(cells) if cell and cell.kind == kind]
        for coordinate in (lambda i: i // side, lambda i: i % side):
            actual = sum(coordinate(i) < side // 2 for i in indices)
            expected = len(indices) * (side // 2) / side
            penalty += max(0, int(abs(actual - expected) - 3 + .999999))
    blanks = {i for i, cell in enumerate(cells) if cell is None}
    if len(blanks) == 2:
        a, b = sorted(blanks)
        penalty += int(max(abs(a // side - b // side), abs(a % side - b % side)) <= 1)
    else:
        remaining = set(blanks)
        while remaining:
            pending = [remaining.pop()]
            count = 0
            while pending:
                i = pending.pop(); count += 1
                for j in (i-side, i+side, i-1, i+1):
                    if j in remaining and abs(i//side-j//side)+abs(i%side-j%side) == 1:
                        remaining.remove(j); pending.append(j)
            penalty += max(0, count - 3)
        for row in range(side-1):
            for col in range(side-1):
                penalty += int(all((row+dy)*side+col+dx in blanks for dy in (0,1) for dx in (0,1)))
    first, second = cells.index(Cell(1, 'black')), cells.index(Cell(17, 'red'))
    penalty += int(max(abs(first//side-second//side), abs(first%side-second%side)) <= 1)
    return penalty


def make_board(stage: int, rng: random.Random | None = None) -> list[Cell | None]:
    rng = rng if rng is not None else random.Random()
    side, _ = STAGES[stage]
    cells: list[Cell | None] = list(target_sequence(stage))
    cells.extend([None] * (side * side - len(cells)))
    # Rejection sampling retains random positions, including empty cells.
    # The bounded best-candidate fallback prevents a pathological RNG from
    # blocking the UI. Normal random streams reach zero well before this limit.
    best, best_penalty = cells[:], float('inf')
    for _ in range(2048):
        rng.shuffle(cells)
        penalty = _layout_penalty(cells, side)
        if penalty == 0:
            return cells
        if penalty < best_penalty:
            best, best_penalty = cells[:], penalty
    return best


def safe_ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator > 0 else 0.0


def coefficient(errors: int, allowed: int) -> float:
    if allowed <= 0:
        return 1.0 if errors == 0 else 0.0
    return max(0.0, 1.0 - errors / allowed)


def calculate_metrics(intervals: list[float], errors: int, range_intervals: list[float],
                      range_errors: int, norm: Norm) -> dict[str, float | int]:
    mean = sum(intervals) / len(intervals) if intervals else 0.0
    range_mean = sum(range_intervals) / len(range_intervals) if range_intervals else 0.0
    pace = safe_ratio(norm.cycle, mean)
    range_pace = safe_ratio(norm.range_cycle, range_mean)
    error_coef = coefficient(errors, norm.allowed_errors)
    range_error_coef = coefficient(range_errors, norm.range_allowed_errors)
    table_pace = pace * error_coef
    range_table_pace = range_pace * range_error_coef
    return {
        "mean_cycle": mean,
        "errors": errors,
        "range_mean_cycle": range_mean,
        "range_errors": range_errors,
        "pace": pace,
        "error_coefficient": error_coef,
        "range_pace": range_pace,
        "range_error_coefficient": range_error_coef,
        "table_pace": table_pace,
        "range_table_pace": range_table_pace,
        "interference_index": safe_ratio(range_table_pace, table_pace),
    }


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def button(parent, text: str, command: Callable, *, primary: bool = True, width: int = 24):
    bg = BLUE if primary else BACK
    fg = "#111111"
    active = BLUE_HOVER if primary else BACK_HOVER
    return tk.Button(parent, text=text, command=command, width=width, pady=10,
                     bg=bg, fg=fg, activebackground=active, activeforeground=fg,
                     relief="raised", bd=3, cursor="hand2", font=("Arial", 11, "bold"))


class RedBlackApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_TITLE)
        width = min(1200, max(600, self.root.winfo_screenwidth() - 40))
        height = min(800, max(400, self.root.winfo_screenheight() - 100))
        self.root.geometry(f"{width}x{height}")
        self.root.minsize(min(640, width), min(420, height))
        self.root.configure(bg=BG)
        self.settings = read_json(SETTINGS_FILE, DEFAULT_SETTINGS.copy())
        self.session: list[dict] = []
        self.stage = 0
        self.training = False
        self.after_ids: set[str] = set()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.show_home()

    def clear(self):
        for aid in tuple(self.after_ids):
            try:
                self.root.after_cancel(aid)
            except tk.TclError:
                pass
        self.after_ids.clear()
        self.root.attributes("-fullscreen", False)
        for child in self.root.winfo_children():
            child.destroy()

    def later(self, delay: int, callback: Callable):
        holder = [""]
        def run():
            self.after_ids.discard(holder[0])
            callback()
        holder[0] = self.root.after(delay, run)
        self.after_ids.add(holder[0])

    def header(self, title: str, subtitle: str = ""):
        top = tk.Frame(self.root, bg=BG, height=80)
        top.pack(fill="x")
        top.pack_propagate(False)
        tk.Label(top, text="Тест", bg=BG, fg=INK, font=("Arial", -16)).pack(pady=(4, 0))
        tk.Label(top, text=title.upper(), bg=BG, fg=INK, font=("Arial", -25, "bold")).pack()
        if subtitle:
            label = tk.Label(top, text=subtitle, bg=BG, fg=MUTED, font=("Arial", -13))
            label.pack(fill="x")
            top.bind("<Configure>", lambda e: label.configure(wraplength=max(100, e.width-20)))

    def illustrations(self, parent):
        """Левая колонка в стиле стартовых экранов Aviatest v2."""
        box = tk.Frame(parent, bg=BG)
        refs = []
        for filename in ("circle.png", "cockpit.png"):
            try:
                image = tk.PhotoImage(file=str(RESOURCE_DIR / "assets" / filename))
                factor = max(1, image.width() // 270)
                image = image.subsample(factor, factor)
                refs.append(image)
                tk.Label(box, image=image, bg=BG, bd=0).pack(pady=8)
            except tk.TclError:
                pass
        box._image_refs = refs
        return box

    def show_home(self):
        self.clear()
        self.header(APP_TITLE, "Психофизиологическая методика оценки темпа и помехоустойчивости")
        body = tk.Frame(self.root, bg=BG)
        body.pack(expand=True, fill="both", padx=12, pady=8)
        card = tk.Frame(body, bg=CARD, bd=2, relief="groove")
        card.pack(expand=True, fill="both")
        tk.Label(card, text="КРАСНО-ЧЁРНЫЕ\nТАБЛИЦЫ", bg=CARD, fg=INK,
                 font=("Arial", -26, "bold"), justify="center").pack(pady=(8, 4))
        tk.Label(card, text="3 этапа  •  последовательный поиск чисел  •  автоматический расчёт результатов",
                 bg=CARD, fg=MUTED, font=("Arial", -14), wraplength=580).pack(pady=(0, 6))
        button(card, "НАЧАТЬ ТЕСТ", self.show_briefing).pack(pady=6)
        training_button = button(card, "ТРЕНИРОВКА", self.start_training, primary=False)
        training_button.configure(bg="#f2d64b", activebackground="#e3c12d")
        training_button.pack(pady=6)
        button(card, "ИНСТРУКЦИЯ", self.show_instruction, primary=False).pack(pady=6)
        button(card, "НАСТРОЙКИ НОРМАТИВОВ", self.show_settings, primary=False).pack(pady=6)
        button(card, "ПОСЛЕДНИЕ РЕЗУЛЬТАТЫ", self.show_history, primary=False).pack(pady=6)
        for child in card.winfo_children():
            if isinstance(child, tk.Button):
                child.configure(font=("Arial", -16, "bold"), pady=4, width=30)
                child.pack_configure(pady=3)

    def show_instruction(self):
        self.clear(); self.header("Инструкция")
        frame = tk.Frame(self.root, bg=CARD, padx=12, pady=8)
        frame.pack(expand=True, fill="both", padx=12, pady=8)
        text = (
            "Нажимайте числа по очереди, чередуя ряды.\n\n"
            "Этап 1 (6×6): чёрные числа 1→17, красные 17→1.\n"
            "Пример: чёрное 1, красное 17, чёрное 2, красное 16…\n\n"
            "Этап 2 (8×8): после каждой пары нажимайте белое число на красном фоне 1→17.\n\n"
            "Этап 3 (9×9): дополнительно нажимайте белое число на чёрном фоне 17→1.\n\n"
            "При ошибке над таблицей появится сообщение «ОШИБКА», а правильная ячейка "
            "коротко подсветится зелёным. Затем нажмите её и продолжайте. Время не ограничено."
        )
        button(frame, "НАЗАД", self.show_home, primary=False, width=16).pack(side="bottom", pady=4)
        scroll = tk.Scrollbar(frame)
        scroll.pack(side="right", fill="y")
        body = tk.Text(frame, wrap="word", bg=CARD, fg=INK, relief="flat", height=1, width=1,
                       font=("Arial", -17), yscrollcommand=scroll.set)
        body.insert("1.0", text)
        body.configure(state="disabled")
        body.pack(fill="both", expand=True)
        scroll.configure(command=body.yview)

    def show_briefing(self):
        self.clear(); self.header("Подготовка к тесту")
        card = tk.Frame(self.root, bg=CARD, padx=45, pady=35)
        card.pack(expand=True, padx=120, pady=55, fill="both")
        tk.Label(card, text="Фамилия, имя или код испытуемого", bg=CARD, fg=INK,
                 font=("Arial", 13, "bold")).pack(pady=(20, 8))
        participant = tk.StringVar(value=self.settings.get("participant", ""))
        entry = ttk.Entry(card, textvariable=participant, font=("Arial", 13), width=38)
        entry.pack(ipady=7); entry.focus_set()
        tk.Label(card, text="Тест состоит из трёх этапов. Между этапами можно сделать паузу.",
                 bg=CARD, fg=MUTED, font=("Arial", 12)).pack(pady=30)
        def start():
            self.settings["participant"] = participant.get().strip()
            self.save_settings()
            self.session = []
            self.training = False
            self.start_stage(1)
        button(card, "НАЧАТЬ", start).pack(pady=6)
        button(card, "НАЗАД", self.show_home, primary=False).pack(pady=6)

    def show_settings(self):
        self.clear(); self.header("Настройки нормативов", "Значения используются в формулах приведённого темпа")
        card = tk.Frame(self.root, bg=CARD, padx=8, pady=8)
        card.pack(expand=True, fill="both", padx=12, pady=12)
        headers = ("Этап", "Тц норм, с", "N доп", "Тц(7) норм, с", "N(7) доп")
        for col, value in enumerate(headers):
            tk.Label(card, text=value, bg=CARD, fg=INK, font=("Arial", -14, "bold")).grid(row=0, column=col, padx=3, pady=5)
        entries: dict[int, list[ttk.Entry]] = {}
        for stage in range(1, 4):
            raw = self.settings.get(f"stage_{stage}", DEFAULT_SETTINGS[f"stage_{stage}"])
            tk.Label(card, text=str(stage), bg=CARD, fg="#245a2a", font=("Arial", 13, "bold")).grid(row=stage, column=0)
            entries[stage] = []
            for col, key in enumerate(("cycle", "allowed_errors", "range_cycle", "range_allowed_errors"), 1):
                e = ttk.Entry(card, width=8, justify="center", font=("Arial", -15))
                e.insert(0, str(raw.get(key, DEFAULT_SETTINGS[f"stage_{stage}"][key])))
                e.grid(row=stage, column=col, padx=3, pady=4, ipady=3, sticky="ew")
                entries[stage].append(e)
        card.grid_columnconfigure(tuple(range(5)), weight=1)
        actions = tk.Frame(card, bg=CARD); actions.grid(row=5, column=0, columnspan=5, pady=12)
        def save():
            try:
                for stage, fields in entries.items():
                    values = [float(fields[0].get().replace(",", ".")), int(fields[1].get()),
                              float(fields[2].get().replace(",", ".")), int(fields[3].get())]
                    if min(values) <= 0:
                        raise ValueError
                    self.settings[f"stage_{stage}"] = asdict(Norm(*values))
            except ValueError:
                messagebox.showerror("Настройки", "Введите положительные числовые значения.")
                return
            self.save_settings(); messagebox.showinfo("Настройки", "Нормативы сохранены."); self.show_home()
        button(actions, "СОХРАНИТЬ", save, width=18).pack(side="left", padx=8)
        button(actions, "ОТМЕНА", self.show_home, primary=False, width=18).pack(side="left", padx=8)

    def start_stage(self, stage: int):
        self.clear(); self.root.attributes("-fullscreen", True)
        self.stage = stage
        self.sequence = target_sequence(stage)
        self.board = make_board(stage)
        self.position = 0
        self.errors = 0
        self.range_errors = 0
        self.intervals: list[float] = []
        self.range_intervals: list[float] = []
        self.last_click = time.perf_counter()
        self.started_at = self.last_click
        self.completed_elapsed: float | None = None
        self.pending_stage_result: dict | None = None
        self.cell_widgets: dict[Cell, tk.Button] = {}
        self.flash_generation = 0

        shell = tk.Frame(self.root, bg=TEST_BG); shell.pack(fill="both", expand=True)
        top = tk.Frame(shell, bg=TEST_BG, height=42); top.pack(fill="x"); top.pack_propagate(False)
        tk.Label(top, text=f"ЭТАП {stage} ИЗ 3", bg=TEST_BG, fg=INK,
                 font=("Arial", -22, "bold")).place(relx=.5, rely=.5, anchor="center")
        footer = tk.Frame(shell, bg=TEST_BG)
        footer.pack(side="bottom", fill="x", padx=12, pady=(4, 8))
        for column in range(3):
            footer.grid_columnconfigure(column, weight=1)
        common = dict(font=("Arial", -20, "bold"), width=0, padx=6, pady=6,
                      bd=3, relief="raised", cursor="hand2")
        self.cancel_stage_button = tk.Button(footer, text="ОТМЕНА", command=self.undo_last_click,
                                             bg="#f2d64b", activebackground="#e3c12d", **common)
        self.cancel_stage_button.grid(row=0, column=0, sticky="ew", padx=4)
        self.next_stage_button = tk.Button(footer, text="ДАЛЕЕ", command=lambda: None,
                                           bg="#58cc63", activebackground="#43b84f",
                                           disabledforeground="#6c7a6c", **common)
        self.next_stage_button.grid(row=0, column=1, sticky="ew", padx=4)
        self.next_stage_button.configure(state="disabled")
        tk.Button(footer, text="ВЫХОД", command=self.confirm_abort,
                  bg="#d95a5a", activebackground="#b93c3c", fg="white",
                  activeforeground="white", **common).grid(row=0, column=2, sticky="ew", padx=4)
        content = tk.Frame(shell, bg=TEST_BG); content.pack(fill="both", expand=True, padx=8, pady=(0, 4))
        content.grid_columnconfigure(0, minsize=100, weight=0)
        content.grid_columnconfigure(1, weight=1)
        content.grid_columnconfigure(2, minsize=100, weight=0)
        content.grid_rowconfigure(0, weight=1)
        tk.Frame(content, bg=TEST_BG, width=100).grid(row=0, column=0, sticky="nsew")
        center = tk.Frame(content, bg=TEST_BG); center.grid(row=0, column=1, sticky="nsew")
        self.error_label = tk.Label(center, text=" ", bg=TEST_BG, fg=RED, font=("Arial", -18, "bold"))
        self.error_label.pack(pady=(0, 4))
        self.grid_frame = tk.Frame(center, bg=GRID, bd=1)
        self.grid_frame.pack(expand=True)
        self.grid_frame.grid_propagate(False)
        side, _ = STAGES[stage]
        size = 1  # Set from the allocated viewport after Tk has laid out the controls.
        font_size = 16
        for index, cell in enumerate(self.board):
            row, col = divmod(index, side)
            if cell is None:
                w = tk.Label(self.grid_frame, text="", bg="#e5dfc2", width=1, height=1)
            else:
                bg, fg = self.cell_colors(cell)
                w = tk.Button(self.grid_frame, text=str(cell.number), bg=bg, fg=fg,
                              activebackground=bg, activeforeground=fg, relief="flat", bd=0,
                              font=("Arial", -font_size, "bold"), cursor="hand2", padx=0, pady=0,
                              command=lambda c=cell: self.click_cell(c))
                self.cell_widgets[cell] = w
            w.grid(row=row, column=col, padx=1, pady=1, sticky="nsew")
            self.grid_frame.grid_rowconfigure(row, minsize=0, weight=1, uniform="cells")
            self.grid_frame.grid_columnconfigure(col, minsize=0, weight=1, uniform="cells")
        hud = tk.Frame(content, bg=TEST_BG)
        hud.grid(row=0, column=2, sticky="ne")
        self.time_canvas = tk.Canvas(hud, width=96, height=320, bg=TEST_BG, highlightthickness=0)
        self.time_canvas.pack()
        self.progress_label = tk.Label(hud, text=f"0 / {len(self.sequence)}", bg=TEST_BG, fg=INK,
                                       font=("Arial", 10, "bold"))
        self.progress_label.pack(pady=(4, 0))
        def fit_board(event=None):
            if not center.winfo_exists():
                return
            available_height = center.winfo_height() - self.error_label.winfo_reqheight() - 8
            cell_size = max(1, min(center.winfo_width()-4, available_height-4) // side)
            extent = side * cell_size + 2
            self.grid_frame.configure(width=extent, height=extent)
            pixels = max(10, int(cell_size * .43))
            for widget in self.cell_widgets.values():
                widget.configure(font=("Arial", -pixels, "bold"))
            self.time_canvas.configure(height=max(90, min(320, content.winfo_height()-36)))
        center.bind("<Configure>", fit_board)
        self.later(0, fit_board)
        self.tick()

    @staticmethod
    def cell_colors(cell: Cell) -> tuple[str, str]:
        return {
            "black": ("#ffffff", "#15191d"),
            "red": ("#ffffff", RED),
            "white_red": (RED, "#ffffff"),
            "white_black": ("#14191f", "#ffffff"),
        }[cell.kind]

    def tick(self):
        elapsed = self.completed_elapsed if self.completed_elapsed is not None else time.perf_counter() - self.started_at
        canvas = self.time_canvas
        canvas.delete("all")
        bottom = max(70, canvas.winfo_height()-12)
        canvas.create_text(48, 18, text="ВРЕМЯ", fill="#102744", font=("Arial", -14, "bold"))
        canvas.create_rectangle(19, 34, 77, bottom, outline="#233142", fill="#e6ecf4", width=3)
        inner_top, inner_bottom = 38, bottom-4
        fill_height = min(inner_bottom - inner_top, int(elapsed * 2.2))
        if fill_height:
            canvas.create_rectangle(23, inner_bottom - fill_height, 73, inner_bottom,
                                    outline="", fill="#3c82ff")
        self.later(100, self.tick)

    def click_cell(self, cell: Cell):
        if self.position >= len(self.sequence):
            return
        expected = self.sequence[self.position]
        if cell != expected:
            self.errors += 1
            if 7 <= expected.number <= 9:
                self.range_errors += 1
            self.error_label.config(text="ОШИБКА")
            self.flash_correct(expected)
            return
        now = time.perf_counter()
        interval = now - self.last_click
        self.intervals.append(interval)
        if 7 <= expected.number <= 9:
            self.range_intervals.append(interval)
        self.last_click = now
        self.position += 1
        self.error_label.config(text=" ")
        self.progress_label.config(text=f"{self.position} / {len(self.sequence)}")
        if self.position == len(self.sequence):
            self.finish_stage(now - self.started_at)

    def undo_last_click(self):
        if not getattr(self, "position", 0):
            return
        self.position -= 1
        previous = self.sequence[self.position]
        if self.intervals:
            self.intervals.pop()
        if 7 <= previous.number <= 9 and self.range_intervals:
            self.range_intervals.pop()
        self.last_click = time.perf_counter()
        self.error_label.config(text=" ")
        self.progress_label.config(text=f"{self.position} / {len(self.sequence)}")

    def flash_correct(self, cell: Cell):
        widget = self.cell_widgets[cell]
        self.flash_generation += 1
        generation = self.flash_generation
        widget.config(bg=GREEN, fg="white", activebackground=GREEN, activeforeground="white")
        def restore():
            if generation == self.flash_generation and widget.winfo_exists():
                bg, fg = self.cell_colors(cell)
                widget.config(bg=bg, fg=fg, activebackground=bg, activeforeground=fg)
        self.later(650, restore)

    def finish_stage(self, duration: float):
        raw = self.settings.get(f"stage_{self.stage}", DEFAULT_SETTINGS[f"stage_{self.stage}"])
        metrics = calculate_metrics(self.intervals, self.errors, self.range_intervals,
                                    self.range_errors, Norm(**raw))
        metrics.update({"stage": self.stage, "duration": duration,
                        "target_count": len(self.sequence), "board_side": STAGES[self.stage][0],
                        "layout_version": "complete17_mixed_v1"})
        self.session.append(metrics)
        self.completed_elapsed = duration
        self.pending_stage_result = metrics
        self.error_label.config(text="ЭТАП ЗАВЕРШЁН", fg="#245a2a")
        self.cancel_stage_button.configure(state="disabled")
        self.next_stage_button.configure(state="normal", command=self.open_pending_result)

    def open_pending_result(self):
        if self.pending_stage_result is not None:
            self.show_stage_result(self.pending_stage_result)

    def start_training(self):
        self.session = []
        self.training = True
        self.start_stage(1)

    def show_stage_result(self, result: dict):
        self.clear(); self.header(f"Этап {result['stage']} завершён")
        card = tk.Frame(self.root, bg=CARD, padx=12, pady=8); card.pack(expand=True, fill="both", padx=16, pady=12)
        tk.Label(card, text=f"ТЕМП ТАБЛИЦ: {result['table_pace']:.3f}", bg=CARD, fg=BLUE,
                 font=("Arial", -24, "bold")).pack(pady=(4, 8))
        data = (
            ("Время этапа", f"{result['duration']:.1f} с"),
            ("Среднее время цикла", f"{result['mean_cycle']:.3f} с"),
            ("Ошибки", str(result['errors'])),
            ("Среднее время цикла 7–9", f"{result['range_mean_cycle']:.3f} с"),
            ("Ошибки 7–9", str(result['range_errors'])),
            ("Индекс помехоустойчивости", f"{result['interference_index']:.3f}"),
        )
        table = tk.Frame(card, bg=CARD); table.pack()
        for row, (name, value) in enumerate(data):
            tk.Label(table, text=name, bg=CARD, fg=MUTED, font=("Arial", -16), anchor="w", width=30).grid(row=row, column=0, pady=5)
            tk.Label(table, text=value, bg=CARD, fg=INK, font=("Arial", -16, "bold"), anchor="e", width=12).grid(row=row, column=1, pady=5)
        if self.training:
            self.training = False
            button(card, "НА ГЛАВНУЮ", self.show_home).pack(pady=(8, 4))
        elif result["stage"] < 3:
            button(card, f"ПЕРЕЙТИ К ЭТАПУ {result['stage'] + 1}", lambda: self.start_stage(result["stage"] + 1)).pack(pady=(8, 4))
        else:
            self.save_result()
            button(card, "ИТОГОВЫЕ РЕЗУЛЬТАТЫ", self.show_final).pack(pady=(8, 4))

    def save_result(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        record = {"date": datetime.now().isoformat(timespec="seconds"),
                  "participant": self.settings.get("participant", ""), "stages": self.session}
        records = read_json(RESULTS_FILE, [])
        if not isinstance(records, list): records = []
        records.append(record)
        RESULTS_FILE.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        new_file = not CSV_FILE.exists()
        with CSV_FILE.open("a", encoding="utf-8-sig", newline="") as stream:
            writer = csv.writer(stream, delimiter=";")
            if new_file:
                writer.writerow(("Дата", "Испытуемый", "Этап", "Время", "Тц", "Ошибки", "Тц 7–9", "Ошибки 7–9", "Темп", "Индекс"))
            for s in self.session:
                writer.writerow((record["date"], record["participant"], s["stage"], f"{s['duration']:.3f}",
                                 f"{s['mean_cycle']:.3f}", s["errors"], f"{s['range_mean_cycle']:.3f}",
                                 s["range_errors"], f"{s['table_pace']:.5f}", f"{s['interference_index']:.5f}"))

    def show_final(self):
        self.clear(); self.header("Итоговые результаты")
        card = tk.Frame(self.root, bg=CARD, padx=32, pady=24); card.pack(expand=True, fill="both", padx=65, pady=32)
        tk.Label(card, text=self.settings.get("participant") or "Испытуемый не указан", bg=CARD, fg=INK,
                 font=("Arial", 18, "bold")).pack(pady=(4, 18))
        chart = tk.Canvas(card, bg=CARD, height=285, highlightthickness=0); chart.pack(fill="x", expand=True)
        chart.update_idletasks(); w = max(700, chart.winfo_width()); cx, cy, radius = w / 2, 142, 105
        points = []
        max_value = max(1.0, *(float(s["table_pace"]) for s in self.session))
        for ring in (.25, .5, .75, 1.0):
            pts=[]
            for i in range(3):
                a=-math.pi/2+i*2*math.pi/3; pts += [cx+radius*ring*math.cos(a), cy+radius*ring*math.sin(a)]
            chart.create_polygon(pts, outline="#d6e0ea", fill="", width=1)
        for i, s in enumerate(self.session):
            a=-math.pi/2+i*2*math.pi/3; ratio=min(1, float(s["table_pace"])/max_value)
            points += [cx+radius*ratio*math.cos(a), cy+radius*ratio*math.sin(a)]
            lx, ly=cx+(radius+27)*math.cos(a), cy+(radius+27)*math.sin(a)
            chart.create_text(lx, ly, text=f"Этап {i+1}\n{s['table_pace']:.3f}", fill=INK, font=("Arial", 10, "bold"), justify="center")
        chart.create_polygon(points, fill="#5aa7dc", stipple="gray50", outline=BLUE, width=3)
        psi = self.session[0]["interference_index"] if self.session else 0
        chart.create_text(w-18, 18, text=f"ψ = {psi:.3f}", anchor="ne", fill="#245a2a", font=("Arial", 16, "bold"))
        tk.Label(card, text=f"Результаты сохранены: {CSV_FILE}", bg=CARD, fg=MUTED, font=("Arial", 9)).pack(pady=5)
        button(card, "НА ГЛАВНУЮ", self.show_home).pack(pady=8)

    def show_history(self):
        records = read_json(RESULTS_FILE, [])
        self.clear(); self.header("Последние результаты")
        card = tk.Frame(self.root, bg=CARD, padx=25, pady=20); card.pack(expand=True, fill="both", padx=45, pady=28)
        columns = ("date", "name", "s1", "s2", "s3")
        tree = ttk.Treeview(card, columns=columns, show="headings", height=15)
        for col, title, width in zip(columns, ("Дата", "Испытуемый", "Этап 1", "Этап 2", "Этап 3"), (180, 280, 110, 110, 110)):
            tree.heading(col, text=title); tree.column(col, width=width, anchor="center")
        for rec in reversed(records[-100:]) if isinstance(records, list) else []:
            vals = [f"{s.get('table_pace', 0):.3f}" for s in rec.get("stages", [])]
            vals += ["—"] * (3-len(vals))
            tree.insert("", "end", values=(rec.get("date", "").replace("T", " "), rec.get("participant") or "—", *vals[:3]))
        tree.pack(expand=True, fill="both")
        button(card, "НАЗАД", self.show_home, primary=False, width=16).pack(pady=(16, 0))

    def save_settings(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        SETTINGS_FILE.write_text(json.dumps(self.settings, ensure_ascii=False, indent=2), encoding="utf-8")

    def confirm_abort(self):
        if messagebox.askyesno("Прервать тест", "Прервать текущий тест и вернуться на главный экран?"):
            self.show_home()

    def close(self):
        self.clear(); self.root.destroy()


def main():
    root = tk.Tk()
    try:
        root.iconname(APP_TITLE)
        style = ttk.Style(root)
        if "clam" in style.theme_names(): style.theme_use("clam")
    except tk.TclError:
        pass
    RedBlackApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
