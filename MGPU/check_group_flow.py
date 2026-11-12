"""End-to-end UI acceptance of unified login, moderation, group settings and surfaces."""
import json
from pathlib import Path
import tempfile
import tkinter as tk
from tkinter import ttk

import aviatest_v4 as v
from accounts import account_profile
from demo_accounts import demo_payloads
from mode_ui import install_modes, descendants
from storage import seed_configs, participant_directory
from surface_norms import write_norms


def button(parent,text):
    return next(w for w in descendants(parent) if isinstance(w,(tk.Button,ttk.Button)) and w.cget('text')==text)


def main():
    errors=[]
    with tempfile.TemporaryDirectory(prefix='aviatest45_flow_') as folder:
        directory=Path(folder);seed_configs(directory,Path(__file__).parent)
        v.base._runtime_app_dir=lambda:directory
        install_modes(v);v.base._enable_windows_dpi_awareness()
        root=tk.Tk();root.report_callback_exception=lambda *args:errors.append(args)
        app=v.base.StartPageApp(root)
        # Explicit synthetic QA norms, never production defaults.
        write_norms(app.groups.directory(1),[80,80,80])
        root.attributes('-fullscreen',False);root.geometry('1366x768+0+0');root.update()
        assert set(app.fields)=={'login','password'} and app.current_profile is None
        captions={w.cget('text') for w in descendants(root) if isinstance(w,tk.Button) and w.winfo_ismapped()}
        assert captions=={'Войти','Выход','Регистрация','Показать пароль'}
        def login(login,password):
            app.show_mode_selection();app.fields['login'].set(login);app.fields['password'].set(password)
            app._new_submit();root.update()
            if app.active_account:
                assert 'Тест предназначен' in app.intro_text
                button(app.main,'ДАЛЕЕ').invoke();root.update()
        login('admin','wrong')
        assert app.error_var.get()=='Неверный логин или пароль' and not app.admin_authenticated
        app.show_registration()
        fields=dict(name='Участник группы',age='30',education='Высшее',login='pending',password='qa-only',confirmation='mismatch')
        for key,value in fields.items():app.fields[key].set(value)
        app.register();assert 'совпадают' in app.error_var.get() and app.fields['name'].get()==fields['name']
        app.fields['confirmation'].set('qa-only');app.register();root.update()
        assert app.current_profile is None and app.active_account is None
        assert 'назначения группы' in app.error_var.get()
        identifier,_=app.accounts.authenticate('pending','qa-only')
        assert app.groups.membership(identifier) is None
        assert not participant_directory(directory,identifier).exists()
        login('pending','qa-only')
        assert app.current_profile is None and 'назначения группы' in app.error_var.get()
        login('admin','nowayin!')
        assert app.admin_authenticated and app.view_mode=='researcher'
        app.groups.create(2,4);app.groups.create(3,6)
        app.select_group_settings(2);root.update()
        assert set(app.research_widgets)==set('ABCD')
        assert not app.chkt_settings_btn.winfo_ismapped()
        # Changing the current group's variant refreshes its editor on manager close.
        manager=app.open_groups();root.update()
        manager._groups_tree.selection_set('2');root.update();manager._variant_var.set('6')
        button(manager,'Применить вариант к выбранной').invoke();root.update()
        button(manager,'Закрыть').invoke();root.update()
        assert set(app.research_widgets)==set('ABCDE') and app.chkt_settings_btn.winfo_ismapped()
        manager=app.open_groups();root.update()
        manager._groups_tree.selection_set('2');root.update();manager._variant_var.set('4')
        button(manager,'Применить вариант к выбранной').invoke();root.update()
        button(manager,'Закрыть').invoke();root.update()
        assert set(app.research_widgets)==set('ABCD') and not app.chkt_settings_btn.winfo_ismapped()
        entry=app.research_widgets['B']['stage_1_time_s']['widget']
        entry.delete(0,'end');entry.insert(0,'37');root.update()
        assert app.save_research_settings()
        assert json.loads((app.groups.directory(2)/'orientation_config.json').read_text())['stage_1_time_s']==37
        assert json.loads((app.groups.directory(1)/'orientation_config.json').read_text())['stage_1_time_s']!=37
        manager=app.open_groups();root.update()
        assert len(manager._groups_tree.get_children())==3
        manager._members_tree.selection_set(identifier);manager._group_var.set('2')
        button(manager,'Назначить группу').invoke();root.update()
        assert app.groups.membership(identifier)=={'number':2,'test_count':4}
        manager._number_var.set('90');manager._variant_var.set('6')
        button(manager,'Создать группу').invoke();root.update()
        assert app.groups.get(90)['test_count']==6
        manager._groups_tree.selection_set('90');root.update()
        button(manager,'Настройки выбранной группы').invoke();root.update()
        assert app.editing_group_number==90 and set(app.research_widgets)==set('ABCDE')
        assert app.chkt_settings_btn.winfo_ismapped()
        login('pending','qa-only')
        assert app.view_mode=='menu' and app.allowed_codes==tuple('ACDB')
        assert json.loads((app.base_dir/'orientation_config.json').read_text())['stage_1_time_s']==37
        mapped={code for code,card in app.menu_cards.items() if card.winfo_ismapped()}
        assert mapped==set('ABCD'),mapped
        before=app.progress_store.progress_file.read_bytes()
        app.launch_test('E');app.launch_test('F');app.view_results('F')
        assert app.progress_store.progress_file.read_bytes()==before
        for code,payload in demo_payloads(2,app.current_profile).items():
            if code in app.allowed_codes:
                app.progress_store.save_test_result(app.current_profile,code,payload)
                app.progress_store.mark_completed(app.current_profile,code)
        app.refresh_menu_state();root.update()
        assert app.progress_store.next_test_code(app.current_profile) is None
        top=app.continue_next_test();root.update()
        assert top._surface.order==('A','C','D','B') and len(top._surface.find_withtag('sample'))==12
        top.destroy();root.update()
        saved=app.progress_store.get_test_result(app.current_profile,'B')
        assert saved['study_group']=={'number':2,'test_count':4}
        assert saved['group_settings']['orientation_config.json']['stage_1_time_s']==37
        login('user1','password1')
        assert app.allowed_codes==tuple('ACDEFB') and app.active_group['number']==1
        top=app.show_integral_results();root.update()
        assert len(top._surface.find_withtag('sample'))==18
        top.destroy();root.update()
        # Preserve six-test data when the same demo account is reassigned to four tests.
        first_id=app.active_account;first_dir=app.base_dir
        raw=(first_dir/'data/user_progress.json').read_bytes()
        app.groups.assign(first_id,2)
        login('user1','password1')
        assert app.allowed_codes==tuple('ACDB')
        assert (first_dir/'data/user_progress.json').read_bytes()==raw
        top=app.show_integral_results();root.update()
        assert len(top._surface.find_withtag('sample'))==12
        top.destroy();root.update()
        login('admin','nowayin!')
        app.select_group_settings(2);root.update()
        previous=app.base_dir
        app.show_all_results_browser();root.update()
        assert app.base_dir==directory
        for child in root.winfo_children():
            if isinstance(child,tk.Toplevel):child.destroy()
        root.update();assert app.base_dir==previous
        for scale in (100,125,150):
            root.tk.call('tk','scaling',(96/72)*scale/100)
            root.geometry('1366x768+0+0');app.show_mode_selection();root.update()
            for text in ('Войти','Выход','Регистрация'):
                widget=button(root,text)
                assert widget.winfo_ismapped()
                assert widget.winfo_rooty()+widget.winfo_height() <= root.winfo_rooty()+root.winfo_height()
            app.show_registration();root.update()
            widget=button(root,'Зарегистрироваться')
            assert widget.winfo_rooty()+widget.winfo_height() <= root.winfo_rooty()+root.winfo_height()
        root.destroy()
        # Restart never authenticates automatically, pending registrations remain pending.
        root=tk.Tk();root.report_callback_exception=lambda *args:errors.append(args)
        app=v.base.StartPageApp(root);root.update()
        assert set(app.fields)=={'login','password'} and app.current_profile is None
        app.fields['login'].set('pending');app.fields['password'].set('qa-only');app._new_submit();root.update()
        assert app.allowed_codes==tuple('ACDB') and app.progress_store.next_test_code(app.current_profile) is None
        root.destroy()
        assert not errors,errors
    print('PASS: unified login; no mode selector; pending registration and denied login; numbered groups via real UI; assignment activates account; isolated editable settings; four/six allowed methods; 12/18 surface samples; hidden tests blocked; original results retained; admin catalog context restored; restart; 1366x768 Tk scaling 100/125/150; no callback errors.')


if __name__=='__main__':main()
