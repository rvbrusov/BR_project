from __future__ import annotations

import random
import tkinter as tk

from orient_new_v1 import COURSES
from orient_new_v1_1 import INSTRUMENT_STYLE_VERSION, OrientationTestV11
from orient_new_v2 import OrientationTestV2


APP_TITLE = "Ориентация — тестовый круг v2.1"
PITCH_VALUES_15 = tuple(range(-90, 91, 15))
ROLL_VALUES_15 = tuple(range(0, 181, 15))


class OrientationTestV21(OrientationTestV2):
    """Version 2 answers with the complete vector test circle from v1.1."""

    # Reuse the complete v1.1 vector drawing, while the two hooks below adapt
    # its geometry to the exact linear 15-degree scales used by this stage.
    draw = OrientationTestV11.draw
    draw_face = OrientationTestV11.draw_face
    draw_course_scale = OrientationTestV11.draw_course_scale
    draw_roll_scale = OrientationTestV11.draw_roll_scale
    draw_pitch_scale = OrientationTestV11.draw_pitch_scale
    draw_airplane = OrientationTestV11.draw_airplane
    pitch_number_font = staticmethod(OrientationTestV11.pitch_number_font)
    maximize = OrientationTestV11.maximize
    instrument_style_version = INSTRUMENT_STYLE_VERSION

    def build_answer_ui(self, parent: tk.Widget, bg: str) -> None:
        """Make the complete answer block as wide as the white test canvas."""
        super().build_answer_ui(parent, bg)

        area = self.answer_sections.master
        area.pack_configure(fill="x")
        self.answer_sections.pack_configure(fill="x")
        self.answer_sections.grid_propagate(True)

        section_boxes = self.answer_sections.winfo_children()
        for column in range(len(section_boxes)):
            self.answer_sections.grid_columnconfigure(
                column, weight=1, pad=0, uniform="answer_sections"
            )

        if self.answer_stage == 2:
            section_boxes[0].grid_configure(sticky="w", padx=0)
            section_boxes[1].grid_configure(sticky="e", padx=0)
        else:
            section_boxes[0].grid_configure(sticky="w", padx=0)
            section_boxes[1].grid_configure(sticky="n", padx=0)
            section_boxes[2].grid_configure(sticky="e", padx=0)

        self.numeric_keypad.pack_configure(fill="x")
        for button in self.pitch_digit_buttons:
            button.pack_forget()
        for column, button in enumerate(self.pitch_digit_buttons):
            self.numeric_keypad.grid_columnconfigure(
                column, weight=1, uniform="numeric_keys"
            )
            left_pad = 0 if column == 0 else 2
            right_pad = 0 if column == len(self.pitch_digit_buttons) - 1 else 2
            button.grid(
                row=0,
                column=column,
                padx=(left_pad, right_pad),
                sticky="ew",
            )

    def __init__(self, root: tk.Tk) -> None:
        super().__init__(root)
        self.canvas.configure(width=620)
        self.root.title(APP_TITLE)

    def display_roll_angle(self, roll: float) -> float:
        return float(roll)

    def pitch_offset(self, pitch: float, radius: float) -> float:
        return radius * float(pitch) / 90.0

    def new_task(self, _event: tk.Event | None = None) -> None:
        previous = (
            self.pitch,
            self.roll,
            self.course_index,
            self.direction_index,
            self.compass_rotation_index,
        )
        while True:
            self.pitch = random.choice(PITCH_VALUES_15)
            self.roll = random.choice(ROLL_VALUES_15)
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
            current = (
                self.pitch,
                self.roll,
                self.course_index,
                self.direction_index,
                self.compass_rotation_index,
            )
            if current != previous:
                break
        if hasattr(self, "task_number"):
            self.task_number += 1
        if self.answers_enabled:
            self.reset_answers()
        self.draw()

    def valid_pitch_answers(self) -> set[str]:
        return {f"{value:+d}" for value in PITCH_VALUES_15}

    def finish_test(self) -> None:
        if self.test_complete:
            return
        if self.answers_enabled and not any(
            row["task"] == self.task_number for row in self.results
        ):
            self.record_answers()

        completed_numbers = {int(row["task"]) for row in self.results}
        for task_number in range(1, 6):
            if task_number not in completed_numbers:
                self.results.append(
                    {
                        "task": task_number,
                        "course_answer": "",
                        "course_correct": "—",
                        "pitch_answer": "",
                        "pitch_correct": "—",
                        "roll_answer": "",
                        "roll_correct": "—",
                        "is_correct": False,
                    }
                )
        self.results.sort(key=lambda row: int(row["task"]))
        super().finish_test()


def main() -> None:
    root = tk.Tk()
    OrientationTestV21(root)
    root.mainloop()


if __name__ == "__main__":
    main()
