"""Авиатест v4: отдельная копия проекта, шесть методик и 3D-поверхность."""
from __future__ import annotations

import json
import math
import sys
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk

import aviatest_v2 as v2
import red_black_numbers as rb

base = v2.base
APP_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
ROOT = APP_DIR / "aviatest_v4_data" if getattr(sys, "frozen", False) else APP_DIR
ORDER = ("A", "C", "D", "E", "F", "B")
TITLES = ("Сенсомоторная деятельность", "Запоминание фигур", "Счётно-логическая деятельность",
          "Сложная логическая деятельность", "Переключение внимания", "Пространственная ориентация")
# These are stage descriptors, not a shared numerical Y scale.
STAGES = {
    "A": ("X", "X/Y", "X/Y/крен"),
    "C": ("4 фигуры", "5 фигур", "6 фигур"),
    "D": ("однозначные", "двузначные", "трёхзначные"),
    "E": ("простые", "средние", "сложные"),
    "F": ("этап 1", "этап 2", "этап 3"),
    "B": ("курс", "курс/тангаж", "курс/тангаж/крен"),
}


def number(value):
    """Missing, malformed, negative and nonfinite measurements are gaps, never zero."""
    if value is None or isinstance(value, bool):
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) and result >= 0 else None
    except (TypeError, ValueError, OverflowError):
        return None


def mapping(value):
    return value if isinstance(value, dict) else {}


def extract_values(payloads):
    values = {}
    for code, suffix in (("A", "a"), ("C", "b"), ("D", "c"), ("E", "d")):
        payload = mapping(payloads.get(code))
        summary = mapping(payload.get("summary"))
        values[code] = [number(summary.get(f"t{level}_{suffix}")) for level in ("min", "medio", "max")]
        # Older count records can have stage values without the summary triple.
        if code == "D":
            stages = mapping(summary.get("stages")) or mapping(payload.get("stages"))
            for i in range(3):
                key = f"t{('min', 'medio', 'max')[i]}_c"
                if key not in summary:
                    values[code][i] = number(mapping(stages.get(str(i + 1))).get("t_value"))
    # Keep the legacy accuracy measure explicit. Do not manufacture a pace from it.
    stages = mapping(mapping(payloads.get("B")).get("stages"))
    values["B"] = []
    for i in range(1, 4):
        item = mapping(stages.get(str(i)))
        accuracy = number(item.get("accuracy_pct"))
        if accuracy is not None and accuracy <= 100 and number(item.get("tasks")) != 0:
            values["B"].append(accuracy / 100)
        else:
            values["B"].append(None)
    f_stages = mapping(payloads.get("F")).get("stages", [])
    by_stage = {}
    if isinstance(f_stages, list):
        for stage in f_stages:
            if isinstance(stage, dict):
                by_stage[str(stage.get("stage"))] = stage
    values["F"] = [number(mapping(by_stage.get(str(i))).get("table_pace")) for i in range(1, 4)]
    return values


def collect_values(owner, profile):
    return extract_values({code: owner.progress_store.get_test_result(profile, code) for code in ORDER})


def smooth_runs(points, resolution=16):
    """Shape-preserving cubic Hermite curves, passing through samples without overshoot."""
    runs=[]; run=[]
    for point in [*points,None]:
        if point is None or point[2] is None:
            if len(run)>=2:
                delta=[b[2]-a[2] for a,b in zip(run,run[1:])]
                slopes=[delta[0]]+[0 if a*b<=0 else 2*a*b/(a+b) for a,b in zip(delta,delta[1:])]+[delta[-1]]
                curve=[]
                for i,(a,b) in enumerate(zip(run,run[1:])):
                    for j in range(resolution):
                        t=j/resolution
                        z=(2*t**3-3*t*t+1)*a[2]+(t**3-2*t*t+t)*slopes[i]+(-2*t**3+3*t*t)*b[2]+(t**3-t*t)*slopes[i+1]
                        curve.append((a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t,z))
                runs.append(curve+[run[-1]])
            run=[]
        else: run.append(point)
    return runs


