"""Researcher UI for numbered groups, settings and participant assignments."""
import tkinter as tk
from tkinter import ttk


def show_group_manager(owner):
    if not owner.admin_authenticated:
        return owner.show_mode_selection()
    top = tk.Toplevel(owner.root)
    top.title('Группы и участники')
    top.geometry(f'{min(1100, owner.root.winfo_screenwidth()-60)}x{min(730, owner.root.winfo_screenheight()-100)}+20+20')
    top.minsize(640, 440)
    top.transient(owner.root)
    top.grab_set()
    notebook = ttk.Notebook(top)
    notebook.pack(fill='both', expand=True, padx=14, pady=14)
    group_page, member_page = ttk.Frame(notebook, padding=12), ttk.Frame(notebook, padding=12)
    notebook.add(group_page, text='Группы')
    notebook.add(member_page, text='Участники и назначение группы')
    for page in (group_page, member_page):
        page.columnconfigure(0, weight=1)
        page.rowconfigure(1, weight=1)
    ttk.Label(group_page, text='Группа задаёт набор методик и отдельные параметры. Настройки новой группы копируются из выбранной.').grid(row=0, column=0, sticky='w', pady=(0, 8))
    groups = ttk.Treeview(group_page, columns=('number','variant','members'), show='headings', selectmode='browse')
    for key, label, width in (('number','Номер группы',150),('variant','Вариант прохождения',260),('members','Участников',140)):
        groups.heading(key,text=label); groups.column(key,width=width,stretch=True)
    groups.grid(row=1, column=0, sticky='nsew')
    group_scroll=ttk.Scrollbar(group_page,orient='vertical',command=groups.yview)
    group_scroll.grid(row=1,column=1,sticky='ns')
    groups.configure(yscrollcommand=group_scroll.set)
    form = ttk.Frame(group_page)
    form.grid(row=2, column=0, sticky='ew', pady=10)
    number, variant = tk.StringVar(), tk.StringVar(value='6')
    ttk.Label(form,text='Номер новой группы').grid(row=0,column=0,sticky='w',padx=(0,8))
    ttk.Entry(form,textvariable=number,width=12).grid(row=0,column=1,padx=(0,16))
    ttk.Label(form,text='Количество тестов').grid(row=0,column=2,sticky='w',padx=(0,8))
    ttk.Combobox(form,textvariable=variant,values=('4','6'),state='readonly',width=6).grid(row=0,column=3)
    status = tk.StringVar()
    group_choice = tk.StringVar()
    reload_editor = [False]

    def refresh():
        selected = groups.selection()
        groups.delete(*groups.get_children())
        for row in owner.groups.list_groups():
            groups.insert('', 'end', iid=str(row['number']), values=(row['number'], 'Тесты 1, 2, 3, 6' if row['test_count']==4 else 'Тесты 1–6', row['participants']))
        if selected and groups.exists(selected[0]):
            groups.selection_set(selected[0])
        members.delete(*members.get_children())
        for row in owner.groups.participants():
            fields = row['profile']
            members.insert('', 'end', iid=row['participant_id'], values=(row['login'], fields.get('name',''),
                str(row['group']) if row['group'] else 'Ожидает назначения', fields.get('age',''),
                fields.get('flight_hours',''), fields.get('aircraft_type',''), fields.get('position',''), fields.get('education',''), fields.get('gender','')))
        choices.configure(values=[str(row['number']) for row in owner.groups.list_groups()])
        if not group_choice.get():
            group_choice.set(str(owner.editing_group_number))

    def selected_group():
        if not groups.selection():
            raise ValueError('Выберите группу в списке.')
        return int(groups.selection()[0])

    def perform(action):
        try:
            action()
            if top.winfo_exists():
                refresh()
        except (ValueError, OSError) as exc:
            status.set(str(exc))

    def create():
        template = int(groups.selection()[0]) if groups.selection() else owner.editing_group_number
        row = owner.groups.create(number.get(), int(variant.get()), template)
        status.set(f"Группа {row['number']} создана. Настройки скопированы из группы {template}.")

    def update_variant():
        selected = selected_group()
        owner.groups.set_variant(selected, int(variant.get()))
        reload_editor[0] = selected == owner.editing_group_number
        status.set(f'Вариант группы {selected} сохранён. Он применяется при следующем входе участника.')

    def edit():
        selected = selected_group()
        top.destroy()
        owner.select_group_settings(selected)

    def close():
        top.destroy()
        if reload_editor[0] and owner.admin_authenticated:
            owner.build_researcher_ui()

    bar = ttk.Frame(group_page)
    bar.grid(row=3,column=0,sticky='w')
    ttk.Button(bar,text='Создать группу',command=lambda:perform(create)).pack(side='left',padx=(0,8))
    ttk.Button(bar,text='Применить вариант к выбранной',command=lambda:perform(update_variant)).pack(side='left',padx=(0,8))
    ttk.Button(bar,text='Настройки выбранной группы',command=lambda:perform(edit)).pack(side='left')
    groups.bind('<<TreeviewSelect>>',lambda e: variant.set(str(owner.groups.get(int(groups.selection()[0]))['test_count'])) if groups.selection() else None)
    ttk.Label(member_page,text='Новые регистрации ожидают назначения группы. Можно выделить нескольких участников.').grid(row=0,column=0,sticky='w',pady=(0,8))
    member_holder = ttk.Frame(member_page)
    member_holder.grid(row=1,column=0,sticky='nsew')
    member_holder.columnconfigure(0,weight=1); member_holder.rowconfigure(0,weight=1)
    keys=('login','name','group','age','hours','aircraft','position','education','gender')
    members = ttk.Treeview(member_holder,columns=keys,show='headings',selectmode='extended')
    for key,label,width in zip(keys,('Логин','ФИО','Группа / статус','Возраст','Налёт','Тип ВС','Должность','Образование','Пол'),(110,250,180,70,90,140,140,160,100)):
        members.heading(key,text=label); members.column(key,width=width,stretch=False)
    members.grid(row=0,column=0,sticky='nsew')
    horizontal=ttk.Scrollbar(member_holder,orient='horizontal',command=members.xview)
    horizontal.grid(row=1,column=0,sticky='ew')
    vertical=ttk.Scrollbar(member_holder,orient='vertical',command=members.yview)
    vertical.grid(row=0,column=1,sticky='ns')
    members.configure(xscrollcommand=horizontal.set,yscrollcommand=vertical.set)
    assign_bar=ttk.Frame(member_page)
    assign_bar.grid(row=2,column=0,sticky='w',pady=12)
    ttk.Label(assign_bar,text='Назначить группу №').pack(side='left',padx=(0,8))
    choices=ttk.Combobox(assign_bar,textvariable=group_choice,state='readonly',width=12)
    choices.pack(side='left',padx=(0,10))
    def assign():
        if not members.selection():
            raise ValueError('Выберите участника или нескольких участников.')
        owner.groups.assign_many(members.selection(),group_choice.get())
        status.set(f'Группа {group_choice.get()} назначена. Участники могут войти в программу.')
    ttk.Button(assign_bar,text='Назначить группу',command=lambda:perform(assign)).pack(side='left')
    ttk.Button(assign_bar,text='Обновить список',command=refresh).pack(side='left',padx=8)
    ttk.Label(top,textvariable=status,wraplength=900).pack(fill='x',padx=16,pady=(0,8))
    ttk.Button(top,text='Закрыть',command=close).pack(anchor='e',padx=16,pady=(0,12))
    top.protocol('WM_DELETE_WINDOW',close)
    refresh()
    top._groups_tree, top._members_tree = groups, members
    top._group_var, top._number_var, top._variant_var = group_choice, number, variant
    return top
