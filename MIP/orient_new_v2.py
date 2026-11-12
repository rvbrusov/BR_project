from __future__ import annotations

import math
import random
import time
import tkinter as tk

from orient_new_v1 import (
    BLACK, COURSES, GROUND, PITCHES, RED, ROLLS, SKY,
    OrientationTest, polar, rhumb_angle, rotated_course,
)


APP_TITLE = "Ориентация — тестовый круг v2"
SKY_V2 = "#91dff3"
GROUND_V2 = "#e4c1ac"
HORIZON_V2 = "#087aa3"
V2_PITCHES = tuple(value for value in PITCHES if value != 0)


class OrientationTestV2(OrientationTest):
    ANSWER_STAGE = 2

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.configure(bg="#f6f0d8")
        self.root.minsize(900, 720)
        self.root.bind("<Escape>", lambda _event: self.exit_app())
        self.root.protocol("WM_DELETE_WINDOW", self.exit_app)
        self.pitch = self.roll = self.course_index = 0
        self.compass_rotation_index = 0
        self.direction_index = 3
        self.task_number = 0
        self.answer_stage = self.ANSWER_STAGE
        self.answers_enabled = self.answer_stage >= 2
        self.results: list[dict[str, object]] = []
        self.course_answer = ""
        self.course_locked = False
        self.pitch_sign = ""
        self.pitch_digits = ""
        self.roll_direction = ""
        self.roll_digits = ""
        self.active_numeric_field = "pitch"
        self.invalid_dialog: tk.Toplevel | None = None
        self.test_complete = False
        self.test_started_at = time.perf_counter()
        self.elapsed_seconds = 0.0
        self.timer_after_id: str | None = None
        self.complete_dialog: tk.Toplevel | None = None
        self.build_test_ui()
        self.maximize()
        self.new_task()
        self.update_timer()
        self.root.title(APP_TITLE)

    def maximize(self) -> None:
        try:
            self.root.state("zoomed")
        except tk.TclError:
            self.root.geometry(f"{self.root.winfo_screenwidth()}x{self.root.winfo_screenheight()}+0+0")

    def build_test_ui(self) -> None:
        bg = "#f6f0d8"
        content = tk.Frame(self.root, bg=bg)
        content.pack(expand=True, pady=(8, 4))
        self.time_bar_canvas = tk.Canvas(
            self.root, width=96, height=320, bg=bg, highlightthickness=0
        )
        self.time_bar_canvas.place(x=24, y=24)
        self.canvas = tk.Canvas(
            content, width=530, height=470,
            bg="white", highlightthickness=0
        )
        self.canvas.pack()
        self.canvas.bind("<Configure>", self.redraw)
        if self.answers_enabled:
            self.build_answer_ui(content, bg)

        footer = tk.Frame(self.root, bg=bg)
        footer.pack(side="bottom", fill="x", padx=28, pady=(4, 16))
        for column in range(3):
            footer.grid_columnconfigure(column, weight=1)
        common = dict(
            font=("Arial", 18, "bold"), width=12, padx=10, pady=6,
            bd=3, relief="raised", cursor="hand2",
        )
        self.cancel_button = tk.Button(
            footer, text="\u041e\u0442\u043c\u0435\u043d\u0430",
            command=self.reset_answers,
            state=tk.NORMAL if self.answers_enabled else tk.DISABLED,
            bg="#f2d64b", activebackground="#e3c12d", **common,
        )
        self.cancel_button.grid(row=0, column=0, sticky="w")
        self.next_button = tk.Button(
            footer, text="\u0414\u0430\u043b\u0435\u0435", command=self.next_task,
            bg="#58cc63", activebackground="#43b84f", **common,
        )
        self.next_button.grid(row=0, column=1)
        self.exit_button = tk.Button(
            footer, text="\u0412\u044b\u0445\u043e\u0434", command=self.exit_app,
            bg="#d95a5a", activebackground="#b93c3c", fg="white", **common,
        )
        self.exit_button.grid(row=0, column=2, sticky="e")

    def build_answer_ui(self, parent: tk.Widget, bg: str) -> None:
        area = tk.Frame(parent, bg=bg)
        area.pack(pady=(6, 0))
        sections = tk.Frame(area, bg=bg)
        sections.pack()
        self.answer_sections = sections

        course_box = tk.Frame(sections, bg=bg)
        course_box.grid(row=0, column=0, padx=(0, 28), sticky="n")
        tk.Label(course_box, text="\u041a\u0423\u0420\u0421", bg="#f3dc83",
                 font=("Arial", 18, "bold"), relief="solid", bd=2).pack(fill="x")
        self.course_answer_label = tk.Label(
            course_box, text="", bg="#ffd900", font=("Arial", 18, "bold"),
            relief="solid", bd=2,
        )
        self.course_answer_label.pack(fill="x", pady=(3, 5))
        course_keys = tk.Frame(course_box, bg=bg)
        course_keys.pack()
        self.course_letter_buttons: list[tk.Button] = []
        for index, letter in enumerate(("\u0421", "\u042e", "\u0412", "\u0417")):
            button = tk.Button(
                course_keys, text=letter,
                command=lambda value=letter: self.select_course_letter(value),
                bg="white", activebackground="#ffd900", font=("Arial", 16, "bold"),
                width=3, bd=2, cursor="hand2",
            )
            button.grid(row=index // 2, column=index % 2, padx=2, pady=2, sticky="nsew")
            self.course_letter_buttons.append(button)

        pitch_box = tk.Frame(sections, bg=bg)
        pitch_box.grid(row=0, column=1, sticky="n")
        self.pitch_title_label = tk.Label(
            pitch_box, text="\u0422\u0410\u041d\u0413\u0410\u0416", bg="#f3dc83",
            font=("Arial", 18, "bold"), relief="solid", bd=2,
        )
        self.pitch_title_label.pack(fill="x")
        self.pitch_input_frame = tk.Frame(pitch_box, bg="#ffd900")
        self.pitch_input_frame.pack(fill="x", pady=(3, 5))
        self.pitch_input_frame.grid_columnconfigure(0, weight=0)
        self.pitch_input_frame.grid_columnconfigure(1, weight=1)
        self.pitch_sign_label = tk.Label(
            self.pitch_input_frame, text="", bg="#ffd900", font=("Arial", 18, "bold"),
            width=3, relief="solid", bd=2,
        )
        self.pitch_sign_label.grid(row=0, column=0, sticky="nsew")
        self.pitch_digits_label = tk.Label(
            self.pitch_input_frame, text="", bg="#ffd900", font=("Arial", 18, "bold"),
            relief="solid", bd=2,
        )
        self.pitch_digits_label.grid(row=0, column=1, sticky="nsew")
        self.pitch_sign_buttons: list[tk.Button] = []
        for sign, caption in (("+", "+  \u043a\u0430\u0431\u0440\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u0435"),
                              ("-", "-  \u043f\u0438\u043a\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u0435")):
            button = tk.Button(
                pitch_box, text=caption,
                command=lambda value=sign: self.select_pitch_sign(value),
                bg="white", activebackground="#ffd900", font=("Arial", 16, "bold"),
                bd=2, cursor="hand2",
            )
            button.pack(fill="x", pady=2)
            self.pitch_sign_buttons.append(button)

        self.roll_direction_buttons: list[tk.Button] = []
        if self.answer_stage >= 3:
            roll_box = tk.Frame(sections, bg=bg)
            roll_box.grid(row=0, column=2, padx=(28, 0), sticky="n")
            self.roll_title_label = tk.Label(
                roll_box, text="\u041a\u0420\u0415\u041d", bg="#f3dc83",
                font=("Arial", 18, "bold"), relief="solid", bd=2,
            )
            self.roll_title_label.pack(fill="x")
            self.roll_input_frame = tk.Frame(roll_box, bg="#ffd900")
            self.roll_input_frame.pack(fill="x", pady=(3, 5))
            self.roll_input_frame.grid_columnconfigure(0, weight=0)
            self.roll_input_frame.grid_columnconfigure(1, weight=1)
            self.roll_direction_label = tk.Label(
                self.roll_input_frame, text="", bg="#ffd900",
                font=("Arial", 18, "bold"), width=3, relief="solid", bd=2,
            )
            self.roll_direction_label.grid(row=0, column=0, sticky="nsew")
            self.roll_digits_label = tk.Label(
                self.roll_input_frame, text="", bg="#ffd900",
                font=("Arial", 18, "bold"), width=5, relief="solid", bd=2,
            )
            self.roll_digits_label.grid(row=0, column=1, sticky="nsew")
            for direction, caption in (("\u041b", "\u043b\u0435\u0432\u044b\u0439"),
                                       ("\u041f", "\u043f\u0440\u0430\u0432\u044b\u0439")):
                button = tk.Button(
                    roll_box, text=caption,
                    command=lambda value=direction: self.select_roll_direction(value),
                    bg="white", activebackground="#ffd900",
                    font=("Arial", 16, "bold"), bd=2, cursor="hand2",
                )
                button.pack(fill="x", pady=2)
                self.roll_direction_buttons.append(button)

        digits = tk.Frame(area, bg=bg)
        digits.pack(pady=(6, 0))
        self.numeric_keypad = digits
        self.pitch_digit_buttons: list[tk.Button] = []
        for digit in "0123456789":
            button = tk.Button(
                digits, text=digit,
                command=lambda value=digit: self.select_numeric_digit(value),
                bg="white", activebackground="#ffd900", font=("Arial", 16, "bold"),
                width=3, bd=2, cursor="hand2",
            )
            button.pack(side="left", padx=2)
            self.pitch_digit_buttons.append(button)
        if self.answer_stage == 2:
            self.root.update_idletasks()
            sections.configure(
                width=digits.winfo_reqwidth(),
                height=sections.winfo_reqheight(),
            )
            sections.grid_propagate(False)
            sections.grid_columnconfigure(0, weight=1)
            sections.grid_columnconfigure(1, weight=1)
            course_box.grid_configure(sticky="nw", padx=0)
            pitch_box.grid_configure(sticky="ne")
        elif self.answer_stage >= 3:
            self.root.update_idletasks()
            extra_width = max(0, digits.winfo_reqwidth() - sections.winfo_reqwidth())
            sections.grid_columnconfigure(1, pad=extra_width)

    def new_task(self, _event: tk.Event | None = None) -> None:
        previous = (
            self.pitch, self.roll, self.course_index, self.direction_index,
            self.compass_rotation_index,
        )
        while (
            self.pitch, self.roll, self.course_index, self.direction_index,
            self.compass_rotation_index,
        ) == previous:
            self.pitch = random.choice(V2_PITCHES)
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
            self.compass_rotation_index = random.randrange(1, len(COURSES))
        if hasattr(self, "task_number"):
            self.task_number += 1
        if self.answers_enabled:
            self.reset_answers()
        self.draw()

    def valid_pitch_answers(self) -> set[str]:
        return {"0" if value == 0 else f"{value:+d}" for value in PITCHES}

    def select_course_letter(self, letter: str) -> None:
        if self.test_complete or self.course_locked:
            return
        self.course_answer += letter
        self.course_answer_label.configure(text=self.course_answer)
        if len(self.course_answer) >= 3:
            if self.course_answer in COURSES:
                self.course_locked = True
                for button in self.course_letter_buttons:
                    button.configure(state=tk.DISABLED)
            else:
                self.show_invalid_message("\u043d\u0435\u0434\u043e\u043f\u0443\u0441\u0442\u0438\u043c\u044b\u0439 \u043a\u0443\u0440\u0441", "course")

    def select_pitch_sign(self, sign: str) -> None:
        if self.test_complete:
            return
        self.active_numeric_field = "pitch"
        self.pitch_sign = sign
        self.update_pitch_answer_label()

    def select_numeric_digit(self, digit: str) -> None:
        if self.answer_stage >= 3:
            if self.active_numeric_field == "roll":
                self.select_roll_digit(digit)
                return
            # Zero bank has no direction. Once pitch contains a complete valid
            # answer, a plain zero belongs to the roll field.
            if digit == "0" and self.current_pitch_answer() in self.valid_pitch_answers():
                self.active_numeric_field = "roll"
                self.select_roll_digit(digit)
                return
        self.select_pitch_digit(digit)

    def select_pitch_digit(self, digit: str) -> None:
        if self.test_complete or len(self.pitch_digits) >= 2:
            return
        self.pitch_digits += digit
        self.update_pitch_answer_label()
        if len(self.pitch_digits) == 2 and self.current_pitch_answer() not in self.valid_pitch_answers():
            self.show_invalid_message("\u043d\u0435\u0434\u043e\u043f\u0443\u0441\u0442\u0438\u043c\u044b\u0439 \u0442\u0430\u043d\u0433\u0430\u0436", "pitch")

    def valid_roll_answers(self) -> set[str]:
        magnitudes = (22, 45, 67, 112, 135, 167)
        return {"0"} | {
            f"{direction}{value}"
            for direction in ("\u041b", "\u041f")
            for value in magnitudes
        }

    def select_roll_direction(self, direction: str) -> None:
        if self.test_complete:
            return
        self.active_numeric_field = "roll"
        self.roll_direction = direction
        self.update_roll_answer_label()

    def select_roll_digit(self, digit: str) -> None:
        if self.test_complete or len(self.roll_digits) >= 3:
            return
        self.roll_digits += digit
        self.update_roll_answer_label()
        valid_numbers = ("0", "22", "45", "67", "112", "135", "167")
        if not any(value.startswith(self.roll_digits) for value in valid_numbers):
            self.show_invalid_message("\u043d\u0435\u043a\u043e\u0440\u0440\u0435\u043a\u0442\u043d\u044b\u0439 \u043a\u0440\u0435\u043d", "roll")

    def current_pitch_answer(self) -> str:
        return f"{self.pitch_sign}{self.pitch_digits}"

    def current_roll_answer(self) -> str:
        if self.roll_digits and int(self.roll_digits) == 0:
            return "0"
        return f"{self.roll_direction}{self.roll_digits}"

    def update_pitch_answer_label(self) -> None:
        self.pitch_sign_label.configure(text=self.pitch_sign)
        self.pitch_digits_label.configure(text=self.pitch_digits)

    def update_roll_answer_label(self) -> None:
        self.roll_direction_label.configure(text=self.roll_direction)
        self.roll_digits_label.configure(text=self.roll_digits)

    def reset_course_answer(self) -> None:
        self.course_answer = ""
        self.course_locked = False
        if hasattr(self, "course_answer_label"):
            self.course_answer_label.configure(text="")
            for button in self.course_letter_buttons:
                button.configure(state=tk.NORMAL)

    def reset_pitch_answer(self) -> None:
        self.pitch_sign = ""
        self.pitch_digits = ""
        if hasattr(self, "pitch_sign_label"):
            self.pitch_sign_label.configure(text="")
            self.pitch_digits_label.configure(text="")

    def reset_roll_answer(self) -> None:
        self.roll_direction = ""
        self.roll_digits = ""
        if hasattr(self, "roll_direction_label"):
            self.roll_direction_label.configure(text="")
            self.roll_digits_label.configure(text="")

    def reset_answers(self) -> None:
        if not self.answers_enabled or self.test_complete:
            return
        self.reset_course_answer()
        self.reset_pitch_answer()
        if self.answer_stage >= 3:
            self.reset_roll_answer()
        self.active_numeric_field = "pitch"

    def show_invalid_message(self, message: str, field: str) -> None:
        if field == "course":
            self.reset_course_answer()
        elif field == "pitch":
            self.reset_pitch_answer()
        else:
            self.reset_roll_answer()
        if self.invalid_dialog is not None:
            try:
                self.invalid_dialog.destroy()
            except tk.TclError:
                pass
        dialog = tk.Toplevel(self.root)
        self.invalid_dialog = dialog
        dialog.withdraw()
        dialog.overrideredirect(True)
        dialog.transient(self.root)
        dialog.configure(bg="#c62828")
        tk.Label(dialog, text=message, bg="#fff4f4", fg="#9b111e",
                 font=("Arial", 18, "bold"), padx=24, pady=14).pack(padx=2, pady=2)
        dialog.update_idletasks()
        width, height = dialog.winfo_reqwidth(), dialog.winfo_reqheight()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - width) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - height) // 2
        dialog.geometry(f"{width}x{height}+{x}+{y}")
        dialog.deiconify()
        dialog.lift()
        dialog.after(2000, lambda current=dialog: self.close_invalid_dialog(current))

    def close_invalid_dialog(self, dialog: tk.Toplevel) -> None:
        try:
            dialog.destroy()
        except tk.TclError:
            pass
        if self.invalid_dialog is dialog:
            self.invalid_dialog = None

    def record_answers(self) -> None:
        if any(row["task"] == self.task_number for row in self.results):
            return
        course_correct = rotated_course(self.course_index, self.compass_rotation_index)
        pitch_correct = "0" if self.pitch == 0 else f"{self.pitch:+d}"
        pitch_answer = self.current_pitch_answer()
        roll_answer = self.current_roll_answer() if self.answer_stage >= 3 else ""
        roll_correct = self.correct_roll_answer() if self.answer_stage >= 3 else ""
        is_correct = self.course_answer == course_correct and pitch_answer == pitch_correct
        if self.answer_stage >= 3:
            is_correct = is_correct and roll_answer == roll_correct
        self.results.append({
            "task": self.task_number,
            "course_answer": self.course_answer,
            "course_correct": course_correct,
            "pitch_answer": pitch_answer,
            "pitch_correct": pitch_correct,
            "roll_answer": roll_answer,
            "roll_correct": roll_correct,
            "is_correct": is_correct,
        })

    def correct_roll_answer(self) -> str:
        horizon_index = round(self.roll / 22.5) % 16
        airplane_index = round(self.airplane_roll / 22.5) % 16
        relative_steps = (airplane_index - horizon_index) % 16
        if relative_steps > 8:
            relative_steps -= 16
        if relative_steps == 0:
            return "0"
        magnitudes = {1: 22, 2: 45, 3: 67, 5: 112, 6: 135, 7: 167}
        direction = "\u041f" if relative_steps > 0 else "\u041b"
        return f"{direction}{magnitudes[abs(relative_steps)]}"

    def next_task(self) -> None:
        if self.test_complete:
            self.exit_app()
            return
        if self.answers_enabled:
            if self.course_answer and self.course_answer not in COURSES:
                self.show_invalid_message("\u043d\u0435\u0434\u043e\u043f\u0443\u0441\u0442\u0438\u043c\u044b\u0439 \u043a\u0443\u0440\u0441", "course")
                return
            pitch_answer = self.current_pitch_answer()
            if pitch_answer and pitch_answer not in self.valid_pitch_answers():
                self.show_invalid_message("\u043d\u0435\u0434\u043e\u043f\u0443\u0441\u0442\u0438\u043c\u044b\u0439 \u0442\u0430\u043d\u0433\u0430\u0436", "pitch")
                return
            if self.answer_stage >= 3:
                roll_answer = self.current_roll_answer()
                if roll_answer and roll_answer not in self.valid_roll_answers():
                    self.show_invalid_message("\u043d\u0435\u043a\u043e\u0440\u0440\u0435\u043a\u0442\u043d\u044b\u0439 \u043a\u0440\u0435\u043d", "roll")
                    return
            self.record_answers()
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
            self.finish_test()
        else:
            self.timer_after_id = self.root.after(100, self.update_timer)

    def draw_time_bar(self, ratio: float) -> None:
        canvas = self.time_bar_canvas
        canvas.delete("all")
        canvas.create_text(48, 18, text="\u0412\u0420\u0415\u041c\u042f", fill="#102744",
                           font=("Arial", 10, "bold"))
        canvas.create_rectangle(19, 34, 77, 308, outline="#233142", fill="#e6ecf4", width=3)
        fill_height = 266 * max(0.0, min(1.0, ratio))
        if fill_height:
            canvas.create_rectangle(23, 304 - fill_height, 73, 304,
                                    outline="", fill="#3c82ff")

    def completion_message(self) -> str:
        return (
            "\u0412\u0442\u043e\u0440\u043e\u0439 \u044d\u0442\u0430\u043f \u0442\u0435\u0441\u0442\u0430 \u0437\u0430\u0432\u0435\u0440\u0448\u0451\u043d, "
            "\u0434\u043b\u044f \u043f\u0435\u0440\u0435\u0445\u043e\u0434\u0430 \u043a \u0441\u043b\u0435\u0434\u0443\u044e\u0449\u0435\u043c\u0443 \u044d\u0442\u0430\u043f\u0443 "
            "\u043d\u0430\u0436\u043c\u0438\u0442\u0435 \"\u0414\u0430\u043b\u0435\u0435\""
        )

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
        if self.answers_enabled:
            self.record_answers()
            for button in (self.course_letter_buttons + self.pitch_sign_buttons
                           + self.roll_direction_buttons + self.pitch_digit_buttons):
                button.configure(state=tk.DISABLED)
            self.cancel_button.configure(state=tk.DISABLED)
            self.show_results_table()
        self.next_button.configure(state=tk.NORMAL)
        self.show_complete_dialog()

    def show_results_table(self) -> None:
        panel = tk.Frame(self.root, bg="white", highlightbackground="#1976a3", highlightthickness=2)
        tk.Label(panel, text="\u0422\u0430\u0431\u043b\u0438\u0446\u0430 \u043e\u0442\u0432\u0435\u0442\u043e\u0432", bg="white", fg="#102744",
                 font=("Arial", 14, "bold"), pady=7).pack(fill="x")
        correct_count = sum(bool(row["is_correct"]) for row in self.results)
        tk.Label(panel, text=f"\u041f\u0440\u0430\u0432\u0438\u043b\u044c\u043d\u044b\u0445: {correct_count}    \u041d\u0435\u043f\u0440\u0430\u0432\u0438\u043b\u044c\u043d\u044b\u0445: {len(self.results) - correct_count}",
                 bg="white", fg="#102744", font=("Arial", 10, "bold"), pady=3).pack(fill="x")
        table = tk.Frame(panel, bg="#233142")
        table.pack(padx=8, pady=(4, 8))
        if self.answer_stage >= 3:
            headers = ("\u2116", "\u041a\u0443\u0440\u0441", "\u0412\u0435\u0440\u043d\u043e", "\u0422\u0430\u043d\u0433.", "\u0412\u0435\u0440\u043d\u043e",
                       "\u041a\u0440\u0435\u043d", "\u0412\u0435\u0440\u043d\u043e", "\u0418\u0442\u043e\u0433")
            widths = (2, 5, 6, 6, 6, 6, 6, 8)
        else:
            headers = ("\u2116", "\u041a\u0443\u0440\u0441", "\u0412\u0435\u0440\u043d\u043e", "\u0422\u0430\u043d\u0433\u0430\u0436", "\u0412\u0435\u0440\u043d\u043e", "\u0418\u0442\u043e\u0433")
            widths = (2, 6, 7, 7, 7, 8)
        for column, (header, width) in enumerate(zip(headers, widths)):
            tk.Label(table, text=header, width=width, bg="#dce8f4", fg="#102744",
                     font=("Arial", 9, "bold"), bd=1, relief="solid", pady=4).grid(row=0, column=column)
        for row_index, row in enumerate(self.results, start=1):
            verdict = "\u0412\u0435\u0440\u043d\u043e" if row["is_correct"] else "\u041d\u0435\u0432\u0435\u0440\u043d\u043e"
            if self.answer_stage >= 3:
                values = (row["task"], row["course_answer"] or "\u2014", row["course_correct"],
                          row["pitch_answer"] or "\u2014", row["pitch_correct"],
                          row["roll_answer"] or "\u2014", row["roll_correct"], verdict)
            else:
                values = (row["task"], row["course_answer"] or "\u2014", row["course_correct"],
                          row["pitch_answer"] or "\u2014", row["pitch_correct"], verdict)
            for column, (value, width) in enumerate(zip(values, widths)):
                verdict_bg = "#d7f0d8" if row["is_correct"] else "#f6d4d4"
                tk.Label(table, text=str(value), width=width,
                         bg=verdict_bg if column == len(values) - 1 else "white", fg="#102744",
                         font=("Arial", 9), bd=1, relief="solid", pady=4).grid(row=row_index, column=column)
        seconds = int(self.elapsed_seconds)
        tk.Label(panel, text=f"\u0417\u0430\u0442\u0440\u0430\u0447\u0435\u043d\u043e \u0432\u0440\u0435\u043c\u0435\u043d\u0438: {seconds // 60:02d}:{seconds % 60:02d}",
                 bg="white", fg="#102744", font=("Arial", 10, "bold"), pady=6).pack(fill="x")
        self.results_panel = panel
        self.root.update_idletasks()
        panel.place(x=130, rely=0.5, anchor="w")
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
        tk.Label(
            panel, text=self.completion_message(), bg="white", fg="#0c254a",
            font=("Times New Roman", 22, "bold"), justify="center",
            wraplength=390, padx=24, pady=22,
        ).pack()
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
            self.timer_after_id = None
        self.root.destroy()

    def draw(self) -> None:
        self.canvas.delete("all")
        width = max(1, self.canvas.winfo_width())
        height = max(1, self.canvas.winfo_height())
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
        self.canvas.create_oval(
            cx - inner,
            cy - inner,
            cx + inner,
            cy + inner,
            fill=SKY_V2,
            outline="",
        )

        # Pitch is read on a sinusoidal vertical scale.  The perpendicular
        # distance from the centre to the horizon is the radius of the
        # imaginary circle tangent to the horizon and crossing the selected
        # pitch mark.  Rounded labels 22 and 67 represent the exact 22.5- and
        # 67.5-degree positions of the 16-step scale.
        pitch_scale_radius = inner
        offset = pitch_scale_radius * math.sin(
            math.radians(rhumb_angle(self.pitch))
        )

        # ROLLS contains the 16 rhumb positions.  In canvas coordinates this
        # line direction is perpendicular to the radius aimed at that rhumb.
        angle = math.radians(rhumb_angle(self.roll))
        down_angle = angle + math.pi / 2
        half_arc = math.acos(offset / inner)
        ground_points: list[float] = []
        steps = 120
        for step in range(steps + 1):
            arc_angle = down_angle - half_arc + 2 * half_arc * step / steps
            ground_points.extend(
                (cx + inner * math.cos(arc_angle), cy + inner * math.sin(arc_angle))
            )
        self.canvas.create_polygon(*ground_points, fill=GROUND_V2, outline="")

        # Draw the horizon as a separate high-contrast straight chord.
        along = (math.cos(angle), math.sin(angle))
        down = (-math.sin(angle), math.cos(angle))
        chord_half = math.sqrt(max(0.0, inner * inner - offset * offset))
        x1 = cx + down[0] * offset - along[0] * chord_half
        y1 = cy + down[1] * offset - along[1] * chord_half
        x2 = cx + down[0] * offset + along[0] * chord_half
        y2 = cy + down[1] * offset + along[1] * chord_half
        self.canvas.create_line(
            x1,
            y1,
            x2,
            y2,
            fill=HORIZON_V2,
            width=max(3, round(4.0 * s)),
        )

    def draw_course_scale(self, cx: float, cy: float, r: float, s: float) -> None:
        self.canvas.create_oval(
            cx - r,
            cy - r,
            cx + r,
            cy + r,
            outline="#666666",
            width=max(1, 1.5 * s),
        )
        inner_edge = r - 28 * s
        self.canvas.create_oval(
            cx - inner_edge,
            cy - inner_edge,
            cx + inner_edge,
            cy + inner_edge,
            outline="white",
            width=max(2, 3 * s),
        )

        # Exactly 16 rhumb marks, without intermediate short marks.
        for index in range(16):
            degree = index * 22.5
            x1, y1 = polar(cx, cy, r - 2 * s, degree)
            x2, y2 = polar(cx, cy, inner_edge, degree)
            self.canvas.create_line(x1, y1, x2, y2, fill=BLACK, width=max(2, 3 * s))

        course_angle = self.course_index * 22.5
        tip = polar(cx, cy, r + 63 * s, course_angle)
        left = polar(cx, cy, r + 3 * s, course_angle - 5.4)
        right = polar(cx, cy, r + 3 * s, course_angle + 5.4)
        self.canvas.create_polygon(*tip, *left, *right, fill=RED, outline=RED)

        direction_angle = self.direction_index * 22.5
        label_x, label_y = polar(cx, cy, r + 28 * s, direction_angle)
        horizontal_direction = math.sin(math.radians(direction_angle))
        if horizontal_direction > 0.1:
            label_anchor = "w"
        elif horizontal_direction < -0.1:
            label_anchor = "e"
        else:
            label_anchor = "center"
        self.canvas.create_text(
            label_x,
            label_y,
            text=rotated_course(self.direction_index, self.compass_rotation_index),
            fill=RED,
            font=("Arial", max(10, round(24 * s)), "bold"),
            anchor=label_anchor,
        )

    def draw_roll_scale(self, cx: float, cy: float, r: float, s: float) -> None:
        # A roll value at every rhumb except 0 and 180 degrees.
        label_radius = r - 60 * s
        font = self.scale_number_font(s)
        for degree, label in (
            (22.5, "22"),
            (45, "45"),
            (67.5, "67"),
            (90, "90"),
            (112.5, "112"),
            (135, "135"),
            (157.5, "167"),
            (202.5, "167"),
            (225, "135"),
            (247.5, "112"),
            (270, "90"),
            (292.5, "67"),
            (315, "45"),
            (337.5, "22"),
        ):
            x, y = polar(cx, cy, label_radius, degree)
            self.canvas.create_text(x, y, text=label, fill=BLACK, font=font)

    def draw_pitch_scale(self, cx: float, cy: float, r: float, s: float) -> None:
        # The pitch scale is sinusoidal.  All red numerals match the black
        # roll-scale font and stay on one vertical axis.  The 67 label is moved
        # slightly towards the centre to keep it separate from the 90 label,
        # while both scale marks remain at their exact sinusoidal positions.
        # The 90-degree marks lie exactly on the coloured test-circle edge.
        half_height = r - 29 * s
        for value in (-90, -67, -45, -22, 0, 22, 45, 67, 90):
            y = cy - half_height * math.sin(
                math.radians(rhumb_angle(value))
            )
            half_line = (38 if value in (-90, -45, 0, 45, 90) else 24) * s
            text_gap = 55 * s
            line_width = max(1, round(1.8 * s))
            for x1, x2 in (
                (cx - text_gap - half_line, cx - text_gap),
                (cx + text_gap, cx + text_gap + half_line),
            ):
                self.canvas.create_line(x1, y, x2, y, fill=BLACK, width=line_width + 2)
                self.canvas.create_line(x1, y, x2, y, fill="white", width=line_width)
            label_y = y
            if abs(value) == 67:
                label_y += math.copysign(16 * s, value)
            if value != 0:
                label = str(abs(value))
                font = self.pitch_number_font(value, s)
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    self.canvas.create_text(
                        cx + dx, label_y + dy, text=label, fill=BLACK, font=font
                    )
                self.canvas.create_text(
                    cx, label_y, text=label, fill="white", font=font
                )

    @staticmethod
    def scale_number_font(scale: float) -> tuple[str, int]:
        """Return the font used by the black roll-scale numbers."""
        return ("Arial", max(13, round(30 * scale)))

    @staticmethod
    def pitch_number_font(value: int, scale: float) -> tuple[str, int]:
        """Return the same font size as the black roll-scale numbers."""
        del value
        return ("Arial", max(13, round(30 * scale)))

    def draw_airplane(self, cx: float, cy: float, s: float, roll: float) -> None:
        airplane_scale = 2.0 * s
        center = (110.0, 82.0)
        angle = math.radians(rhumb_angle(roll))

        def point(x: float, y: float) -> tuple[float, float]:
            dx = (x - center[0]) * airplane_scale
            dy = (y - center[1]) * airplane_scale
            return (
                cx + dx * math.cos(angle) - dy * math.sin(angle),
                cy + dx * math.sin(angle) + dy * math.cos(angle),
            )

        def line(points: list[tuple[float, float]], width: float) -> None:
            coordinates: list[float] = []
            for x, y in points:
                coordinates.extend(point(x, y))
            self.canvas.create_line(
                *coordinates,
                fill=BLACK,
                width=max(2, width * airplane_scale),
                capstyle=tk.ROUND,
                joinstyle=tk.ROUND,
            )

        # Enlarged central circle.
        circle_points = [
            (
                110 + 23 * math.cos(math.tau * index / 48),
                82 + 21 * math.sin(math.tau * index / 48),
            )
            for index in range(49)
        ]
        body: list[float] = []
        for x, y in circle_points:
            body.extend(point(x, y))
        self.canvas.create_polygon(*body, fill="#dff1fb", outline="")

        # One straight wing line. The stabilizers from v1 are intentionally absent.
        line([(4, 82), (87, 82)], 5)
        line([(133, 82), (216, 82)], 5)

        # Landing gear retained from the original vector airplane.
        line([(62, 82), (62, 108)], 4)
        line([(158, 82), (158, 108)], 4)

        # The keel stops before the central circle instead of crossing it.
        line([(110, 32), (110, 57)], 5)
        line(circle_points, 5)


def main() -> None:
    root = tk.Tk()
    OrientationTestV2(root)
    root.mainloop()


if __name__ == "__main__":
    main()