class IntegralSurface3D(tk.Canvas):
    """Native Tk rendering: bilinear surface, depth sorted triangles and sample stems."""
    def __init__(self, parent, values, order=None, **kwargs):
        super().__init__(parent, bg="white", highlightthickness=0, **kwargs)
        self.order = tuple(order or ORDER)
        self.titles = tuple(dict(zip(ORDER,TITLES))[code] for code in self.order)
        self.values = {code: [number(v) for v in (list(values.get(code, [])) + [None] * 3)[:3]] for code in self.order}
        self.yaw, self.pitch, self.zoom = math.radians(45), math.asin(1 / math.sqrt(3)), 1.0
        self.labels = True
        self._drag = None
        self._pending = None
        maximum = max((v for row in self.values.values() for v in row if v is not None), default=0)
        raw_step = max(1.2, maximum) / 5
        power = 10 ** math.floor(math.log10(raw_step))
        self.step = next(k * power for k in (1, 2, 2.5, 5, 10) if k * power >= raw_step)
        self.zmax = math.ceil(max(1.2, maximum) / self.step) * self.step
        self.bind("<Configure>", self.redraw)
        self.bind("<ButtonPress-1>", lambda e: setattr(self, "_drag", (e.x, e.y)))
        self.bind("<B1-Motion>", self.drag)
        self.bind("<ButtonRelease-1>", lambda e: setattr(self, "_drag", None))
        self.bind("<MouseWheel>", self.wheel)
        self.bind("<Button-4>", lambda e: self.change_zoom(1.1))
        self.bind("<Button-5>", lambda e: self.change_zoom(1 / 1.1))
        self.bind("<Double-Button-1>", lambda e: self.reset_view())
        self.bind("<Destroy>", self.cleanup)

    def cleanup(self, event):
        if event.widget is self and self._pending is not None:
            self.after_cancel(self._pending)
            self._pending = None

    def reset_view(self):
        self.yaw, self.pitch, self.zoom = math.radians(45), math.asin(1 / math.sqrt(3)), 1.0
        self.redraw()

    def drag(self, event):
        if self._drag is not None:
            x, y = self._drag
            self.yaw = (self.yaw + (event.x - x) * .008) % (2 * math.pi)
            self.pitch = min(math.radians(80), max(math.radians(8), self.pitch + (event.y - y) * .007))
            self._drag = event.x, event.y
            self.redraw()

    def wheel(self, event):
        if event.delta:
            self.change_zoom(1.1 if event.delta > 0 else 1 / 1.1)
        return "break"

    def change_zoom(self, factor):
        self.zoom = min(1.65, max(.65, self.zoom * factor))
        self.redraw()
        return "break"

    def project(self, x, y, z):
        x, y, z = (x - (len(self.order)-1)/2) * 1.1, (y - 1) * 2.2, z / self.zmax * 2.8 - 1.2
        cy, sy, cp, sp = math.cos(self.yaw), math.sin(self.yaw), math.cos(self.pitch), math.sin(self.pitch)
        horizontal, depth = x * cy - y * sy, x * sy + y * cy
        vertical = z * cp - depth * sp
        scale = min(max(1, self.winfo_width() - 400) / 10.5, max(1, self.winfo_height() - 120) / 6.2) * self.zoom
        return (self.winfo_width() * .5 + horizontal * scale,
                self.winfo_height() * .48 - vertical * scale,
                depth * cp + z * sp)

    def line3(self, points, **kwargs):
        flat = [c for p in points for c in self.project(*p)[:2]]
        self.create_line(*flat, **kwargs)

    @staticmethod
    def colour(value):
        # A fixed display range makes equal values the same colour for every person.
        # These are visual anchors, not pass/fail thresholds or new normative values.
        # Keep the existing display breakpoints .5/.65/1/1.5: higher is greener.
        stops=((0,(115,35,23)),(.25,(201,47,27)),(.5,(244,131,25)),
               (.65,(255,224,28)),(1,(145,213,41)),(1.5,(15,166,61)),(2,(0,102,47)))
        value=max(0.0,min(2.0,value))
        for (low,left),(high,right) in zip(stops,stops[1:]):
            if value<=high:
                fraction=(value-low)/(high-low)
                return "#%02x%02x%02x" % tuple(round(a+(b-a)*fraction) for a,b in zip(left,right))
        return "#00662f"

    def redraw(self, _event=None):
        # Coalesce configure/drag bursts so all callbacks leave the UI responsive.
        if self._pending is None:
            self._pending = self.after_idle(self.draw)

    def draw(self):
        self._pending = None
        self.delete("all")
        if self.winfo_width() < 80 or self.winfo_height() < 80:
            return
        for x in range(len(self.order)):
            self.line3([(x,0,0),(x,2,0)], fill="#d8dbe0")
        for y in range(3):
            self.line3([(0,y,0),(len(self.order)-1,y,0)], fill="#d8dbe0")
        for n in range(round(self.zmax / self.step) + 1):
            z = n * self.step
            self.line3([(0,2,z),(len(self.order)-1,2,z)], fill="#e5e7eb")
            self.line3([(0,0,z),(0,2,z)], fill="#e5e7eb")
            px, py, _ = self.project(0,0,z)
            self.create_text(px-10, py, text=f"{z:g}", anchor="e", fill="#45556c", font=("Arial", 10))
        self.line3([(0,0,0),(0,0,self.zmax)], fill="#64748b", width=2)
        # Split each measured cell into a dense bilinear mesh. Never bridge a missing corner.
        primitives = []
        for x in range(len(self.order)-1):
            for y in range(2):
                a,b = self.values[self.order[x]][y:y+2]
                c,d = self.values[self.order[x+1]][y:y+2]
                if None in (a,b,c,d):
                    continue
                def sample(u,v):
                    return (x+u,y+v,a*(1-u)*(1-v)+c*u*(1-v)+b*(1-u)*v+d*u*v)
                for ix in range(7):
                    for iy in range(7):
                        u,v,du = ix/7,iy/7,1/7
                        quad = [sample(u,v),sample(u+du,v),sample(u+du,v+du),sample(u,v+du)]
                        for inds in ((0,1,2),(0,2,3)):
                            pts = [self.project(*quad[i]) for i in inds]
                            value = sum(quad[i][2] for i in inds)/3
                            primitives.append((sum(p[2] for p in pts)/3,"surface",pts,self.colour(value)))
        for x,code in enumerate(self.order):
            for y,value in enumerate(self.values[code]):
                if value is not None:
                    p,foot = self.project(x,y,value),self.project(x,y,0)
                    primitives.append(((p[2]+foot[2])/2,"stem",[foot,p],None))
                    primitives.append((p[2]+.002,"dot",[p],(code,y,value)))
        # Depth grows towards the viewer; painter's algorithm draws far items first.
        # Measured samples and their stems remain visible, as in Boris's reference.
        # Only the opaque surface triangles need depth sorting.
        for _,kind,pts,detail in sorted(primitives,key=lambda p:({"surface":0,"stem":1,"dot":2}[p[1]],p[0])):
            flat = [c for p in pts for c in p[:2]]
            if kind == "surface":
                self.create_polygon(*flat, fill=detail, outline=detail, tags="surface")
            elif kind == "stem":
                self.create_line(*flat, fill="#555555", width=1.4, tags="stem")
            else:
                px,py = pts[0][:2]
                self.create_oval(px-5,py-5,px+5,py+5,fill="#ff1717",outline="#7e1111",tags="sample")
        # Transparent reference plane; stipple keeps measurements visible in native Tk.
        plane=[self.project(x,y,1.0) for x,y in ((0,0),(len(self.order)-1,0),(len(self.order)-1,2),(0,2))]
        self.create_polygon(*[c for point in plane for c in point[:2]],fill="#73b8bb",
                            stipple="gray12",outline="#559c9f",width=1.5,tags="norm_plane")
        px,py,_=self.project(0,2,1.0)
        self.create_text(px-8,py-12,text="Норма темпа · 1,0",anchor="e",fill="#337b7e",font=("Arial",10,"bold"),tags="norm_label")
        # Smooth connections interpolate only adjacent existing measurements.
        for x,code in enumerate(self.order):
            for curve in smooth_runs([(x,y,value) for y,value in enumerate(self.values[code])]):
                self.line3(curve,fill="#24496c",width=2,tags="curve_within")
        for y in range(3):
            for curve in smooth_runs([(x,y,self.values[code][y]) for x,code in enumerate(self.order)]):
                self.line3(curve,fill="#5b3a70",width=2,tags="curve_across")
        self.tag_raise("sample")
        # Keep measured value labels readable above the surface, with collision avoidance.
        occupied = []
        if self.labels:
            for x,code in enumerate(self.order):
                for y,value in enumerate(self.values[code]):
                    if value is None:
                        continue
                    px,py,_ = self.project(x,y,value)
                    text = f"{'p' if code == 'B' else 't'}={value:.2f}"
                    for offset in (16,30,44,58):
                        box=(px-27,py-offset-7,px+27,py-offset+7)
                        if not any(box[0]<b[2] and box[2]>b[0] and box[1]<b[3] and box[3]>b[1] for b in occupied):
                            occupied.append(box)
                            self.create_text(px,py-offset,text=text,fill="#24446a",font=("Arial",10),tags="value")
                            break
        # Isometric reset: the three projected positive axes are 120 degrees apart.
        self.line3([(0,0,0),(len(self.order)-.3,0,0)],fill="#426ba4",width=2,arrow="last",tags="axis")
        self.line3([(0,0,0),(0,2.6,0)],fill="#426ba4",width=2,arrow="last",tags="axis")
        self.line3([(0,0,0),(0,0,self.zmax*1.12)],fill="#426ba4",width=2,arrow="last",tags="axis")
        for x,title in enumerate(self.titles):
            px,py,_ = self.project(x,-.85,0)
            # Label rotation follows the projected element axis when the user rotates.
            ax,ay,_ = self.project(x,0,0)
            bx,by,_ = self.project(x,1,0)
            angle = math.degrees(math.atan2(by-ay,ax-bx))
            if angle>90: angle-=180
            if angle<-90: angle+=180
            self.create_text(px+5,py-7,text=title,anchor="w",angle=angle,
                             fill="#163456",font=("Arial",10,"bold"),tags="method")
        for y,title in enumerate(("MIN","MED","MAX")):
            px,py,_ = self.project(0,y,0)
            self.create_text(px-10,py+6,text=title,anchor="e",fill="#163456",font=("Arial",10,"bold"),tags="stage")
        for point,title,anchor in (((0,0,self.zmax*1.12),"Темп\nдеятельности","s"),
                                   ((0,2.65,0),"Число\nэлементов","n"),
                                   ((len(self.order)-.2,0,0),"Сложность\nдеятельности","n")):
            px,py,_=self.project(*point)
            self.create_text(px,py-5 if anchor=="s" else py+8,text=title,anchor=anchor,
                             fill="#163456",font=("Arial",11,"bold"),tags="axis_title")
        self.create_text(self.winfo_width()-16,14,text="Мышь — вращение · колесо — масштаб",anchor="ne",fill="#607086",font=("Arial",10))
        # Colour legend is independent of the automatic vertical camera scale.
        legend_x=self.winfo_width()-66
        legend_top=95
        legend_height=max(90,min(220,self.winfo_height()-175))
        for i in range(80):
            value=2*(1-i/79)
            y1=legend_top+i*legend_height/80
            self.create_rectangle(legend_x,y1,legend_x+16,y1+legend_height/80+1,
                                  fill=self.colour(value),outline="",tags="colour_scale")
        for value in (0,.5,1,1.5,2):
            self.create_text(legend_x+22,legend_top+(1-value/2)*legend_height,
                             text="2+" if value==2 else f"{value:g}",anchor="w",fill="#45556c",font=("Arial",9))
        self.create_text(legend_x+8,legend_top-15,text="Лучше ↑",fill="#45556c",font=("Arial",10,"bold"))
        self.create_text(legend_x+8,legend_top+legend_height+17,text="Хуже ↓",fill="#45556c",font=("Arial",10,"bold"))
        if not any(v is not None for row in self.values.values() for v in row):
            self.create_text(self.winfo_width()/2,self.winfo_height()/2,text="Нет сохранённых результатов",fill="#667085",font=("Arial",18,"bold"))


