import random
import tkinter as tk
from dataclasses import dataclass
from itertools import permutations
from typing import Dict, List, Optional, Tuple

ALPHABET = "ABCD"
LETTER_TO_DIGIT: Dict[str, int] = {"A": 1, "B": 2, "C": 3, "D": 4}
COLOR_NAMES: Dict[str, str] = {"A": "розовый", "B": "синий", "C": "зеленый", "D": "желтый"}
ROWS = 3
COLS = 4
CELL_WIDTH = 180
CELL_HEIGHT = 110

POCKET_COLORS: Dict[str, str] = {
    "A": "#ef476f",
    "B": "#118ab2",
    "C": "#06d6a0",
    "D": "#ffd166",
}

POS_PATTERNS = {
    2: ["11", "12"],
    3: ["123", "121", "122", "112"],
    4: ["1122", "1221", "1123", "1223", "1323", "1233", "1213", "1234"],
}

NONPOS_PATTERNS_Y = {
    1: ["112", "121", "211"],
    3: ["123", "132", "213", "231", "312", "321"],
}

NONPOS_PATTERNS_X = {
    1: ["1112", "1121", "1211", "2111"],
    2: ["1122", "1221", "2211", "2112", "1212", "2121"],
    3: [
        "1231",
        "1321",
        "2131",
        "2311",
        "3121",
        "3211",
        "1213",
        "1312",
        "2113",
        "3112",
        "1123",
        "1132",
    ],
    4: ["".join(p) for p in permutations("1234")],
}


@dataclass
class RuleSpec:
    axis: str
    kind: str
    pattern: Optional[str] = None
    nonpos_type: Optional[int] = None
    z_mode: Optional[str] = None
    z_shift: Optional[int] = None


def shift_letter(letter: str, delta: int) -> str:
    idx = ALPHABET.index(letter)
    return ALPHABET[(idx + delta) % len(ALPHABET)]


def random_letters(count: int) -> List[str]:
    return random.sample(list(ALPHABET), count)


def shuffled_alphabet() -> List[str]:
    letters = list(ALPHABET)
    random.shuffle(letters)
    return letters


def choose_methods(L: int) -> List[str]:
    methods = [random.choice(["x", "y"])]
    for _ in range(1, L):
        methods.append(random.choice(["x", "y", "z"]))
    if all(m == "z" for m in methods):
        methods[0] = random.choice(["x", "y"])
    return methods


def choose_rule_for_axis(axis: str) -> RuleSpec:
    if axis == "x":
        if random.choice([True, False]):
            return RuleSpec(axis="x", kind="positional", pattern=random.choice(POS_PATTERNS[4]))
        nonpos_type = random.choice(sorted(NONPOS_PATTERNS_X.keys()))
        return RuleSpec(
            axis="x",
            kind="nonpositional",
            pattern=random.choice(NONPOS_PATTERNS_X[nonpos_type]),
            nonpos_type=nonpos_type,
        )

    if axis == "y":
        if random.choice([True, False]):
            return RuleSpec(axis="y", kind="positional", pattern=random.choice(POS_PATTERNS[3]))
        nonpos_type = random.choice(sorted(NONPOS_PATTERNS_Y.keys()))
        return RuleSpec(
            axis="y",
            kind="nonpositional",
            pattern=random.choice(NONPOS_PATTERNS_Y[nonpos_type]),
            nonpos_type=nonpos_type,
        )

    mode, shift = random.choice(
        [
            ("shift_prev", -2),
            ("shift_prev", -1),
            ("shift_prev", 0),
            ("shift_prev", 1),
            ("shift_prev", 2),
            ("copy_left_prev", 0),
            ("copy_top_prev", 0),
            ("copy_left_prev", 1),
            ("copy_top_prev", 1),
        ]
    )
    return RuleSpec(axis="z", kind="z_op", z_mode=mode, z_shift=shift)


def _build_signature_plane_for_rule(rule: RuleSpec) -> List[List[str]]:
    sig = [["" for _ in range(COLS)] for _ in range(ROWS)]
    assert rule.pattern is not None
    if rule.axis == "x":
        for r in range(ROWS):
            for c in range(COLS):
                sig[r][c] = rule.pattern[c]
        return sig
    for c in range(COLS):
        for r in range(ROWS):
            sig[r][c] = rule.pattern[r]
    return sig


