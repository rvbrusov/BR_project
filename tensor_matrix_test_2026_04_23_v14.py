import random
import tkinter as tk
import csv
import time
from dataclasses import dataclass
from datetime import datetime
from itertools import permutations
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ALPHABET = "ABCD"
LETTER_TO_DIGIT: Dict[str, int] = {"A": 1, "B": 2, "C": 3, "D": 4}
COLOR_NAMES: Dict[str, str] = {"A": "красный", "B": "синий", "C": "желтый", "D": "черный"}
ROWS = 3
COLS = 4
WHITE_ALLOWED_CELLS = [
    (r, c)
    for r in range(ROWS)
    for c in range(COLS)
    if (r, c) not in {(0, 0), (0, COLS - 1), (ROWS - 1, 0), (ROWS - 1, COLS - 1)}
]
CELL_WIDTH = 180
CELL_HEIGHT = 110

POCKET_COLORS: Dict[str, str] = {
    "A": "#c00000",
    "B": "#000795",
    "C": "#e9f201",
    "D": "#000000",
}
INSTRUCTION_TEXT = (
    "Вам будут показаны 12 щитов, закрашенных по определенной логике.\n"
    "Один щит пустой.\n"
    "Ваша задача - понять, какие цвета должны быть использованы для этого щита и закрасить их. "
    "Для этого нажмите на белое поле щита, а потом - на цвет, который считаете подходящим.\n"
    "Когда закончите - нажмите кнопку \"Далее\"."
)