def show_integral(self):
    from surface_view import show_integral as show_normalized_integral
    return show_normalized_integral(self)


def f_payload(owner, stages):
    return {"test_code":"F","test_label":"Тест 5 · ЧКТ","completed":True,
            "completed_at":datetime.now().isoformat(timespec="seconds"),
            "session_id":owner.current_session.session_id,"participant":v2._participant(owner.current_session),
            "stages":list(stages),"summary":{"table_pace":[s["table_pace"] for s in stages]}}


def persist_f(owner, payload):
    if not isinstance(payload.get("stages"),list) or {s.get("stage") for s in payload["stages"] if isinstance(s,dict)} != {1,2,3}:
        raise ValueError("ЧКТ: для сохранения нужны все три этапа")
    payload["result_path"] = base.save_method_payload(owner.base_dir,"F",payload["session_id"],payload)
    owner.progress_store.save_test_result(owner.current_profile,"F",payload)
    owner.progress_store.mark_completed(owner.current_profile,"F")


def export_f_excel(root, payload):
    """Add ChKT to its own sheet, preserving the A–E columns of the existing workbook."""
    import openpyxl
    path=base._fixed417_external_excel_path(root)
    if not path.exists():
        path=base._fixed423_prepare_excel_file(root)
    if path is None:
        raise OSError("Не удалось создать Excel-книгу")
    workbook=openpyxl.load_workbook(path)
    try:
        sheet=workbook["ЧКТ"] if "ЧКТ" in workbook.sheetnames else workbook.create_sheet("ЧКТ")
        headers=["Сессия","Дата","ФИО","Возраст","Пол"]
        for i in range(1,4):headers.extend([f"Этап {i} · темп",f"Этап {i} · ошибки",f"Этап {i} · время, с"])
        if sheet.cell(1,1).value is None:
            for col,title in enumerate(headers,1):sheet.cell(1,col,title)
            sheet.freeze_panes="F2"
            for cell in sheet[1]:
                cell.font=openpyxl.styles.Font(bold=True)
                cell.alignment=openpyxl.styles.Alignment(wrap_text=True)
            sheet.column_dimensions['C'].width=32
        participant=mapping(payload.get("participant"))
        row=[payload.get("session_id"),payload.get("completed_at"),participant.get("name"),participant.get("age"),participant.get("gender")]
        stages={s["stage"]:s for s in payload["stages"]}
        for i in range(1,4):row.extend([stages[i].get("table_pace"),stages[i].get("errors"),stages[i].get("duration")])
        # A repeated save of one session replaces its row instead of duplicating it.
        target=next((i for i in range(2,sheet.max_row+1) if sheet.cell(i,1).value==row[0] and sheet.cell(i,3).value==row[2]),sheet.max_row+1)
        for col,value in enumerate(row,1):sheet.cell(target,col,value)
        main=workbook.worksheets[0]
        columns=ensure_chkt_columns(main)
        main_row=base._fixed417_find_or_create_participant_row(main,str(participant.get("name", "")))
        base._fixed417_write_login(main,main_row,participant)
        for i in range(1,4):
            for field in ("table_pace","errors","duration"):
                main.cell(main_row,columns[(i,field)],stages[i].get(field))
        workbook.save(path)
        return path
    finally:
        workbook.close()