def _signature_to_plane_letters(signature: List[List[str]], alphabet_order: List[str]) -> List[List[str]]:
    out = [["" for _ in range(COLS)] for _ in range(ROWS)]
    token_to_letter: Dict[str, str] = {}
    next_index = 0
    for r in range(ROWS):
        for c in range(COLS):
            token = signature[r][c]
            if token not in token_to_letter:
                token_to_letter[token] = alphabet_order[next_index]
                next_index += 1
            out[r][c] = token_to_letter[token]
    return out


def _signature_from_plane_letters(plane: List[List[str]]) -> List[List[str]]:
    sig = [["" for _ in range(COLS)] for _ in range(ROWS)]
    for r in range(ROWS):
        for c in range(COLS):
            sig[r][c] = str(LETTER_TO_DIGIT[plane[r][c]])
    return sig


def generate_z_plane(prev_plane: List[List[str]], rule: RuleSpec) -> List[List[str]]:
    plane = [["" for _ in range(COLS)] for _ in range(ROWS)]
    for r in range(ROWS):
        for c in range(COLS):
            if rule.z_mode == "shift_prev":
                plane[r][c] = shift_letter(prev_plane[r][c], rule.z_shift or 0)
            elif rule.z_mode == "copy_left_prev":
                plane[r][c] = shift_letter(prev_plane[r][c - 1], rule.z_shift or 0) if c > 0 else random.choice(ALPHABET)
            elif rule.z_mode == "copy_top_prev":
                plane[r][c] = shift_letter(prev_plane[r - 1][c], rule.z_shift or 0) if r > 0 else random.choice(ALPHABET)
            else:
                plane[r][c] = random.choice(ALPHABET)
    return plane


def compose_cells(planes: List[List[List[str]]]) -> List[List[str]]:
    cells = [["" for _ in range(COLS)] for _ in range(ROWS)]
    for r in range(ROWS):
        for c in range(COLS):
            cells[r][c] = "".join(planes[k][r][c] for k in range(len(planes)))
    return cells


def _format_rule(idx: int, rule: RuleSpec, axis: str) -> str:
    if axis in ("x", "y"):
        if rule.kind == "positional":
            return f"k{idx}: {axis} pos({rule.pattern})"
        return f"k{idx}: {axis} nonpos({rule.pattern})"
    if rule.z_mode == "shift_prev":
        return f"k{idx}: z shift({rule.z_shift:+d})"
    if rule.z_shift:
        return f"k{idx}: z {rule.z_mode}({rule.z_shift:+d})"
    return f"k{idx}: z {rule.z_mode}"


def generate_tensor(selected_l: Optional[int] = None) -> Tuple[int, List[List[str]], List[str], Dict[str, object]]:
    L = selected_l if selected_l in (2, 3, 4) else random.choice([2, 3, 4])
    methods = choose_methods(L)
    letter_planes: List[List[List[str]]] = []
    signature_planes: List[List[List[str]]] = []
    pocket_alphabets: List[List[str]] = []
    rule_descriptions: List[str] = []

    # 1) Всегда начинаем с первого кармана.
    # 2) Для него задаем значение через случайную перестановку A/B/C/D.
    # 3) На основе сигнатуры строим все первые карманы ячеек.
    first_axis = methods[0]
    first_rule = choose_rule_for_axis(first_axis)
    first_signature = _build_signature_plane_for_rule(first_rule)
    first_alphabet = shuffled_alphabet()
    first_plane = _signature_to_plane_letters(first_signature, first_alphabet)
    signature_planes.append(first_signature)
    letter_planes.append(first_plane)
    pocket_alphabets.append(first_alphabet)
    rule_descriptions.append(_format_rule(1, first_rule, first_axis) + f"; alphabet={''.join(first_alphabet)}")

    # 4) Генерируем вторые карманы и далее.
    for idx in range(1, L):
        method = methods[idx]
        if method in ("x", "y"):
            rule = choose_rule_for_axis(method)
            sig_plane = _build_signature_plane_for_rule(rule)
            
            # Для позиционных используем новый shuffled_alphabet()
            # Для непозиционных используем символы из предыдущей плоскости в перетасованном порядке
            if rule.kind == "positional":
                alphabet_order = shuffled_alphabet()
            else:
                # Собираем уникальные символы из предыдущей плоскости и перетасовываем их
                prev_symbols = set()
                for r in range(ROWS):
                    for c in range(COLS):
                        prev_symbols.add(letter_planes[-1][r][c])
                alphabet_order = list(prev_symbols)
                random.shuffle(alphabet_order)
            
            plane = _signature_to_plane_letters(sig_plane, alphabet_order)
            signature_planes.append(sig_plane)
            letter_planes.append(plane)
            pocket_alphabets.append(alphabet_order)
            rule_descriptions.append(_format_rule(idx + 1, rule, method) + f"; alphabet={''.join(alphabet_order)}")
        else:
            rule = choose_rule_for_axis("z")
            plane = generate_z_plane(letter_planes[-1], rule)
            sig_plane = _signature_from_plane_letters(plane)
            signature_planes.append(sig_plane)
            letter_planes.append(plane)
            pocket_alphabets.append([])
            rule_descriptions.append(_format_rule(idx + 1, rule, "z"))

    debug_info: Dict[str, object] = {
        "methods": methods,
        "letter_planes": letter_planes,
        "signature_planes": signature_planes,
        "pocket_alphabets": pocket_alphabets,
    }
    return L, compose_cells(letter_planes), rule_descriptions, debug_info


