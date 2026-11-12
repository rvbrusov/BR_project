from __future__ import annotations

import math
import random
import time
import tkinter as tk


APP_TITLE = "Ориентация — тестовый круг"
SKY = "#c9e6f8"
GROUND = "#ead8c9"
RED = "#ed1717"
BLACK = "#090909"
# Cyrillic names used by all three versions.  For intermediate rhumbs the
# pole direction (north/south) is written first: СВВ, ЮВВ, ЮЗЗ, СЗЗ.
COURSES = (
    "\u0421", "\u0421\u0421\u0412", "\u0421\u0412", "\u0421\u0412\u0412",
    "\u0412", "\u042e\u0412\u0412", "\u042e\u0412", "\u042e\u042e\u0412",
    "\u042e", "\u042e\u042e\u0417", "\u042e\u0417", "\u042e\u0417\u0417",
    "\u0417", "\u0421\u0417\u0417", "\u0421\u0417", "\u0421\u0421\u0417",
)
PITCHES = (-67, -45, -22, 0, 22, 45, 67)
ROLLS = (-167, -135, -112, -90, -67, -45, -22, 0, 22, 45, 67, 90, 112, 135, 167, 180)


def rotated_course(position_index: int, compass_rotation_index: int) -> str:
    """Return the true course at a physical scale position after rotation.

    A positive rotation moves north clockwise around the 16-position scale.
    """
    return COURSES[(position_index - compass_rotation_index) % len(COURSES)]


def rhumb_angle(value: int | float) -> float:
    """Return the exact 22.5-degree angle represented by a rounded label."""
    return round(value / 22.5) * 22.5


def polar(cx: float, cy: float, radius: float, degrees: float) -> tuple[float, float]:
    angle = math.radians(degrees - 90)
    return cx + radius * math.cos(angle), cy + radius * math.sin(angle)