def ensure_chkt_columns(sheet):
    """Append F columns without moving or overwriting the existing A–E/participant fields."""
    import openpyxl
    result={}
    for stage in range(1,4):
        for field,label in (("table_pace","Темп"),("errors","Ошибки"),("duration","Время, с")):
            title=f"ЧКТ · этап {stage} · {label}"
            col=next((c for c in range(1,sheet.max_column+1) if sheet.cell(4,c).value==title),None)
            if col is None:
                col=sheet.max_column+1
                for row,value in enumerate(("Тест 5 · Красно-чёрные таблицы",f"Этап {stage}",("MIN","MED","MAX")[stage-1],title),1):
                    cell=sheet.cell(row,col,value)
                    cell.font=openpyxl.styles.Font(name="Arial",size=10,bold=True,color="FFFFFF")
                    cell.fill=openpyxl.styles.PatternFill("solid",fgColor="36556B")
                    cell.alignment=openpyxl.styles.Alignment(horizontal="center",vertical="center",wrap_text=True)
                sheet.column_dimensions[openpyxl.utils.get_column_letter(col)].width=19
            result[(stage,field)]=col
            sheet.cell(1,col).value='Тест 5 · Красно-чёрные таблицы'
    return result


_original_ensure_headers=base._fixed423_ensure_integrated_excel_headers
def ensure_integrated_headers(sheet):
    _original_ensure_headers(sheet)
    ensure_chkt_columns(sheet)

