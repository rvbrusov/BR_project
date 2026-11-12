"""Mode selection and authenticated navigation around the unchanged method engine."""
import tkinter as tk
import sqlite3
from tkinter import messagebox, ttk
from pathlib import Path

from accounts import AccountStore, account_profile, registration_profile, verify_admin
from storage import participant_directory, seed_configs
from demo_accounts import ensure_demo_accounts
from groups import GroupStore, group_progress_store
from group_manager import show_group_manager
from surface_norms import show_norm_editor
from contextlib import contextmanager


def install_modes(v):
    from display_names import install_runtime_names
    install_runtime_names(v)
    base = v.base
    if getattr(base, '_modes44_installed', False):
        return
    base._modes44_installed = True
    previous_app = base.StartPageApp
    previous_find = base._fixed416_find_progress_key_for_profile
    base._fixed416_find_progress_key_for_profile = lambda data, profile: (
        profile.key if getattr(profile, 'participant_id', '') else previous_find(data, profile))
    previous_participant = base._fixed408_participant_dict

    def participant(profile):
        result = previous_participant(profile)
        if getattr(profile, 'participant_id', ''):
            result['participant_id'] = profile.participant_id
        return result
    base._fixed408_participant_dict = participant

    class Catalog(base.UserProgressStore):
        def _load(self):
            records = super()._load()
            for identifier, fields in AccountStore(self.base_dir).profiles():
                directory = participant_directory(self.base_dir, identifier)
                if directory.exists():
                    records.update(base.UserProgressStore(directory)._load())
            return records

        def _save(self, records):
            accounts = AccountStore(self.base_dir).profiles()
            account_keys = {'account:' + identifier for identifier, _ in accounts}
            super()._save({key: value for key, value in records.items() if key not in account_keys})
            for identifier, fields in accounts:
                directory = participant_directory(self.base_dir, identifier)
                key = 'account:' + identifier
                if directory.exists() or key in records:
                    base.UserProgressStore(directory)._save({key: records[key]} if key in records else {})

    previous_summaries = base._fixed416_all_user_summaries

    def summaries(store):
        if not isinstance(store, Catalog):
            return previous_summaries(store)
        rows = previous_summaries(base.UserProgressStore(store.base_dir))
        for identifier, fields in AccountStore(store.base_dir).profiles():
            profile = account_profile(base, identifier, fields)
            directory = participant_directory(store.base_dir, identifier)
            record = base.UserProgressStore(directory)._load().get(profile.key)
            if record:
                record = dict(record)
                record[base._FIXED416_SUMMARY_KEY] = profile.key
                rows.append((profile, record))
        return rows
    base._fixed416_all_user_summaries = summaries

    previous_home = v.rb.RedBlackApp.show_home
    previous_settings = v.rb.RedBlackApp.show_settings

    def chkt_home(child):
        previous_home(child)
        if not getattr(child.root, '_aviatest_research_authorized', False):
            for widget in list(descendants(child.root)):
                if isinstance(widget, tk.Button) and widget.cget('text') == 'НАСТРОЙКИ НОРМАТИВОВ':
                    widget.destroy()

    def chkt_settings(child):
        if getattr(child.root, '_aviatest_research_authorized', False):
            return previous_settings(child)
        messagebox.showerror('Доступ закрыт', 'Для изменения нормативов войдите в исследовательскую версию.', parent=child.root)
    v.rb.RedBlackApp.show_home = chkt_home
    v.rb.RedBlackApp.show_settings = chkt_settings
    previous_dirty = base._fixed425_set_settings_dirty

    def settings_dirty(owner, dirty):
        previous_dirty(owner, dirty)
        if getattr(owner, 'admin_authenticated', False) and hasattr(owner, 'research_save_btn'):
            owner.style_research_actions()
    base._fixed425_set_settings_dirty = settings_dirty

    class ModeApp(previous_app):
        def __init__(self, root):
            self.data_root = Path(base._runtime_app_dir())
            self.accounts = AccountStore(self.data_root)
            ensure_demo_accounts(v, self.data_root)
            self.groups = GroupStore(self.data_root)
            self.editing_group_number = 1
            self.active_group = None
            self.allowed_codes = tuple('ABCDEF')
            self.surface_order = v.ORDER
            self.admin_authenticated = False
            self.active_account = None
            self.active_group = None
            self.allowed_codes = tuple('ABCDEF')
            self.surface_order = v.ORDER
            self._initialized_modes = False
            self._new_submit = None
            super().__init__(root)
            self._initialized_modes = True
            self.root.minsize(620, 400)
            self.root.title('Авиатест 4.21 — МИП')
            self.root.iconbitmap(str(base._runtime_resource_dir()/'program_icon.ico'))
            self.show_mode_selection()

        def clear_session(self):
            self.current_profile = self.current_session = None
            self.active_account = None
            self.admin_authenticated = False
            self.researcher_mode_enabled = False
            self.base_dir = self.data_root
            self.progress_store = Catalog(self.data_root)
            self.logger = base.ParticipantsLogger(self.data_root)
            for variable in getattr(self, 'fields', {}).values():
                variable.set('')
            self.fields = {}

        def page(self, title, subtitle=''):
            self.destroy_main()
            self.view_mode = 'mode44'
            self._new_submit = None
            self.root.title('Авиатест 4.21 — МИП')
            self.main = tk.Frame(self.root, bg='#eef3f8')
            self.main.pack(fill='both', expand=True)
            self.main.columnconfigure(0, weight=1)
            self.main.rowconfigure(1, weight=1)
            heading = tk.Frame(self.main, bg='#eef3f8')
            heading.grid(row=0, column=0, sticky='ew', padx=24, pady=(16, 6))
            tk.Label(heading, text=title, bg='#eef3f8', fg='#163456',
                     font=('Segoe UI', 19, 'bold')).pack(anchor='w')
            if subtitle:
                label = tk.Label(heading, text=subtitle, bg='#eef3f8', justify='left', anchor='w', font=('Segoe UI', 10))
                label.pack(fill='x')
                heading.bind('<Configure>', lambda e: label.configure(wraplength=max(200, e.width)))
            holder = tk.Frame(self.main, bg='#eef3f8')
            holder.grid(row=1, column=0, sticky='nsew', padx=24)
            holder.columnconfigure(0, weight=1)
            holder.rowconfigure(0, weight=1)
            canvas = tk.Canvas(holder, bg='#eef3f8', highlightthickness=0)
            canvas.grid(row=0, column=0, sticky='nsew')
            scroll = ttk.Scrollbar(holder, orient='vertical', command=canvas.yview)
            scroll.grid(row=0, column=1, sticky='ns')
            canvas.configure(yscrollcommand=scroll.set)
            body = tk.Frame(canvas, bg='#eef3f8')
            body.columnconfigure(1, weight=1)
            item = canvas.create_window((0, 0), window=body, anchor='nw')
            body.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
            canvas.bind('<Configure>', lambda e: canvas.itemconfigure(item, width=e.width))
            def wheel(event):
                canvas.yview_scroll(-int(event.delta / 120), 'units')
            self.main.bind('<MouseWheel>', wheel)
            self.page_canvas = canvas
            self.fields = {}
            self.form_body = body
            footer = tk.Frame(self.main, bg='#eef3f8')
            footer.grid(row=2, column=0, sticky='ew', padx=24, pady=(6, 16))
            self.error_var = tk.StringVar()
            error = tk.Label(footer, textvariable=self.error_var, bg='#eef3f8', fg='#a21c21', justify='left', anchor='w', font=('Segoe UI', 10))
            error.pack(fill='x', pady=(0, 8))
            footer.bind('<Configure>', lambda e: error.configure(wraplength=max(200, e.width)))
            self.actions = tk.Frame(footer, bg='#eef3f8')
            self.actions.pack(fill='x')
            return body

        def action(self, label, command):
            primary = label in ('Войти', 'Зарегистрироваться')
            button = tk.Button(self.actions, text=label, command=command, font=('Segoe UI', 10),
                width=max(12, len(label) + 2), height=1, padx=8, pady=4, bd=0, relief='flat',
                bg='#245da8' if primary else '#dce4ed', fg='white' if primary else '#19334e',
                activebackground='#1c4b89' if primary else '#ccd7e4',
                activeforeground='white' if primary else '#19334e')
            button.pack(side='left', padx=(0, 10))
            return button

        def field(self, key, label, secret=False, choices=None):
            row = len(self.fields)
            variable = tk.StringVar(value=choices[0] if choices else '')
            self.fields[key] = variable
            tk.Label(self.form_body, text=label, bg='#eef3f8', font=('Segoe UI', 11), anchor='w').grid(
                row=row, column=0, sticky='w', padx=(0, 18), pady=5)
            if choices:
                entry = ttk.Combobox(self.form_body, textvariable=variable, values=choices, state='readonly', font=('Segoe UI', 11))
            else:
                entry = tk.Entry(self.form_body, textvariable=variable, show='●' if secret else '', font=('Segoe UI', 11))
            entry.grid(row=row, column=1, sticky='ew', pady=5, ipady=3, padx=(0, 8))
            if secret:
                from password_toggle import add_toggle
                add_toggle(entry).grid(row=row,column=2,padx=(0,4),pady=5)
            # Per-widget bindings make scroll work while typing or hovering labels.
            entry.bind('<MouseWheel>', lambda e: self.page_canvas.yview_scroll(-int(e.delta / 120), 'units'))
            entry.bind('<FocusIn>', lambda e, r=row: self.page_canvas.yview_moveto(max(0, r - 2) / max(1, len(self.fields))))
            if row == 0:
                entry.focus_set()
            return entry

        def show_mode_selection(self):
            self.clear_session()
            self.show_login()

        def show_user_choice(self):
            self.show_mode_selection()

        def identity_header(self, heading, scale=1., padding=True):
            for child in heading.winfo_children():
                child.destroy()
            banner = tk.Frame(heading, bg='#fffed6')
            banner.pack(anchor='center',pady=(8,20) if padding else 0)
            try:
                from PIL import Image, ImageTk
                source = base._runtime_resource_dir() / 'assets' / 'circle.png'
                self._login_emblem = ImageTk.PhotoImage(Image.open(source).resize((round(96*scale),round(96*scale)),Image.Resampling.LANCZOS))
                tk.Label(banner, image=self._login_emblem, bg='#fffed6').grid(row=0,column=0,padx=round(8*scale),pady=round(8*scale))
            except OSError:
                tk.Label(banner,text='СПР',font=('Segoe UI',20,'bold'),bg='#fffed6').grid(row=0,column=0,padx=12)
            tk.Label(banner, text='СИСТЕМНЫЙ ТЕСТ\nПСИХИЧЕСКОЙ\nРАБОТОСПОСОБНОСТИ',
                font=('Segoe UI',round(16*scale),'bold'), bg='#fffed6', fg='#152c42', justify='center').grid(row=0,column=1,padx=round(12*scale),pady=round(8*scale))
            extent=round(100*scale)
            mark = tk.Canvas(banner,width=extent,height=extent,bg='#fffed6',highlightthickness=0)
            mark.grid(row=0,column=2,padx=round(8*scale))
            mark.create_oval(5*scale,5*scale,95*scale,95*scale,fill='#fffed6',outline='#163456',width=max(2,3*scale))
            mark.create_text(extent/2,extent/2,text='СПР',font=('Times New Roman',round(24*scale),'bold'),fill='#152c42')
            return banner

        def show_login(self, admin=False):
            self.page('')
            # Keep the complete login composition centered, without a scroll area.
            for child in self.main.winfo_children():child.destroy()
            self.main.unbind('<MouseWheel>')
            self.login_group=tk.Frame(self.main,bg='#eef3f8')
            self.login_group.place(relx=.5,rely=.5,anchor='center')
            self.login_header=tk.Frame(self.login_group,bg='#eef3f8')
            self.login_header.pack()
            self.form_body=tk.Frame(self.login_group,bg='#eef3f8')
            self.form_body.pack()
            self._login_labels=[];self._login_entries=[]
            for row,(key,label) in enumerate((('login','Логин'),('password','Пароль'))):
                self.fields[key]=tk.StringVar()
                widget=tk.Label(self.form_body,text=label,bg='#eef3f8',anchor='w')
                widget.grid(row=row,column=0,sticky='w',padx=(0,22),pady=6)
                self._login_labels.append(widget)
                entry=tk.Entry(self.form_body,textvariable=self.fields[key],show='●' if key=='password' else '',
                    width=28,bg='white',relief='flat',bd=0,highlightthickness=1,
                    highlightbackground='#bbc3cb',highlightcolor='#245da8')
                entry.grid(row=row,column=1,sticky='ew',pady=6,ipady=4)
                self._login_entries.append(entry)
            from password_toggle import add_toggle
            self._login_eye=add_toggle(self._login_entries[1])
            self._login_eye.grid(row=1,column=2,padx=(6,0))
            self.actions=tk.Frame(self.form_body,bg='#eef3f8')
            self.actions.grid(row=2,column=0,columnspan=3,pady=(18,12))
            def submit():
                login, password = self.fields['login'].get(), self.fields['password'].get()
                try:
                    if verify_admin(login, password):
                        self.fields['password'].set('')
                        self.clear_session()
                        self.admin_authenticated = True
                        self.build_researcher_ui()
                    else:
                        record = self.accounts.authenticate(login, password)
                        if not record:
                            self.error_var.set('Неверный логин или пароль')
                            return
                        self.fields['password'].set('')
                        self.enter_account(*record)
                        self.show_user_intro()
                except (OSError, ValueError, sqlite3.Error) as exc:
                    self.error_var.set(f'Не удалось открыть учётную запись: {exc}')
            self._new_submit = submit
            self.action('Войти', submit)
            self.action('Выход', self.exit_app)
            self._login_link=tk.Button(self.form_body,text='Регистрация',command=self.show_registration,
                bg='#eef3f8',fg='#245da8',activebackground='#eef3f8',activeforeground='#1c4b89',bd=0,cursor='hand2')
            self._login_link.grid(row=3,column=0,columnspan=3,pady=(4,0))
            self._login_error=tk.Label(self.form_body,textvariable=self.error_var,bg='#eef3f8',fg='#a21c21',justify='center')
            self._login_error.grid(row=4,column=0,columnspan=3,pady=(6,0))
            from welcome_ui import setup_login
            setup_login(self,base._runtime_resource_dir())
            self._login_size=None
            self.main.bind('<Configure>',self.layout_login)
            self.layout_login()
            self._login_entries[0].focus_set()

        def layout_login(self,event=None):
            from welcome_ui import layout_login
            layout_login(self)

        def show_user_intro(self):
            from welcome_ui import show_user_intro
            show_user_intro(self)

        def show_registration(self):
            self.page('')
            heading=self.main.grid_slaves(row=0)[0]
            self.identity_header(heading)
            tk.Label(heading,text='Регистрация',bg='#eef3f8',fg='#163456',font=('Segoe UI',16,'bold')).pack(anchor='w',pady=(0,6))
            for key, label in (('name', 'ФИО'), ('age', 'Возраст, полных лет'), ('education', 'Образование')):
                self.field(key, label)
            self.field('gender', 'Пол', choices=('Мужской', 'Женский'))
            self.field('login', 'Логин')
            self.field('password', 'Пароль', secret=True)
            self.field('confirmation', 'Подтверждение пароля', secret=True)
            self._new_submit = self.register
            self.action('Зарегистрироваться', self.register)
            self.action('Назад', self.show_user_choice)

        def register(self):
            try:
                profile=registration_profile(base,{key:variable.get() for key,variable in self.fields.items()})
                record = self.accounts.register(self.fields['login'].get(), self.fields['password'].get(),
                                                self.fields['confirmation'].get(), profile)
                self.fields['password'].set('')
                self.fields['confirmation'].set('')
                login = self.fields['login'].get()
                self.show_mode_selection()
                self.fields['login'].set(login)
                self.error_var.set('Регистрация завершена. Ожидайте назначения группы исследователем.')
            except (ValueError, OSError, sqlite3.Error) as exc:
                self.error_var.set(str(exc))

        def enter_account(self, identifier, fields):
            directory, member = self.groups.prepare_participant(identifier)
            self.allowed_codes = self.groups.codes(identifier)
            self.surface_order = tuple(code for code in v.ORDER if code in self.allowed_codes)
            self.active_group = member
            self.base_dir = directory
            self.progress_store = group_progress_store(base, directory, self.allowed_codes, member)
            self.logger = base.ParticipantsLogger(directory)
            self.admin_authenticated = self.researcher_mode_enabled = False
            self.active_account = identifier
            self.current_profile = account_profile(base, identifier, fields)
            self.current_session = self.make_session(self.current_profile)
            self.progress_store.ensure_user(self.current_profile)
            self.build_menu_ui()

        def build_researcher_ui(self):
            if not self._initialized_modes:
                self.show_mode_selection()
                return
            if not self.admin_authenticated:
                self.show_login(True)
                return
            self.base_dir = self.groups.directory(self.editing_group_number)
            self.progress_store = Catalog(self.data_root)
            super().build_researcher_ui()
            for tab in self.research_tabs.tabs():
                label=self.research_tabs.tab(tab,'text')
                for code in v.ORDER:
                    if label in (f'Тест {code}',f'Тест {code.lower()}'):
                        self.research_tabs.tab(tab,text=base.TEST_LABELS[code])
            count=self.groups.get(self.editing_group_number)['test_count']
            if count==6:
                fifth=ttk.Frame(self.research_tabs,padding=20)
                ttk.Label(fifth,text='Тест 5 · Переключение внимания',font=('Segoe UI',16,'bold')).pack(anchor='w')
                ttk.Label(fifth,text='Красно-чёрные таблицы. Параметры сохраняются для выбранной группы.').pack(anchor='w',pady=(8,16))
                ttk.Button(fifth,text='Открыть настройки теста 5',command=self.open_chkt_settings).pack(anchor='w')
                self.research_tabs.add(fifth,text='Тест 5')
            else:
                for tab in self.research_tabs.tabs():
                    if self.research_tabs.tab(tab,'text') in ('Тест 4','Тест 5'):self.research_tabs.forget(tab)
            tabs=sorted(self.research_tabs.tabs(),key=lambda tab:self.research_tabs.tab(tab,'text'))
            if hasattr(self.research_tabs,'insert'):
                for index,tab in enumerate(tabs):self.research_tabs.insert(index,tab)
            self.research_subtitle.configure(text='Настройки методик и результаты участников. Изменения можно сохранить перед выходом.')
            self.research_next_btn.configure(text='Сохранить настройки', command=self.save_research_settings)
            self.research_exit_btn.configure(text='Выйти из исследовательского режима', command=self.leave_research)
            self.research_status_var.set('')
            self.chkt_settings_btn = tk.Button(self.research_header, text='Тест 5 · ЧКТ', command=self.open_chkt_settings)
            self.chkt_settings_btn.grid(row=0, column=1, sticky='e')
            self.research_header.columnconfigure(1, weight=1)
            self.groups_btn = tk.Button(self.research_header,text='Группы и участники',command=self.open_groups)
            self.groups_btn.grid(row=0,column=2,padx=(10,0))
            self.surface_norms_btn=tk.Button(self.research_actions_top,text='Нормативы поверхности',command=self.open_surface_norms)
            if self.groups.get(self.editing_group_number)['test_count'] == 4:
                self.chkt_settings_btn.grid_remove()
            self.style_research_actions()
            # The legacy notebook hides native tabs and draws a separate bar.
            # Rebuild that visible bar after adding/reordering numbered pages.
            base._fixed416_style_research_tabs(self)

        def save_research_settings(self):
            if not self.admin_authenticated:
                return self.show_login(True)
            try:
                for filename, cfg in self.collect_researcher_configs():
                    base.save_config_dataclass(self.groups.directory(self.editing_group_number), filename, cfg)
                base._fixed425_set_settings_dirty(self, False)
                self.research_status_var.set('Настройки сохранены.')
                self.style_research_actions()
                return True
            except (ValueError, OSError) as exc:
                self.research_status_var.set(str(exc))
                return False

        apply_researcher_and_open_login = save_research_settings

        def leave_research(self):
            if self.admin_authenticated and not base._fixed425_save_open_settings(self, show_error=True):
                return
            self.show_mode_selection()

        def apply_researcher_layout(self):
            super().apply_researcher_layout()
            if self.admin_authenticated:
                self.research_next_btn.configure(text='Сохранить настройки')
                self.research_exit_btn.configure(text='Выйти из исследовательского режима', wraplength=230)
                self.style_research_actions()

        def style_research_actions(self):
            background = '#eef3f8'
            self.main.configure(bg=background)
            self.main.pack_configure(padx=18, pady=14)
            self.research_header.configure(bg=background)
            self.research_header.grid_configure(pady=(0, 6))
            self.research_title.configure(bg=background, fg='#163456', font=('Segoe UI', 20, 'bold'))
            count = self.groups.get(self.editing_group_number)['test_count']
            self.research_subtitle.configure(bg=background, fg='#536174', font=('Segoe UI', 10),
                text=f'Группа №{self.editing_group_number} · тесты 1, 2, 3, 6' if count==4 else f'Группа №{self.editing_group_number} · тесты 1–6', wraplength=1000)
            self.research_subtitle.grid_configure(pady=(0, 12))
            self.research_actions_top.configure(bg=background)
            self.research_actions_top.grid_configure(pady=(0, 12))
            self.research_status.configure(bg=background, font=('Segoe UI', 10))
            if not self.research_status_var.get():
                self.research_status.grid_remove()
            else:
                self.research_status.grid(row=3, column=0, sticky='ew', pady=(0, 8))
            for index, button in enumerate((self.research_exit_btn, self.research_default_btn,
                    self.research_all_results_btn, self.research_next_btn, self.research_save_btn)):
                button.configure(font=('Segoe UI', 10), padx=14, pady=7, width=0, height=1,
                                 bd=0, relief='flat', wraplength=0, bg='#dce4ed', fg='#19334e',
                                 activebackground='#ccd7e4', activeforeground='#19334e')
                button.grid_configure(sticky='w', padx=(0, 8), pady=0)
                self.research_actions_top.grid_columnconfigure(index, weight=0, uniform='')
            self.research_exit_btn.configure(text='Выйти из режима', bg='#a6212d', fg='white',
                activebackground='#861a24', activeforeground='white', disabledforeground='#f0d9dc')
            self.research_default_btn.configure(text='Сбросить настройки')
            self.research_all_results_btn.configure(text='Все результаты')
            self.research_next_btn.configure(text='Сохранить настройки', bg='#245da8', fg='white',
                activebackground='#1c4b89', activeforeground='white')
            # The legacy editor reveals a second Save button when dirty. Keep one action.
            self.research_save_btn.grid_remove()
            self.research_next_btn.grid_configure(column=3)
            self.research_actions_top.grid_columnconfigure(5, weight=1)
            if hasattr(self,'surface_norms_btn') and self.surface_norms_btn.winfo_exists():
                self.surface_norms_btn.configure(font=('Segoe UI',10),bg='#dce4ed',fg='#19334e',
                    activebackground='#ccd7e4',activeforeground='#19334e',relief='flat',bd=0,
                    padx=14,pady=7,height=1,wraplength=0)
                self.surface_norms_btn.grid(row=0,column=4,sticky='w',padx=(0,8))
            if hasattr(self, 'chkt_settings_btn') and self.chkt_settings_btn.winfo_exists():
                self.chkt_settings_btn.configure(font=('Segoe UI', 10), bg='#dce4ed', fg='#19334e',
                    activebackground='#ccd7e4', activeforeground='#19334e', relief='flat', bd=0, padx=12, pady=7)
            if hasattr(self,'groups_btn') and self.groups_btn.winfo_exists():
                self.groups_btn.configure(font=('Segoe UI',10),bg='#245da8',fg='white',
                    activebackground='#1c4b89',activeforeground='white',relief='flat',bd=0,padx=12,pady=7)

        def open_chkt_settings(self):
            if not self.admin_authenticated:
                return self.show_login(True)
            if self.groups.get(self.editing_group_number)['test_count'] != 6:
                return
            v.rb.DATA_DIR = self.groups.directory(self.editing_group_number) / 'red_black_data'
            v.rb.SETTINGS_FILE = v.rb.DATA_DIR / 'settings.json'
            v.rb.RESULTS_FILE = v.rb.DATA_DIR / 'results.json'
            v.rb.CSV_FILE = v.rb.DATA_DIR / 'results.csv'
            top = tk.Toplevel(self.root)
            top._aviatest_research_authorized = True
            top.transient(self.root)
            top.grab_set()
            child = v.rb.RedBlackApp(top)
            child.show_settings()
            top.title('Тест 5 · Настройки красно-чёрных таблиц')

        def open_surface_norms(self):
            if not self.admin_authenticated:
                return self.show_mode_selection()
            if not self.save_research_settings():
                return
            return show_norm_editor(self)

        def build_menu_ui(self):
            if not self.active_account:
                return self.show_mode_selection()
            super().build_menu_ui()
            self.root.title('Авиатест 4.21 — МИП')
            self.settings_btn.grid_remove()
            self.all_results_btn.grid_remove()
            self.exit_btn.configure(text='Выйти из аккаунта', command=self.show_mode_selection)
            self.style_menu_actions()

        def style_menu_actions(self):
            if not self.menu_btn_frame.winfo_exists():
                return
            for index in range(7):
                self.menu_btn_frame.grid_columnconfigure(index, weight=0, uniform='')
            complete = self.progress_store.next_test_code(self.current_profile) is None
            specifications = (
                ('exit_btn', 'Выйти из аккаунта', '#a6212d', '#861a24', 'white'),
                ('continue_btn', 'Общий профиль СПР' if complete else 'Следующий тест', '#245da8', '#1c4b89', 'white'),
                ('restart_btn', 'Начать сначала', '#dce4ed', '#ccd7e4', '#19334e'),
                ('integral_results_btn', 'Интегральный результат', '#245da8', '#1c4b89', 'white'))
            buttons = []
            for attr, label, background, active, foreground in specifications:
                button = getattr(self, attr, None)
                if button is not None and button.winfo_exists():
                    button.configure(text=label, font=('Segoe UI', 10), width=24, height=1,
                        wraplength=0, padx=8, pady=5, bd=0, relief='flat',
                        bg=background, fg=foreground, activebackground=active,
                        activeforeground=foreground, disabledforeground='#748295')
                    buttons.append(button)
            available = self.menu_btn_frame.winfo_width()
            if available <= 1:
                available = max(600, int(self.root.winfo_width() * .65))
            requested = sum(button.winfo_reqwidth() + 8 for button in buttons)
            columns = len(buttons) if requested <= available else 2
            for column in range(columns):
                self.menu_btn_frame.grid_columnconfigure(column, weight=1, uniform='actions442')
            for index, button in enumerate(buttons):
                button.grid(row=index // columns, column=index % columns, sticky='', padx=4, pady=4)

        def refresh_menu_state(self):
            super().refresh_menu_state()
            from display_names import bind_status_variable
            if hasattr(self,'menu_status_var'):bind_status_variable(self.menu_status_var)
            if self.active_account and getattr(self, 'view_mode', '') == 'menu':
                self.layout_group_cards()
                self.style_menu_actions()

        def show_all_results_browser(self):
            if not self.admin_authenticated:
                return self.show_mode_selection()
            old_directory = self.base_dir
            self.base_dir = self.data_root
            before = set(self.root.winfo_children())
            try:
                result = super().show_all_results_browser()
            except Exception:
                self.base_dir = old_directory
                raise
            windows = [w for w in self.root.winfo_children() if w not in before and isinstance(w,tk.Toplevel)]
            if windows:
                top = windows[0]
                top.grab_set()
                def restore(event):
                    if event.widget is top:
                        self.base_dir = old_directory
                top.bind('<Destroy>',restore,add='+')
            else:
                self.base_dir = old_directory
            return result

        @contextmanager
        def group_specs(self):
            original = base.RESEARCH_CONFIG_SPECS
            if self.groups.get(self.editing_group_number)['test_count'] == 4:
                base.RESEARCH_CONFIG_SPECS = [item for item in original if item[0] in 'ABCD']
            try:
                yield
            finally:
                base.RESEARCH_CONFIG_SPECS = original

        def _populate_researcher_fields(self):
            with self.group_specs():
                return super()._populate_researcher_fields()

        def collect_researcher_configs(self):
            with self.group_specs():
                return super().collect_researcher_configs()

        def reset_researcher_defaults(self):
            with self.group_specs():
                return super().reset_researcher_defaults()

        def select_group_settings(self, number):
            if not self.admin_authenticated:
                return self.show_mode_selection()
            self.groups.get(number)
            self.editing_group_number = int(number)
            self.build_researcher_ui()

        def open_groups(self):
            if not self.admin_authenticated:
                return self.show_mode_selection()
            if not self.save_research_settings():
                return
            return show_group_manager(self)

        def layout_group_cards(self):
            if not self.current_profile:
                return
            for code, card in self.menu_cards.items():
                if code not in self.allowed_codes:
                    card.grid_remove()
            columns=2 if len(self.allowed_codes)==4 else 3
            for i,code in enumerate(self.allowed_codes):
                self.menu_cards[code].grid(row=i//columns,column=i%columns,sticky='nsew',padx=6,pady=6)
            for col in range(3):
                self.tests_grid.grid_columnconfigure(col,weight=1 if col<columns else 0,
                    uniform='testcards47' if col<columns else '',minsize=0)
            for row in range(3):
                self.tests_grid.grid_rowconfigure(row,weight=1 if row<2 else 0,minsize=0)
            progress=self.progress_store.get_progress(self.current_profile)
            completed = progress.get('completed_tests',[])
            for code in self.allowed_codes:
                self.menu_result_buttons[code].configure(text='Показать результат' if progress.get('results',{}).get(code) else 'Результатов пока нет')
            text = ', '.join(base.TEST_LABELS[c] for c in self.allowed_codes if c in completed) or 'пока нет'
            next_code = self.progress_store.next_test_code(self.current_profile)
            self.menu_intro_var.set(f'Участник: {self.current_profile.name}. Группа №{self.active_group["number"]} · {len(self.allowed_codes)} теста' if len(self.allowed_codes)==4 else f'Участник: {self.current_profile.name}. Группа №{self.active_group["number"]} · 6 тестов')
            self.menu_status_var.set(f'Пройдено: {text}.\n' + (f'Следующий тест: {base.TEST_LABELS[next_code]}.' if next_code else 'Все тесты группы пройдены.'))
            self.layout_full_width_menu()

        def _apply_common_shell_layout(self,width,height,scale):
            if self.view_mode!='menu':
                return super()._apply_common_shell_layout(width,height,scale)
            # The menu needs no image sidebar. Avoid the legacy image-resizing path.
            self.layout_full_width_menu()

        def layout_full_width_menu(self):
            if self.view_mode!='menu' or not hasattr(self,'tests_grid'):
                return
            self.main.configure(bg='#eef3f8')
            self.main.pack_configure(padx=18,pady=12)
            self.main.grid_columnconfigure(0,weight=1,uniform='',minsize=0)
            self.main.grid_columnconfigure(1,weight=0,uniform='',minsize=0)
            self.left.grid_remove()
            self.right.grid(row=0,column=0,columnspan=2,sticky='nsew',padx=0,pady=0)
            self.right.configure(bg='#eef3f8')
            for row in range(5):
                self.right.grid_rowconfigure(row,weight=1 if row==3 else 0,minsize=0)
            self.title_small.grid_remove()
            self.title_big.configure(text='Выбор тестов',font=('Segoe UI',20,'bold'),bg='#eef3f8',fg='#163456',anchor='w',justify='left')
            self.title_big.grid_configure(sticky='ew',pady=(0,6))
            self.body.configure(font=('Segoe UI',10),bg='#eef3f8',wraplength=max(500,self.root.winfo_width()-60))
            self.body.grid_configure(sticky='ew',pady=(0,8))
            self.menu_panel.grid_configure(sticky='nsew',pady=(0,8))
            self.menu_panel.configure(bg='white',bd=1,relief='solid')
            self.menu_panel.grid_rowconfigure(2,weight=1)
            self.menu_title.configure(font=('Segoe UI',11,'bold'),bg='white',anchor='w')
            self.menu_status_label.configure(font=('Segoe UI',10),bg='white',wraplength=max(500,self.root.winfo_width()-80))
            self.tests_grid.configure(bg='white')
            self.tests_grid.grid_configure(sticky='nsew')
            columns=2 if len(self.allowed_codes)==4 else 3
            wrap=max(220,(self.root.winfo_width()-120)//columns-40)
            for code in self.allowed_codes:
                self.menu_cards[code].grid_rowconfigure(0,weight=1)
                self.menu_buttons[code].configure(font=('Segoe UI',12,'bold'),height=0,width=0,wraplength=wrap)
                self.menu_result_buttons[code].configure(font=('Segoe UI',10),height=1,width=0,wraplength=0,pady=4)
            self.menu_btn_frame.configure(bg='#eef3f8')

        def apply_menu_layout(self):
            super().apply_menu_layout()
            if self.active_account:
                self.settings_btn.grid_remove()
                self.all_results_btn.grid_remove()
                self.layout_group_cards()
                self.style_menu_actions()

        def launch_test(self, code):
            if not self.active_account or code not in self.allowed_codes:
                self.menu_status_var.set('Эта методика недоступна назначенной группе.')
                return
            return super().launch_test(code)

        def continue_next_test(self):
            if not self.active_account:
                return
            code = self.progress_store.next_test_code(self.current_profile)
            return self.launch_test(code) if code else self.show_integral_results()

        def show_all_tests_results(self):
            return self.show_integral_results()

        def view_results(self, code):
            if not self.admin_authenticated and code not in self.allowed_codes:
                return
            if self.current_profile:
                from surface_view import surface_data
                from storage import participant_directory
                identifier=getattr(self.current_profile,'participant_id','')
                store=base.UserProgressStore(participant_directory(self.data_root,identifier)) if identifier else self.progress_store
                payload=store.get_test_result(self.current_profile,code)
                if isinstance(payload,dict) and payload.get('data_source')=='synthetic_demo':
                    from demo_results import show_demo_result
                    return show_demo_result(self,code,payload)
            return super().view_results(code)

        def show_integral_results(self):
            identifier = getattr(self.current_profile,'participant_id','')
            codes = self.groups.codes(identifier) if identifier else tuple('ABCDEF')
            self.surface_order = tuple(code for code in v.ORDER if code in codes)
            if not self.surface_order:
                return
            return super().show_integral_results()

        def build_start_ui(self):
            self.show_mode_selection()

        def submit_form(self):
            if self.view_mode == 'mode44' and self._new_submit:
                self._new_submit()

        def apply_current_layout(self):
            if getattr(self, 'view_mode', '') == 'mode44':
                self._resize_after_id = None
                return
            return super().apply_current_layout()

        def handle_enter(self):
            if self.view_mode == 'mode44':
                if self._new_submit:
                    self._new_submit()
            else:
                return super().handle_enter()

    base.StartPageApp = ModeApp


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)
