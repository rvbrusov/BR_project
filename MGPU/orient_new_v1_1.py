from __future__ import annotations

import math
import time
import tkinter as tk

from orient_new_v1 import (
    BLACK,
    COURSES,
    RED,
    OrientationTest,
    polar,
    rhumb_angle,
    rotated_course,
)


APP_TITLE = "Ориентация — тестовый круг v1.1"
INSTRUMENT_STYLE_VERSION = "double_height_fin_clear_of_fuselage_and_label_v6"
SKY_COLOR = "#91dff3"
GROUND_COLOR = "#e4c1ac"
HORIZON_COLOR = "#123f73"
OUTER_SCALE_COLOR = "#315d24"
INNER_CIRCLE_COLOR = "#2f67a3"
ROLL_MAJOR_COLOR = "#0d354d"
ROLL_MINOR_COLOR = "#244d63"
WHITE_RING_WIDTH = 48.0
ROLL_SCALE_DEPTH = 36.0
ROLL_MINOR_SCALE_DEPTH = 20.0
ROLL_MINOR_RIM_GAP = 12.0
ROLL_LABEL_INSET = 55.0
PITCH_TICK_INNER_OFFSET = 29.0
PITCH_MINOR_TICK_LENGTH = 13.0
PITCH_90_CLEARANCE_DEGREES = 5
COURSE_TICK_OUTER_INSET = 1.0
COURSE_TICK_INNER_INSET = 36.0