base._fixed423_ensure_integrated_excel_headers=ensure_integrated_headers


_original_prepare_excel=base._fixed423_prepare_excel_file
def prepare_integrated_excel(root):
    """Backfill missing main-sheet F results from the existing detailed sheet."""
    path=_original_prepare_excel(root)
    if path is None: return path
    import openpyxl
    workbook=openpyxl.load_workbook(path)
    try:
        if 'ЧКТ' not in workbook.sheetnames: return path
        main=workbook.worksheets[0]; columns=ensure_chkt_columns(main)
        records=list(workbook['ЧКТ'].iter_rows(min_row=2,values_only=True))
        records.sort(key=lambda row:str(row[1] or ''),reverse=True)
        for record in records:
            if len(record)<14 or not record[2]: continue
            row=base._fixed417_find_or_create_participant_row(main,str(record[2]))
            if main.cell(row,2).value is None:
                base._fixed417_write_login(main,row,dict(name=record[2],age=record[3],gender=record[4]))
            for stage in range(1,4):
                for offset,field in enumerate(('table_pace','errors','duration')):
                    cell=main.cell(row,columns[(stage,field)])
                    if cell.value is None:cell.value=record[5+(stage-1)*3+offset]
        workbook.save(path)
    finally:workbook.close()
    return path