def code_to_color_names(code: str) -> str:
    return "-".join(COLOR_NAMES[ch] for ch in code)


class TensorMatrixApp:
    def __init__(self, master: tk.Tk) -> None:
        self.master = master
        self.master.title("Генератор матриц 4x3 (цветные квадраты)")
        screen_w = self.master.winfo_screenwidth()
        screen_h = self.master.winfo_screenheight()
        self.master.geometry(f"{int(screen_w * 0.92)}x{int(screen_h * 0.9)}+20+20")
        self.master.minsize(860, 680)
        self.master.configure(bg="#f2f2f2")

        self.current_l = 0
        self.current_cells: Optional[List[List[str]]] = None
        self.correct_answer = ""
        self.missing_r = -1
        self.missing_c = -1
        self.user_answer: List[Optional[str]] = []
        self.selected_slot: Optional[int] = None
        self.current_debug_info: Dict[str, object] = {}

        l_frame = tk.Frame(master, bg="#f2f2f2")
        l_frame.pack(pady=(12, 10))
        tk.Label(l_frame, text="Число карманов L:", font=("Arial", 12, "bold"), bg="#f2f2f2").pack(side="left", padx=(0, 10))
        self.l_var = tk.IntVar(value=3)
        for l_value in (2, 3, 4):
            radio = tk.Radiobutton(
                l_frame,
                text=str(l_value),
                variable=self.l_var,
                value=l_value,
                command=self.on_l_change,
                font=("Arial", 13),
                bg="#f2f2f2",
                activebackground="#f2f2f2",
                highlightthickness=0,
            )
            radio.pack(side="left", padx=10)

        self.matrix_area = tk.Frame(master, bg="#f2f2f2")
        self.matrix_area.pack(fill="both", expand=True, pady=8)

        self.content_row = tk.Frame(self.matrix_area, bg="#f2f2f2")
        self.content_row.pack(fill="both", expand=True, padx=10)

        self.left_panel = tk.Frame(self.content_row, bg="#f2f2f2")
        self.left_panel.pack(side="left", fill="both", expand=False, padx=(0, 10))

        self.right_panel = tk.Frame(self.content_row, bg="#f2f2f2")
        self.right_panel.pack(side="left", fill="both", expand=True)

        self.grid_frame = tk.Frame(self.left_panel, bg="#f2f2f2")
        self.grid_frame.pack()

        self.cell_canvases: List[List[tk.Canvas]] = []
        for r in range(ROWS):
            row_canvases: List[tk.Canvas] = []
            for c in range(COLS):
                canvas = tk.Canvas(
                    self.grid_frame,
                    width=CELL_WIDTH,
                    height=CELL_HEIGHT,
                    bg="white",
                    highlightthickness=2,
                    highlightbackground="#c9ced6",
                )
                canvas.grid(row=r, column=c, padx=8, pady=8)
                canvas.bind("<Button-1>", lambda event, rr=r, cc=c: self.on_cell_click(rr, cc, event))
                row_canvases.append(canvas)
            self.cell_canvases.append(row_canvases)

        action_frame = tk.Frame(self.left_panel, bg="#f2f2f2")
        action_frame.pack(pady=(8, 6))

        self.next_btn = tk.Button(
            action_frame,
            text="Далее",
            font=("Arial", 13, "bold"),
            width=10,
            height=2,
            command=self.check_and_next,
            bg="#2eb872",
            fg="white",
            activebackground="#269863",
        )
        self.next_btn.pack(side="left", padx=8)

        self.cancel_btn = tk.Button(
            action_frame,
            text="Отмена",
            font=("Arial", 13, "bold"),
            width=10,
            height=2,
            command=self.reset_missing_cell,
            bg="#f4d35e",
            fg="#333333",
            activebackground="#e7c650",
        )
        self.cancel_btn.pack(side="left", padx=8)

        self.status_label = tk.Label(self.left_panel, text="", font=("Arial", 13, "bold"), bg="#f2f2f2", fg="#1f3b73")
        self.status_label.pack(pady=(10, 8))

        self.palette_frame = tk.Frame(self.left_panel, bg="#f2f2f2")
        self.palette_frame.pack(pady=(2, 8))
        self.palette_buttons_frame = tk.Frame(self.palette_frame, bg="#f2f2f2")
        self.palette_buttons_frame.pack()
        for pocket in ALPHABET:
            tk.Button(
                self.palette_buttons_frame,
                text=pocket,
                command=lambda p=pocket: self.apply_color(p),
                width=6,
                height=2,
                font=("Arial", 12, "bold"),
                bg=POCKET_COLORS[pocket],
                fg="#1f1f1f",
                activebackground=POCKET_COLORS[pocket],
            ).pack(side="left", padx=5)

        self.correct_preview_label = tk.Label(
            self.left_panel,
            text="",
            font=("Arial", 11, "bold"),
            bg="#f2f2f2",
            fg="#2f2f2f",
        )
        self.correct_preview_label.pack(pady=(2, 2))

        self.correct_preview_canvas = tk.Canvas(
            self.left_panel,
            width=CELL_WIDTH,
            height=CELL_HEIGHT,
            bg="#f2f2f2",
            highlightthickness=0,
        )
        self.correct_preview_canvas.pack(pady=(0, 8))

        tk.Label(
            self.right_panel,
            text="Служебные параметры",
            font=("Arial", 12, "bold"),
            bg="#f2f2f2",
            fg="#2f2f2f",
            anchor="w",
        ).pack(fill="x", pady=(0, 6))

        self.debug_frame = tk.Frame(self.right_panel, bg="#f2f2f2")
        self.debug_frame.pack(fill="both", expand=True, pady=(2, 8))
        self.debug_text = tk.Text(
            self.debug_frame,
            font=("Courier New", 10),
            bg="#fcfcfc",
            fg="#3f3f3f",
            wrap="word",
            height=10,
            padx=10,
            pady=8,
            relief="solid",
            bd=1,
        )
        self.debug_scroll = tk.Scrollbar(self.debug_frame, orient="vertical", command=self.debug_text.yview)
        self.debug_text.configure(yscrollcommand=self.debug_scroll.set)
        self.debug_text.pack(side="left", fill="both", expand=True)
        self.debug_scroll.pack(side="right", fill="y")
        self.debug_text.configure(state="disabled")

        btn_frame = tk.Frame(master, bg="#f2f2f2")
        btn_frame.pack(side="bottom", fill="x", padx=16, pady=(8, 14))

        self.start_btn = tk.Button(
            btn_frame,
            text="Начать тестирование",
            font=("Arial", 13, "bold"),
            width=18,
            height=2,
            command=self.start_test,
            bg="#4CAF50",
            fg="white",
            activebackground="#449d48",
        )
        self.start_btn.pack(side="left")

        self.exit_btn = tk.Button(
            btn_frame,
            text="Выход",
            font=("Arial", 13, "bold"),
            width=10,
            height=2,
            command=self.master.destroy,
            bg="#d9534f",
            fg="white",
            activebackground="#c9302c",
        )
        self.exit_btn.pack(side="right")

        self.start_test()

    def _show_popup(self, text: str, bg: str, fg: str = "white", duration_ms: int = 1800) -> None:
        popup = tk.Toplevel(self.master)
        popup.transient(self.master)
        popup.grab_set()
        popup.title("")
        popup.configure(bg=bg)
        popup.resizable(False, False)
        tk.Label(popup, text=text, bg=bg, fg=fg, font=("Arial", 14, "bold"), padx=18, pady=14).pack()
        popup.update_idletasks()
        x = self.master.winfo_rootx() + (self.master.winfo_width() - popup.winfo_width()) // 2
        y = self.master.winfo_rooty() + 80
        popup.geometry(f"+{x}+{y}")
        popup.after(duration_ms, popup.destroy)

    def _slot_positions(self, count: int, width: int = CELL_WIDTH, height: int = CELL_HEIGHT) -> Tuple[List[Tuple[float, float]], int]:
        square = 28
        h_gap = 10
        v_gap = 8
        x_center = width / 2
        y_center = height / 2

        if count == 2:
            total_w = 2 * square + h_gap
            x0 = (width - total_w) / 2
            y0 = y_center - square / 2
            return [(x0, y0), (x0 + square + h_gap, y0)], square

        if count == 3:
            total_w = 2 * square + h_gap
            x0 = (width - total_w) / 2
            y_top = y_center - square - v_gap / 2
            y_bottom = y_center + v_gap / 2
            return [(x0, y_top), (x0 + square + h_gap, y_top), (x_center - square / 2, y_bottom)], square

        if count == 4:
            total_w = 2 * square + h_gap
            x0 = (width - total_w) / 2
            y_top = y_center - square - v_gap / 2
            y_bottom = y_center + v_gap / 2
            return [
                (x0, y_top),
                (x0 + square + h_gap, y_top),
                (x0, y_bottom),
                (x0 + square + h_gap, y_bottom),
            ], square

        total_w = count * square + (count - 1) * h_gap
        x0 = (width - total_w) / 2
        y0 = y_center - square / 2
        return [(x0 + i * (square + h_gap), y0) for i in range(count)], square

    def _draw_code(self, canvas: tk.Canvas, code: str) -> None:
        canvas.delete("all")
        positions, square = self._slot_positions(len(code))
        for idx, ch in enumerate(code):
            x0, y0 = positions[idx]
            canvas.create_rectangle(
                x0,
                y0,
                x0 + square,
                y0 + square,
                fill=POCKET_COLORS.get(ch, "#d0d0d0"),
                outline="#444444",
                width=1,
            )

    def _draw_correct_preview(self, code: str) -> None:
        self.correct_preview_canvas.delete("all")
        positions, square = self._slot_positions(len(code))
        for idx, ch in enumerate(code):
            x0, y0 = positions[idx]
            self.correct_preview_canvas.create_rectangle(
                x0,
                y0,
                x0 + square,
                y0 + square,
                fill=POCKET_COLORS.get(ch, "#d0d0d0"),
                outline="#444444",
                width=1,
            )

    def _clear_correct_preview(self) -> None:
        self.correct_preview_label.config(text="")
        self.correct_preview_canvas.delete("all")

    def _draw_missing_cell(self) -> None:
        if self.missing_r < 0 or self.missing_c < 0 or not self.correct_answer:
            return
        canvas = self.cell_canvases[self.missing_r][self.missing_c]
        canvas.delete("all")
        positions, square = self._slot_positions(len(self.correct_answer))
        for idx in range(len(self.correct_answer)):
            x0, y0 = positions[idx]
            chosen = self.user_answer[idx] if idx < len(self.user_answer) else None
            fill_color = POCKET_COLORS.get(chosen, "#ffffff") if chosen else "#ffffff"
            outline_color = "#2b2b2b" if idx == self.selected_slot else "#9fa6ad"
            border = 2 if idx == self.selected_slot else 1
            canvas.create_rectangle(x0, y0, x0 + square, y0 + square, fill=fill_color, outline=outline_color, width=border)

    def on_cell_click(self, row: int, col: int, event: tk.Event) -> None:
        if row != self.missing_r or col != self.missing_c or not self.correct_answer:
            return
        positions, square = self._slot_positions(len(self.correct_answer))
        self.selected_slot = None
        for idx in range(len(self.correct_answer)):
            x0, y0 = positions[idx]
            if x0 <= event.x <= x0 + square and y0 <= event.y <= y0 + square:
                self.selected_slot = idx
                break
        self._draw_missing_cell()

    def apply_color(self, pocket: str) -> None:
        if not self.correct_answer:
            return
        if self.selected_slot is None:
            self.status_label.config(text="Сначала кликни по нужному пустому карману.", fg="#8a6d3b")
            return
        self.user_answer[self.selected_slot] = pocket
        self._draw_missing_cell()

    def reset_missing_cell(self) -> None:
        if not self.correct_answer:
            return
        self.user_answer = [None] * len(self.correct_answer)
        self.selected_slot = None
        self.status_label.config(text="Выбор в пустой ячейке сброшен.", fg="#1f3b73")
        self._draw_missing_cell()

    def _reveal_correct_answer(self) -> None:
        self.user_answer = list(self.correct_answer)
        self.selected_slot = None
        self._draw_missing_cell()

    def check_and_next(self) -> None:
        if not self.correct_answer:
            self.status_label.config(text="Сначала нажми «Начать тестирование».", fg="#8a6d3b")
            return
        if any(ch is None for ch in self.user_answer):
            self.status_label.config(text="Заполни все пустые карманы перед проверкой.", fg="#8a6d3b")
            return

        attempt = "".join(ch for ch in self.user_answer if ch is not None)
        if attempt == self.correct_answer:
            self.status_label.config(text="Верно", fg="#1e7f3f")
            self._show_popup("Верно", bg="#2eb872", fg="white", duration_ms=1200)
            self.master.after(1250, self.start_test)
        else:
            text = f"Неверно. Правильно: {self.correct_answer} ({code_to_color_names(self.correct_answer)})"
            self.status_label.config(text=text, fg="#a94442")
            self.correct_preview_label.config(text="Правильный ответ:")
            self._draw_correct_preview(self.correct_answer)
            self._show_popup("Неверно. Показан правильный ответ.", bg="#f0ad4e", fg="#333333", duration_ms=2200)
            self._reveal_correct_answer()

    def _format_cells_letters(self, cells: List[List[str]]) -> str:
        rows = [" ".join(cells[r][c] for c in range(COLS)) for r in range(ROWS)]
        return "\n".join(rows)

    def _format_plane(self, plane: List[List[str]]) -> str:
        return "\n".join(" ".join(plane[r][c] for c in range(COLS)) for r in range(ROWS))

    def _update_debug_block(self, cells: List[List[str]], rules: List[str], debug_info: Dict[str, object]) -> None:
        letter_planes: List[List[List[str]]] = debug_info.get("letter_planes", [])  # type: ignore[assignment]
        signature_planes: List[List[List[str]]] = debug_info.get("signature_planes", [])  # type: ignore[assignment]
        pocket_alphabets: List[List[str]] = debug_info.get("pocket_alphabets", [])  # type: ignore[assignment]

        mapping_digits = ", ".join(f"{ch}→{LETTER_TO_DIGIT[ch]}" for ch in ALPHABET)
        mapping_colors = ", ".join(f"{ch}→{COLOR_NAMES[ch]} ({POCKET_COLORS[ch]})" for ch in ALPHABET)

        lines: List[str] = []
        lines.append("1) Вид в буквах (матрица кодов):")
        lines.append(self._format_cells_letters(cells))
        lines.append("")
        lines.append("2) Вид в сигнатурах (по карманам):")
        for idx, sig_plane in enumerate(signature_planes, start=1):
            lines.append(f"k{idx}:")
            lines.append(self._format_plane(sig_plane))
            if idx - 1 < len(pocket_alphabets) and pocket_alphabets[idx - 1]:
                lines.append(f"alphabet k{idx}: {''.join(pocket_alphabets[idx - 1])}")
            if idx - 1 < len(letter_planes):
                lines.append(f"letters k{idx}:")
                lines.append(self._format_plane(letter_planes[idx - 1]))
            lines.append("")
        lines.append("3) Как буквы переводятся в цифры:")
        lines.append(mapping_digits)
        lines.append("")
        lines.append("4) Как буквы переводятся в цвета:")
        lines.append(mapping_colors)

        full_text = "Правила генерации:\n" + "\n".join(rules) + "\n\n" + "\n".join(lines)
        self.debug_text.configure(state="normal")
        self.debug_text.delete("1.0", "end")
        self.debug_text.insert("1.0", full_text)
        self.debug_text.see("1.0")
        self.debug_text.configure(state="disabled")

    def start_test(self) -> None:
        L, cells, rules, debug_info = generate_tensor(self.l_var.get())
        self.current_l = L
        self.current_cells = cells
        self.current_debug_info = debug_info
        self.missing_r = random.randrange(ROWS)
        self.missing_c = random.randrange(COLS)
        self.correct_answer = cells[self.missing_r][self.missing_c]
        self.user_answer = [None] * len(self.correct_answer)
        self.selected_slot = None
        self._clear_correct_preview()

        for r in range(ROWS):
            for c in range(COLS):
                if r == self.missing_r and c == self.missing_c:
                    continue
                self._draw_code(self.cell_canvases[r][c], cells[r][c])
        self._draw_missing_cell()

        self.status_label.config(text="Выбери карман кликом и закрась его цветом из палитры.", fg="#1f3b73")
        self._update_debug_block(cells, rules, debug_info)

    def on_l_change(self) -> None:
        self.start_test()


def main() -> None:
    root = tk.Tk()
    TensorMatrixApp(root)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        try:
            root.destroy()
        except Exception:
            pass


if __name__ == "__main__":
    main()
