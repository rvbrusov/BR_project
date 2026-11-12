"""Display synthetic stage results from the same account data as the surface.

Demo payloads contain three representative measurements, rather than raw trial
histories. Do not send them to legacy detail renderers which substitute zero
for absent trial counts and per-stage reports.
"""
import tkinter as tk
from tkinter import ttk
import aviatest_v4 as v
from surface_view import surface_data


def show_demo_result(owner,code,payload):
    raw,values,norms,missing,group,error=surface_data(owner)
    index=v.ORDER.index(code)+1
    title=dict(zip(v.ORDER,v.TITLES))[code]
    name=owner.current_profile.name
    previous=owner.root.grab_current()
    top=tk.Toplevel(owner.root)
    top.title(f'Тест {index} · {title} · {name}')
    top.geometry('920x430');top.minsize(760,360)
    top.transient(owner.root);top.grab_set()
    body=ttk.Frame(top,padding=20);body.pack(fill='both',expand=True)
    ttk.Label(body,text=f'Тест {index} · {title}',font=('Arial',18,'bold'),wraplength=850).pack(anchor='w')
    ttk.Label(body,text=name,wraplength=850).pack(anchor='w',pady=(8,4))
    ttk.Label(body,text='Демонстрационные данные · min / med / max',wraplength=850).pack(anchor='w',pady=(0,16))
    columns=('stage','raw','norm','relative')
    table=ttk.Treeview(body,columns=columns,show='headings',height=3)
    for key,caption in zip(columns,('Уровень сложности','Точность, %' if code=='B' else 'Приведённый темп','Норматив','Результат / норматив')):
        table.heading(key,text=caption);table.column(key,width=190,anchor='center')
    def numeric(value):return 'нет данных' if value is None else f'{value:.3f}'.replace('.',',')
    for stage,label in enumerate(('min','med','max')):
        original=raw[code][stage]
        original=original*100 if code=='B' and original is not None else original
        norm=norms[stage] if code=='B' else 1.
        table.insert('','end',values=(label,numeric(original),numeric(norm),numeric(values[code][stage])))
    table.pack(fill='x',pady=(0,12))
    ttk.Label(body,text='Показаны сохранённые демонстрационные значения. Истории отдельных проб для этих примеров нет.',wraplength=850).pack(anchor='w')
    if error:ttk.Label(body,text=error,wraplength=850).pack(anchor='w')
    def close():
        top.destroy()
        if previous is not None and previous.winfo_exists():previous.grab_set()
    ttk.Button(body,text='Закрыть',command=close).pack(anchor='e',pady=(16,0))
    top.protocol('WM_DELETE_WINDOW',close);top.bind('<Escape>',lambda e:close())
    top._demo_result_table=table
    top._demo_code=code
    top._demo_values=list(values[code])
    top._demo_participant_id=getattr(owner.current_profile,'participant_id','')
    return top