base._fixed423_prepare_excel_file=prepare_integrated_excel


def launch_f(self):
    if not self.current_profile or not self.current_session:
        return
    if not getattr(self,"researcher_mode_enabled",False) and self.progress_store.next_test_code(self.current_profile) != "F":
        messagebox.showinfo("Порядок тестов","Тест 5 доступен после тестов 1–4.",parent=self.root)
        return
    owner=self
    profile=self.current_profile
    # Use this owner's storage, including UI tests with a temporary directory.
    rb.DATA_DIR=Path(self.base_dir)/"red_black_data"
    rb.SETTINGS_FILE=rb.DATA_DIR/"settings.json"
    rb.RESULTS_FILE=rb.DATA_DIR/"results.json"
    rb.CSV_FILE=rb.DATA_DIR/"results.csv"
    top=tk.Toplevel(self.root)
    top.transient(self.root);top.grab_set()
    class IntegratedRedBlack(rb.RedBlackApp):
        def show_briefing(self):
            self.clear();self.header("ЧКТ · подготовка к тесту")
            frame=tk.Frame(self.root,bg=rb.CARD,padx=30,pady=30);frame.pack(expand=True)
            tk.Label(frame,text=f"Испытуемый: {profile.name}",bg=rb.CARD,font=("Arial",18,"bold")).pack(pady=20)
            tk.Label(frame,text="Три этапа. Результаты будут сохранены в текущий профиль Авиатеста.",bg=rb.CARD,font=("Arial",12)).pack(pady=12)
            def start():
                self.session=[];self.training=False;self.start_stage(1)
            rb.button(frame,"НАЧАТЬ",start).pack(pady=12)
            rb.button(frame,"НАЗАД",self.show_home,primary=False).pack()

        def save_result(self):
            if getattr(self,"_saved_session",None) is self.session:
                return
            try:
                persist_f(owner,f_payload(owner,self.session))
            except Exception as exc:
                messagebox.showerror("ЧКТ — ошибка сохранения",str(exc),parent=self.root)
                raise
            self._saved_session=self.session
            try:
                export_f_excel(owner.base_dir,owner.progress_store.get_test_result(profile,"F"))
            except Exception as exc:
                messagebox.showwarning("ЧКТ · Excel",f"Результат сохранён в профиле и JSON. Excel не обновлён: {exc}",parent=self.root)
            owner.refresh_menu_state()

        def show_final(self):
            self.clear();self.header("ЧКТ · результаты сохранены")
            body=tk.Frame(self.root,bg=rb.CARD,padx=35,pady=35);body.pack(expand=True)
            for s in self.session:
                tk.Label(body,text=f"Этап {s['stage']}: t={s['table_pace']:.3f} · ошибок {s['errors']}",bg=rb.CARD,font=("Arial",16)).pack(pady=10)
            rb.button(body,"В МЕНЮ АВИАТЕСТА",self.close).pack(pady=20)

        def show_history(self):
            show_f_results(owner,parent=self.root)

        def close(self):
            active=self.stage>0 and hasattr(self,"position") and self.position<len(self.sequence) and self.after_ids
            if active and not messagebox.askyesno("Закрыть ЧКТ","Текущий незавершённый этап не будет сохранён. Закрыть?",parent=self.root):
                return
            super().close();owner.refresh_menu_state()

    child=IntegratedRedBlack(top)
    child.settings=json.loads(json.dumps(child.settings))
    child.settings["participant"]=profile.name
    top._red_black=child
    return top


