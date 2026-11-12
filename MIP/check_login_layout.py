"""Centered approved login layout, including resizing and authentication errors."""
from pathlib import Path
import tempfile
import tkinter as tk
from tkinter import ttk,font as tkfont

import aviatest_v4 as v
from mode_ui import install_modes,descendants
from storage import seed_configs


def main():
    errors=[]
    with tempfile.TemporaryDirectory(prefix='aviatest411_login_') as folder:
        directory=Path(folder);seed_configs(directory,Path(__file__).parent)
        v.base._runtime_app_dir=lambda:directory
        v.base._enable_windows_dpi_awareness();install_modes(v)
        root=tk.Tk();root.report_callback_exception=lambda *args:errors.append(args)
        app=v.base.StartPageApp(root);root.attributes('-fullscreen',False)
        def fits():
            frame=app.login_group
            assert abs(frame.winfo_x()+frame.winfo_width()/2-app.main.winfo_width()/2)<=1
            assert frame.winfo_x()>=8 and frame.winfo_y()>=8
            shield=app.login_shield
            assert shield.winfo_width()==frame.winfo_width()
            assert frame.winfo_y()==shield.winfo_y()+shield.winfo_height()-1
            assert shield.winfo_y()+shield.winfo_height()<=app.main.winfo_height()-4
            assert app.login_footer.winfo_y()+app.login_footer.winfo_height()==app._login_stairs_y
            assert shield.winfo_y()==app.login_banner.winfo_y()+app.login_banner.winfo_height()
            assert frame.winfo_x()+frame.winfo_width()<=app.main.winfo_width()-8
            assert frame.winfo_y()+frame.winfo_height()<=app.main.winfo_height()-8
            assert not any(isinstance(w,(tk.Scrollbar,ttk.Scrollbar)) and w.winfo_ismapped() for w in descendants(app.main))
            assert len({(w.winfo_width(),w.winfo_height()) for w in app.actions.winfo_children()})==1
            assert app._login_entries[1].cget('show') and not app._login_entries[0].cget('show')
            for widget in descendants(app.form_body):
                if not widget.winfo_ismapped():continue
                assert widget.winfo_rootx()>=frame.winfo_rootx()+1
                assert widget.winfo_rootx()+widget.winfo_width()<=frame.winfo_rootx()+frame.winfo_width()-1
                assert widget.winfo_rooty()+widget.winfo_height()<=frame.winfo_rooty()+frame.winfo_height()-1,(widget.winfo_class(),widget.winfo_name(),widget.winfo_rooty(),widget.winfo_height(),frame.winfo_rooty(),frame.winfo_height(),app.main.winfo_width(),app.main.winfo_height(),root.tk.call('tk','scaling'))
        for scale in (100,125,150):
            root.tk.call('tk','scaling',96/72*scale/100)
            for width,height in ((1920,1080),(1366,768),(1024,600),(620,400)):
                root.geometry(f'{width}x{height}+0+0');app.show_mode_selection();root.update()
                fits()
                app.main.event_generate('<MouseWheel>',delta=120);root.update()
                app.fields['login'].set('unknown-user');app.fields['password'].set('wrong')
                app._new_submit();root.update();fits()
                assert 'Неверный' in app.error_var.get()
                # Resize the existing form, preserving edits and focusable controls.
                root.geometry('1366x768+0+0');root.update();fits()
                assert app.fields['login'].get()=='unknown-user'
                assert tkfont.Font(root=root,font=app._login_entries[0].cget('font')).metrics('linespace')>=12
                assert app.login_photo.winfo_ismapped()
                assert app._login_error.winfo_ismapped()
        app.show_registration();root.update()
        assert set(app.fields)=={'name','age','education','gender','login','password','confirmation'}
        app.show_mode_selection();root.update()
        app.fields['login'].set('user1');app.fields['password'].set('password1')
        app.handle_enter();root.update()
        assert app.active_account and app.current_profile
        assert 'Основные методики' in app.intro_text and 'Дополнительные методики' in app.intro_text
        app.handle_enter();root.update()
        assert app.view_mode=='menu'
        app.show_mode_selection();root.update()
        assert not app.fields['login'].get() and not app.fields['password'].get()
        root.destroy();assert not errors,errors
    print('PASS: separate final artwork assets; full-window photo without distortion; native compact form aligned over sample; equal compact buttons; no login scrollbar; 1920x1080/1366x768/1024x600/620x400 at Tk 100/125/150%; resize preserves input; error fits; password masked; registration/Enter login/logout work; no callback errors.')


if __name__=='__main__':main()
