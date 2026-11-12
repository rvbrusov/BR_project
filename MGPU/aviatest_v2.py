from __future__ import annotations

import importlib.util
import json
import math
import queue
import random
import sys
import threading
import time
import tkinter as tk
from dataclasses import asdict, dataclass, fields
from datetime import datetime
from pathlib import Path
from typing import Any

import orient_final as orientation


APP_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = Path(getattr(sys, "_MEIPASS", APP_DIR))
FIXED428_SOURCE = RUNTIME_DIR / "fixed428_app_2026-04-25_portable_build.py"
if not FIXED428_SOURCE.exists():
    FIXED428_SOURCE = APP_DIR / "fixed428_app_2026-04-25_portable_build.py"


def _load_fixed428():
    module_name = "_aviatest_fixed428"
    spec = importlib.util.spec_from_file_location(module_name, FIXED428_SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Не удалось загрузить основу приложения: {FIXED428_SOURCE}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


base = _load_fixed428()


_ORIENTATION_SAVE_LOCK = threading.Lock()


@dataclass
class OrientationConfig:
    stage_1_time_s: float = 120.0
    stage_2_time_s: float = 120.0
    stage_3_time_s: float = 120.0
    training_stage_1_time_s: float = 60.0
    training_stage_2_time_s: float = 60.0
    training_stage_3_time_s: float = 60.0

    def stage_time(self, stage: int, training: bool) -> float:
        prefix = "training_stage" if training else "stage"
        return max(0.1, float(getattr(self, f"{prefix}_{int(stage)}_time_s")))


def load_orientation_config(root: Path) -> OrientationConfig:
    path = Path(root) / "orientation_config.json"
    raw: dict[str, Any] = {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            raw = loaded
    except Exception:
        pass
    values: dict[str, float] = {}
    for field in fields(OrientationConfig):
        try:
            values[field.name] = max(0.1, float(raw.get(field.name, field.default)))
        except Exception:
            values[field.name] = float(field.default)
    return OrientationConfig(**values)


class _AviatestOrientationStyle:
    """Instrument appearance requested specifically for the integrated test."""

    _black = "#090909"
    _red = "#ed1717"
    _sky = "#91dff3"
    _ground = "#e4c1ac"
    _inner_circle = "#2f67a3"
    _white_ring_width = 48.0
    _test_block_width = 760
    _test_block_height = 530
    _stage_1_test_block_height = 760
    _test_circle_diameter = 430
    _course_letter_font_size = 20
    _test_field_top_crop = 30.0
    # Only numbered pitch marks may be generated.  Zero remains the centred
    # horizon and ±90 are identified by the full-colour fill; the thin 30/60
    # ticks are visual intermediates, never task answers.
    _allowed_pitch_values = (-90, -75, -45, -15, 0, 15, 45, 75, 90)
    _stage3_pitch_values = tuple(value for value in _allowed_pitch_values if abs(value) < 90)
    _allowed_roll_values = tuple(range(0, 181, 15))

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # V1.1, V2.1 and V3.1 each restore the legacy 620-pixel canvas width
        # near the end of their own initialisation.  Apply the integrated layout
        # only after that whole chain has finished, so all three stages retain it.
        super().__init__(*args, **kwargs)
        self.root.update_idletasks()
        content = getattr(self, "_orientation_content", self.canvas.master)
        answer_widgets = getattr(self, "_orientation_answer_widgets", None)
        if answer_widgets is None:
            answer_widgets = [
                widget
                for widget in content.winfo_children()
                if widget is not self.canvas
            ]
        if int(getattr(self, "final_stage_number", 0) or 0) in (2, 3) and hasattr(
            self,
            "_orientation_reference_answer_widget",
        ):
            # Stage 2 has two compact cash rows.  Reserve the same single-row
            # height used by stage 1 so both stages keep an identical dial size;
            # the normal outer safety allowance absorbs the second compact row.
            answer_height = self._orientation_reference_answer_widget.winfo_reqheight()
        else:
            answer_height = sum(widget.winfo_reqheight() for widget in answer_widgets)
        footer_height = sum(
            widget.winfo_reqheight()
            for widget in self.root.pack_slaves()
            if widget is not content
        )
        available_height = (
            self.root.winfo_screenheight() - answer_height - footer_height - 88
        )
        if int(getattr(self, "final_stage_number", 0) or 0) in (1, 2, 3):
            # The compact single-row answer area leaves enough vertical space
            # for a substantially larger first-stage instrument.
            field_height = max(
                470,
                min(self._stage_1_test_block_height, available_height),
            )
        else:
            field_height = max(470, min(self._test_block_height, available_height))
        self.canvas.configure(
            width=self._test_block_width,
            height=field_height,
        )
        self.root.update_idletasks()
        self.redraw()

    def build_test_ui(self) -> None:
        """Keep the white instrument field and answer block equally wide."""
        super().build_test_ui()
        self.canvas.configure(
            width=self._test_block_width,
            height=self._test_block_height,
        )

        content = self.canvas.master
        answer_widgets = [
            widget for widget in content.winfo_children() if widget is not self.canvas
        ]
        for widget in answer_widgets:
            if widget is self.canvas:
                continue
            try:
                if widget.winfo_manager() == "pack":
                    widget.pack_configure(fill="x")
            except tk.TclError:
                pass

        # Do not disable geometry propagation here: doing so collapses the
        # content frame to a one-pixel-high line because the frame has no fixed
        # height of its own.  The canvas supplies the shared width, while the
        # packed answer area keeps its natural height.

        # The canvas determines the content width; every answer area packed with
        # fill="x" therefore has exactly the same visible width on every stage.

    def new_task(self, _event: tk.Event | None = None) -> None:
        """Generate only numbered pitch positions plus the 0/90 endpoints."""
        super().new_task(_event)
        redraw = False
        stage_number = int(getattr(self, "final_stage_number", 0) or 0)
        allowed_pitch_values = self._stage3_pitch_values if stage_number == 3 else self._allowed_pitch_values
        if int(self.pitch) not in allowed_pitch_values:
            self.pitch = random.choice(allowed_pitch_values)
            redraw = True
        if int(self.roll) not in self._allowed_roll_values:
            self.roll = random.choice(self._allowed_roll_values)
            redraw = True

        # With a permanently vertical pitch ladder, a vertical horizon cannot
        # intersect an intermediate pitch mark.  Keep that one horizon angle
        # only for the centred or full-colour endpoint indications.
        display_roll = float(self.display_roll_angle(self.roll)) % 180.0
        if math.isclose(display_roll, 90.0, abs_tol=1e-9) and abs(self.pitch) not in (0, 90):
            self.pitch = 0 if stage_number == 3 else random.choice((-90, 0, 90))
            redraw = True
        if int(getattr(self, "final_stage_number", 0) or 0) in (1, 2):
            # Stages 1 and 2 never rotate the aircraft itself.  Store the
            # invariant as state as well as enforcing it during drawing below.
            self.airplane_roll = 0
        if redraw:
            self.draw()

    def display_roll_angle(self, roll: float) -> float:
        """Use the exact 15-degree value on every integrated stage."""
        return float(roll)

    def pitch_offset(self, pitch: float, radius: float) -> float:
        """Map every 15-degree pitch value directly to its vertical tick."""
        return radius * float(pitch) / 90.0

    def valid_pitch_answers(self) -> set[str]:
        """Accept exactly the signed scale values, with an unsigned zero."""
        values = self._stage3_pitch_values if int(getattr(self, "final_stage_number", 0) or 0) == 3 else self._allowed_pitch_values
        return {
            "0" if value == 0 else f"{value:+d}"
            for value in values
        }

    def draw(self) -> None:
        """Draw a larger circle while retaining clearance inside the canvas."""
        self.canvas.delete("all")
        width = max(1, self.canvas.winfo_width())
        height = max(1, self.canvas.winfo_height())
        stage_number = int(getattr(self, "final_stage_number", 0) or 0)
        if stage_number in (1, 2, 3):
            # The course triangle is the farthest element: its tip is 63
            # reference pixels outside the dial.  Account for that footprint
            # explicitly, so the circle occupies the maximum safe area without
            # clipping any direction marker at the canvas edges.
            footprint_factor = 1.0 + 2.0 * 63.0 / 620.0
            edge_margin = 8.0
            sizing_height = height + self._test_field_top_crop
            size = min(
                (width - 2.0 * edge_margin) / footprint_factor,
                (sizing_height - 2.0 * edge_margin) / footprint_factor,
            )
        else:
            # Keep the established geometry of stages 2 and 3 unchanged.
            size = min(self._test_circle_diameter, width - 300.0, height - 80.0)
        size = max(1.0, size)
        radius = size / 2.0
        cx = width / 2.0
        if stage_number in (1, 2, 3):
            # Render the same instrument as before, but remove a strip from the
            # top of its white field while preserving the lower alignment.
            cy = (height - self._test_field_top_crop) / 2.0
        else:
            cy = height / 2.0
        scale = size / 620.0

        self.draw_face(cx, cy, radius, scale)
        self.draw_course_scale(cx, cy, radius, scale)
        self.draw_roll_scale(cx, cy, radius, scale)
        self.draw_pitch_scale(cx, cy, radius, scale)
        if int(getattr(self, "final_stage_number", 0) or 0) in (1, 2):
            # Stages 1 and 2 assess course/pitch without aircraft-bank input.
            # Only the third stage may rotate the aircraft symbol itself.
            airplane_roll = 0.0
        else:
            airplane_roll = getattr(self, "airplane_roll", self.roll)
        self.draw_airplane(cx, cy, scale, airplane_roll)

    @staticmethod
    def pitch_number_font(_value: int, scale: float) -> tuple[str, int, str]:
        return ("Arial", max(12, round(25 * scale)), "bold")

    def maximize(self) -> None:
        """Make every embedded stage cover the underlying aviatest menu."""
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

    def _place_popup_above_answer_blocks(self, dialog: tk.Toplevel | None) -> None:
        """Keep transient dialogs in the upper-right, clear of every cash block."""
        if dialog is None:
            return
        try:
            dialog.update_idletasks()
            width = dialog.winfo_reqwidth()
            height = dialog.winfo_reqheight()
            x = self.root.winfo_rootx() + self.root.winfo_width() - width - 24
            y = self.root.winfo_rooty() + 18
            dialog.geometry(f"{width}x{height}+{max(0, x)}+{max(0, y)}")
            dialog.lift()
        except tk.TclError:
            pass

    def _keep_canvas_item_visible(self, item: int, padding: float = 5.0) -> None:
        """Move a canvas item just enough to keep its complete bbox visible."""
        bounds = self.canvas.bbox(item)
        if bounds is None:
            return
        left, top, right, bottom = bounds
        width = max(1, self.canvas.winfo_width())
        height = max(1, self.canvas.winfo_height())
        dx = 0.0
        dy = 0.0
        if left < padding:
            dx = padding - left
        elif right > width - padding:
            dx = width - padding - right
        if top < padding:
            dy = padding - top
        elif bottom > height - padding:
            dy = height - padding - bottom
        if dx or dy:
            self.canvas.move(item, dx, dy)

    def show_results_table(self) -> None:
        """Show results inside the white field, never on top of a cash block."""
        super().show_results_table()
        panel = getattr(self, "results_panel", None)
        if panel is None:
            return
        try:
            # The inherited stage implementations used different type sizes
            # for the same parts of their result tables.  Use one compact set
            # on all stages so the table fits below the pitch answer block.
            panel_children = panel.winfo_children()
            if len(panel_children) >= 4:
                panel_children[0].configure(
                    font=("Arial", 14, "bold"),
                    pady=7,
                )
                panel_children[1].configure(
                    font=("Arial", 10, "bold"),
                    pady=3,
                )
                table = panel_children[2]
                for cell in table.winfo_children():
                    row = int(cell.grid_info().get("row", 0))
                    cell.configure(
                        font=("Arial", 9, "bold" if row == 0 else "normal"),
                        pady=4,
                    )
                panel_children[-1].configure(
                    font=("Arial", 10, "bold"),
                    pady=6,
                )
            self.root.update_idletasks()
            root_x = self.root.winfo_rootx()
            root_y = self.root.winfo_rooty()
            canvas_x = self.canvas.winfo_rootx() - root_x
            canvas_y = self.canvas.winfo_rooty() - root_y
            panel_width = panel.winfo_reqwidth()
            panel_height = panel.winfo_reqheight()
            if hasattr(self, "pitch_title_label"):
                pitch_box = self.pitch_title_label.master
                pitch_right = pitch_box.winfo_rootx() - root_x + pitch_box.winfo_width()
                pitch_bottom = pitch_box.winfo_rooty() - root_y + pitch_box.winfo_height()
                x = max(5, pitch_right - panel_width)
                y = pitch_bottom + 14
            else:
                # Stage 1 has no pitch controls, but its results occupy the
                # same reserved lower-left zone used below that block on the
                # other stages.
                x = max(5, canvas_x - 18 - panel_width)
                footer_top = (
                    self.cancel_button.master.winfo_rooty() - root_y
                )
                y = max(8, footer_top - 16 - panel_height)
            # Clear the original ``rely=0.5`` option as well; Tk otherwise
            # adds half the window height to this absolute y coordinate.
            panel.place(
                x=x,
                y=y,
                relx=0.0,
                rely=0.0,
                anchor="nw",
            )
            panel.lift()
        except tk.TclError:
            pass

    def show_invalid_answer(self) -> None:
        super().show_invalid_answer()
        self._place_popup_above_answer_blocks(
            getattr(self, "invalid_answer_dialog", None)
        )

    def show_invalid_message(self, message: str, field: str) -> None:
        super().show_invalid_message(message, field)
        self._place_popup_above_answer_blocks(getattr(self, "invalid_dialog", None))

    def show_complete_dialog(self) -> None:
        super().show_complete_dialog()
        self._place_popup_above_answer_blocks(getattr(self, "complete_dialog", None))

    @staticmethod
    def _polar(
        cx: float,
        cy: float,
        radius: float,
        degrees: float,
    ) -> tuple[float, float]:
        angle = math.radians(degrees - 90.0)
        return cx + radius * math.cos(angle), cy + radius * math.sin(angle)

    def draw_face(self, cx: float, cy: float, r: float, s: float) -> None:
        inner = r - self._white_ring_width * s
        self.canvas.create_oval(
            cx - inner,
            cy - inner,
            cx + inner,
            cy + inner,
            fill=self._sky,
            outline="",
        )

        pitch_mark_offset = self.pitch_offset(self.pitch, inner)
        angle = math.radians(self.display_roll_angle(self.roll))
        cosine = math.cos(angle)

        if abs(float(self.pitch)) >= 90.0:
            # The ±90 positions have no tick or number: the complete blue or
            # brown fill is their only indication.
            offset = max(-inner, min(inner, pitch_mark_offset))
        else:
            # The pitch ladder is fixed vertically.  Offset the tilted horizon
            # so its intersection with that ladder lands exactly on the
            # selected numbered 15/45/75 mark (or the centred zero).  Using the
            # raw perpendicular
            # offset made tilted horizons appear between two valid marks.
            offset = pitch_mark_offset * cosine
        down_angle = angle + math.pi / 2.0
        half_arc = math.acos(max(-1.0, min(1.0, offset / inner)))
        ground_points: list[float] = []
        for step in range(121):
            arc_angle = down_angle - half_arc + 2.0 * half_arc * step / 120.0
            ground_points.extend(
                (cx + inner * math.cos(arc_angle), cy + inner * math.sin(arc_angle))
            )
        self.canvas.create_polygon(*ground_points, fill=self._ground, outline="")

        along = (math.cos(angle), math.sin(angle))
        down = (-math.sin(angle), math.cos(angle))
        chord_half = math.sqrt(max(0.0, inner * inner - offset * offset))
        horizon_cx = cx + down[0] * offset
        horizon_cy = cy + down[1] * offset
        # Draw only the horizon chord.  Its perpendicular/normal is omitted.
        self.canvas.create_line(
            horizon_cx - along[0] * chord_half,
            horizon_cy - along[1] * chord_half,
            horizon_cx + along[0] * chord_half,
            horizon_cy + along[1] * chord_half,
            fill="#123f73",
            width=max(2, round(3.0 * s)),
            tags=("horizon_line",),
        )

    def draw_course_scale(self, cx: float, cy: float, r: float, s: float) -> None:
        inner = r - self._white_ring_width * s
        self.canvas.create_oval(
            cx - r,
            cy - r,
            cx + r,
            cy + r,
            outline=self._black,
            width=max(3, round(5.0 * s)),
        )
        self.canvas.create_oval(
            cx - inner,
            cy - inner,
            cx + inner,
            cy + inner,
            outline=self._inner_circle,
            width=max(2, round(3.0 * s)),
        )

        for index in range(len(orientation.COURSES)):
            degree = index * 22.5
            x1, y1 = self._polar(cx, cy, r - 1.0 * s, degree)
            x2, y2 = self._polar(cx, cy, r - 36.0 * s, degree)
            self.canvas.create_line(
                x1,
                y1,
                x2,
                y2,
                fill=self._black,
                width=max(3, round(5.2 * s)),
            )

        course_angle = self.course_index * 22.5
        tip = self._polar(cx, cy, r + 63.0 * s, course_angle)
        left = self._polar(cx, cy, r + 10.5 * s, course_angle - 3.15)
        right = self._polar(cx, cy, r + 10.5 * s, course_angle + 3.15)
        if int(getattr(self, "final_stage_number", 0) or 0) in (1, 2, 3):
            # The white field is cropped at the top.  Keep only the extreme
            # vertex inside the canvas; the base remains attached to its scale
            # mark, so the pointer stays readable and does not cover the ring.
            tip = (tip[0], max(4.0, tip[1]))
        self.canvas.create_polygon(
            *tip,
            *left,
            *right,
            fill=self._red,
            outline=self._red,
        )

        direction_angle = self.direction_index * 22.5
        if int(getattr(self, "final_stage_number", 0) or 0) in (1, 2, 3):
            # Match the red course label to the letters in the stage-1 cash row.
            label_font_size = self._course_letter_font_size
        else:
            label_font_size = max(13, round(24 * s))
        radial_text_height = abs(math.cos(math.radians(direction_angle)))
        label_clearance = max(3.0, 6.0 * s)
        label_offset = label_clearance + radial_text_height * label_font_size * 0.78
        label_x, label_y = self._polar(cx, cy, r + label_offset, direction_angle)
        horizontal_direction = math.sin(math.radians(direction_angle))
        if horizontal_direction > 0.1:
            anchor = "w"
        elif horizontal_direction < -0.1:
            anchor = "e"
        else:
            anchor = "center"
        direction_name = orientation.COURSES[
            (self.direction_index - self.compass_rotation_index)
            % len(orientation.COURSES)
        ]
        label_item = self.canvas.create_text(
            label_x,
            label_y,
            text=direction_name,
            fill=self._red,
            font=("Arial", label_font_size, "bold"),
            anchor=anchor,
            tags=("course_direction_label",),
        )
        # Course names contain up to three Cyrillic letters.  At the cardinal
        # and diagonal extremes their actual rendered width can exceed the
        # radial estimate, so clamp the real text bbox on every side.
        self._keep_canvas_item_visible(label_item)

    def draw_pitch_scale(self, cx: float, cy: float, r: float, s: float) -> None:
        circle_radius = r - self._white_ring_width * s
        font = self.pitch_number_font(0, s)
        labelled_values = {15, 45, 75}

        # 90 degrees is intentionally represented by the solid sky/ground fill
        # alone, without a tick or a number.
        for value in range(-75, 76, 15):
            y = cy - circle_radius * value / 90.0
            major = abs(value) in labelled_values
            inner = 25.0 * s
            if major:
                outer = 68.0 * s
                width = max(4, round(5.5 * s))
            else:
                outer = inner + 29.0 * s
                width = max(3, round(3.2 * s))

            # Two extra canvas pixels leave the thinnest practical one-pixel
            # black border on either side of the white tick.
            outline_width = width + 2
            outline_color = self._black
            self.canvas.create_line(
                cx - outer,
                y,
                cx - inner,
                y,
                fill=outline_color,
                width=outline_width,
            )
            self.canvas.create_line(
                cx + inner,
                y,
                cx + outer,
                y,
                fill=outline_color,
                width=outline_width,
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
            if abs(value) in labelled_values:
                text_y = y
                outline_offset = 1
                for dx, dy in (
                    (-outline_offset, 0),
                    (outline_offset, 0),
                    (0, -outline_offset),
                    (0, outline_offset),
                ):
                    self.canvas.create_text(
                        cx + dx,
                        text_y + dy,
                        text=str(abs(value)),
                        fill=self._black,
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
        circle_radius = r - self._white_ring_width * s
        tick_outer_radius = circle_radius
        for degree in range(0, 360, 15):
            scale_value = degree % 90
            major = scale_value in {15, 45, 75}
            current_outer_radius = circle_radius
            tick_length = (36.0 if major else 20.0) * s
            if degree in {15, 165, 195, 345}:
                # These four marks point directly at the white 75-degree pitch
                # marks.  Shorten only them and preserve a visible gap.
                tick_length -= 7.0 * s
            x1, y1 = self._polar(cx, cy, current_outer_radius, degree)
            x2, y2 = self._polar(cx, cy, current_outer_radius - tick_length, degree)
            self.canvas.create_line(
                x1,
                y1,
                x2,
                y2,
                fill="#0d354d" if major else "#244d63",
                width=max(2, round((3.2 if major else 2.2) * s)),
            )

        label_radius = tick_outer_radius - 55.0 * s
        font = self.pitch_number_font(0, s)
        labelled_values = {15, 45, 75, 105, 135, 165}
        for degree in range(15, 360, 15):
            # Zero is at the top.  Values grow independently down the right and
            # left sides and meet at 180 degrees at the bottom.  Neither endpoint
            # is labelled.
            value = degree if degree < 180 else 360 - degree
            if value not in labelled_values:
                continue
            x, y = self._polar(cx, cy, label_radius, degree)
            if value in {15, 165}:
                # Keep the upper/lower roll numerals clear of the central
                # white pitch numerals and their horizontal marks.
                x += math.copysign(10.0 * s, x - cx)
                y += (2.0 if value == 15 else -2.0) * s
            self.canvas.create_text(
                x,
                y,
                text=str(value),
                fill=self._black,
                font=font,
            )

    def draw_airplane(self, cx: float, cy: float, s: float, roll: float) -> None:
        """Draw the white centre and two straight wings without stabilizers."""
        if int(getattr(self, "final_stage_number", 0) or 0) in (1, 2):
            # Enforce zero aircraft bank at the final rendering boundary.  This
            # protects stages 1 and 2 even if an inherited redraw passes the
            # horizon roll or stale airplane state by mistake.
            roll = 0.0
        airplane_scale = 1.30 * s
        center = (110.0, 82.0)
        angle = math.radians(self.display_roll_angle(roll))
        cosine = math.cos(angle)
        sine = math.sin(angle)

        def point(x: float, y: float) -> tuple[float, float]:
            dx = (x - center[0]) * airplane_scale
            dy = (y - center[1]) * airplane_scale
            return cx + dx * cosine - dy * sine, cy + dx * sine + dy * cosine

        def line(
            points: list[tuple[float, float]],
            width: float,
            tags: tuple[str, ...] = (),
        ) -> None:
            coordinates: list[float] = []
            for x, y in points:
                coordinates.extend(point(x, y))
            self.canvas.create_line(
                *coordinates,
                fill=self._black,
                width=max(2, width * airplane_scale),
                capstyle=tk.ROUND,
                joinstyle=tk.ROUND,
                tags=tags,
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
        self.canvas.create_polygon(*body, fill="white", outline="")
        # The wings share one axis, begin at the circle outline and nearly reach
        # the roll numerals.  They never pass through the inner circle.
        line(
            [(-34.0, 82.0), (87.0, 82.0)],
            7.0,
            ("airplane_wing",),
        )
        line(
            [(133.0, 82.0), (254.0, 82.0)],
            7.0,
            ("airplane_wing",),
        )
        # Keep the vertical fin and both landing-gear legs outside the circle.
        line([(110.0, 33.0), (110.0, 54.0)], 7.0)
        line([(62.0, 82.0), (62.0, 108.0)], 5.0)
        line([(158.0, 82.0), (158.0, 108.0)], 5.0)
        line(circle_points, 6.0)


class _IntegratedOrientationTimer:
    def update_timer(self) -> None:
        self.timer_after_id = None
        if self.test_complete:
            return
        elapsed = max(0.0, time.perf_counter() - self.test_started_at)
        limit = self.final_controller.orientation_config.stage_time(
            self.final_stage_number, self.final_training
        )
        self.draw_time_bar(min(1.0, elapsed / limit))
        if elapsed >= limit:
            if self.final_stage_number == 1:
                self.record_answer()
            self.finish_test()
        else:
            self.timer_after_id = self.root.after(100, self.update_timer)


class IntegratedOrientationStage1(
    _IntegratedOrientationTimer,
    _AviatestOrientationStyle,
    orientation.FinalStage1,
):
    def build_test_ui(self) -> None:
        """First-stage layout: maximum dial area and one compact answer row."""
        bg = "#f6f0d8"
        content = tk.Frame(self.root, bg=bg)
        content.pack(expand=True, pady=(8, 4))

        self.time_bar_canvas = tk.Canvas(
            self.root,
            width=96,
            height=320,
            bg=bg,
            highlightthickness=0,
        )
        self.time_bar_canvas.place(x=24, y=24)

        self.canvas = tk.Canvas(
            content,
            width=self._test_block_width,
            height=self._stage_1_test_block_height,
            bg="white",
            highlightthickness=0,
        )
        self.canvas.pack()
        self.canvas.bind("<Configure>", self.redraw)

        answer_row = tk.Frame(content, bg=bg)
        answer_row.pack(fill="x", pady=(4, 0))
        answer_row.grid_columnconfigure(0, weight=4, uniform="stage_1_answer")
        answer_row.grid_columnconfigure(1, weight=2, uniform="stage_1_answer")
        for column in range(2, 6):
            answer_row.grid_columnconfigure(column, weight=1, uniform="stage_1_answer")

        cash_font = ("Arial", self._course_letter_font_size, "bold")
        self.answer_label = tk.Label(
            answer_row,
            text="",
            bg="#cfe5b8",
            fg=self._black,
            font=cash_font,
            relief="solid",
            bd=2,
        )
        self.answer_label.grid(row=0, column=0, sticky="nsew", padx=(0, 2))

        tk.Label(
            answer_row,
            text="Курс",
            bg="#f3dc83",
            fg=self._black,
            font=cash_font,
            relief="solid",
            bd=2,
        ).grid(row=0, column=1, sticky="nsew")

        self.letter_buttons = []
        for column, letter in enumerate(("С", "Ю", "З", "В"), start=2):
            button = tk.Button(
                answer_row,
                text=letter,
                command=lambda value=letter: self.select_letter(value),
                bg="white",
                activebackground="#ffd900",
                fg=self._black,
                font=cash_font,
                bd=2,
                relief="raised",
                pady=0,
                highlightthickness=0,
                cursor="hand2",
            )
            button.grid(row=0, column=column, sticky="nsew")
            self.letter_buttons.append(button)

        footer = tk.Frame(self.root, bg=bg)
        footer.pack(side="bottom", fill="x", padx=28, pady=(4, 16))
        for column in range(3):
            footer.grid_columnconfigure(column, weight=1)
        common = dict(
            font=("Arial", 18, "bold"),
            width=12,
            padx=10,
            pady=6,
            bd=3,
            relief="raised",
            cursor="hand2",
        )
        self.cancel_button = tk.Button(
            footer,
            text="Отмена",
            command=self.cancel_answer,
            bg="#f2d64b",
            activebackground="#e3c12d",
            **common,
        )
        self.cancel_button.grid(row=0, column=0, sticky="w")
        self.next_button = tk.Button(
            footer,
            text="Далее",
            command=self.next_task,
            bg="#58cc63",
            activebackground="#43b84f",
            **common,
        )
        self.next_button.grid(row=0, column=1)
        self.exit_button = tk.Button(
            footer,
            text="Выход",
            command=self.exit_app,
            bg="#d95a5a",
            activebackground="#b93c3c",
            fg="white",
            **common,
        )
        self.exit_button.grid(row=0, column=2, sticky="e")


class IntegratedOrientationStage2(
    _IntegratedOrientationTimer,
    _AviatestOrientationStyle,
    orientation.FinalStage2,
):
    def draw_pitch_scale(self, cx: float, cy: float, r: float, s: float) -> None:
        """Keep the pitch ladder vertical regardless of horizon bank."""
        _AviatestOrientationStyle.draw_pitch_scale(self, cx, cy, r, s)

    def build_test_ui(self) -> None:
        """Compact stage-2/3 layout with side controls and cash rows below."""
        bg = "#f6f0d8"
        content = tk.Frame(self.root, bg=bg)
        content.pack(expand=True, pady=(8, 4))
        self._orientation_content = content

        self.time_bar_canvas = tk.Canvas(
            self.root,
            width=96,
            height=320,
            bg=bg,
            highlightthickness=0,
        )
        self.time_bar_canvas.place(x=24, y=24)

        body = tk.Frame(content, bg=bg)
        body.pack()

        has_roll_controls = int(getattr(self, "answer_stage", 2) or 2) >= 3
        # Stage 2 has free space on the right.  Use part of it to increase the
        # clearance between the pitch controls and left-side course letters.
        pitch_gap = 18 if has_roll_controls else 36
        body.grid_columnconfigure(0, minsize=210 + pitch_gap)
        pitch_box = tk.Frame(body, bg=bg)
        pitch_box.grid(row=0, column=0, padx=(0, pitch_gap), sticky="ew")
        self.pitch_title_label = tk.Label(
            pitch_box,
            text="ТАНГАЖ",
            bg="#f3dc83",
            fg=self._black,
            font=("Arial", self._course_letter_font_size, "bold"),
            relief="solid",
            bd=2,
            pady=8,
        )
        self.pitch_title_label.pack(fill="x")

        self.pitch_input_frame = tk.Frame(pitch_box, bg="#cfe5b8")
        self.pitch_input_frame.pack(fill="x", pady=(2, 2))
        self.pitch_input_frame.grid_columnconfigure(0, weight=1)
        self.pitch_input_frame.grid_columnconfigure(1, weight=3)
        self.pitch_sign_label = tk.Label(
            self.pitch_input_frame,
            text="",
            bg="#cfe5b8",
            fg=self._black,
            font=("Arial", self._course_letter_font_size, "bold"),
            relief="solid",
            bd=2,
        )
        self.pitch_sign_label.grid(row=0, column=0, sticky="nsew")
        self.pitch_digits_label = tk.Label(
            self.pitch_input_frame,
            text="",
            bg="#cfe5b8",
            fg=self._black,
            font=("Arial", self._course_letter_font_size, "bold"),
            relief="solid",
            bd=2,
        )
        self.pitch_digits_label.grid(row=0, column=1, sticky="nsew")

        self.pitch_sign_buttons = []
        for sign, caption in (("+", "кабрирование"), ("-", "пикирование")):
            button = tk.Button(
                pitch_box,
                text=caption,
                command=lambda value=sign: self.select_pitch_sign(value),
                bg="white",
                activebackground="#ffd900",
                fg=self._black,
                font=("Arial", self._course_letter_font_size, "bold"),
                bd=2,
                pady=0,
                highlightthickness=0,
                cursor="hand2",
            )
            button.pack(fill="x")
            self.pitch_sign_buttons.append(button)
        main_column = tk.Frame(body, bg=bg)
        main_column.grid(row=0, column=1, sticky="n")
        self.roll_direction_buttons = []
        if has_roll_controls:
            # Mirror the complete left-side footprint around the centred dial.
            body.grid_columnconfigure(2, minsize=228)
            roll_box = tk.Frame(body, bg=bg)
            roll_box.grid(row=0, column=2, padx=(18, 0), sticky="ew")
            self.roll_title_label = tk.Label(
                roll_box,
                text="КРЕН",
                bg="#f3dc83",
                fg=self._black,
                font=("Arial", self._course_letter_font_size, "bold"),
                relief="solid",
                bd=2,
                pady=8,
            )
            self.roll_title_label.pack(fill="x")

            self.roll_input_frame = tk.Frame(roll_box, bg="#cfe5b8")
            self.roll_input_frame.pack(fill="x", pady=(2, 2))
            self.roll_input_frame.grid_columnconfigure(0, weight=1)
            self.roll_input_frame.grid_columnconfigure(1, weight=3)
            self.roll_direction_label = tk.Label(
                self.roll_input_frame,
                text="",
                bg="#cfe5b8",
                fg=self._black,
                font=("Arial", self._course_letter_font_size, "bold"),
                relief="solid",
                bd=2,
            )
            self.roll_direction_label.grid(row=0, column=0, sticky="nsew")
            self.roll_digits_label = tk.Label(
                self.roll_input_frame,
                text="",
                bg="#cfe5b8",
                fg=self._black,
                font=("Arial", self._course_letter_font_size, "bold"),
                relief="solid",
                bd=2,
            )
            self.roll_digits_label.grid(row=0, column=1, sticky="nsew")

            for direction, caption in (("П", "правый"), ("Л", "левый")):
                button = tk.Button(
                    roll_box,
                    text=caption,
                    command=lambda value=direction: self.select_roll_direction(value),
                    bg="white",
                    activebackground="#ffd900",
                    fg=self._black,
                    font=("Arial", self._course_letter_font_size, "bold"),
                    bd=2,
                    pady=0,
                    highlightthickness=0,
                    cursor="hand2",
                )
                button.pack(fill="x")
                self.roll_direction_buttons.append(button)
        else:
            # Balance the pitch panel on the opposite side.  The main white
            # field, and therefore the dial itself, shares the screen centre
            # with stage 1 even though stage 2 has no roll controls.
            tk.Frame(body, bg=bg, width=210, height=1).grid(row=0, column=2)
        self.canvas = tk.Canvas(
            main_column,
            width=self._test_block_width,
            height=self._stage_1_test_block_height,
            bg="white",
            highlightthickness=0,
        )
        self.canvas.pack()
        self.canvas.bind("<Configure>", self.redraw)

        course_row = tk.Frame(main_column, bg=bg)
        course_row.pack(fill="x", pady=(3, 0))
        course_row.grid_columnconfigure(0, weight=4, uniform="stage_2_course")
        course_row.grid_columnconfigure(1, weight=2, uniform="stage_2_course")
        for column in range(2, 6):
            course_row.grid_columnconfigure(column, weight=1, uniform="stage_2_course")

        compact_font = ("Arial", self._course_letter_font_size, "bold")
        self.course_answer_label = tk.Label(
            course_row,
            text="",
            bg="#cfe5b8",
            fg=self._black,
            font=compact_font,
            relief="solid",
            bd=2,
        )
        self.course_answer_label.grid(row=0, column=0, sticky="nsew", padx=(0, 2))
        tk.Label(
            course_row,
            text="Курс",
            bg="#f3dc83",
            fg=self._black,
            font=compact_font,
            relief="solid",
            bd=2,
        ).grid(row=0, column=1, sticky="nsew")

        self.course_letter_buttons = []
        for column, letter in enumerate(("С", "Ю", "З", "В"), start=2):
            button = tk.Button(
                course_row,
                text=letter,
                command=lambda value=letter: self.select_course_letter(value),
                bg="white",
                activebackground="#ffd900",
                fg=self._black,
                font=compact_font,
                bd=2,
                pady=0,
                highlightthickness=0,
                cursor="hand2",
            )
            button.grid(row=0, column=column, sticky="nsew")
            self.course_letter_buttons.append(button)

        self.numeric_keypad = tk.Frame(main_column, bg=bg)
        self.numeric_keypad.pack(fill="x")
        self.pitch_digit_buttons = []
        for column, digit in enumerate("1234567890"):
            self.numeric_keypad.grid_columnconfigure(
                column,
                weight=1,
                uniform="stage_2_digits",
            )
            button = tk.Button(
                self.numeric_keypad,
                text=digit,
                command=lambda value=digit: self.select_numeric_digit(value),
                bg="white",
                activebackground="#ffd900",
                fg=self._black,
                font=compact_font,
                bd=2,
                pady=0,
                highlightthickness=0,
                cursor="hand2",
            )
            button.grid(row=0, column=column, sticky="nsew")
            self.pitch_digit_buttons.append(button)

        self._orientation_answer_widgets = (course_row, self.numeric_keypad)
        self._orientation_reference_answer_widget = course_row

        footer = tk.Frame(self.root, bg=bg)
        footer.pack(side="bottom", fill="x", padx=28, pady=(4, 16))
        for column in range(3):
            footer.grid_columnconfigure(column, weight=1)
        common = dict(
            font=("Arial", 18, "bold"),
            width=12,
            padx=10,
            pady=6,
            bd=3,
            relief="raised",
            cursor="hand2",
        )
        self.cancel_button = tk.Button(
            footer,
            text="Отмена",
            command=self.reset_answers,
            bg="#f2d64b",
            activebackground="#e3c12d",
            **common,
        )
        self.cancel_button.grid(row=0, column=0, sticky="w")
        self.next_button = tk.Button(
            footer,
            text="Далее",
            command=self.next_task,
            bg="#58cc63",
            activebackground="#43b84f",
            **common,
        )
        self.next_button.grid(row=0, column=1)
        self.exit_button = tk.Button(
            footer,
            text="Выход",
            command=self.exit_app,
            bg="#d95a5a",
            activebackground="#b93c3c",
            fg="white",
            **common,
        )
        self.exit_button.grid(row=0, column=2, sticky="e")


class IntegratedOrientationStage3(
    _IntegratedOrientationTimer,
    _AviatestOrientationStyle,
    orientation.FinalStage3,
):
    build_test_ui = IntegratedOrientationStage2.build_test_ui
    # Use the same horizon-aligned pitch ladder as stage 2.  Stage 3 still
    # retains its independently generated aircraft bank for the roll answer.
    draw_pitch_scale = IntegratedOrientationStage2.draw_pitch_scale


class IntegratedOrientationApp(orientation.OrientFinalApp):
    stage_classes = (
        IntegratedOrientationStage1,
        IntegratedOrientationStage2,
        IntegratedOrientationStage3,
    )

    def __init__(self, root: tk.Toplevel, config: OrientationConfig) -> None:
        self.orientation_config = config
        self.integrated_completed = False
        super().__init__(root)

    def sequence_finished(self) -> None:
        if self.active_training:
            self.active_stage_number = 0
            self.show_instruction_page()
            return
        self.active_stage_number = 0
        self.integrated_completed = len(self.stage_results.get("test", [])) == 3
        self.shutdown()


def _participant(session: Any) -> dict[str, Any]:
    data = {
        "name": getattr(session, "name", ""),
        "age": getattr(session, "age", ""),
        "gender": getattr(session, "gender", ""),
    }
    for name in ("flight_hours", "aircraft_type", "education", "position", "profession"):
        value = getattr(session, name, "")
        if value not in (None, ""):
            data[name] = value
    return data


def _orientation_stage_summary(stage_item: dict[str, Any]) -> dict[str, Any]:
    rows = [row for row in stage_item.get("results", []) if isinstance(row, dict)]
    total = len(rows)
    correct = sum(bool(row.get("is_correct")) for row in rows)
    elapsed = max(0.0, float(stage_item.get("elapsed_seconds", 0.0) or 0.0))
    return {
        "stage": int(stage_item.get("stage", 0) or 0),
        "tasks": total,
        "correct": correct,
        "incorrect": max(0, total - correct),
        "accuracy_pct": round(100.0 * correct / total, 2) if total else 0.0,
        "elapsed_seconds": round(elapsed, 2),
        "average_seconds": round(elapsed / total, 2) if total else 0.0,
        "results": rows,
    }


def _build_orientation_payload(owner: Any, session: Any, app: IntegratedOrientationApp) -> dict[str, Any]:
    stage_items = sorted(
        app.stage_results.get("test", []), key=lambda item: int(item.get("stage", 0))
    )
    stages = {
        str(item["stage"]): item
        for item in (_orientation_stage_summary(stage) for stage in stage_items)
    }
    total_tasks = sum(int(item["tasks"]) for item in stages.values())
    total_correct = sum(int(item["correct"]) for item in stages.values())
    payload = {
        "test_code": "B",
        "test_label": base.TEST_LABELS["B"],
        "completed": bool(app.integrated_completed),
        "completed_at": datetime.now().isoformat(timespec="seconds"),
        "session_id": getattr(session, "session_id", ""),
        "participant": _participant(session),
        "stages": stages,
        "summary": {
            "total_tasks": total_tasks,
            "correct": total_correct,
            "incorrect": max(0, total_tasks - total_correct),
            "accuracy_pct": round(100.0 * total_correct / total_tasks, 2) if total_tasks else 0.0,
            "total_time_s": round(sum(float(item["elapsed_seconds"]) for item in stages.values()), 2),
            "calculation_version": "aviatest_v2_orientation_summary_v1",
        },
    }
    return payload


def _run_orientation(owner: Any, session: Any) -> dict[str, Any]:
    owner.set_enabled(False)
    window = tk.Toplevel(owner.root)
    window.transient(owner.root)
    app = IntegratedOrientationApp(window, load_orientation_config(owner.base_dir))
    try:
        owner.root.wait_window(window)
    finally:
        try:
            owner.root.deiconify()
            owner.open_fullscreen()
            owner.root.lift()
            owner.root.focus_force()
        except Exception:
            pass
        owner.set_enabled(True)

    result = {
        "completed": bool(app.integrated_completed),
        "stages": list(app.stage_results.get("test", [])),
    }
    if app.stage_results.get("test"):
        result["persistence_payload"] = _build_orientation_payload(owner, session, app)
    return result


def _schedule_orientation_save(
    owner: Any,
    profile: Any,
    session: Any,
    payload: dict[str, Any],
    completed: bool,
) -> None:
    """Persist orientation results without blocking Tk's event loop."""
    outcome: queue.Queue[tuple[dict[str, Any] | None, Exception | None]] = queue.Queue(maxsize=1)
    owner._aviatest_orientation_save_pending = True

    try:
        button = owner.menu_buttons.get("B")
        if button is not None:
            button.configure(state=tk.DISABLED, text="ТЕСТ B\nСОХРАНЕНИЕ…")
    except Exception:
        pass

    def save_worker() -> None:
        saved_payload: dict[str, Any] | None = None
        error: Exception | None = None
        try:
            with _ORIENTATION_SAVE_LOCK:
                saved_payload = dict(payload)
                saved_payload["result_path"] = base.save_method_payload(
                    owner.base_dir,
                    "B",
                    saved_payload.get("session_id") or "session",
                    saved_payload,
                )
                owner.progress_store.save_test_result(profile, "B", saved_payload)
                if completed:
                    owner.progress_store.mark_completed(profile, "B")
                _export_integrated_payload(owner.base_dir, saved_payload)
        except Exception as exc:
            error = exc
        outcome.put((saved_payload, error))

    threading.Thread(
        target=save_worker,
        name="aviatest-orientation-save",
        daemon=True,
    ).start()

    def poll_save() -> None:
        try:
            saved_payload, error = outcome.get_nowait()
        except queue.Empty:
            try:
                owner.root.after(75, poll_save)
            except tk.TclError:
                pass
            return

        owner._aviatest_orientation_save_pending = False
        try:
            owner.refresh_menu_state()
            owner.root.update_idletasks()
        except Exception:
            return

        if error is not None:
            try:
                owner.logger.log_event(
                    session,
                    event_type="menu_event",
                    screen="test_menu",
                    test_name="test_b",
                    action="save_failed",
                    note=f"{type(error).__name__}: {error}",
                )
                base.messagebox.showerror(
                    "Ошибка сохранения",
                    "Результаты авиагоризонта не удалось сохранить. "
                    "Подробности записаны в журнал.",
                )
            except Exception:
                pass
            return

        if completed and saved_payload is not None:
            try:
                owner.logger.log_event(
                    session,
                    event_type="menu_event",
                    screen="test_menu",
                    test_name="test_b",
                    action="marked_completed",
                    note=f"{base.TEST_LABELS['B']} завершён и сохранён.",
                )
            except Exception:
                pass

    owner.root.after(75, poll_save)


def _shifted_payload(owner: Any, session: Any, result: dict, code: str, kind: str) -> dict:
    payload: dict[str, Any] = {
        "test_code": code,
        "test_label": base.TEST_LABELS[code],
        "completed": bool(result.get("completed")),
        "completed_at": datetime.now().isoformat(timespec="seconds"),
        "session_id": getattr(session, "session_id", ""),
        "participant": _participant(session),
        "summary": result.get("summary", {}),
    }
    if kind == "memory":
        payload["cycles"] = result.get("cycles", [])
    elif kind == "count":
        payload["stages"] = result.get("stages", {})
    else:
        payload["tasks"] = result.get("tasks", [])
    payload["result_path"] = base.save_method_payload(
        owner.base_dir, code, payload["session_id"] or "session", payload
    )
    return payload


def _run_shifted_method(owner: Any, session: Any, code: str) -> dict:
    if code == "C":
        cfg = base.load_method_b_config(owner.base_dir)
        factory = lambda: base.MethodBWindow(owner.root, session, owner.logger, owner.base_dir, cfg).run()
        kind = "memory"
    elif code == "D":
        cfg = base.load_method_c_config(owner.base_dir)
        factory = lambda: base.MethodCWindow(owner.root, session, owner.logger, owner.base_dir, cfg).run()
        kind = "count"
    else:
        cfg = base.load_method_d_config(owner.base_dir)
        factory = lambda: base.MethodDWindow(owner.root, session, owner.logger, owner.base_dir, cfg).run()
        kind = "patterns"
    result = base._run_modal_method(owner, factory)
    if result.get("completed"):
        payload = _shifted_payload(owner, session, result, code, kind)
        owner.progress_store.save_test_result(owner.current_profile, code, payload)
        _export_integrated_payload(owner.base_dir, payload)
    return result


def _launch_test(self, code: str) -> None:
    if not self.current_profile or not self.current_session or code not in base.TEST_ORDER:
        return
    completed = self.progress_store.get_progress(self.current_profile).get("completed_tests", [])
    next_code = self.progress_store.next_test_code(self.current_profile)
    researcher = bool(getattr(self, "researcher_mode_enabled", False))
    if not researcher and code != next_code:
        if code in completed:
            base.messagebox.showinfo("Уже пройдено", f"{base.TEST_LABELS[code]} уже пройден.")
        else:
            base.messagebox.showwarning("Порядок тестов", f"Сейчас доступен только {base.TEST_LABELS[next_code]}.")
        return
    self.logger.log_event(
        self.current_session,
        event_type="menu_event",
        screen="test_menu",
        test_name=f"test_{code.lower()}",
        action="launch_requested",
        note=base.TEST_DESCRIPTIONS[code],
    )
    if code == "A":
        result = self.run_method_a(self.current_session)
    elif code == "B":
        result = _run_orientation(self, self.current_session)
    else:
        result = _run_shifted_method(self, self.current_session, code)

    if code == "B" and isinstance(result.get("persistence_payload"), dict):
        # Return control to Tk immediately.  The B result, progress file and
        # integrated workbook are written by one serialized background job.
        self.refresh_menu_state()
        if result.get("completed"):
            self.show_test_completed_dialog("B")
        _schedule_orientation_save(
            self,
            self.current_profile,
            self.current_session,
            result["persistence_payload"],
            bool(result.get("completed")),
        )
        return

    if result.get("completed"):
        self.progress_store.mark_completed(self.current_profile, code)
        self.logger.log_event(
            self.current_session,
            event_type="menu_event",
            screen="test_menu",
            test_name=f"test_{code.lower()}",
            action="marked_completed",
            note=f"{base.TEST_LABELS[code]} завершён и сохранён.",
        )
        self.refresh_menu_state()
        self.show_test_completed_dialog(code)
    else:
        self.refresh_menu_state()


def _replace_widget_text(widget: tk.Misc, old: str, new: str) -> None:
    try:
        text = str(widget.cget("text"))
        if old in text:
            widget.configure(text=text.replace(old, new))
    except Exception:
        pass
    for child in widget.winfo_children():
        _replace_widget_text(child, old, new)


def _shift_window_labels(method_name: str, old: str, new: str) -> None:
    cls = getattr(base, method_name)
    previous = cls._build_ui

    def wrapped(self):
        result = previous(self)
        try:
            self.win.title(str(self.win.title()).replace(old, new))
            _replace_widget_text(self.win, old, new)
        except Exception:
            pass
        return result

    cls._build_ui = wrapped


def _show_orientation_results(self, payload: dict) -> None:
    top, outer = base._open_results_top(self, "Результаты — Тест B. Пространственная ориентация")
    participant = payload.get("participant", {}) if isinstance(payload.get("participant"), dict) else {}
    stages = payload.get("stages", {}) if isinstance(payload.get("stages"), dict) else {}
    summary = payload.get("summary", {}) if isinstance(payload.get("summary"), dict) else {}
    header = tk.Frame(outer, bg="#ffffff", highlightthickness=1, highlightbackground="#d8e1ec")
    header.pack(fill="x", padx=24, pady=(24, 10))
    tk.Frame(header, bg="#67a9ff", height=6).pack(fill="x")
    body = tk.Frame(header, bg="#ffffff")
    body.pack(fill="x", padx=22, pady=14)
    tk.Label(body, text="Тест B   Пространственная ориентация (авиагоризонт)", bg="#ffffff", fg="#102744", font=("Times New Roman", 28, "bold")).pack(anchor="w")
    tk.Label(body, text=f"{participant.get('name', '')}, {participant.get('age', '')} лет. Общая точность: {float(summary.get('accuracy_pct', 0.0) or 0.0):.1f}%.", bg="#ffffff", fg="#5a6678", font=("Arial", 10, "bold")).pack(anchor="w", pady=(4, 0))
    cards = tk.Frame(outer, bg="#eef3f8")
    cards.pack(fill="x", padx=24, pady=(0, 12))
    titles = ("Курс", "Курс и тангаж", "Курс, тангаж и крен")
    colors = ("#67a9ff", "#53c26b", "#c98cff")
    for index in range(3):
        item = stages.get(str(index + 1), {}) if isinstance(stages, dict) else {}
        cards.grid_columnconfigure(index, weight=1, uniform="orientation_results")
        card = tk.Frame(cards, bg="#ffffff", highlightthickness=1, highlightbackground="#d8e1ec")
        card.grid(row=0, column=index, sticky="nsew", padx=(0 if index == 0 else 3, 0))
        tk.Frame(card, bg=colors[index], height=5).pack(fill="x")
        tk.Label(card, text=f"{float(item.get('accuracy_pct', 0.0) or 0.0):.0f}%", bg="#ffffff", fg="#102744", font=("Arial", 27, "bold")).pack(pady=(10, 2))
        tk.Label(card, text=titles[index], bg="#ffffff", fg="#425065", font=("Arial", 12, "bold"), wraplength=320).pack(padx=8)
        tk.Label(card, text=f"Верно {int(item.get('correct', 0) or 0)} из {int(item.get('tasks', 0) or 0)} · {float(item.get('elapsed_seconds', 0.0) or 0.0):.1f} с", bg="#ffffff", fg="#657385", font=("Arial", 10)).pack(pady=(4, 12))
    table = tk.Frame(outer, bg="#ffffff", highlightthickness=1, highlightbackground="#9c9c9c")
    table.pack(fill="x", padx=24, pady=(0, 24))
    headings = ("Показатель", "Этап 1", "Этап 2", "Этап 3")
    for col, text in enumerate(headings):
        table.grid_columnconfigure(col, weight=2 if col == 0 else 1)
        tk.Label(table, text=text, bg="#ffd400", font=("Arial", 11, "bold"), bd=1, relief="solid", pady=7).grid(row=0, column=col, sticky="nsew")
    metrics = (
        ("Заданий", "tasks", "{}"),
        ("Верных ответов", "correct", "{}"),
        ("Ошибок", "incorrect", "{}"),
        ("Точность", "accuracy_pct", "{:.1f}%"),
        ("Время", "elapsed_seconds", "{:.1f} с"),
        ("Среднее время ответа", "average_seconds", "{:.1f} с"),
    )
    for row, (label, key, fmt) in enumerate(metrics, 1):
        values = [label]
        for stage in range(1, 4):
            value = stages.get(str(stage), {}).get(key, 0)
            values.append(fmt.format(value))
        for col, value in enumerate(values):
            tk.Label(table, text=value, bg="#effff4" if col == 0 else "#ffffff", fg="#102744", font=("Arial", 10, "bold" if col == 0 else "normal"), bd=1, relief="solid", padx=7, pady=6).grid(row=row, column=col, sticky="nsew")


def _call_shifted_result(self, code: str, payload: dict) -> None:
    mapping = {
        "C": (self.show_method_b_results, "Тест B", "Тест C"),
        "D": (self.show_method_c_results, "Тест C", "Тест D"),
        "E": (self.show_method_d_results, "Тест D", "Тест E"),
    }
    handler, old, new = mapping[code]
    before = set(self.root.winfo_children())
    handler(payload)
    for window in set(self.root.winfo_children()) - before:
        if isinstance(window, tk.Toplevel):
            try:
                window.title(str(window.title()).replace(old, new))
            except Exception:
                pass
            _replace_widget_text(window, old, new)


def _view_results(self, code: str) -> None:
    if not self.current_profile:
        return
    payload = self.progress_store.get_test_result(self.current_profile, code)
    if not payload:
        base.messagebox.showinfo("Результаты", f"Для {base.TEST_LABELS[code]} пока нет сохранённых результатов.")
        return
    if code == "A":
        self.show_method_a_results(payload)
    elif code == "B":
        _show_orientation_results(self, payload)
    else:
        _call_shifted_result(self, code, payload)


def _collect_all_values(self, profile=None) -> dict[str, list[float]]:
    profile = profile or self.current_profile
    if not profile:
        return {}
    payloads = {code: self.progress_store.get_test_result(profile, code) or {} for code in base.TEST_ORDER}
    values = {code: [0.0, 0.0, 0.0] for code in base.TEST_ORDER}
    a = payloads["A"]
    a_summary = a.get("summary", {}) if isinstance(a.get("summary"), dict) else {}
    values["A"] = [float(a_summary.get(key, 0.0) or 0.0) for key in ("tmin_a", "tmedio_a", "tmax_a")]
    if values["A"] == [0.0, 0.0, 0.0]:
        reports = a.get("reports", []) if isinstance(a.get("reports"), list) else []
        values["A"] = [float(reports[i].get("stability_pct", 0.0) or 0.0) / 100.0 if i < len(reports) else 0.0 for i in range(3)]
    b_stages = payloads["B"].get("stages", {}) if isinstance(payloads["B"].get("stages"), dict) else {}
    values["B"] = [float(b_stages.get(str(i), {}).get("accuracy_pct", 0.0) or 0.0) / 100.0 for i in range(1, 4)]
    c_summary = payloads["C"].get("summary", {}) if isinstance(payloads["C"].get("summary"), dict) else {}
    values["C"] = [float(c_summary.get(key, 0.0) or 0.0) for key in ("tmin_b", "tmedio_b", "tmax_b")]
    d_summary = payloads["D"].get("summary", {}) if isinstance(payloads["D"].get("summary"), dict) else {}
    values["D"] = [float(d_summary.get(key, 0.0) or 0.0) for key in ("tmin_c", "tmedio_c", "tmax_c")]
    e_summary = payloads["E"].get("summary", {}) if isinstance(payloads["E"].get("summary"), dict) else {}
    values["E"] = [float(e_summary.get(key, 0.0) or 0.0) for key in ("tmin_d", "tmedio_d", "tmax_d")]
    return values


def _show_all_tests_results(self) -> None:
    if not self.current_profile:
        return
    values = _collect_all_values(self, self.current_profile)
    top, outer = base._open_results_top(self, "Итоговые результаты по всем тестам")
    header = tk.Frame(outer, bg="#ffffff", highlightthickness=1, highlightbackground="#d8e1ec")
    header.pack(fill="x", padx=24, pady=(24, 12))
    tk.Frame(header, bg="#6b7dff", height=6).pack(fill="x")
    tk.Label(header, text="Итоговые результаты по всем тестам", bg="#ffffff", fg="#102744", font=("Times New Roman", 28, "bold")).pack(anchor="w", padx=20, pady=(14, 2))
    tk.Label(header, text=f"{self.current_profile.name}, {self.current_profile.age} лет, {self.current_profile.gender}", bg="#ffffff", fg="#5a6678", font=("Arial", 11, "bold")).pack(anchor="w", padx=20, pady=(0, 14))
    table = tk.Frame(outer, bg="#ffffff", highlightthickness=1, highlightbackground="#123747")
    table.pack(fill="x", padx=24, pady=(0, 12))
    headings = ("Уровень", "A · Слежение", "B · Авиагоризонт", "C · Память", "D · Счёт", "E · Закономерности")
    for col, text in enumerate(headings):
        table.grid_columnconfigure(col, weight=1)
        tk.Label(table, text=text, bg="#c9ffff", fg="#102744", font=("Arial", 12, "bold"), bd=1, relief="solid", padx=6, pady=12, wraplength=220).grid(row=0, column=col, sticky="nsew")
    for row, level in enumerate(("Min", "Med", "Max"), 1):
        tk.Label(table, text=level, bg="#c9ffff", fg="#102744", font=("Arial", 14, "bold"), bd=1, relief="solid", pady=18).grid(row=row, column=0, sticky="nsew")
        for col, code in enumerate(base.TEST_ORDER, 1):
            value = float(values.get(code, [0.0, 0.0, 0.0])[row - 1])
            color = base._fixed376_cell_color(value)
            tk.Label(table, text=f"{value:.2f}", bg=color, fg="#102744", font=("Arial", 16, "bold"), bd=1, relief="solid", pady=18).grid(row=row, column=col, sticky="nsew")
    tk.Label(outer, text="Для теста B показатель равен доле правильных ответов на соответствующем этапе. Для остальных тестов используются их итоговые приведённые показатели.", bg="#eef3f8", fg="#5a6678", font=("Arial", 10), wraplength=1300, justify="left").pack(anchor="w", padx=28, pady=(0, 24))


_ORIENTATION_EXCEL_START = 187


def _excel_headers() -> dict[int, tuple[str, str, str, str]]:
    headers = dict(_ORIGINAL_EXCEL_HEADERS())
    for col, values in list(headers.items()):
        group = values[0]
        if 104 <= col <= 119:
            group = group.replace("Тест B", "Тест C")
        elif col in (120, 121, 122) or 127 <= col <= 150:
            group = group.replace("Тест C", "Тест D")
        elif col in (123, 124, 125) or 151 <= col <= 186:
            group = group.replace("Тест D", "Тест E")
        headers[col] = (group, values[1], values[2], values[3])
    headers[104] = ("Тест C", "Память", "1", "tпамять 1")
    summary_fields = (("N", "заданий"), ("Nверн", "верных"), ("Nош", "ошибок"), ("Точность", "%"), ("T", "время, с"), ("Tср", "среднее время, с"))
    for stage in range(1, 4):
        base_col = _ORIENTATION_EXCEL_START + (stage - 1) * len(summary_fields)
        for offset, (symbol, title) in enumerate(summary_fields):
            headers[base_col + offset] = ("Тест B · Авиагоризонт", f"Этап {stage}", str(stage), f"{symbol} · {title}")
    headers[_ORIENTATION_EXCEL_START + 18] = ("Тест B · Авиагоризонт", "Итог", "", "Всего заданий")
    headers[_ORIENTATION_EXCEL_START + 19] = ("Тест B · Авиагоризонт", "Итог", "", "Верных ответов")
    headers[_ORIENTATION_EXCEL_START + 20] = ("Тест B · Авиагоризонт", "Итог", "", "Общая точность, %")
    return headers


def _write_orientation_excel(ws, row: int, payload: dict) -> None:
    stages = payload.get("stages", {}) if isinstance(payload.get("stages"), dict) else {}
    keys = ("tasks", "correct", "incorrect", "accuracy_pct", "elapsed_seconds", "average_seconds")
    for stage in range(1, 4):
        item = stages.get(str(stage), {}) if isinstance(stages, dict) else {}
        base_col = _ORIENTATION_EXCEL_START + (stage - 1) * len(keys)
        for offset, key in enumerate(keys):
            base._fixed417_set_if_value(ws, row, base_col + offset, item.get(key))
    summary = payload.get("summary", {}) if isinstance(payload.get("summary"), dict) else {}
    for offset, key in enumerate(("total_tasks", "correct", "accuracy_pct"), 18):
        base._fixed417_set_if_value(ws, row, _ORIENTATION_EXCEL_START + offset, summary.get(key))


def _export_integrated_payload(root: Path | str, payload: dict) -> None:
    if not isinstance(payload, dict):
        return
    participant = payload.get("participant", {}) if isinstance(payload.get("participant"), dict) else {}
    if not str(participant.get("name", "") or "").strip():
        return
    path = base._fixed417_external_excel_path(root)
    if not path.exists():
        # Preparation is needed only for first-run creation/copying.  Existing
        # workbooks go straight to the single load/save cycle below.
        path = base._fixed423_prepare_excel_file(root)
        if path is None:
            return
    try:
        import openpyxl
        workbook = openpyxl.load_workbook(path)
        sheet = workbook.active
        base._fixed423_ensure_integrated_excel_headers(sheet)
        row = base._fixed417_find_or_create_participant_row(sheet, str(participant.get("name", "")))
        base._fixed417_write_login(sheet, row, participant)
        code = str(payload.get("test_code", "") or "").upper()
        if code == "A":
            base._fixed417_write_method_a(sheet, row, payload)
        elif code == "B":
            _write_orientation_excel(sheet, row, payload)
        elif code == "C":
            base._fixed417_write_method_b(sheet, row, payload)
        elif code == "D":
            base._fixed423_write_method_c(sheet, row, payload)
        elif code == "E":
            base._fixed423_write_method_d(sheet, row, payload)
        workbook.save(path)
    except Exception as exc:
        try:
            base._fixed417_log_excel_export(root, f"Ошибка экспорта aviatest_v2: {type(exc).__name__}: {exc}")
        except Exception:
            pass


def _research_groups(code: str, cls) -> list[tuple[str, list[str]]]:
    declared = [field.name for field in fields(cls)]
    hidden = {"etap1_norm_speed", "etap2_norm_speed", "etap3_norm_speed"} if code == "E" else set()
    declared = [name for name in declared if name not in hidden]
    used: set[str] = set()
    result: list[tuple[str, list[str]]] = []
    for title, names in base.RESEARCH_SECTION_META.get(code, []):
        selected = [name for name in names if name in declared and name not in used]
        if selected:
            result.append((title, selected))
            used.update(selected)
    remaining = [name for name in declared if name not in used]
    if remaining:
        result.append(("Прочие параметры", remaining))
    return result


def _migrate_progress(store) -> None:
    data = store._load()
    if not isinstance(data, dict):
        return
    changed = False
    for key, record in data.items():
        if not isinstance(record, dict) or record.get("aviatest_v1_order_migrated"):
            continue
        results = record.get("results", {}) if isinstance(record.get("results"), dict) else {}
        # Records created by Aviatest v2 already use the A/B/C/D/E order.  Old
        # releases did not stamp new records with the migration marker, so the
        # next application start shifted perfectly valid v2 results again and
        # the integrated table consequently displayed zeroes.  Recognize the
        # unambiguous v2 layout before applying the legacy B/C/D shift.
        b_payload = results.get("B") if isinstance(results.get("B"), dict) else {}
        c_payload = results.get("C") if isinstance(results.get("C"), dict) else {}
        is_v2_record = (
            "E" in results
            or isinstance(b_payload.get("stages"), dict)
            or str(b_payload.get("test_code", "")).upper() == "B"
            or str(c_payload.get("test_code", "")).upper() == "C"
        )
        if is_v2_record:
            record["aviatest_v1_order_migrated"] = datetime.now().isoformat(timespec="seconds")
            data[key] = record
            changed = True
            continue
        shifted: dict[str, Any] = {}
        for old, new in (("D", "E"), ("C", "D"), ("B", "C")):
            payload = results.pop(old, None)
            if isinstance(payload, dict):
                payload = dict(payload)
                payload["test_code"] = new
                payload["test_label"] = base.TEST_LABELS[new]
                shifted[new] = payload
        results.update(shifted)
        record["results"] = results
        mapping = {"A": "A", "B": "C", "C": "D", "D": "E"}
        completed = [mapping[code] for code in record.get("completed_tests", []) if code in mapping]
        record["completed_tests"] = [code for code in base.TEST_ORDER if code in completed]
        for item in record.get("history", []) if isinstance(record.get("history"), list) else []:
            if isinstance(item, dict) and item.get("test_code") in mapping:
                item["test_code"] = mapping[item["test_code"]]
        record["aviatest_v1_order_migrated"] = datetime.now().isoformat(timespec="seconds")
        data[key] = record
        changed = True
    if changed:
        store._save(data)


def _install_integration() -> None:
    global _ORIGINAL_EXCEL_HEADERS
    old_specs = {code: (title, cls, filename) for code, title, cls, filename in base.RESEARCH_CONFIG_SPECS}
    old_meta = {code: dict(base.RESEARCH_FIELD_META.get(code, {})) for code in ("A", "B", "C", "D")}
    old_sections = {code: list(base.RESEARCH_SECTION_META.get(code, [])) for code in ("A", "B", "C", "D")}

    base.TEST_ORDER = ["A", "B", "C", "D", "E"]
    base.TEST_LABELS = {code: f"Тест {code}" for code in base.TEST_ORDER}
    base.TEST_DESCRIPTIONS = {
        "A": "Слежение за объектом",
        "B": "Пространственная ориентация (авиагоризонт)",
        "C": "Запоминание фигур в матрице",
        "D": "Счёт в заданном темпе",
        "E": "Закономерности между фигурами",
    }
    base.TEST_FULL_TITLES = {code: f"{base.TEST_LABELS[code]} · {base.TEST_DESCRIPTIONS[code]}" for code in base.TEST_ORDER}
    base.MENU_CARD_TEXT = {
        "A": "Тест A\nСлежение за объектом",
        "B": "Тест B\nПространственная ориентация\n(авиагоризонт)",
        "C": "Тест C\nЗапоминание фигур\nв матрице",
        "D": "Тест D\nСчёт в заданном темпе",
        "E": "Тест E\nЗакономерности\nмежду фигурами",
    }

    base.RESEARCH_FIELD_META = {
        "A": old_meta["A"],
        "B": {
            "stage_1_time_s": {"label": "Этап 1: время теста, с", "help": "Текущий лимит — 120 секунд."},
            "stage_2_time_s": {"label": "Этап 2: время теста, с", "help": "Текущий лимит — 120 секунд."},
            "stage_3_time_s": {"label": "Этап 3: время теста, с", "help": "Текущий лимит — 120 секунд."},
            "training_stage_1_time_s": {"label": "Этап 1: время тренировки, с", "help": "Текущее значение — 60 секунд."},
            "training_stage_2_time_s": {"label": "Этап 2: время тренировки, с", "help": "Текущее значение — 60 секунд."},
            "training_stage_3_time_s": {"label": "Этап 3: время тренировки, с", "help": "Текущее значение — 60 секунд."},
        },
        "C": old_meta["B"],
        "D": old_meta["C"],
        "E": old_meta["D"],
    }
    base.RESEARCH_SECTION_META = {
        "A": old_sections["A"],
        "B": [
            ("Время теста", ["stage_1_time_s", "stage_2_time_s", "stage_3_time_s"]),
            ("Время тренировки", ["training_stage_1_time_s", "training_stage_2_time_s", "training_stage_3_time_s"]),
        ],
        "C": old_sections["B"],
        "D": old_sections["C"],
        "E": old_sections["D"],
    }
    base.RESEARCH_CONFIG_SPECS = [
        ("A", "Тест A · Слежение за объектом", old_specs["A"][1], old_specs["A"][2]),
        ("B", "Тест B · Пространственная ориентация", OrientationConfig, "orientation_config.json"),
        ("C", "Тест C · Запоминание фигур в матрице", old_specs["B"][1], old_specs["B"][2]),
        ("D", "Тест D · Счёт в заданном темпе", old_specs["C"][1], old_specs["C"][2]),
        ("E", "Тест E · Закономерности между фигурами", old_specs["D"][1], old_specs["D"][2]),
    ]
    base._get_research_field_meta = lambda code, name: base.RESEARCH_FIELD_META.get(code, {}).get(name, {"label": name, "help": ""})
    base._get_research_section_groups = _research_groups

    previous_enrich = base.UserProgressStore._enrich_payload_for_storage

    def shifted_enrich(self, code, payload):
        if code == "A":
            return previous_enrich(self, "A", payload)
        if code == "B":
            return dict(payload) if isinstance(payload, dict) else {}
        if code == "C":
            normalized = previous_enrich(self, "B", payload)
            normalized["test_code"] = "C"
            normalized["test_label"] = base.TEST_LABELS["C"]
            return normalized
        return dict(payload) if isinstance(payload, dict) else {}

    base.UserProgressStore._enrich_payload_for_storage = shifted_enrich
    previous_store_init = base.UserProgressStore.__init__
    previous_default_record = base.UserProgressStore._default_record

    def default_record(self, profile):
        record = previous_default_record(self, profile)
        record["aviatest_v1_order_migrated"] = datetime.now().isoformat(timespec="seconds")
        return record

    base.UserProgressStore._default_record = default_record

    def store_init(self, root):
        previous_store_init(self, root)
        _migrate_progress(self)

    base.UserProgressStore.__init__ = store_init

    base.StartPageApp.launch_test = _launch_test
    base.StartPageApp.view_results = _view_results
    base.StartPageApp.show_orientation_results = _show_orientation_results
    base.StartPageApp.collect_integral_values = _collect_all_values
    base.StartPageApp.show_integral_results = _show_all_tests_results
    base._show_integral_results = _show_all_tests_results

    def build_menu(self):
        self._aviatest_menu_layout_signature = None
        self.view_mode = "menu"
        self.destroy_main()
        self.build_base_shell()
        self.right.grid_rowconfigure(2, weight=0)
        self.right.grid_rowconfigure(3, weight=1)
        self.right.grid_rowconfigure(4, weight=0)

        self.title_small.configure(text="Меню")
        self.title_big.configure(text="ВЫБОР\nТЕСТОВ")
        self.body = tk.Label(
            self.right,
            textvariable=self.menu_intro_var,
            bg=base.BG_COLOR,
            fg=base.TEXT_COLOR,
            justify="left",
            anchor="nw",
        )
        self.body.grid(row=2, column=0, sticky="ew")

        self.menu_panel = tk.Frame(self.right, bg=base.PANEL_COLOR, bd=2, relief="groove")
        self.menu_panel.grid(row=3, column=0, sticky="nsew")
        self.menu_panel.grid_columnconfigure(0, weight=1)
        self.menu_panel.grid_rowconfigure(2, weight=1)
        self.menu_title = tk.Label(
            self.menu_panel,
            text="Доступные тесты",
            bg=base.PANEL_COLOR,
            fg=base.TITLE_COLOR,
            anchor="center",
            justify="center",
        )
        self.menu_title.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 6))
        self.menu_status_label = tk.Label(
            self.menu_panel,
            textvariable=self.menu_status_var,
            bg=base.PANEL_COLOR,
            fg="#245a2a",
            justify="left",
            anchor="w",
        )
        self.menu_status_label.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 8))

        self.tests_grid = tk.Frame(self.menu_panel, bg=base.PANEL_COLOR)
        self.tests_grid.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))
        for column in range(3):
            self.tests_grid.grid_columnconfigure(column, weight=1, uniform="aviatest_menu_columns")
        for row in range(2):
            self.tests_grid.grid_rowconfigure(row, weight=1, uniform="aviatest_menu_rows")

        self.menu_buttons = {}
        self.menu_result_buttons = {}
        self.menu_cards = {}
        for index, code in enumerate(base.TEST_ORDER):
            card = tk.Frame(self.tests_grid, bg="#e8e1bf", bd=2, relief="ridge")
            card.grid(row=index // 3, column=index % 3, sticky="nsew", padx=8, pady=8)
            card.grid_columnconfigure(0, weight=1)
            card.grid_rowconfigure(0, weight=1)
            self.menu_cards[code] = card
            button = tk.Button(
                card,
                text=base.menu_card_text(code),
                bg=base.MENU_BG,
                activebackground=base.MENU_ACTIVE,
                relief="raised",
                bd=3,
                cursor="hand2",
                command=lambda current=code: self.launch_test(current),
                justify="center",
                wraplength=230,
            )
            button.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 6))
            self.menu_buttons[code] = button
            result_button = tk.Button(
                card,
                text="РЕЗУЛЬТАТОВ\nПОКА НЕТ",
                bg="#d6dbe5",
                activebackground="#d6dbe5",
                relief="flat",
                bd=1,
                cursor="hand2",
                command=lambda current=code: self.view_results(current),
                justify="center",
                wraplength=230,
            )
            result_button.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
            self.menu_result_buttons[code] = result_button

        self.menu_btn_frame = tk.Frame(self.right, bg=base.BG_COLOR)
        self.menu_btn_frame.grid(row=4, column=0, sticky="ew")
        for column in range(5):
            self.menu_btn_frame.grid_columnconfigure(column, weight=1, uniform="aviatest_actions")
        actions = (
            ("exit_btn", "ВЫХОД", self.exit_app, base.EXIT_BG, base.EXIT_ACTIVE, 0),
            ("settings_btn", "НАСТРОЙКИ", self.build_researcher_ui, base.BACK_BG, base.BACK_ACTIVE, 1),
            ("all_results_btn", "ВСЕ РЕЗУЛЬТАТЫ", self.show_all_results_browser, "#6b7dff", "#5b6de8", 2),
            ("continue_btn", "СЛЕДУЮЩИЙ ТЕСТ", self.continue_next_test, base.NEXT_BG, base.NEXT_ACTIVE, 3),
            ("restart_btn", "НАЧАТЬ СНАЧАЛА", self.restart_progress, base.BACK_BG, base.BACK_ACTIVE, 4),
        )
        for name, text, command, color, active, column in actions:
            button = tk.Button(
                self.menu_btn_frame,
                text=text,
                bg=color,
                activebackground=active,
                fg="white" if name in {"exit_btn", "all_results_btn"} else "#111111",
                relief="raised",
                bd=3,
                cursor="hand2",
                command=command,
                justify="center",
            )
            button.grid(row=0, column=column, sticky="ew")
            setattr(self, name, button)

        self.refresh_menu_state()
        self.apply_current_layout()

    base.StartPageApp.build_menu_ui = build_menu
    previous_menu_layout = base.StartPageApp.apply_menu_layout

    def menu_layout(self):
        width = max(self.root.winfo_width(), 1100)
        height = max(self.root.winfo_height(), 760)
        signature = (int(width), int(height))
        if getattr(self, "_aviatest_menu_layout_signature", None) == signature:
            return
        scale = max(0.72, min(min(width / base.BASE_W, height / base.BASE_H), 1.08))
        compact = width < 1500 or height < 900
        # The menu uses a slightly wider illustration column than the other
        # pages so two square images can fill its height without distortion.
        left_weight, right_weight = (6, 14) if compact else (7, 13)
        pad_x = int((16 if compact else 24) * scale)
        pad_y = int((12 if compact else 18) * scale)
        column_gap = int((14 if compact else 24) * scale)
        image_gap = int((10 if compact else 18) * scale)
        content_width = max(320, width - 2 * pad_x)
        left_width = content_width * left_weight / (left_weight + right_weight) - column_gap
        content_height = max(360, height - 2 * pad_y)
        self._aviatest_menu_image_size = max(
            160, int(min(left_width, (content_height - image_gap) / 2.0))
        )
        previous_menu_layout(self)
        self.main.grid_columnconfigure(0, weight=left_weight, uniform="cols")
        self.main.grid_columnconfigure(1, weight=right_weight, uniform="cols")
        # The image column and the menu column share the same available height.
        # Let the test-selection block consume all remaining vertical space so
        # its lower action row aligns with the bottom of the left illustration.
        self.right.grid_rowconfigure(2, weight=0)
        self.right.grid_rowconfigure(3, weight=1)
        self.right.grid_rowconfigure(4, weight=0)
        self.menu_panel.grid_configure(sticky="nsew")
        self.menu_panel.grid_rowconfigure(2, weight=1)
        self.tests_grid.grid_configure(sticky="nsew")
        for row in range(2):
            self.tests_grid.grid_rowconfigure(row, weight=1, uniform="aviatest_menu_rows")
        for code in base.TEST_ORDER:
            self.menu_cards[code].grid_configure(sticky="nsew")
            self.menu_cards[code].grid_rowconfigure(0, weight=1)
            self.menu_buttons[code].configure(height=3, font=("Arial", 10, "bold"), wraplength=230)
            self.menu_result_buttons[code].configure(height=1, font=("Arial", 9, "bold"), wraplength=230)
        self._aviatest_menu_layout_signature = signature

    base.StartPageApp.apply_menu_layout = menu_layout

    def stable_on_configure(self, event=None):
        # Tk sends <Configure> from every descendant to the toplevel binding.
        # Only a real root-window resize may trigger a page re-layout.
        if event is not None and getattr(event, "widget", None) is not self.root:
            return
        try:
            size = (int(self.root.winfo_width()), int(self.root.winfo_height()))
        except Exception:
            size = None
        if size is not None and getattr(self, "_aviatest_root_size", None) == size:
            return
        self._aviatest_root_size = size
        if self._resize_after_id is not None:
            try:
                self.root.after_cancel(self._resize_after_id)
            except Exception:
                pass
        self._resize_after_id = self.root.after(140, self.apply_current_layout)

    base.StartPageApp.on_configure = stable_on_configure

    previous_set_image = base.StartPageApp.set_image

    def stable_set_image(self, label, image_name, size):
        if getattr(self, "view_mode", "") == "menu":
            size = int(getattr(self, "_aviatest_menu_image_size", size))
        cache_key = (str(image_name), int(size))
        if getattr(label, "_aviatest_image_cache_key", None) == cache_key:
            return
        previous_set_image(self, label, image_name, int(size))
        label._aviatest_image_cache_key = cache_key

    base.StartPageApp.set_image = stable_set_image

    _shift_window_labels("MethodBWindow", "Тест B", "Тест C")
    _shift_window_labels("MethodCWindow", "Тест C", "Тест D")
    _shift_window_labels("MethodDWindow", "Тест D", "Тест E")

    _ORIGINAL_EXCEL_HEADERS = base._fixed423_excel_headers
    base._fixed423_excel_headers = _excel_headers
    base._fixed423_export_payload_to_integrated_excel = _export_integrated_payload
    base._fixed417_export_payload_to_integrated_excel = _export_integrated_payload


_ORIGINAL_EXCEL_HEADERS = base._fixed423_excel_headers
_install_integration()


def main() -> None:
    base._run_app()


if __name__ == "__main__":
    main()
