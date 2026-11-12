from __future__ import annotations

import random
import tkinter as tk

from orient_new_v1 import COURSES, RED
from orient_new_v2_1 import (
    INSTRUMENT_STYLE_VERSION,
    PITCH_VALUES_15,
    ROLL_VALUES_15,
    OrientationTestV21,
)


APP_TITLE = "Ориентация — тестовый круг v3.1"
ROLL_MAGNITUDES_15 = (15, 30, 45, 60, 75, 105, 120, 135, 150, 165)
# At +/-90 degrees pitch the roll axis becomes visually degenerate, so bank
# tasks on stage 3 must never use those two endpoint attitudes.
STAGE3_PITCH_VALUES_15 = tuple(value for value in PITCH_VALUES_15 if abs(value) < 90)
STAGE3_AIRPLANE_ROLLS = tuple(
    signed
    for magnitude in ROLL_MAGNITUDES_15
    for signed in (-magnitude, magnitude)
)


def relative_roll(horizon_roll: int, airplane_roll: int) -> int:
    # The horizon is a line, so angles that differ by 180 degrees describe the
    # same visible orientation.  Return the signed acute angle from the visible
    # horizon to the aircraft wings.
    return int((airplane_roll - horizon_roll + 90) % 180 - 90)


def has_forbidden_relative_roll(horizon_roll: int, airplane_roll: int) -> bool:
    return relative_roll(horizon_roll, airplane_roll) % 90 == 0


class OrientationTestV31(OrientationTestV21):
    """Version 3 answers with independent horizon and aircraft roll angles."""

    ANSWER_STAGE = 3
    instrument_style_version = INSTRUMENT_STYLE_VERSION

    def __init__(self, root: tk.Tk) -> None:
        self.airplane_roll = 0
        super().__init__(root)
        self.canvas.configure(width=620)
        self.root.title(APP_TITLE)

    def new_task(self, _event: tk.Event | None = None) -> None:
        previous = (
            getattr(self, "pitch", 0),
            getattr(self, "roll", 0),
            getattr(self, "airplane_roll", 0),
            getattr(self, "course_index", 0),
            getattr(self, "direction_index", 3),
            getattr(self, "compass_rotation_index", 0),
        )
        while True:
            self.pitch = random.choice(STAGE3_PITCH_VALUES_15)
            self.roll = random.choice(ROLL_VALUES_15)
            self.airplane_roll = random.choice(STAGE3_AIRPLANE_ROLLS)
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
                self.airplane_roll,
                self.course_index,
                self.direction_index,
                self.compass_rotation_index,
            )
            if current != previous:
                break
        if hasattr(self, "task_number"):
            self.task_number += 1
        if getattr(self, "answers_enabled", False):
            self.reset_answers()
        self.draw()

    def valid_roll_answers(self) -> set[str]:
        return {"0"} | {
            f"{direction}{value}"
            for direction in ("Л", "П")
            for value in ROLL_MAGNITUDES_15
        }

    def select_roll_digit(self, digit: str) -> None:
        if self.test_complete or len(self.roll_digits) >= 3:
            return
        self.roll_digits += digit
        self.update_roll_answer_label()
        valid_numbers = ("0",) + tuple(str(value) for value in ROLL_MAGNITUDES_15)
        if not any(value.startswith(self.roll_digits) for value in valid_numbers):
            self.show_invalid_message("некорректный крен", "roll")

    def correct_roll_answer(self) -> str:
        # Bank is the angle between the aircraft wings and the visible horizon,
        # rather than the aircraft drawing's absolute canvas rotation.
        visible_roll = relative_roll(int(self.roll), int(self.airplane_roll))
        if visible_roll == 0:
            return "0"
        direction = "Л" if visible_roll > 0 else "П"
        return f"{direction}{abs(visible_roll)}"

    def completion_message(self) -> str:
        return (
            "Третий этап теста завершён, для просмотра результатов и перехода "
            "к следующему тесту нажмите \"Далее\""
        )

    def draw(self) -> None:
        self.canvas.delete("all")
        width = max(1, self.canvas.winfo_width())
        height = max(1, self.canvas.winfo_height())
        size = min(width, height) * 0.80
        radius = size / 2
        cx, cy = width / 2, height / 2
        scale = size / 620

        self.draw_face(cx, cy, radius, scale)
        self.draw_course_scale(cx, cy, radius, scale)
        self.draw_roll_scale(cx, cy, radius, scale)
        self.draw_pitch_scale(cx, cy, radius, scale)
        self.draw_airplane(cx, cy, scale, self.airplane_roll)


def main() -> None:
    root = tk.Tk()
    OrientationTestV31(root)
    root.mainloop()


if __name__ == "__main__":
    main()
