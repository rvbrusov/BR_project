"""Interactive measured surface styled after the approved Boris reference."""
import math
import tkinter as tk
from tkinter import ttk, font as tkfont
from PIL import Image,ImageDraw,ImageTk
import aviatest_v4 as v
from surface_norms import normalize_surface,read_norms
from storage import participant_directory
from types import SimpleNamespace


from approved_surface import SurfaceCanvas


def surface_data(owner):
    identifier=getattr(owner.current_profile,'participant_id','')
    # A researcher may still hold a different participant store: select by stable account ID.
    store=(v.base.UserProgressStore(participant_directory(owner.data_root,identifier))
           if identifier and hasattr(owner,'data_root') else owner.progress_store)
    raw=v.collect_values(SimpleNamespace(progress_store=store),owner.current_profile)
    group=owner.groups.membership(identifier) if identifier and hasattr(owner,'groups') else None
    norms=[None]*3
    error=''
    if group:
        try:
            norms=read_norms(owner.groups.directory(group['number']))
        except (ValueError,OSError) as exc:
            error=f'Некорректные нормативы поверхности группы: {exc}'
    payload=store.get_test_result(owner.current_profile,'B') or {}
    if payload.get('data_source')=='synthetic_demo':
        demo=payload.get('demo_orientation_norm_pct',[])
        if len(demo)==3:norms=[n if n is not None else demo[i] for i,n in enumerate(norms)]
    values,missing=normalize_surface(raw,norms)
    return raw,values,norms,missing,group,error


