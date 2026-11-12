"""Display-only orientation normalization. No default clinical accuracy is assumed."""
import json
import math
from pathlib import Path
import tkinter as tk
from tkinter import ttk

NORM_FILE = 'surface_norms.json'


def accuracy_norm(value):
    if value is None or isinstance(value,str) and not value.strip():
        return None
    if isinstance(value,bool):
        raise ValueError('Норматив точности должен быть числом больше 0 и не более 100%.')
    try:
        result=float(str(value).strip().replace(',','.'))
    except (ValueError,TypeError):
        raise ValueError('Введите норматив точности в процентах или оставьте поле пустым.') from None
    if not math.isfinite(result) or not 0<result<=100:
        raise ValueError('Норматив точности должен быть числом больше 0 и не более 100%.')
    if result/100==0 or not math.isfinite(1/(result/100)):
        raise ValueError('Норматив точности слишком мал для числового отображения.')
    return result


def read_norms(directory):
    path=Path(directory)/NORM_FILE
    if not path.exists():
        return [None]*3
    try:
        data=json.loads(path.read_text(encoding='utf-8-sig'))
        values=data['orientation_accuracy_pct']
        if not isinstance(values,list) or len(values)!=3:
            raise ValueError('Нужны нормативы трёх этапов.')
        return [accuracy_norm(value) for value in values]
    except (KeyError,TypeError,json.JSONDecodeError) as exc:
        raise ValueError('Некорректный файл нормативов поверхности.') from exc


def write_norms(directory, values):
    if len(values)!=3:
        raise ValueError('Нужны нормативы трёх этапов.')
    parsed=[accuracy_norm(value) for value in values]
    path=Path(directory)/NORM_FILE
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps({'orientation_accuracy_pct':parsed},ensure_ascii=False,indent=2),encoding='utf-8')
    temporary.replace(path)
    return parsed


def normalize_surface(raw, norms):
    """Return a new display matrix; original results, JSON and Excel stay untouched."""
    if len(norms)!=3:
        raise ValueError('Нужны нормативы трёх этапов.')
    result={code:list(values) for code,values in raw.items()}
    result['B']=[]
    missing=[]
    for index, value in enumerate(raw.get('B',[None]*3)):
        norm=accuracy_norm(norms[index])
        if norm is None:
            result['B'].append(None)
            missing.append(index+1)
        else:
            result['B'].append(value/(norm/100) if value is not None else None)
    return result,missing


def show_norm_editor(owner):
    if not owner.admin_authenticated:
        return owner.show_mode_selection()
    directory=owner.groups.directory(owner.editing_group_number)
    top=tk.Toplevel(owner.root)
    top.title(f'Нормативы поверхности · группа №{owner.editing_group_number}')
    top.geometry(f'{min(800,owner.root.winfo_screenwidth()-60)}x{min(520,owner.root.winfo_screenheight()-100)}+30+30');top.minsize(580,380)
    top.transient(owner.root);top.grab_set()
    content=ttk.Frame(top,padding=20);content.pack(fill='both',expand=True)
    content.columnconfigure(1,weight=1)
    ttk.Label(content,text=f'Группа №{owner.editing_group_number}: точность пространственной ориентации',
        font=('Segoe UI',12,'bold'),wraplength=720).grid(row=0,column=0,columnspan=2,sticky='w',pady=(0,12))
    ttk.Label(content,text='Задайте норматив каждого этапа в процентах. Пустое поле означает, что норматив ещё не задан.\n'
        'На поверхности точность делится на норматив; нормативная плоскость равна 1,0.\n'
        'Исходные результаты и расчёты методик сохраняются.',wraplength=720,justify='left').grid(row=1,column=0,columnspan=2,sticky='w',pady=(0,14))
    status=tk.StringVar()
    try:
        values=read_norms(directory)
    except (ValueError,OSError) as exc:
        values=[None]*3;status.set(str(exc))
    fields=[]
    for index,value in enumerate(values,1):
        variable=tk.StringVar(value='' if value is None else f'{value:g}')
        fields.append(variable)
        ttk.Label(content,text=f'Этап {index} · норматив точности, %').grid(row=index+1,column=0,sticky='w',padx=(0,20),pady=6)
        ttk.Entry(content,textvariable=variable,width=16).grid(row=index+1,column=1,sticky='w',pady=6)
    ttk.Label(content,textvariable=status,wraplength=720,foreground='#a21c21').grid(row=5,column=0,columnspan=2,sticky='w',pady=10)
    buttons=ttk.Frame(content);buttons.grid(row=6,column=0,columnspan=2,sticky='e',pady=(8,0))
    def save():
        try:
            write_norms(directory,[field.get() for field in fields])
            owner.research_status_var.set(f'Нормативы поверхности группы №{owner.editing_group_number} сохранены.')
            owner.style_research_actions()
            top.destroy()
        except (ValueError,OSError) as exc:
            status.set(str(exc))
    ttk.Button(buttons,text='Сохранить',command=save).pack(side='left',padx=(0,8))
    ttk.Button(buttons,text='Отмена',command=top.destroy).pack(side='left')
    top._norm_fields=fields;top._norm_status=status
    return top
