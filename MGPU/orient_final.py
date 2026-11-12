from __future__ import annotations

import sys
import time
import tkinter as tk
from pathlib import Path
from typing import Any

from PIL import Image, ImageTk

from orient_new_v1 import COURSES, OrientationTest
from orient_new_v1_1 import INSTRUMENT_STYLE_VERSION, OrientationTestV11
from orient_new_v2 import OrientationTestV2
from orient_new_v2_1 import OrientationTestV21
from orient_new_v3_1 import OrientationTestV31


APP_TITLE = "Пространственная ориентация — авиагоризонт"
ORIENT_FINAL_STYLE_VERSION = INSTRUMENT_STYLE_VERSION
START_BG = "#c8f3f2"
INSTRUCTION_BG = "#ececec"
TEXT_COLOR = "#031a2f"
NEXT_BG = "#59c762"
NEXT_ACTIVE = "#49b553"
TRAINING_BG = "#ffee20"
TRAINING_ACTIVE = "#e3d600"
EXIT_BG = "#e65050"
EXIT_ACTIVE = "#cd3f3f"
CANCEL_BG = "#f2d64b"
CANCEL_ACTIVE = "#e3c12d"


def application_base_dir() -> Path:
    bundled = getattr(sys, "_MEIPASS", None)
    if bundled:
        return Path(bundled)
    return Path(__file__).resolve().parent


