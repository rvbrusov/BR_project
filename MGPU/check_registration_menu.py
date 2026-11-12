"""Acceptance of the marked registration and menu mockups on isolated data."""
from pathlib import Path
import tempfile
import tkinter as tk
from tkinter import ttk

import aviatest_v4 as v
from mode_ui import install_modes,descendants
from storage import seed_configs


def main():
    errors=[]
    with tempfile.TemporaryDirectory(prefix='aviatest47_ui_') as folder:
        directory=Path(folder);seed_configs(directory,Path(__file__).parent)
        v.base._runtime_app_dir=lambda:directory;v.base._enable_windows_dpi_awareness();install_modes(v)
        root=tk.Tk();root.report_callback_exception=lambda *args:errors.append(args)
        app=v.base.StartPageApp(root)
        root.attributes('-fullscreen',False);root.geometry('1366x768+0+0');root.update()
        app.show_registration();root.update()
        assert set(app.fields)=={'name','age','education','gender','login','password','confirmation'}
        labels=[w.cget('text') for w in descendants(app.main) if isinstance(w,(tk.Label,tk.Button,ttk.Label,ttk.Button))]
        assert not any(any(removed in text.lower() for removed in ('налёт','налет','тип вс','должность','текущей недели','перед началом')) for text in labels)
        assert any('СИСТЕМНЫЙ ТЕСТ' in text for text in labels)
        assert len([w for w in descendants(app.main) if isinstance(w,tk.Label) and w.cget('image')])==1
        data=dict(name='Новый участник',age='30',education='',gender='Женский',login='short-new',password='qa-only',confirmation='qa-only')
        for key,value in data.items():app.fields[key].set(value)
        app.register();assert 'образование' in app.error_var.get() and app.fields['name'].get()==data['name']
        app.fields['education'].set('Высшее');app.fields['age'].set('121')
        app.register();assert 'диапазоне' in app.error_var.get() and app.fields['login'].get()==data['login']
        app.fields['age'].set('30');app.register();root.update()
        assert app.current_profile is None and 'назначения группы' in app.error_var.get()
        account=app.accounts.authenticate('short-new','qa-only')
        assert all(account[1][key]=='' for key in ('flight_hours','aircraft_type','position'))
        assert app.groups.membership(account[0]) is None
        app.fields['password'].set('qa-only');app._new_submit();root.update()
        assert app.current_profile is None and 'назначения группы' in app.error_var.get()
        app.groups.assign(account[0],1)
        app.fields['password'].set('qa-only');app._new_submit();root.update()
        button_next=next(w for w in descendants(app.main) if isinstance(w,tk.Button) and w.cget('text')=='ДАЛЕЕ')
        button_next.invoke();root.update()
        assert app.current_profile.name==data['name'] and app.current_profile.flight_hours==''
        assert not app.left.winfo_ismapped() and not app.circle_label.winfo_ismapped() and not app.cockpit_label.winfo_ismapped()
        assert app.right.winfo_width()/app.main.winfo_width()>.98
        assert app.progress_store.next_test_code(app.current_profile)=='A'
        app.groups.create(2,4)
        for count in (4,6):
            app.groups.assign(account[0],2 if count==4 else 1)
            for scale in (100,125,150):
                root.tk.call('tk','scaling',(96/72)*scale/100)
                root.geometry('1366x768+0+0')
                app.show_mode_selection();app.enter_account(*account);root.update()
                app.apply_menu_layout();root.update()
                assert app.right.winfo_width()/app.main.winfo_width()>.98
                assert app.tests_grid.winfo_width()/app.main.winfo_width()>.9
                assert not app.left.winfo_ismapped()
                assert {code for code,card in app.menu_cards.items() if card.winfo_ismapped()}==set('ABCDEF'[:count])
                for code in app.allowed_codes:
                    card=app.menu_cards[code]
                    assert card.winfo_rootx()+card.winfo_width()<=root.winfo_rootx()+root.winfo_width()
                    assert card.winfo_rooty()+card.winfo_height()<=root.winfo_rooty()+root.winfo_height()
                controls=(app.exit_btn,app.continue_btn,app.restart_btn,app.integral_results_btn)
                assert len({(w.winfo_width(),w.winfo_height()) for w in controls})==1, (count,scale,[(w.cget('text'),w.winfo_width(),w.winfo_height(),str(type(w))) for w in controls])
                assert all(w.winfo_rooty()+w.winfo_height()<=root.winfo_rooty()+root.winfo_height() for w in controls)
                app.show_registration();root.update()
                assert set(app.fields)=={'name','age','education','gender','login','password','confirmation'}
                register=next(w for w in descendants(app.main) if isinstance(w,tk.Button) and w.cget('text')=='Зарегистрироваться')
                assert register.winfo_rooty()+register.winfo_height()<=root.winfo_rooty()+root.winfo_height()
        root.destroy();assert not errors,errors
    print('PASS: short registration with retained brand header; removed fields/text/cockpit absent; validation keeps input; pending then group assignment; no sidebar images in four/six menu; >98% full-width layout; cards and equal-size controls fit 1366x768 at Tk scaling 100/125/150; no callback errors.')


if __name__=='__main__':main()