def show_f_results(self, parent=None):
    payload=self.progress_store.get_test_result(self.current_profile,"F") if self.current_profile else None
    if not payload:
        messagebox.showinfo("ЧКТ","Пока нет сохранённых результатов.",parent=self.root);return
    parent=parent or self.root
    previous_grab=parent.grab_current()
    top=tk.Toplevel(parent);top.title("Тест 5 · ЧКТ · результаты");top.geometry("760x360");top.transient(parent);top.grab_set()
    def close():
        top.destroy()
        if previous_grab is not None and previous_grab.winfo_exists():previous_grab.grab_set()
    top.protocol("WM_DELETE_WINDOW",close)
    top.bind("<Escape>",lambda e:close())
    tk.Label(top,text=f"ЧКТ · {self.current_profile.name}",font=("Arial",18,"bold")).pack(pady=16)
    table=ttk.Treeview(top,columns=("stage","pace","errors","duration"),show="headings",height=3)
    for key,title in zip(table["columns"],("Этап","Приведённый темп","Ошибки","Время, с")):
        table.heading(key,text=title);table.column(key,width=170,anchor="center")
    for s in payload.get("stages",[]):
        table.insert("","end",values=(s["stage"],f"{s['table_pace']:.3f}",s.get("errors",0),f"{s.get('duration',0):.1f}"))
    table.pack(fill="x",padx=12)
    tk.Button(top,text="Закрыть",command=close).pack(pady=12)


_original_launch=base.StartPageApp.launch_test
_original_view=base.StartPageApp.view_results
_original_menu=base.StartPageApp.build_menu_ui
_original_layout=base.StartPageApp.apply_menu_layout


def build_menu(self):
    _original_menu(self)
    self.menu_btn_frame.grid_columnconfigure(5,weight=1,uniform="aviatest_actions")
    self.integral_results_btn=tk.Button(self.menu_btn_frame,text="ИНТЕГРАЛЬНЫЙ\nРЕЗУЛЬТАТ",bg="#17a6a6",fg="white",command=self.show_integral_results,bd=3,relief="raised",cursor="hand2")
    self.integral_results_btn.grid(row=0,column=5,sticky="ew")
    self.root.title("Авиатест v4.3")


def menu_layout(self):
    _original_layout(self)
    if hasattr(self,"integral_results_btn") and self.integral_results_btn.winfo_exists():
        self.integral_results_btn.configure(font=("Arial",9,"bold"),wraplength=150)


# Six tests use the existing progress/order machinery; A–E retain their original identifiers.
base.TEST_ORDER=list("ABCDEF")
base.TEST_LABELS["F"]="Тест F · ЧКТ"
base.TEST_DESCRIPTIONS["F"]="Красно-чёрные таблицы"
base.TEST_FULL_TITLES["F"]="Тест F · Красно-чёрные таблицы"
base.MENU_CARD_TEXT["F"]="ТЕСТ F\nКРАСНО-ЧЁРНЫЕ\nТАБЛИЦЫ"
# Public numbering follows the approved surface; persisted method keys stay stable.
for _index,(_code,_title) in enumerate(zip(ORDER,TITLES),1):
    base.TEST_LABELS[_code]=f'Тест {_index}'
    base.TEST_DESCRIPTIONS[_code]=_title
    base.TEST_FULL_TITLES[_code]=f'Тест {_index} · {_title}'
    base.MENU_CARD_TEXT[_code]=f'ТЕСТ {_index}\n{_title.upper()}'
base.StartPageApp.launch_test=lambda self,code:launch_f(self) if code=="F" else _original_launch(self,code)
base.StartPageApp.view_results=lambda self,code:show_f_results(self) if code=="F" else _original_view(self,code)
base.StartPageApp.show_integral_results=show_integral
base._show_integral_results=show_integral
base.StartPageApp.build_menu_ui=build_menu
base.StartPageApp.apply_menu_layout=menu_layout


def main():
    import shutil
    ROOT.mkdir(parents=True,exist_ok=True)
    if getattr(sys,"frozen",False):
        resource=Path(sys._MEIPASS)
        for name in ("method_a_config.json","method_b_config.json","method_c_config.json","method_d_config.json","orientation_config.json","config_schema_version.txt"):
            source=resource/name
            if source.is_file() and not (ROOT/name).exists():shutil.copy2(source,ROOT/name)
        settings=resource/"red_black_data"/"settings.json"
        if settings.exists() and not (ROOT/"red_black_data"/"settings.json").exists():
            (ROOT/"red_black_data").mkdir(exist_ok=True)
            shutil.copy2(settings,ROOT/"red_black_data"/"settings.json")
    base._runtime_app_dir=lambda:ROOT
    base._run_app()


if __name__=="__main__":
    main()