def instruction_image_path() -> Path:
    base = application_base_dir()
    candidates = (
        base / "assets" / "orient_instruction.png",
        Path(__file__).resolve().parent / "assets" / "orient_instruction.png",
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


class _FinalStageMixin:
    """Connect an existing test stage to the common application controller."""

    def __init__(
        self,
        root: tk.Toplevel,
        controller: "OrientFinalApp",
        stage_number: int,
        training: bool,
    ) -> None:
        self.final_controller = controller
        self.final_stage_number = stage_number
        self.final_training = training
        self._final_closing = False
        self._final_return_to_instruction = False
        super().__init__(root)
        if training and hasattr(self, "exit_button"):
            self.exit_button.configure(command=self.return_to_instruction)

    def update_timer(self) -> None:
        if not self.final_training:
            super().update_timer()
            return

        self.timer_after_id = None
        if self.test_complete:
            return
        elapsed = max(0.0, time.perf_counter() - self.test_started_at)
        self.draw_time_bar(min(1.0, elapsed / 60.0))
        if elapsed >= 60.0:
            if self.final_stage_number == 1:
                self.record_answer()
            self.finish_test()
        else:
            self.timer_after_id = self.root.after(100, self.update_timer)

    def return_to_instruction(self) -> None:
        self._final_return_to_instruction = True
        self.exit_app()

    def show_complete_dialog(self) -> None:
        if not self.final_training:
            super().show_complete_dialog()
            return

        dialog = tk.Toplevel(self.root)
        self.complete_dialog = dialog
        dialog.withdraw()
        dialog.overrideredirect(True)
        dialog.transient(self.root)
        dialog.configure(bg="#1976a3")
        panel = tk.Frame(dialog, bg="white")
        panel.pack(fill="both", expand=True, padx=2, pady=2)
        if self.final_stage_number < 3:
            destination = "к следующему тренировочному этапу"
        else:
            destination = "к инструкции"
        tk.Label(
            panel,
            text=(
                f"Тренировочное задание этапа {self.final_stage_number} завершено. "
                f"Для перехода {destination} нажмите \"Далее\""
            ),
            bg="white",
            fg="#0c254a",
            font=("Times New Roman", 22, "bold"),
            justify="center",
            wraplength=420,
            padx=24,
            pady=22,
        ).pack()
        dialog.update_idletasks()
        width = dialog.winfo_reqwidth()
        height = dialog.winfo_reqheight()
        x = self.root.winfo_rootx() + self.root.winfo_width() - width - 32
        y = self.root.winfo_rooty() + (self.root.winfo_height() - height) // 2
        dialog.geometry(f"{width}x{height}+{x}+{y}")
        dialog.deiconify()
        dialog.lift()

    def exit_app(self) -> None:
        if self._final_closing:
            return
        self._final_closing = True
        completed = bool(getattr(self, "test_complete", False))
        if self._final_return_to_instruction:
            completed = False
        results = [dict(row) for row in getattr(self, "results", [])]
        elapsed = float(getattr(self, "elapsed_seconds", 0.0))

        timer_after_id = getattr(self, "timer_after_id", None)
        if timer_after_id is not None:
            try:
                self.root.after_cancel(timer_after_id)
            except tk.TclError:
                pass
            self.timer_after_id = None

        try:
            self.root.destroy()
        except tk.TclError:
            pass

        try:
            self.final_controller.root.after(
                0,
                lambda: self.final_controller.stage_closed(
                    self.final_stage_number,
                    self.final_training,
                    completed,
                    results,
                    elapsed,
                ),
            )
        except tk.TclError:
            pass


class FinalStage1(_FinalStageMixin, OrientationTestV11):
    def next_task(self) -> None:
        if not self.final_training:
            super().next_task()
            return
        if self.test_complete:
            self.exit_app()
            return
        if self.selected_answer and self.selected_answer not in COURSES:
            self.show_invalid_answer()
            return
        self.record_answer()
        self.finish_test()

    def finish_test(self) -> None:
        if self.final_training:
            OrientationTest.finish_test(self)
        else:
            super().finish_test()


class _FinalAnswerStageMixin(_FinalStageMixin):
    def next_task(self) -> None:
        if not self.final_training:
            super().next_task()
            return
        if self.test_complete:
            self.exit_app()
            return

        if self.course_answer and self.course_answer not in COURSES:
            self.show_invalid_message("недопустимый курс", "course")
            return
        pitch_answer = self.current_pitch_answer()
        if pitch_answer and pitch_answer not in self.valid_pitch_answers():
            self.show_invalid_message("недопустимый тангаж", "pitch")
            return
        if self.answer_stage >= 3:
            roll_answer = self.current_roll_answer()
            if roll_answer and roll_answer not in self.valid_roll_answers():
                self.show_invalid_message("некорректный крен", "roll")
                return

        self.record_answers()
        self.finish_test()

    def finish_test(self) -> None:
        if self.final_training:
            OrientationTestV2.finish_test(self)
        else:
            super().finish_test()


class FinalStage2(_FinalAnswerStageMixin, OrientationTestV21):
    pass


class FinalStage3(_FinalAnswerStageMixin, OrientationTestV31):
    pass


class OrientFinalApp:
    stage_classes = (FinalStage1, FinalStage2, FinalStage3)

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(APP_TITLE)
        self.root.configure(bg=START_BG)
        self.root.protocol("WM_DELETE_WINDOW", self.shutdown)
        self.root.bind("<Escape>", lambda _event: self.shutdown())
        self.root.minsize(900, 650)
        self.instruction_photo: ImageTk.PhotoImage | None = None
        self.active_stage: Any | None = None
        self.active_stage_number = 0
        self.active_training = False
        self.stage_results: dict[str, list[dict[str, object]]] = {}
        self.open_fullscreen()
        self.show_start_page()

    def open_fullscreen(self) -> None:
        try:
            self.root.attributes("-fullscreen", True)
        except tk.TclError:
            width = self.root.winfo_screenwidth()
            height = self.root.winfo_screenheight()
            self.root.geometry(f"{width}x{height}+0+0")

    def clear_page(self) -> None:
        self.root.unbind_all("<MouseWheel>")
        for child in self.root.winfo_children():
            child.destroy()
        self.instruction_photo = None

    @staticmethod
    def styled_button(
        parent: tk.Widget,
        text: str,
        command: Any,
        bg: str,
        activebackground: str,
        width: int,
    ) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            activebackground=activebackground,
            fg="white" if bg == EXIT_BG else "#0f2c12",
            font=("Arial", 20, "bold"),
            width=width,
            padx=10,
            pady=6,
            bd=3,
            relief="raised",
            cursor="hand2",
            highlightthickness=1,
            highlightbackground="#000000",
            highlightcolor="#000000",
        )

    def show_start_page(self) -> None:
        self.clear_page()
        self.root.configure(bg=START_BG)
        self.root.deiconify()
        self.open_fullscreen()
        self.root.update_idletasks()
        page_width = max(900, self.root.winfo_width())
        title_font_size = max(28, min(42, round(page_width / 38)))

        page = tk.Frame(self.root, bg=START_BG)
        page.pack(fill="both", expand=True)

        tk.Label(
            page,
            text="Методика",
            bg=START_BG,
            fg=TEXT_COLOR,
            font=("Arial", 34, "bold"),
        ).place(relx=0.5, rely=0.06, anchor="n")
        tk.Label(
            page,
            text="ПРОСТРАНСТВЕННАЯ ОРИЕНТАЦИЯ\n(АВИАГОРИЗОНТ)",
            bg=START_BG,
            fg="#000000",
            font=("Arial", title_font_size, "bold"),
            justify="center",
            wraplength=page_width - 80,
        ).place(relx=0.5, rely=0.14, anchor="n")

        self.styled_button(
            page,
            "ДАЛЕЕ",
            self.show_instruction_page,
            NEXT_BG,
            NEXT_ACTIVE,
            14,
        ).place(relx=0.5, rely=0.58, anchor="center")

        footer = tk.Frame(page, bg=START_BG)
        footer.pack(side="bottom", fill="x", padx=16, pady=(0, 14))
        footer.grid_columnconfigure(0, weight=1)
        footer.grid_columnconfigure(1, weight=1)
        self.styled_button(
            footer,
            "Выход",
            self.shutdown,
            EXIT_BG,
            EXIT_ACTIVE,
            12,
        ).grid(row=0, column=0, sticky="w")
        cancel_button = self.styled_button(
            footer,
            "Отмена",
            self.shutdown,
            CANCEL_BG,
            CANCEL_ACTIVE,
            12,
        )
        cancel_button.configure(fg="#4f3900")
        cancel_button.grid(row=0, column=1, sticky="e")

    def show_instruction_page(self) -> None:
        self.clear_page()
        self.root.configure(bg=INSTRUCTION_BG)
        self.root.deiconify()
        self.open_fullscreen()
        self.root.update_idletasks()

        page = tk.Frame(self.root, bg=INSTRUCTION_BG)
        page.pack(fill="both", expand=True, padx=24, pady=(16, 12))

        image_area = tk.Frame(page, bg=INSTRUCTION_BG)
        image_area.pack(fill="both", expand=True)
        path = instruction_image_path()
        if path.exists():
            with Image.open(path) as source:
                image = source.convert("RGB")
                max_width = max(600, self.root.winfo_width() - 80)
                max_height = max(420, self.root.winfo_height() - 150)
                scale = min(
                    max_width / max(1, image.width),
                    max_height / max(1, image.height),
                    1.0,
                )
                draw_size = (
                    max(1, round(image.width * scale)),
                    max(1, round(image.height * scale)),
                )
                image = image.resize(draw_size, Image.Resampling.LANCZOS)
            self.instruction_photo = ImageTk.PhotoImage(image)
            tk.Label(
                image_area,
                image=self.instruction_photo,
                bg=INSTRUCTION_BG,
                bd=0,
                highlightthickness=0,
            ).pack(expand=True)
        else:
            tk.Label(
                image_area,
                text=f"Не найден файл инструкции:\n{path}",
                bg=INSTRUCTION_BG,
                fg="#2b2b2b",
                font=("Arial", 16, "bold"),
                justify="center",
            ).pack(expand=True)

        buttons = tk.Frame(page, bg=INSTRUCTION_BG)
        buttons.pack(side="bottom", fill="x", pady=(6, 8), before=image_area)
        for column in range(3):
            buttons.grid_columnconfigure(column, weight=1, uniform="instruction_buttons")

        self.styled_button(
            buttons,
            "Выход",
            self.shutdown,
            EXIT_BG,
            EXIT_ACTIVE,
            10,
        ).grid(row=0, column=0)
        self.styled_button(
            buttons,
            "Тренировка",
            lambda: self.start_sequence(training=True),
            TRAINING_BG,
            TRAINING_ACTIVE,
            14,
        ).grid(row=0, column=1)
        self.styled_button(
            buttons,
            "ДАЛЕЕ",
            lambda: self.start_sequence(training=False),
            NEXT_BG,
            NEXT_ACTIVE,
            12,
        ).grid(row=0, column=2)

    def start_sequence(self, training: bool) -> None:
        self.active_training = training
        self.active_stage_number = 1
        mode = "training" if training else "test"
        self.stage_results = {mode: []}
        self.root.withdraw()
        self.launch_stage()

    def launch_stage(self) -> None:
        if not 1 <= self.active_stage_number <= len(self.stage_classes):
            self.sequence_finished()
            return
        stage_root = tk.Toplevel(self.root)
        stage_class = self.stage_classes[self.active_stage_number - 1]
        self.active_stage = stage_class(
            stage_root,
            self,
            self.active_stage_number,
            self.active_training,
        )

    def stage_closed(
        self,
        stage_number: int,
        training: bool,
        completed: bool,
        results: list[dict[str, object]],
        elapsed: float,
    ) -> None:
        self.active_stage = None
        if not completed:
            if training:
                self.active_stage_number = 0
                self.show_instruction_page()
            else:
                self.shutdown()
            return

        mode = "training" if training else "test"
        self.stage_results.setdefault(mode, []).append(
            {
                "stage": stage_number,
                "elapsed_seconds": elapsed,
                "results": results,
            }
        )
        if stage_number < len(self.stage_classes):
            self.active_stage_number = stage_number + 1
            self.launch_stage()
        else:
            self.sequence_finished()

    def show_results_page(self) -> None:
        """Show the three-stage summary in the visual style of test D (v421)."""
        self.clear_page()
        self.root.configure(bg="#eef3f8")
        self.root.deiconify()
        self.open_fullscreen()

        shell = tk.Frame(self.root, bg="#eef3f8")
        shell.pack(fill="both", expand=True)
        canvas = tk.Canvas(shell, bg="#eef3f8", highlightthickness=0)
        scrollbar = tk.Scrollbar(shell, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        outer = tk.Frame(canvas, bg="#eef3f8")
        window_id = canvas.create_window((0, 0), window=outer, anchor="nw")
        outer.bind(
            "<Configure>",
            lambda _event: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.bind(
            "<Configure>",
            lambda event: canvas.itemconfigure(window_id, width=event.width),
        )
        canvas.bind_all(
            "<MouseWheel>",
            lambda event: canvas.yview_scroll(int(-event.delta / 120), "units"),
        )

        stages = sorted(
            self.stage_results.get("test", []), key=lambda item: int(item["stage"])
        )
        stage_titles = (
            "Этап 1 — определение курса",
            "Этап 2 — курс и тангаж",
            "Этап 3 — курс, тангаж и крен",
        )
        stage_colors = ("#67a9ff", "#53c26b", "#c98cff")
        stage_bottom_colors = ("#78d3e2", "#ffb35c", "#ef7070")

        def summary(item: dict[str, object]) -> dict[str, float | int]:
            rows = list(item.get("results", []))
            total = len(rows)
            correct = sum(bool(row.get("is_correct")) for row in rows)
            elapsed = float(item.get("elapsed_seconds", 0.0) or 0.0)
            return {
                "total": total,
                "correct": correct,
                "incorrect": total - correct,
                "accuracy": (100.0 * correct / total) if total else 0.0,
                "elapsed": elapsed,
                "average": (elapsed / total) if total else 0.0,
            }

        summaries = [summary(item) for item in stages]
        total_tasks = sum(int(item["total"]) for item in summaries)
        total_correct = sum(int(item["correct"]) for item in summaries)
        total_accuracy = 100.0 * total_correct / total_tasks if total_tasks else 0.0

        header = tk.Frame(
            outer, bg="#ffffff", highlightthickness=1, highlightbackground="#d8e1ec"
        )
        header.pack(fill="x", padx=24, pady=(24, 10))
        tk.Frame(header, bg="#67a9ff", height=6).pack(fill="x")
        head_body = tk.Frame(header, bg="#ffffff")
        head_body.pack(fill="both", expand=True, padx=22, pady=(14, 12))
        tk.Label(
            head_body,
            text="Пространственная ориентация   Авиагоризонт",
            bg="#ffffff",
            fg="#102744",
            font=("Times New Roman", 30, "bold"),
        ).pack(anchor="w")
        tk.Label(
            head_body,
            text=(
                f"Тест завершён. Выполнено заданий: {total_tasks}. "
                f"Верных ответов: {total_correct}. Общая точность: {total_accuracy:.0f}%."
            ),
            bg="#ffffff",
            fg="#5a6678",
            font=("Arial", 10, "bold"),
        ).pack(anchor="w", pady=(4, 0))

        cards_row = tk.Frame(outer, bg="#eef3f8")
        cards_row.pack(fill="x", padx=24, pady=(0, 4))
        for index, stats in enumerate(summaries):
            cards_row.grid_columnconfigure(index, weight=1, uniform="orientation_cards")
            card = tk.Frame(
                cards_row,
                bg="#ffffff",
                highlightthickness=1,
                highlightbackground="#d8e1ec",
            )
            card.grid(row=0, column=index, sticky="nsew", padx=(0 if index == 0 else 2, 0))
            tk.Frame(card, bg=stage_colors[index], height=4).pack(fill="x")
            body = tk.Frame(card, bg="#ffffff")
            body.pack(fill="both", expand=True, padx=10, pady=8)
            tk.Label(
                body,
                text=f'{float(stats["accuracy"]):.0f}%',
                bg="#ffffff",
                fg="#102744",
                font=("Arial", 26, "bold"),
            ).pack()
            tk.Label(
                body,
                text=f'верно {stats["correct"]} из {stats["total"]}',
                bg="#ffffff",
                fg="#5a6678",
                font=("Arial", 10),
            ).pack(pady=(4, 0))

        stage_row = tk.Frame(outer, bg="#eef3f8")
        stage_row.pack(fill="x", padx=24, pady=(0, 12))
        for index, title in enumerate(stage_titles):
            stage_row.grid_columnconfigure(index, weight=1, uniform="orientation_stages")
            block = tk.Frame(
                stage_row,
                bg="#ffffff",
                highlightthickness=1,
                highlightbackground="#d8e1ec",
                height=94,
            )
            block.grid(row=0, column=index, sticky="nsew", padx=(0 if index == 0 else 2, 0))
            block.grid_propagate(False)
            tk.Frame(block, bg=stage_bottom_colors[index], height=3).pack(fill="x")
            tk.Label(
                block,
                text=title,
                bg="#ffffff",
                fg="#111111",
                font=("Arial", 16, "bold"),
                wraplength=350,
                justify="center",
            ).pack(fill="both", expand=True, padx=8, pady=8)

        table = tk.Frame(
            outer, bg="#ffffff", highlightthickness=1, highlightbackground="#9c9c9c"
        )
        table.pack(fill="x", padx=24, pady=(0, 12))
        headings = ("Показатель", "Этап 1", "Этап 2", "Этап 3")
        for column, heading in enumerate(headings):
            table.grid_columnconfigure(column, weight=2 if column == 0 else 1)
            tk.Label(
                table,
                text=heading,
                bg="#ffd400",
                fg="#1a1a1a",
                font=("Arial", 11, "bold"),
                bd=1,
                relief="solid",
                padx=7,
                pady=7,
            ).grid(row=0, column=column, sticky="nsew")
        metrics = (
            ("Выполнено заданий", lambda value: str(value["total"])),
            ("Верных ответов", lambda value: str(value["correct"])),
            ("Ошибок", lambda value: str(value["incorrect"])),
            ("Точность", lambda value: f'{float(value["accuracy"]):.1f}%'),
            ("Время этапа", lambda value: f'{float(value["elapsed"]):.1f} с'),
            ("Среднее время задания", lambda value: f'{float(value["average"]):.1f} с'),
        )
        for row_index, (label, formatter) in enumerate(metrics, start=1):
            values = (label,) + tuple(formatter(item) for item in summaries)
            for column, value in enumerate(values):
                tk.Label(
                    table,
                    text=value,
                    bg="#effff4" if column == 0 else "#ffffff",
                    fg="#102744",
                    font=("Arial", 10, "bold" if column == 0 else "normal"),
                    bd=1,
                    relief="solid",
                    padx=7,
                    pady=6,
                    anchor="w" if column == 0 else "center",
                ).grid(row=row_index, column=column, sticky="nsew")

        details = tk.Frame(
            outer, bg="#ffffff", highlightthickness=1, highlightbackground="#d8e1ec"
        )
        details.pack(fill="x", padx=24, pady=(0, 12))
        tk.Label(
            details,
            text="Ответы по заданиям",
            bg="#ffffff",
            fg="#102744",
            font=("Arial", 18, "bold"),
        ).pack(anchor="w", padx=16, pady=(12, 8))
        for index, item in enumerate(stages):
            rows = list(item.get("results", []))
            line_parts = []
            for row in rows:
                mark = "✓" if row.get("is_correct") else "✗"
                if index == 0:
                    answer = row.get("answer", "—")
                    correct = row.get("correct", "—")
                else:
                    answer_parts = [row.get("course_answer", "—"), row.get("pitch_answer", "—")]
                    correct_parts = [row.get("course_correct", "—"), row.get("pitch_correct", "—")]
                    if index == 2:
                        answer_parts.append(row.get("roll_answer", "—"))
                        correct_parts.append(row.get("roll_correct", "—"))
                    answer = " / ".join(str(value or "—") for value in answer_parts)
                    correct = " / ".join(str(value or "—") for value in correct_parts)
                line_parts.append(f'{row.get("task", "—")}: {answer} → {correct} {mark}')
            tk.Label(
                details,
                text=f"{stage_titles[index]}\n" + "    ".join(line_parts),
                bg="#ffffff",
                fg="#20324d",
                font=("Arial", 10, "bold" if index == 0 else "normal"),
                justify="left",
                wraplength=1400,
            ).pack(anchor="w", fill="x", padx=16, pady=(0, 10))

        buttons = tk.Frame(outer, bg="#eef3f8")
        buttons.pack(fill="x", padx=24, pady=(0, 24))
        self.styled_button(
            buttons, "ДАЛЕЕ", self.shutdown,
            NEXT_BG, NEXT_ACTIVE, 14,
        ).pack(side="left")
        self.styled_button(
            buttons, "ВЫХОД", self.shutdown, EXIT_BG, EXIT_ACTIVE, 12,
        ).pack(side="right")

    def sequence_finished(self) -> None:
        if self.active_training:
            self.active_stage_number = 0
            self.show_instruction_page()
        else:
            self.active_stage_number = 0
            self.show_results_page()

    def shutdown(self) -> None:
        try:
            self.root.destroy()
        except tk.TclError:
            pass


def main() -> None:
    root = tk.Tk()
    OrientFinalApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