class OrientationTestV11(OrientationTest):
    """Version 1.1 with the revised vector aircraft and instrument scales."""

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
        self.canvas.configure(width=620)
        self.maximize()
        self.new_task()
        self.update_timer()
        self.root.title(APP_TITLE)

    def maximize(self) -> None:
        """Cover the whole screen so a parent page cannot remain visible below."""
        try:
            self.root.attributes("-fullscreen", True)
        except tk.TclError:
            self.root.geometry(
                f"{self.root.winfo_screenwidth()}x{self.root.winfo_screenheight()}+0+0"
            )
        try:
            self.root.lift()
            self.root.focus_force()
        except tk.TclError:
            pass

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
        self.draw_airplane(cx, cy, scale, self.roll)

    def finish_test(self) -> None:
        if self.test_complete:
            return

        if not any(row["task"] == self.task_number for row in self.results):
            self.record_answer()
        completed_numbers = {int(row["task"]) for row in self.results}
        for task_number in range(1, 6):
            if task_number not in completed_numbers:
                self.results.append(
                    {
                        "task": task_number,
                        "answer": "—",
                        "correct": "—",
                        "is_correct": False,
                    }
                )
        self.results.sort(key=lambda row: int(row["task"]))
        super().finish_test()

    @staticmethod
    def pitch_number_font(_value: int, scale: float) -> tuple[str, int]:
        return ("Arial", max(10, round(24 * scale)))

    def display_roll_angle(self, roll: float) -> float:
        return rhumb_angle(roll)

    def pitch_offset(self, pitch: float, radius: float) -> float:
        return radius * math.sin(math.radians(rhumb_angle(pitch)))

    def draw_face(self, cx: float, cy: float, r: float, s: float) -> None:
        inner = r - WHITE_RING_WIDTH * s
        self.canvas.create_oval(
            cx - inner,
            cy - inner,
            cx + inner,
            cy + inner,
            fill=SKY_COLOR,
            outline="",
        )

        offset = self.pitch_offset(self.pitch, inner)
        angle = math.radians(self.display_roll_angle(self.roll))
        down_angle = angle + math.pi / 2
        half_arc = math.acos(max(-1.0, min(1.0, offset / inner)))
        ground_points: list[float] = []
        for step in range(121):
            arc_angle = down_angle - half_arc + 2 * half_arc * step / 120
            ground_points.extend(
                (cx + inner * math.cos(arc_angle), cy + inner * math.sin(arc_angle))
            )
        self.canvas.create_polygon(*ground_points, fill=GROUND_COLOR, outline="")

        along = (math.cos(angle), math.sin(angle))
        down = (-math.sin(angle), math.cos(angle))
        chord_half = math.sqrt(max(0.0, inner * inner - offset * offset))
        horizon_cx = cx + down[0] * offset
        horizon_cy = cy + down[1] * offset
        # Keep only the horizon chord: thinner than before and without a normal.
        line_width = max(2, round(3.0 * s))
        self.canvas.create_line(
            horizon_cx - along[0] * chord_half,
            horizon_cy - along[1] * chord_half,
            horizon_cx + along[0] * chord_half,
            horizon_cy + along[1] * chord_half,
            fill=HORIZON_COLOR,
            width=line_width,
        )

    def draw_course_scale(self, cx: float, cy: float, r: float, s: float) -> None:
        inner = r - WHITE_RING_WIDTH * s
        self.canvas.create_oval(
            cx - r,
            cy - r,
            cx + r,
            cy + r,
            outline=BLACK,
            width=max(3, round(5.0 * s)),
        )
        self.canvas.create_oval(
            cx - inner,
            cy - inner,
            cx + inner,
            cy + inner,
            outline=INNER_CIRCLE_COLOR,
            width=max(2, round(3.0 * s)),
        )

        for index in range(len(COURSES)):
            degree = index * 22.5
            # The direction ticks now start at the outer rim and point
            # inwards, while retaining a clear gap before the blue circle.
            x1, y1 = polar(cx, cy, r - COURSE_TICK_OUTER_INSET * s, degree)
            x2, y2 = polar(cx, cy, r - COURSE_TICK_INNER_INSET * s, degree)
            self.canvas.create_line(
                x1,
                y1,
                x2,
                y2,
                fill=BLACK,
                width=max(3, round(5.2 * s)),
            )

        course_angle = self.course_index * 22.5
        tip = polar(cx, cy, r + 63 * s, course_angle)
        left = polar(cx, cy, r + 10.5 * s, course_angle - 3.15)
        right = polar(cx, cy, r + 10.5 * s, course_angle + 3.15)
        self.canvas.create_polygon(
            *tip,
            *left,
            *right,
            fill=RED,
            outline=RED,
        )

        direction_angle = self.direction_index * 22.5
        label_font_size = max(13, round(24 * s))
        # Text anchored on the left/right already grows away from the rim.
        # Compensate only for its vertical half-height, so every direction
        # keeps approximately the same small visible gap from the circle.
        radial_text_height = abs(math.cos(math.radians(direction_angle)))
        label_clearance = max(3.0, 6.0 * s)
        label_offset = label_clearance + radial_text_height * label_font_size * 0.78
        label_x, label_y = polar(cx, cy, r + label_offset, direction_angle)
        horizontal_direction = math.sin(math.radians(direction_angle))
        if horizontal_direction > 0.1:
            anchor = "w"
        elif horizontal_direction < -0.1:
            anchor = "e"
        else:
            anchor = "center"
        self.canvas.create_text(
            label_x,
            label_y,
            text=rotated_course(self.direction_index, self.compass_rotation_index),
            fill=RED,
            font=("Arial", label_font_size, "bold"),
            anchor=anchor,
            tags=("course_direction_label",),
        )

    def draw_pitch_scale(self, cx: float, cy: float, r: float, s: float) -> None:
        circle_radius = r - WHITE_RING_WIDTH * s
        maximum_offset = circle_radius
        font = self.pitch_number_font(0, s)

        for value in range(-90, 91, 5):
            y = cy - maximum_offset * value / 90.0
            labelled = value % 15 == 0
            inner = PITCH_TICK_INNER_OFFSET * s
            if labelled:
                outer = 55 * s
                if value == 0:
                    # The centre mark remains split around the aircraft hub,
                    # but each visible half is twice as long as the others.
                    outer = inner + 2 * (outer - inner)
                width = max(1, round(1.6 * s))
            else:
                outer = inner + PITCH_MINOR_TICK_LENGTH * s
                width = max(1, round(1.2 * s))

            self.canvas.create_line(
                cx - outer,
                y,
                cx - inner,
                y,
                fill=BLACK,
                width=width + 2,
            )
            self.canvas.create_line(
                cx + inner,
                y,
                cx + outer,
                y,
                fill=BLACK,
                width=width + 2,
            )
            self.canvas.create_line(
                cx - outer,
                y,
                cx - inner,
                y,
                fill="white",
                width=width,
            )
            self.canvas.create_line(
                cx + inner,
                y,
                cx + outer,
                y,
                fill="white",
                width=width,
            )
            if abs(value) in (15, 45, 75):
                text_y = y
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    self.canvas.create_text(
                        cx + dx,
                        text_y + dy,
                        text=str(abs(value)),
                        fill=BLACK,
                        font=font,
                    )
                self.canvas.create_text(
                    cx,
                    text_y,
                    text=str(abs(value)),
                    fill="white",
                    font=font,
                )

    def draw_roll_scale(self, cx: float, cy: float, r: float, s: float) -> None:
        circle_radius = r - WHITE_RING_WIDTH * s
        tick_outer_radius = circle_radius
        for degree in range(0, 360, 5):
            distance_from_pitch_90 = min(
                degree % 180,
                180 - degree % 180,
            )
            if distance_from_pitch_90 <= PITCH_90_CLEARANCE_DEGREES:
                continue
            major = degree % 15 == 0
            current_outer_radius = (
                tick_outer_radius
                if major
                else tick_outer_radius - ROLL_MINOR_RIM_GAP * s
            )
            tick_length = (
                ROLL_SCALE_DEPTH if major else ROLL_MINOR_SCALE_DEPTH
            ) * s
            x1, y1 = polar(cx, cy, current_outer_radius, degree)
            x2, y2 = polar(cx, cy, current_outer_radius - tick_length, degree)
            self.canvas.create_line(
                x1,
                y1,
                x2,
                y2,
                fill=ROLL_MAJOR_COLOR if major else ROLL_MINOR_COLOR,
                width=(
                    max(2, round(3.2 * s))
                    if major
                    else max(2, round(2.2 * s))
                ),
            )

        label_radius = circle_radius - ROLL_LABEL_INSET * s
        font = self.pitch_number_font(0, s)
        for degree in range(15, 360, 15):
            if degree == 180:
                continue
            value = degree if degree < 180 else 360 - degree
            if value not in (15, 45, 75, 105, 135, 165):
                continue
            x, y = polar(cx, cy, label_radius, degree)
            self.canvas.create_text(
                x,
                y,
                text=str(value),
                fill=BLACK,
                font=font,
            )

    def draw_airplane(self, cx: float, cy: float, s: float, roll: float) -> None:
        # Former black aircraft marker from the original version.  Its vertical
        # centre stroke is the aircraft fin, not a normal to the horizon.
        airplane_scale = 1.30 * s
        center = (110.0, 82.0)
        angle = math.radians(self.display_roll_angle(roll))
        cosine = math.cos(angle)
        sine = math.sin(angle)

        def point(x: float, y: float) -> tuple[float, float]:
            dx = (x - center[0]) * airplane_scale
            dy = (y - center[1]) * airplane_scale
            return (
                cx + dx * cosine - dy * sine,
                cy + dx * sine + dy * cosine,
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

        circle_points = [
            (
                110.0 + 23.0 * math.cos(math.tau * index / 48.0),
                82.0 + 21.0 * math.sin(math.tau * index / 48.0),
            )
            for index in range(49)
        ]
        body: list[float] = []
        for x, y in circle_points:
            body.extend(point(x, y))
        self.canvas.create_polygon(*body, fill="#dff1fb", outline="")
        # Extended wings stop shortly before the roll-number ring.
        line([(-34.0, 74.0), (80.0, 83.3)], 7.0)
        line([(140.0, 83.3), (254.0, 74.0)], 7.0)
        # The fin approaches the fuselage outline but does not enter the circle.
        line([(110.0, 33.0), (110.0, 54.0)], 7.0)
        line([(62.0, 81.6), (62.0, 108.0)], 5.0)
        line([(158.0, 81.6), (158.0, 108.0)], 5.0)
        # A clean fuselage: no internal black bar; the red pitch zero is drawn later.
        line(circle_points, 6.0)


def main() -> None:
    root = tk.Tk()
    OrientationTestV11(root)
    root.mainloop()


if __name__ == "__main__":
    main()