def show_integral(owner):
    if not owner.current_profile:
        return
    raw,values,norms,missing,group,error=surface_data(owner)
    order=tuple(getattr(owner,'surface_order',v.ORDER))
    group_label=f"Группа №{group['number']} · " if group else ''
    variant_label='4 методики' if len(order)==4 else '6 методик'
    profile_name=owner.current_profile.name
    previous_grab=owner.root.grab_current()
    top=tk.Toplevel(owner.root)
    top.title(f'Авиатест 4.21 · {profile_name} · {group_label}{variant_label} · интегральная поверхность')
    top.configure(bg='#f3f6fa')
    top.geometry(f'{owner.root.winfo_screenwidth()}x{owner.root.winfo_screenheight()}+0+0')
    top.minsize(820,520)
    top.transient(owner.root)
    top.grab_set()
    top.attributes('-fullscreen',True)
    tk.Label(top,text='ПСИХИЧЕСКАЯ РАБОТОСПОСОБНОСТЬ',font=('Arial',-32),bg='white',fg='#101820').pack(fill='x',pady=(8,0))
    tk.Label(top,text='(топологическая поверхность)',font=('Arial',-30),bg='white',fg='#101820').pack(fill='x',pady=(0,24))
    profile_bar=tk.Frame(top,bg='#eef3f8',padx=10,pady=3)
    profile_bar.pack(fill='x')
    toolbar=tk.Frame(top,bg='#eef3f8',padx=10,pady=5)
    toolbar.pack(fill='x')
    chart=SurfaceCanvas(top,values,order=order,cursor='fleur')
    heading=tk.Label(profile_bar,text=f'{group_label}{variant_label} · {profile_name}',
        bg='#eef3f8',fg='#163456',font=('Segoe UI',10,'bold'),anchor='w')
    heading.pack(side='left',fill='x',expand=True)
    def resize_heading(event):
        # Keep the compact toolbar available even for long participant names.
        heading.configure(wraplength=max(140,event.width-650))
    toolbar.bind('<Configure>',resize_heading)
    def close():
        top.destroy()
        if previous_grab is not None and previous_grab.winfo_exists():
            previous_grab.grab_set()
    def fullscreen():
        top.attributes('-fullscreen',not bool(top.attributes('-fullscreen')))
    def toggle_labels():
        chart.labels=labels.get();chart.redraw()
    labels=tk.BooleanVar(value=True)
    plane=tk.BooleanVar(value=True)
    def toggle_plane():
        chart.plane=plane.get();chart.redraw()
    def control(text,command):
        widget=tk.Button(toolbar,text=text,command=command,font=('Segoe UI',10),
            bg='#dce4ed',fg='#19334e',activebackground='#ccd7e4',activeforeground='#19334e',
            relief='flat',bd=0,padx=10,pady=5)
        widget.pack(side='left',padx=(6,0))
        return widget
    control('Исходный вид',chart.reset_view)
    tk.Checkbutton(toolbar,text='Значения',variable=labels,command=toggle_labels,
        bg='#eef3f8',activebackground='#eef3f8',font=('Segoe UI',10)).pack(side='left',padx=6)
    tk.Checkbutton(toolbar,text='Плоскость нормы',variable=plane,command=toggle_plane,
        bg='#eef3f8',activebackground='#eef3f8',font=('Segoe UI',10)).pack(side='left',padx=6)
    def show_table():
        table_top=tk.Toplevel(top)
        table_top.title('Исходные значения и сравнение с нормой')
        table_top.geometry(f'{min(1100,top.winfo_screenwidth()-60)}x{min(720,top.winfo_screenheight()-100)}+20+20')
        table_top.transient(top);table_top.grab_set()
        holder=ttk.Frame(table_top,padding=12);holder.pack(fill='both',expand=True)
        holder.columnconfigure(0,weight=1);holder.rowconfigure(0,weight=1)
        keys=('method','stage','raw','norm','relative')
        table=ttk.Treeview(holder,columns=keys,show='headings')
        for key,title,width in zip(keys,('Методика','Этап','Исходный результат','Норматив','Отношение к норме'),(270,100,190,160,180)):
            table.heading(key,text=title);table.column(key,width=width,stretch=True)
        table.grid(row=0,column=0,sticky='nsew')
        scroll=ttk.Scrollbar(holder,orient='vertical',command=table.yview)
        scroll.grid(row=0,column=1,sticky='ns');table.configure(yscrollcommand=scroll.set)
        titles=dict(zip(v.ORDER,v.TITLES))
        for code in order:
            for stage in range(3):
                original=raw[code][stage];relative=values[code][stage]
                original_text='нет данных' if original is None else f'{original*100:.2f} %' if code=='B' else f't = {original:.3f}'
                norm_text=('не задан' if norms[stage] is None else f'{norms[stage]:g} %') if code=='B' else 't = 1,0'
                relative_text='нет норматива' if code=='B' and norms[stage] is None else 'нет данных' if relative is None else f'{relative:.3f}'
                table.insert('','end',values=(titles[code],('MIN','MED','MAX')[stage],original_text,norm_text,relative_text))
        def close_table():
            table_top.destroy()
            if top.winfo_exists():top.grab_set()
        ttk.Button(holder,text='Закрыть',command=close_table).grid(row=1,column=0,columnspan=2,sticky='e',pady=(10,0))
        table_top.protocol('WM_DELETE_WINDOW',close_table)
        table_top.bind('<Escape>',lambda e:close_table() or 'break')
        table_top._data_table=table
        return table_top
    control('Таблица',show_table)
    control('Окно / весь экран',fullscreen)
    control('Закрыть',close)
    message='Норма = 1,0 · ниже — хуже, выше — лучше · слева — методики; справа — min / med / max · мышь — вращение, колесо — масштаб'
    if missing and 'B' in order:
        message+=' · Точность теста 6: норматив не задан для этапов '+', '.join(map(str,missing))+'; исходные значения — в таблице'
    if getattr(owner.current_profile,'participant_id',''):
        b=v.base.UserProgressStore(participant_directory(owner.data_root,owner.current_profile.participant_id)).get_test_result(owner.current_profile,'B') or {}
        if b.get('data_source')=='synthetic_demo' and b.get('demo_orientation_norm_pct') and group:
            try:configured=read_norms(owner.groups.directory(group['number']))
            except (ValueError,OSError):configured=[]
            if any(x is None for x in configured):
                message+=' · ДЕМО: условный норматив точности 80%; для реальных результатов не применяется'
    if error:message+=' · '+error
    status=tk.Label(top,text=message,font=('Segoe UI',9),fg='#536174',bg='#eef3f8',anchor='w',justify='left',padx=10,pady=4)
    status.pack(side='bottom',fill='x')
    status.bind('<Configure>',lambda e:status.configure(wraplength=max(500,e.width-20)))
    chart.pack(fill='both',expand=True)
    top.bind('<Escape>',lambda e:close() or 'break')
    top.bind('<F11>',lambda e:fullscreen() or 'break')
    top.protocol('WM_DELETE_WINDOW',close)
    top._surface,top._surface_raw,top._surface_norms=chart,raw,norms
    top._surface_participant_id=getattr(owner.current_profile,'participant_id','')
    top._surface_name=profile_name
    top._show_table=show_table
    return top
