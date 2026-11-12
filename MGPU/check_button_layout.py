"""Pixel-level consistency of navigation buttons at three simulated DPI scales."""
from pathlib import Path
import tempfile
import tkinter as tk

import aviatest_v4 as v
from mode_ui import install_modes
from storage import seed_configs


def main():
    with tempfile.TemporaryDirectory(prefix='aviatest442_buttons_') as folder:
        directory = Path(folder)
        seed_configs(directory, Path(__file__).parent)
        v.base._runtime_app_dir = lambda: directory
        v.base._enable_windows_dpi_awareness()
        install_modes(v)
        root = tk.Tk()
        errors = []
        root.report_callback_exception = lambda *args: errors.append(args)
        app = v.base.StartPageApp(root)
        root.attributes('-fullscreen', False)
        for scale in (100, 125, 150):
            root.tk.call('tk', 'scaling', (96 / 72) * scale / 100)
            root.geometry('1366x768+0+0')
            app.show_user_choice()
            root.update()
            assert set(app.fields)=={'login','password'}
            actions = app.actions.winfo_children()
            assert len({(w.winfo_width(), w.winfo_height()) for w in actions}) == 1
            assert max(w.winfo_width() for w in actions)<=250
            app.enter_account(*app.accounts.authenticate('user1', 'password1'))
            root.update()
            app.apply_menu_layout()
            root.update()
            buttons = (app.exit_btn, app.continue_btn, app.restart_btn, app.integral_results_btn)
            assert len({(w.winfo_width(), w.winfo_height()) for w in buttons}) == 1, (scale, [(w.cget('text'), w.winfo_width(), w.winfo_height()) for w in buttons])
            assert all('\n' not in w.cget('text') and w.cget('height') == 1 and w.cget('wraplength') == 0 for w in buttons)
            assert all(w.winfo_rootx() + w.winfo_width() <= root.winfo_rootx() + root.winfo_width() for w in buttons)
            assert all(w.winfo_rooty() + w.winfo_height() <= root.winfo_rooty() + root.winfo_height() for w in buttons)
            app.refresh_menu_state()
            root.update()
            assert len({(w.winfo_width(), w.winfo_height()) for w in buttons}) == 1
            app.show_mode_selection()
        root.destroy()
        assert not errors, errors
    print('PASS: menu actions have identical pixel dimensions; single-line labels; survive refresh; fit 1366x768; compact unified-login buttons; Tk scaling 100/125/150%.')


if __name__ == '__main__':
    main()