class _OrientationTestLegacy:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(APP_TITLE)
        self.root.configure(bg="white")
        self.root.minsize(620, 620)
        self.root.geometry("850x850")
        self.root.bind("<Escape>", lambda _event: self.root.destroy())

        self.canvas = tk.Canvas(root, bg="white", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Button-1>", self.new_task)
        self.canvas.bind("<Configure>", self.redraw)

        self.pitch = 0
        self.roll = 0
        self.course_index = 0
        self.direction_index = 3
        self.new_task()

    def maximize(self) -> None:
        try:
            self.root.state("zoomed")
        except tk.TclError:
            self.root.geometry(f"{self.root.winfo_screenwidth()}x{self.root.winfo_screenheight()}+0+0")

    def build_test_ui(self) -> None:
        bg = "#f6f0d8"
        content = tk.Frame(self.root, bg=bg)
        content.pack(expand=True, pady=(8, 4))
        self.time_bar_canvas = tk.Canvas(self.root, width=96, height=320, bg=bg, highlightthickness=0)
        self.time_bar_canvas.place(x=24, y=24)
        self.canvas = tk.Canvas(content, width=530, height=470, bg="white", highlightthickness=0)
        self.canvas.pack()
        self.canvas.bind("<Configure>", self.redraw)

        box = tk.Frame(content, bg=bg)
        box.pack(pady=(20, 0))
        tk.Label(box, text="\u041a\u0423\u0420\u0421", bg="#f3dc83", font=("Arial", 18, "bold"),
                 relief="solid", bd=2).pack(fill="x")
        self.answer_label = tk.Label(box, text="", bg="#ffd900", font=("Arial", 18, "bold"),
                                     relief="solid", bd=2)
        self.answer_label.pack(fill="x", pady=(3, 7))
        letters = tk.Frame(box, bg=bg)
        letters.pack()
        self.letter_buttons: list[tk.Button] = []
        for index, letter in enumerate(("\u0421", "\u042e", "\u0412", "\u0417")):
            button = tk.Button(letters, text=letter, command=lambda value=letter: self.select_letter(value),
                               bg="white", activebackground="#ffd900", font=("Arial", 16, "bold"),
                               width=3, bd=2, cursor="hand2")
            button.grid(row=index // 2, column=index % 2, padx=3, pady=3)
            self.letter_buttons.append(button)

        footer = tk.Frame(self.root, bg=bg)
        footer.pack(side="bottom", fill="x", padx=28, pady=(4, 16))
        for column in range(3):
            footer.grid_columnconfigure(column, weight=1)
        common = dict(font=("Arial", 18, "bold"), width=12, padx=10, pady=6,
                      bd=3, relief="raised", cursor="hand2")
        self.cancel_button = tk.Button(footer, text="\u041e\u0442\u043c\u0435\u043d\u0430", command=self.cancel_answer,
                                       bg="#f2d64b", activebackground="#e3c12d", **common)
        self.cancel_button.grid(row=0, column=0, sticky="w")
        self.next_button = tk.Button(footer, text="\u0414\u0430\u043b\u0435\u0435", command=self.next_task,
                                     bg="#58cc63", activebackground="#43b84f", **common)
        self.next_button.grid(row=0, column=1)
        self.exit_button = tk.Button(footer, text="\u0412\u044b\u0445\u043e\u0434", command=self.exit_app,
                                     bg="#d95a5a", activebackground="#b93c3c", fg="white", **common)
        self.exit_button.grid(row=0, column=2, sticky="e")

    def new_task(self, _event: tk.Event | None = None) -> None:
        previous = (self.pitch, self.roll, self.course_index, self.direction_index)
        while (self.pitch, self.roll, self.course_index, self.direction_index) == previous:
            self.pitch = random.choice(PITCHES)
            self.roll = random.choice(ROLLS)
            self.course_index = random.randrange(len(COURSES))
            allowed_directions = [
                index
                for index in range(len(COURSES))
                if min(
                    (index - self.course_index) % len(COURSES),
                    (self.course_index - index) % len(COURSES),
                )
                >= 3
                and (index - self.course_index) % len(COURSES)
                != len(COURSES) // 2
            ]
            self.direction_index = random.choice(allowed_directions)
        self.draw()

    def redraw(self, _event: tk.Event | None = None) -> None:
        self.draw()

    def draw(self) -> None:
        self.canvas.delete("all")
        width = max(1, self.canvas.winfo_width())
        height = max(1, self.canvas.winfo_height())
        # Leave room for the course arrow and labels outside the dial.
        size = min(width, height) * 0.72
        radius = size / 2
        cx, cy = width / 2, height / 2
        scale = size / 620

        self.draw_face(cx, cy, radius, scale)
        self.draw_course_scale(cx, cy, radius, scale)
        self.draw_roll_scale(cx, cy, radius, scale)
        self.draw_pitch_scale(cx, cy, radius, scale)
        self.draw_airplane(cx, cy, scale, self.roll)

    def draw_face(self, cx: float, cy: float, r: float, s: float) -> None:
        inner = r - 29 * s
        self.canvas.create_oval(cx - inner, cy - inner, cx + inner, cy + inner, fill=SKY, outline="")

        # The horizon moves with pitch and tilts with roll.
        offset = max(-inner * 0.72, min(inner * 0.72, self.pitch / 90 * inner * 0.62))
        # Fill the circular segment on the "ground" side of one straight chord.
        # Building the arc around the downward normal avoids an extra closing edge.
        angle = math.radians(self.roll)
        down_angle = angle + math.pi / 2
        half_arc = math.acos(offset / inner)
        ground_points: list[float] = []
        steps = 120
        for step in range(steps + 1):
            a = down_angle - half_arc + 2 * half_arc * step / steps
            ground_points.extend((cx + inner * math.cos(a), cy + inner * math.sin(a)))
        self.canvas.create_polygon(*ground_points, fill=GROUND, outline="")

    def draw_course_scale(self, cx: float, cy: float, r: float, s: float) -> None:
        self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r, outline="#666666", width=max(1, 1.5 * s))
        inner_edge = r - 28 * s
        self.canvas.create_oval(
            cx - inner_edge,
            cy - inner_edge,
            cx + inner_edge,
            cy + inner_edge,
            outline="white",
            width=max(2, 3 * s),
        )
        # Two marks per rhumb; every second mark is an exact 16-rhumb direction.
        for index in range(32):
            degree = index * 11.25
            length = (24 if index % 2 == 0 else 12) * s
            x1, y1 = polar(cx, cy, r - 2 * s, degree)
            x2, y2 = polar(cx, cy, r - length, degree)
            self.canvas.create_line(x1, y1, x2, y2, fill=BLACK, width=max(2, 3 * s))

        course_angle = self.course_index * 22.5
        # The triangle starts at the exact scale mark and points away from the dial.
        tip = polar(cx, cy, r + 27 * s, course_angle)
        left = polar(cx, cy, r + 3 * s, course_angle - 3.6)
        right = polar(cx, cy, r + 3 * s, course_angle + 3.6)
        self.canvas.create_polygon(*tip, *left, *right, fill=RED, outline=RED)

        direction_angle = self.direction_index * 22.5
        # The first/last letter begins at the outer end of its exact rhumb mark.
        label_x, label_y = polar(cx, cy, r + 20 * s, direction_angle)
        horizontal_direction = math.sin(math.radians(direction_angle))
        if horizontal_direction > 0.1:
            # On the right, the first letter lies on the radial direction.
            label_anchor = "w"
        elif horizontal_direction < -0.1:
            # On the left, the last letter lies on the radial direction.
            label_anchor = "e"
        else:
            label_anchor = "center"
        self.canvas.create_text(
            label_x,
            label_y,
            text=COURSES[self.direction_index],
            fill=RED,
            font=("Arial", max(8, round(16 * s)), "bold"),
            anchor=label_anchor,
        )

    def draw_roll_scale(self, cx: float, cy: float, r: float, s: float) -> None:
        scale_r = r - 52 * s
        font = ("Arial", max(10, round(20 * s)))
        for degree in range(0, 360, 5):
            length = (15 if degree % 22.5 == 0 else 8) * s
            x1, y1 = polar(cx, cy, scale_r, degree)
            x2, y2 = polar(cx, cy, scale_r - length, degree)
            self.canvas.create_line(x1, y1, x2, y2, fill="#56616a", width=max(1, 1.5 * s))

        for degree, label in zip(range(0, 360, 45), ("0", "45", "90", "135", "180", "135", "90", "45")):
            x, y = polar(cx, cy, scale_r - 42 * s, degree)
            self.canvas.create_text(x, y, text=label, fill=BLACK, font=font)

    def draw_pitch_scale(self, cx: float, cy: float, _r: float, s: float) -> None:
        font = ("Arial", max(10, round(19 * s)))
        spacing = 43 * s
        for value in PITCHES:
            y = cy - value / 22.5 * spacing
            half = (31 if value in (-90, -45, 0, 45, 90) else 18) * s
            line_width = max(1, round(1.5 * s))
            for x1, x2 in (
                (cx - half - 28 * s, cx - 28 * s),
                (cx + 28 * s, cx + half + 28 * s),
            ):
                self.canvas.create_line(x1, y, x2, y, fill=BLACK, width=line_width + 2)
                self.canvas.create_line(x1, y, x2, y, fill="white", width=line_width)
            if value != 0:
                label = str(abs(value))
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    self.canvas.create_text(cx + dx, y + dy, text=label, fill=BLACK, font=font)
                self.canvas.create_text(cx, y, text=label, fill="white", font=font)

    def draw_airplane(self, cx: float, cy: float, s: float, roll: float) -> None:
        # Geometry copied from the old orientation program; every part remains vector-based.
        airplane_scale = 1.30 * s
        center = (110.0, 82.0)
        angle = math.radians(roll)

        def point(x: float, y: float) -> tuple[float, float]:
            dx = (x - center[0]) * airplane_scale
            dy = (y - center[1]) * airplane_scale
            return (
                cx + dx * math.cos(angle) - dy * math.sin(angle),
                cy + dx * math.sin(angle) + dy * math.cos(angle),
            )

        def line(points: list[tuple[float, float]], width: float) -> None:
            coords: list[float] = []
            for x, y in points:
                coords.extend(point(x, y))
            self.canvas.create_line(
                *coords,
                fill=BLACK,
                width=max(2, width * airplane_scale),
                capstyle=tk.ROUND,
                joinstyle=tk.ROUND,
            )

        body: list[float] = []
        circle_points = [
            (110 + 23 * math.cos(math.tau * index / 48), 82 + 21 * math.sin(math.tau * index / 48))
            for index in range(49)
        ]
        for x, y in circle_points:
            body.extend(point(x, y))
        self.canvas.create_polygon(*body, fill="#dff1fb", outline="")
        line([(4, 76.5), (91, 84.1)], 7)
        line([(129, 84.1), (216, 76.5)], 7)
        line([(70, 72), (150, 72)], 6)
        line([(110, 38), (110, 78)], 7)
        line([(62, 81.6), (62, 108)], 5)
        line([(158, 81.6), (158, 108)], 5)
        line(circle_points, 6)


class OrientationTest(_OrientationTestLegacy):
    """Version 1: v2 appearance with a fixed level horizon and airplane."""

    def __init__(self, root: tk.Tk) -> None:
        if type(self) is not OrientationTest:
            super().__init__(root)
            return
        self.root = root
        self.root.configure(bg="#f6f0d8")
        self.root.minsize(900, 720)
        self.root.bind("<Escape>", lambda _event: self.exit_app())
        self.root.protocol("WM_DELETE_WINDOW", self.exit_app)
        self.pitch = self.roll = self.course_index = 0
        self.compass_rotation_index = 0
        self.direction_index = 3
        self.task_number = 0
        self.results: list[dict[str, object]] = []
        self.selected_answer = ""
        self.answer_locked = False
        self.test_complete = False
        self.test_started_at = time.perf_counter()
        self.elapsed_seconds = 0.0
        self.timer_after_id: str | None = None
        self.results_panel: tk.Frame | None = None
        self.complete_dialog: tk.Toplevel | None = None
        self.invalid_answer_dialog: tk.Toplevel | None = None
        self.build_test_ui()
        self.maximize()
        self.new_task()
        self.update_timer()
        self.root.after_idle(lambda: self.root.title(
            "\u041e\u0440\u0438\u0435\u043d\u0442\u0430\u0446\u0438\u044f \u2014 \u0442\u0435\u0441\u0442\u043e\u0432\u044b\u0439 \u043a\u0440\u0443\u0433 v1"
        ))
        self.root.title("Ориентация — тестовый круг v1")

    def new_task(self, _event: tk.Event | None = None) -> None:
        self.pitch = 0
        self.roll = 0
        previous = (
            getattr(self, "course_index", 0),
            getattr(self, "direction_index", 3),
            getattr(self, "compass_rotation_index", 0),
        )
        while True:
            self.course_index = random.randrange(len(COURSES))
            allowed_directions = [
                index
                for index in range(len(COURSES))
                if min(
                    (index - self.course_index) % len(COURSES),
                    (self.course_index - index) % len(COURSES),
                )
                >= 3
                and (index - self.course_index) % len(COURSES)
                != len(COURSES) // 2
            ]
            self.direction_index = random.choice(allowed_directions)
            # Zero is excluded: every task must use a genuinely rotated compass.
            self.compass_rotation_index = random.randrange(1, len(COURSES))
            if (self.course_index, self.direction_index, self.compass_rotation_index) != previous:
                break
        self.task_number += 1
        self.reset_answer()
        self.draw()

    def select_letter(self, letter: str) -> None:
        if self.test_complete or self.answer_locked:
            return
        self.selected_answer += letter
        self.answer_label.configure(text=self.selected_answer)
        if len(self.selected_answer) >= 3:
            if self.selected_answer in COURSES:
                self.answer_locked = True
                self.set_letter_buttons_state(tk.DISABLED)
            else:
                self.show_invalid_answer()

    def set_letter_buttons_state(self, state: str) -> None:
        for button in self.letter_buttons:
            button.configure(state=state)

    def reset_answer(self) -> None:
        self.selected_answer = ""
        self.answer_locked = False
        if hasattr(self, "answer_label"):
            self.answer_label.configure(text="")
            self.set_letter_buttons_state(tk.NORMAL)

    def cancel_answer(self) -> None:
        if not self.test_complete:
            self.reset_answer()

    def record_answer(self) -> None:
        if any(row["task"] == self.task_number for row in self.results):
            return
        correct = rotated_course(self.course_index, self.compass_rotation_index)
        self.results.append({"task": self.task_number, "answer": self.selected_answer or "\u2014",
                             "correct": correct, "is_correct": self.selected_answer == correct})

    def next_task(self) -> None:
        if self.test_complete:
            self.exit_app()
            return
        if self.selected_answer and self.selected_answer not in COURSES:
            self.show_invalid_answer()
            return
        self.record_answer()
        if self.task_number >= 5:
            self.finish_test()
        else:
            self.new_task()

    def update_timer(self) -> None:
        self.timer_after_id = None
        if self.test_complete:
            return
        elapsed = max(0.0, time.perf_counter() - self.test_started_at)
        self.draw_time_bar(min(1.0, elapsed / 120.0))
        if elapsed >= 120.0:
            self.record_answer()
            self.finish_test()
        else:
            self.timer_after_id = self.root.after(100, self.update_timer)

    def show_invalid_answer(self) -> None:
        self.reset_answer()
        if self.invalid_answer_dialog is not None:
            try:
                self.invalid_answer_dialog.destroy()
            except tk.TclError:
                pass
        dialog = tk.Toplevel(self.root)
        self.invalid_answer_dialog = dialog
        dialog.withdraw()
        dialog.overrideredirect(True)
        dialog.transient(self.root)
        dialog.configure(bg="#c62828")
        tk.Label(
            dialog,
            text="\u043d\u0435\u0434\u043e\u043f\u0443\u0441\u0442\u0438\u043c\u044b\u0439 \u043a\u0443\u0440\u0441",
            bg="#fff4f4",
            fg="#9b111e",
            font=("Arial", 18, "bold"),
            padx=24,
            pady=14,
        ).pack(padx=2, pady=2)
        dialog.update_idletasks()
        width, height = dialog.winfo_reqwidth(), dialog.winfo_reqheight()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - width) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - height) // 2
        dialog.geometry(f"{width}x{height}+{x}+{y}")
        dialog.deiconify()
        dialog.lift()
        dialog.after(2000, lambda current=dialog: self.close_invalid_answer(current))

    def close_invalid_answer(self, dialog: tk.Toplevel) -> None:
        try:
            dialog.destroy()
        except tk.TclError:
            pass
        if self.invalid_answer_dialog is dialog:
            self.invalid_answer_dialog = None

    def draw_time_bar(self, ratio: float) -> None:
        canvas = self.time_bar_canvas
        canvas.delete("all")
        canvas.create_text(48, 18, text="\u0412\u0420\u0415\u041c\u042f", fill="#102744", font=("Arial", 10, "bold"))
        canvas.create_rectangle(19, 34, 77, 308, outline="#233142", fill="#e6ecf4", width=3)
        fill_height = 266 * max(0.0, min(1.0, ratio))
        if fill_height:
            canvas.create_rectangle(23, 304 - fill_height, 73, 304, outline="", fill="#3c82ff")

    def finish_test(self) -> None:
        if self.test_complete:
            return
        self.test_complete = True
        self.elapsed_seconds = max(0.0, time.perf_counter() - self.test_started_at)
        if self.timer_after_id is not None:
            try:
                self.root.after_cancel(self.timer_after_id)
            except tk.TclError:
                pass
            self.timer_after_id = None
        self.set_letter_buttons_state(tk.DISABLED)
        self.cancel_button.configure(state=tk.DISABLED)
        self.next_button.configure(state=tk.NORMAL)
        self.show_results_table()
        self.show_complete_dialog()

    def show_results_table(self) -> None:
        panel = tk.Frame(self.root, bg="white", highlightbackground="#1976a3", highlightthickness=2)
        self.results_panel = panel
        tk.Label(panel, text="\u0422\u0430\u0431\u043b\u0438\u0446\u0430 \u043e\u0442\u0432\u0435\u0442\u043e\u0432", bg="white", fg="#102744",
                 font=("Arial", 15, "bold"), pady=8).pack(fill="x")
        correct_count = sum(bool(row["is_correct"]) for row in self.results)
        tk.Label(panel, text=f"\u041f\u0440\u0430\u0432\u0438\u043b\u044c\u043d\u044b\u0445: {correct_count}    \u041d\u0435\u043f\u0440\u0430\u0432\u0438\u043b\u044c\u043d\u044b\u0445: {len(self.results) - correct_count}",
                 bg="white", fg="#102744", font=("Arial", 11, "bold"), pady=4).pack(fill="x")
        table = tk.Frame(panel, bg="#233142")
        table.pack(padx=10, pady=(4, 10))
        headers = ("\u2116", "\u041e\u0442\u0432\u0435\u0442", "\u041f\u0440\u0430\u0432\u0438\u043b\u044c\u043d\u043e", "\u0418\u0442\u043e\u0433")
        widths = (3, 8, 10, 10)
        for column, (header, width) in enumerate(zip(headers, widths)):
            tk.Label(table, text=header, width=width, bg="#dce8f4", fg="#102744",
                     font=("Arial", 11, "bold"), bd=1, relief="solid", pady=5).grid(row=0, column=column)
        for row_index, row in enumerate(self.results, start=1):
            verdict = "\u0412\u0435\u0440\u043d\u043e" if row["is_correct"] else "\u041d\u0435\u0432\u0435\u0440\u043d\u043e"
            values = (row["task"], row["answer"], row["correct"], verdict)
            for column, (value, width) in enumerate(zip(values, widths)):
                verdict_bg = "#d7f0d8" if row["is_correct"] else "#f6d4d4"
                tk.Label(table, text=str(value), width=width,
                         bg=verdict_bg if column == 3 else "white", fg="#102744",
                         font=("Arial", 11), bd=1, relief="solid", pady=5).grid(row=row_index, column=column)
        seconds = int(self.elapsed_seconds)
        tk.Label(panel, text=f"\u0417\u0430\u0442\u0440\u0430\u0447\u0435\u043d\u043e \u0432\u0440\u0435\u043c\u0435\u043d\u0438: {seconds // 60:02d}:{seconds % 60:02d}",
                 bg="white", fg="#102744", font=("Arial", 11, "bold"), pady=8).pack(fill="x")
        self.root.update_idletasks()
        panel.place(x=140, rely=0.5, anchor="w")
        panel.lift()

    def show_complete_dialog(self) -> None:
        dialog = tk.Toplevel(self.root)
        self.complete_dialog = dialog
        dialog.withdraw()
        dialog.overrideredirect(True)
        dialog.transient(self.root)
        dialog.configure(bg="#1976a3")
        panel = tk.Frame(dialog, bg="white")
        panel.pack(fill="both", expand=True, padx=2, pady=2)
        tk.Label(panel, text=("\u041f\u0435\u0440\u0432\u044b\u0439 \u044d\u0442\u0430\u043f \u0442\u0435\u0441\u0442\u0430 \u0437\u0430\u0432\u0435\u0440\u0448\u0451\u043d, "
                              "\u0434\u043b\u044f \u043f\u0435\u0440\u0435\u0445\u043e\u0434\u0430 \u043a \u0441\u043b\u0435\u0434\u0443\u044e\u0449\u0435\u043c\u0443 \u044d\u0442\u0430\u043f\u0443 "
                              "\u043d\u0430\u0436\u043c\u0438\u0442\u0435 \"\u0414\u0430\u043b\u0435\u0435\""), bg="white", fg="#0c254a",
                 font=("Times New Roman", 22, "bold"), wraplength=360,
                 padx=24, pady=22).pack()
        dialog.update_idletasks()
        width, height = dialog.winfo_reqwidth(), dialog.winfo_reqheight()
        x = self.root.winfo_rootx() + self.root.winfo_width() - width - 32
        y = self.root.winfo_rooty() + (self.root.winfo_height() - height) // 2
        dialog.geometry(f"{width}x{height}+{x}+{y}")
        dialog.deiconify()
        dialog.lift()

    def exit_app(self) -> None:
        if self.timer_after_id is not None:
            try:
                self.root.after_cancel(self.timer_after_id)
            except tk.TclError:
                pass
        self.root.destroy()

    def draw(self) -> None:
        self.canvas.delete("all")
        width = max(1, self.canvas.winfo_width())
        height = max(1, self.canvas.winfo_height())

        # This is the largest safe size for the 530x470 white field: the course
        # arrow and three-letter direction labels retain a small edge margin.
        size = min(width, height) * 0.84
        radius = size / 2
        cx, cy = width / 2, height / 2
        scale = size / 620

        self.draw_face(cx, cy, radius, scale)
        self.draw_course_scale(cx, cy, radius, scale)
        self.draw_roll_scale(cx, cy, radius, scale)
        self.draw_pitch_scale(cx, cy, radius, scale)
        self.draw_airplane(cx, cy, scale, self.roll)

    def draw_face(self, cx: float, cy: float, r: float, s: float) -> None:
        from orient_new_v2 import OrientationTestV2

        OrientationTestV2.draw_face(self, cx, cy, r, s)

    def draw_course_scale(self, cx: float, cy: float, r: float, s: float) -> None:
        from orient_new_v2 import OrientationTestV2

        OrientationTestV2.draw_course_scale(self, cx, cy, r, s)

    @staticmethod
    def scale_number_font(scale: float) -> tuple[str, int]:
        """Return the compact font used by the 10-degree roll scale."""
        return ("Arial", max(7, round(14 * scale)))

    @staticmethod
    def pitch_number_font(_value: int, scale: float) -> tuple[str, int]:
        """Return the font used by the major sinusoidal pitch labels."""
        return ("Arial", max(8, round(18 * scale)))

    def draw_roll_scale(self, cx: float, cy: float, r: float, s: float) -> None:
        circle_radius = r - 29 * s
        label_radius = circle_radius - 24 * s
        font = self.scale_number_font(s)

        # A short internal tick and a degree label for every 10 degrees.  The
        # 0/180 labels are omitted where the vertical pitch scale meets the rim.
        for degree in range(0, 360, 10):
            tick_length = (11 if degree % 30 == 0 else 7) * s
            x1, y1 = polar(cx, cy, circle_radius - 2 * s, degree)
            x2, y2 = polar(cx, cy, circle_radius - 2 * s - tick_length, degree)
            self.canvas.create_line(
                x1, y1, x2, y2,
                fill=BLACK,
                width=max(1, round(1.4 * s)),
            )

            if degree in (0, 180):
                continue
            value = degree if degree < 180 else 360 - degree
            if value in (10, 170):
                continue
            x, y = polar(cx, cy, label_radius, degree)
            self.canvas.create_text(x, y, text=str(value), fill=BLACK, font=font)

    def draw_pitch_scale(self, cx: float, cy: float, r: float, s: float) -> None:
        circle_radius = r - 29 * s
        font = self.pitch_number_font(0, s)
        text_gap = 29 * s

        # Exact sinusoidal tick positions at 10-degree intervals.  Labels are
        # shown through 60 degrees; the compressed 70/80 area uses longer
        # inward ticks instead of overlapping numerals.
        labelled_values = {0, 10, 20, 30, 40, 50, 60, 90}
        for value in range(-90, 91, 10):
            y = cy - circle_radius * math.sin(math.radians(value))
            major = value % 30 == 0
            half_line = (24 if major else 12) * s
            inner_gap = text_gap
            if abs(value) in (70, 80):
                inner_gap = 12 * s
            line_width = max(1, round(1.5 * s))
            for x1, x2 in (
                (cx - text_gap - half_line, cx - inner_gap),
                (cx + inner_gap, cx + text_gap + half_line),
            ):
                self.canvas.create_line(x1, y, x2, y, fill=BLACK, width=line_width + 2)
                self.canvas.create_line(x1, y, x2, y, fill="white", width=line_width)
            if value != 0 and abs(value) in labelled_values:
                label = str(abs(value))
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    self.canvas.create_text(cx + dx, y + dy, text=label, fill=BLACK, font=font)
                self.canvas.create_text(cx, y, text=label, fill="white", font=font)

    def draw_airplane(self, cx: float, cy: float, s: float, _roll: float) -> None:
        from orient_new_v2 import OrientationTestV2

        OrientationTestV2.draw_airplane(self, cx, cy, s, 0)


def main() -> None:
    root = tk.Tk()
    OrientationTest(root)
    root.mainloop()


if __name__ == "__main__":
    main()