POS_PATTERNS = {
    2: ["11", "12"],
    3: ["111", "123", "121", "122", "112"],
    4: ["1111", "1122", "1221", "1123", "1223", "1323", "1233", "1213", "1234"],
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
FORBIDDEN_X_PATTERNS = {"122", "112", "221"}


@dataclass
class RuleSpec:
    axis: str
    kind: str
    pattern: Optional[str] = None
    nonpos_type: Optional[int] = None


def shuffled_alphabet() -> List[str]:
    letters = list(ALPHABET)
    random.shuffle(letters)
    return letters


def choose_methods(L: int) -> List[str]:
    methods = [random.choice(["x", "y"])]
    for _ in range(1, L):
        methods.append(random.choice(["x", "y"]))
    return methods


def _pick_nonpos_pattern(axis: str, nonpos_type: int) -> str:
    if axis == "x":
        pool = [p for p in NONPOS_PATTERNS_X[nonpos_type] if p not in FORBIDDEN_X_PATTERNS]
        positional_pool = set(POS_PATTERNS[4])
    else:
        pool = NONPOS_PATTERNS_Y[nonpos_type]
        positional_pool = set(POS_PATTERNS[3])
    filtered = [p for p in pool if p not in positional_pool]
    if filtered:
        return random.choice(filtered)
    return random.choice(pool)


def _all_unique_permutations(pattern: str) -> List[str]:
    return sorted({"".join(p) for p in permutations(pattern)})


def _pick_nonpos_variants(pattern: str, count: int) -> List[str]:
    variants = _all_unique_permutations(pattern)
    if not variants:
        return [pattern] * count
    if len(variants) >= count:
        return random.sample(variants, count)
    out = variants[:]
    while len(out) < count:
        out.append(random.choice(variants))
    if len(set(out)) == 1 and len(variants) > 1:
        out[-1] = random.choice([v for v in variants if v != out[0]])
    return out


def choose_rule_for_axis(axis: str) -> RuleSpec:
    if axis == "x":
        mode = random.choice(["positional", "nonpositional"])
        if mode == "positional":
            pool = [p for p in POS_PATTERNS[4] if len(p) == 4 and p not in FORBIDDEN_X_PATTERNS]
            return RuleSpec(axis="x", kind="positional", pattern=random.choice(pool))
        nonpos_type = random.choice(sorted(NONPOS_PATTERNS_X.keys()))
        return RuleSpec(
            axis="x",
            kind="nonpositional",
            pattern=_pick_nonpos_pattern("x", nonpos_type),
            nonpos_type=nonpos_type,
        )

    if axis == "y":
        if random.choice([True, False]):
            return RuleSpec(axis="y", kind="positional", pattern=random.choice(POS_PATTERNS[3]))
        nonpos_type = random.choice(sorted(NONPOS_PATTERNS_Y.keys()))
        return RuleSpec(
            axis="y",
            kind="nonpositional",
            pattern=_pick_nonpos_pattern("y", nonpos_type),
            nonpos_type=nonpos_type,
        )

    raise ValueError(f"Unsupported axis: {axis}")


def _build_signature_plane_for_rule(rule: RuleSpec) -> List[List[str]]:
    sig = [["" for _ in range(COLS)] for _ in range(ROWS)]
    assert rule.pattern is not None
    if rule.axis == "x" and rule.kind == "nonpositional":
        row_patterns = _pick_nonpos_variants(rule.pattern, ROWS)
        for r in range(ROWS):
            row_tokens = row_patterns[r]
            for c in range(COLS):
                sig[r][c] = row_tokens[c]
        return sig
    if rule.axis == "x":
        for r in range(ROWS):
            for c in range(COLS):
                sig[r][c] = rule.pattern[c]
        return sig
    if rule.axis == "y" and rule.kind == "nonpositional":
        col_patterns = _pick_nonpos_variants(rule.pattern, COLS)
        for c in range(COLS):
            col_tokens = col_patterns[c]
            for r in range(ROWS):
                sig[r][c] = col_tokens[r]
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
    return f"k{idx}: {axis} {rule.kind}({rule.pattern})"


def _axis_signature_complexity(rule: RuleSpec) -> int:
    pattern = rule.pattern or ""
    uniq = len(set(pattern)) if pattern else 0
    if rule.axis == "x":
        if rule.kind == "positional":
            if uniq == 1:
                return 1
            if uniq in (2, 4):
                return 2
            if uniq == 3:
                return 3
        if rule.kind == "nonpositional":
            if uniq in (2, 4):
                return 3
            if uniq == 3:
                return 4
            return 3
    if rule.axis == "y":
        if rule.kind == "positional":
            if uniq == 1:
                return 1
            if uniq in (2, 3):
                return 2
        if rule.kind == "nonpositional":
            if uniq == 3:
                return 3
            if uniq == 2:
                return 4
            return 3
    return 2


def _calculate_set_complexity(L: int, methods: List[str], rules_specs: List[RuleSpec]) -> Dict[str, object]:
    per_pocket = [_axis_signature_complexity(rule) for rule in rules_specs]
    total = int(sum(per_pocket))
    elements_bonus = 0
    if L == 3:
        elements_bonus = 1
    elif L == 4:
        elements_bonus = 2
    total += elements_bonus
    mix_bonus = 1 if ("x" in methods and "y" in methods) else 0
    total += mix_bonus
    four_pockets_single_axis_bonus = 0
    if L == 4:
        x_count = methods.count("x")
        y_count = methods.count("y")
        if (x_count == 1 and y_count == 3) or (y_count == 1 and x_count == 3):
            four_pockets_single_axis_bonus = 2
    total += four_pockets_single_axis_bonus
    total = max(2, min(20, total))
    return {
        "total": total,
        "per_pocket": per_pocket,
        "elements_bonus": elements_bonus,
        "mix_bonus_xy": mix_bonus,
        "four_pockets_single_axis_bonus": four_pockets_single_axis_bonus,
        "methods": methods[:],
    }


def _generate_tensor_once(selected_l: Optional[int] = None) -> Tuple[int, List[List[str]], List[str], Dict[str, object]]:
    L = selected_l if selected_l in (2, 3, 4) else random.choice([2, 3, 4])
    methods = choose_methods(L)
    letter_planes: List[List[List[str]]] = []
    signature_planes: List[List[List[str]]] = []
    pocket_alphabets: List[List[str]] = []
    rule_descriptions: List[str] = []
    rules_specs: List[RuleSpec] = []

    # 1) Всегда начинаем с первого кармана.
    # 2) Для него задаем значение через случайную перестановку A/B/C/D.
    # 3) На основе сигнатуры строим все первые карманы ячеек.
    first_axis = methods[0]
    first_rule = choose_rule_for_axis(first_axis)
    first_signature = _build_signature_plane_for_rule(first_rule)
    first_alphabet = shuffled_alphabet()
    first_plane = _signature_to_plane_letters(first_signature, first_alphabet)
    rules_specs.append(first_rule)
    signature_planes.append(first_signature)
    letter_planes.append(first_plane)
    pocket_alphabets.append(first_alphabet)
    rule_descriptions.append(_format_rule(1, first_rule, first_axis) + f"; alphabet={''.join(first_alphabet)}")

    # 4) Генерируем вторые карманы и далее.
    for idx in range(1, L):
        method = methods[idx]
        rule = choose_rule_for_axis(method)
        sig_plane = _build_signature_plane_for_rule(rule)
        alphabet_order = shuffled_alphabet()
        plane = _signature_to_plane_letters(sig_plane, alphabet_order)
        rules_specs.append(rule)
        signature_planes.append(sig_plane)
        letter_planes.append(plane)
        pocket_alphabets.append(alphabet_order)
        rule_descriptions.append(_format_rule(idx + 1, rule, method) + f"; alphabet={''.join(alphabet_order)}")

    complexity_info = _calculate_set_complexity(L, methods, rules_specs)
    rule_descriptions.append(
        "complexity: "
        f"{complexity_info['total']} "
        f"(per_pocket={complexity_info['per_pocket']}, "
        f"L_bonus={complexity_info['elements_bonus']}, "
        f"xy_mix_bonus={complexity_info['mix_bonus_xy']}, "
        f"L4_1v3_bonus={complexity_info['four_pockets_single_axis_bonus']})"
    )

    debug_info: Dict[str, object] = {
        "methods": methods,
        "rules_specs": rules_specs,
        "letter_planes": letter_planes,
        "signature_planes": signature_planes,
        "pocket_alphabets": pocket_alphabets,
        "complexity_info": complexity_info,
    }
    return L, compose_cells(letter_planes), rule_descriptions, debug_info


def generate_tensor(selected_l: Optional[int] = None, target_difficulty: Optional[int] = None) -> Tuple[int, List[List[str]], List[str], Dict[str, object]]:
    if target_difficulty is None:
        return _generate_tensor_once(selected_l)
    target = max(2, min(20, int(target_difficulty)))
    best: Optional[Tuple[int, List[List[str]], List[str], Dict[str, object]]] = None
    best_score: Tuple[int, int, int] = (10**9, 10**9, 10**9)
    attempts = 2500 if target <= 5 else 450
    for _ in range(attempts):
        candidate = _generate_tensor_once(selected_l)
        info = candidate[3].get("complexity_info", {})
        actual = int(info.get("total", 2)) if isinstance(info, dict) else 2
        diff = abs(actual - target)
        direction_penalty = 0 if actual >= target else 1
        score = (diff, direction_penalty, random.randint(0, 10**6))
        if score < best_score:
            best = candidate
            best_score = score
        if diff == 0:
            break
    assert best is not None
    return best


def code_to_color_names(code: str) -> str:
    return "-".join(COLOR_NAMES[ch] for ch in code)


class TensorMatrixApp:
    def __init__(self, master: tk.Tk) -> None:
        self.master = master
        self.master.title("Генератор матриц 4x3 (цветные квадраты)")
        screen_w = self.master.winfo_screenwidth()
        screen_h = self.master.winfo_screenheight()
        self.master.geometry(f"{screen_w}x{screen_h}+0+0")
        self.master.minsize(860, 680)
        self.master.configure(bg="#f2f2f2")
        self.is_fullscreen = True
        try:
            self.master.state("zoomed")
        except Exception:
            pass
        self.master.attributes("-fullscreen", True)
        self.master.bind("<F11>", self._toggle_fullscreen)
        self.master.bind("<Escape>", self._exit_fullscreen)

        self.current_l = 0
        self.current_cells: Optional[List[List[str]]] = None
        self.correct_answer = ""
        self.missing_r = -1
        self.missing_c = -1
        self.user_answer: List[Optional[str]] = []
        self.selected_slot: Optional[int] = None
        self.current_debug_info: Dict[str, object] = {}
        self.current_target_difficulty = random.randint(2, 5)
        self.current_actual_difficulty = 2
        self.current_errors = 0
        self.current_started_at = time.monotonic()
        self.task_counter = 0
        self.intro_visible = True
        self.results_file = Path(__file__).resolve().parent / "data" / "tensor_matrix_results.csv"
        self._ensure_results_file()

        l_frame = tk.Frame(master, bg="#f2f2f2")
        l_frame.pack(pady=(12, 10))
        tk.Label(l_frame, text="Число карманов L:", font=("Arial", 12, "bold"), bg="#f2f2f2").pack(side="left", padx=(0, 10))
        self.l_var = tk.IntVar(value=2)
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

        self._build_intro_overlay()

    def _build_intro_overlay(self) -> None:
        self.intro_overlay = tk.Frame(self.master, bg="#f3f0d6")
        self.intro_overlay.place(relx=0.0, rely=0.0, relwidth=1.0, relheight=1.0)

        outer = tk.Frame(self.intro_overlay, bg="#f3f0d6")
        outer.pack(fill="both", expand=True, padx=24, pady=24)

        center_panel = tk.Frame(
            outer,
            bg="#ece7c9",
            highlightthickness=1,
            highlightbackground="#d6d0b3",
        )
        center_panel.pack(fill="both", expand=True)

        instruction = tk.Label(
            center_panel,
            text=INSTRUCTION_TEXT,
            bg="#ece7c9",
            fg="#111111",
            font=("Arial", 18, "bold"),
            justify="center",
            wraplength=860,
        )
        instruction.place(relx=0.5, rely=0.5, anchor="center")

        btns = tk.Frame(outer, bg="#f3f0d6")
        btns.pack(fill="x", pady=(18, 0))

        tk.Button(
            btns,
            text="Начать тестирование",
            command=self.start_or_continue,
            bg="#42d95b",
            activebackground="#35b74a",
            fg="white",
            relief="raised",
            bd=3,
            cursor="hand2",
            font=("Arial", 14, "bold"),
            width=24,
            height=2,
        ).pack(side="left")

        tk.Button(
            btns,
            text="Выход",
            command=self.master.destroy,
            bg="#d64a4a",
            activebackground="#b93c3c",
            fg="white",
            relief="raised",
            bd=3,
            cursor="hand2",
            font=("Arial", 14, "bold"),
            width=12,
            height=2,
        ).pack(side="right")

    def start_or_continue(self) -> None:
        if self.intro_visible:
            self.intro_overlay.place_forget()
            self.intro_visible = False
        self.start_test()

    def _toggle_fullscreen(self, event: Optional[tk.Event] = None) -> str:
        self.is_fullscreen = not self.is_fullscreen
        self.master.attributes("-fullscreen", self.is_fullscreen)
        return "break"

    def _exit_fullscreen(self, event: Optional[tk.Event] = None) -> str:
        self.is_fullscreen = False
        self.master.attributes("-fullscreen", False)
        return "break"

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

    def _ensure_results_file(self) -> None:
        self.results_file.parent.mkdir(parents=True, exist_ok=True)
        if self.results_file.exists():
            return
        with self.results_file.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(
                [
                    "timestamp",
                    "task_no",
                    "L",
                    "target_difficulty",
                    "actual_difficulty",
                    "is_correct",
                    "elapsed_seconds",
                    "errors_count",
                    "correct_answer",
                    "attempt_answer",
                    "methods",
                    "rules",
                ]
            )

    def _log_result(self, is_correct: bool, attempt_answer: str, elapsed_s: float) -> None:
        methods = self.current_debug_info.get("methods", [])
        method_text = ",".join(str(m) for m in methods) if isinstance(methods, list) else ""
        rules_text = str(self.current_debug_info.get("rules_text", ""))
        with self.results_file.open("a", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(
                [
                    datetime.now().isoformat(timespec="seconds"),
                    self.task_counter,
                    self.current_l,
                    int(self.current_target_difficulty),
                    int(self.current_actual_difficulty),
                    int(bool(is_correct)),
                    f"{float(elapsed_s):.3f}",
                    int(self.current_errors),
                    self.correct_answer,
                    attempt_answer,
                    method_text,
                    rules_text,
                ]
            )

    def _shield_layout(self, count: int, width: int = CELL_WIDTH, height: int = CELL_HEIGHT) -> Tuple[Dict[str, float], List[List[Tuple[float, float]]]]:
        ref_w = 300.0
        ref_h = 380.0
        pad = 3.0
        scale = min((float(width) - 2.0 * pad) / ref_w, (float(height) - 2.0 * pad) / ref_h)
        scale = max(scale, 0.1)
        draw_w = ref_w * scale
        draw_h = ref_h * scale
        x0 = (float(width) - draw_w) / 2.0
        y0 = (float(height) - draw_h) / 2.0
        x1 = x0 + draw_w
        y1 = y0 + draw_h
        cx = (x0 + x1) / 2.0

        border = 10.0 * scale
        ix0 = x0 + border
        iy0 = y0 + border
        ix1 = x1 - border
        iy1 = y1 - border
        iw = ix1 - ix0
        ih = iy1 - iy0
        mid_x = (ix0 + ix1) / 2.0
        notch_y = iy0 + 305.0 * scale
        tip_y = iy1 - 6.0 * scale
        trim = 5.0 * scale
        body_bottom_y = notch_y - trim
        split_y = iy0 + (body_bottom_y - iy0) * 0.60
        mt = (mid_x, iy0)
        ms = (mid_x, split_y)
        tl = (ix0, iy0)
        tr = (ix1, iy0)
        bl = (ix0, body_bottom_y)
        br = (ix1, body_bottom_y)
        tip = (cx, tip_y)

        regions: List[List[Tuple[float, float]]] = []
        if count <= 2:
            regions = [
                [tl, mt, tip, bl],
                [mt, tr, br, tip],
            ]
        elif count == 3:
            regions = [
                [tl, mt, ms, (ix0, split_y)],
                [mt, tr, (ix1, split_y), ms],
                [(ix0, split_y), (ix1, split_y), br, tip, bl],
            ]
        else:
            regions = [
                [tl, mt, ms, (ix0, split_y)],
                [mt, tr, (ix1, split_y), ms],
                [(ix0, split_y), ms, tip, bl],
                [ms, (ix1, split_y), br, tip],
            ]

        geom = {
            "x0": x0, "y0": y0, "x1": x1, "y1": y1, "cx": cx,
            "ix0": ix0, "iy0": iy0, "ix1": ix1, "iy1": iy1,
            "notch_y": notch_y,
            "tip_y": tip_y,
            "trim": trim,
            "line_w": max(1.0, round(2.0 * scale, 2)),
            "select_w": max(2.0, round(4.0 * scale, 2)),
        }
        return geom, regions

    def _point_in_polygon(self, x: float, y: float, poly: List[Tuple[float, float]]) -> bool:
        inside = False
        j = len(poly) - 1
        for i in range(len(poly)):
            xi, yi = poly[i]
            xj, yj = poly[j]
            intersects = ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / max(1e-9, (yj - yi)) + xi)
            if intersects:
                inside = not inside
            j = i
        return inside

    def _draw_shield_code(self, canvas: tk.Canvas, code_values: List[Optional[str]], selected_idx: Optional[int] = None) -> List[List[Tuple[float, float]]]:
        canvas.delete("all")
        width = int(canvas.cget("width"))
        height = int(canvas.cget("height"))
        count = max(2, min(4, len(code_values)))
        geom, regions = self._shield_layout(count, width, height)

        frame_color = "#052f44"
        inner_bg = "#2d4957"
        outer = [
            (geom["x0"], geom["y0"]),
            (geom["x1"], geom["y0"]),
            (geom["x1"], geom["notch_y"]),
            (geom["cx"], geom["y1"]),
            (geom["x0"], geom["notch_y"]),
        ]
        inner = [
            (geom["ix0"], geom["iy0"]),
            (geom["ix1"], geom["iy0"]),
            (geom["ix1"], geom["notch_y"] - geom["trim"]),
            (geom["cx"], geom["tip_y"]),
            (geom["ix0"], geom["notch_y"] - geom["trim"]),
        ]
        canvas.create_polygon(outer, fill=frame_color, outline=frame_color, width=geom["line_w"])
        canvas.create_polygon(inner, fill=inner_bg, outline="", width=0)

        for idx, poly in enumerate(regions):
            value = code_values[idx] if idx < len(code_values) else None
            base = POCKET_COLORS.get(value, "#ffffff") if value else "#ffffff"
            canvas.create_polygon(poly, fill=base, outline="", width=0)
            if selected_idx is not None and idx == selected_idx:
                canvas.create_polygon(poly, fill="", outline="#ffffff", width=geom["select_w"])

        for poly in regions:
            canvas.create_polygon(poly, fill="", outline="#0a3348", width=geom["line_w"])
        canvas.create_polygon(inner, fill="", outline="#0a3348", width=geom["line_w"])
        return regions

    def _draw_code(self, canvas: tk.Canvas, code: str) -> None:
        self._draw_shield_code(canvas, [ch for ch in code], selected_idx=None)

    def _draw_correct_preview(self, code: str) -> None:
        self._draw_shield_code(self.correct_preview_canvas, [ch for ch in code], selected_idx=None)

    def _clear_correct_preview(self) -> None:
        self.correct_preview_label.config(text="")
        self.correct_preview_canvas.delete("all")

    def _draw_missing_cell(self) -> None:
        if self.missing_r < 0 or self.missing_c < 0 or not self.correct_answer:
            return
        canvas = self.cell_canvases[self.missing_r][self.missing_c]
        self._draw_shield_code(canvas, self.user_answer, selected_idx=self.selected_slot)

    def on_cell_click(self, row: int, col: int, event: tk.Event) -> None:
        if row != self.missing_r or col != self.missing_c or not self.correct_answer:
            return
        canvas = self.cell_canvases[self.missing_r][self.missing_c]
        _, regions = self._shield_layout(len(self.correct_answer), int(canvas.cget("width")), int(canvas.cget("height")))
        self.selected_slot = None
        for idx, poly in enumerate(regions):
            if self._point_in_polygon(float(event.x), float(event.y), poly):
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
        elapsed_s = max(0.0, time.monotonic() - self.current_started_at)
        if attempt == self.correct_answer:
            self._log_result(is_correct=True, attempt_answer=attempt, elapsed_s=elapsed_s)
            self.current_target_difficulty = min(20, int(self.current_target_difficulty) + random.choice([2, 3]))
            self.status_label.config(text="Верно", fg="#1e7f3f")
            self._show_popup("Верно", bg="#2eb872", fg="white", duration_ms=1200)
            self.master.after(1250, self.start_test)
        else:
            self.current_errors += 1
            self._log_result(is_correct=False, attempt_answer=attempt, elapsed_s=elapsed_s)
            text = f"Неверно. Правильно: {self.correct_answer} ({code_to_color_names(self.correct_answer)})"
            self.status_label.config(text=text, fg="#a94442")
            self.correct_preview_label.config(text="Правильный ответ:")
            self._draw_correct_preview(self.correct_answer)
            self._show_popup("Неверно. Сложность сохраняется.", bg="#f0ad4e", fg="#333333", duration_ms=2200)
            self.master.after(2250, self.start_test)

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
        complexity_info = debug_info.get("complexity_info", {})
        if isinstance(complexity_info, dict):
            lines.append("0) Сложность задачи:")
            lines.append(
                f"target={self.current_target_difficulty}; "
                f"actual={complexity_info.get('total', '?')}; "
                f"per_pocket={complexity_info.get('per_pocket', [])}; "
                f"L_bonus={complexity_info.get('elements_bonus', 0)}; "
                f"xy_mix_bonus={complexity_info.get('mix_bonus_xy', 0)}; "
                f"L4_1v3_bonus={complexity_info.get('four_pockets_single_axis_bonus', 0)}"
            )
            lines.append("")
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
        L, cells, rules, debug_info = generate_tensor(self.l_var.get(), target_difficulty=self.current_target_difficulty)
        self.current_l = L
        self.current_cells = cells
        self.task_counter += 1
        self.current_errors = 0
        self.current_started_at = time.monotonic()
        self.current_debug_info = debug_info
        self.current_debug_info["rules_text"] = " | ".join(rules)
        complexity_info = debug_info.get("complexity_info", {})
        if isinstance(complexity_info, dict):
            self.current_actual_difficulty = int(complexity_info.get("total", self.current_target_difficulty))
        else:
            self.current_actual_difficulty = int(self.current_target_difficulty)
        self.missing_r, self.missing_c = random.choice(WHITE_ALLOWED_CELLS)
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

        self.status_label.config(
            text=(
                "Выбери карман кликом и закрась его цветом из палитры. "
                f"Сложность: цель {self.current_target_difficulty}, факт {self.current_actual_difficulty}."
            ),
            fg="#1f3b73",
        )
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
