"""Temporary synthetic UI preview; never uses the working participant store."""
import argparse
from pathlib import Path
import tempfile
import tkinter as tk

import aviatest_v4 as v
from accounts import account_profile
from mode_ui import install_modes
from storage import seed_configs
from surface_norms import write_norms


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--screen', choices=('start', 'research', 'surface', 'menu','groups','four','surface4','norms','registration','intro','chkt','chkt2','chkt3'), default='start')
    parser.add_argument('--qa-norms',action='store_true',help='Synthetic preview-only accuracy norms, not production defaults')
    parser.add_argument('--user', type=int, default=1)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='aviatest441_preview_') as folder:
        directory = Path(folder)
        seed_configs(directory, Path(__file__).parent)
        v.base._runtime_app_dir = lambda: directory
        v.base._enable_windows_dpi_awareness()
        install_modes(v)
        root = tk.Tk()
        app = v.base.StartPageApp(root)
        root.attributes('-fullscreen', False)
        root.geometry('1366x768+0+0')
        if args.screen in ('four','surface4'):
            app.groups.create(2,4)
            identifier,_=app.accounts.authenticate(f'user{args.user}',f'password{args.user}')
            app.groups.assign(identifier,2)
        if args.qa_norms:
            write_norms(app.groups.directory(2 if args.screen=='surface4' else 1),[80,80,80])
        if args.screen in ('menu','four'):
            app.enter_account(*app.accounts.authenticate(f'user{args.user}', f'password{args.user}'))
        if args.screen in ('research', 'surface','surface4','groups','norms'):
            app.admin_authenticated = True
            app.build_researcher_ui()
        if args.screen in ('surface','surface4'):
            identifier, fields = app.accounts.authenticate(f'user{args.user}', f'password{args.user}')
            app.current_profile = account_profile(v.base, identifier, fields)
            top = app.show_integral_results()
            top.title(f'ДЕМО user{args.user} — интегральная поверхность')
        if args.screen in ('chkt','chkt2','chkt3'):
            app.enter_account(*app.accounts.authenticate(f'user{args.user}',f'password{args.user}'))
            app.progress_store.reset_progress(app.current_profile)
            for code in 'ABCDE':app.progress_store.mark_completed(app.current_profile,code)
            child=v.launch_f(app)._red_black
            child.start_stage({'chkt':1,'chkt2':2,'chkt3':3}[args.screen])
        if args.screen=='intro':
            app.enter_account(*app.accounts.authenticate(f'user{args.user}',f'password{args.user}'))
            app.show_user_intro()
        if args.screen=='registration':
            app.show_registration()
        if args.screen=='groups':
            app.groups.create(2,4)
            app.open_groups()
        if args.screen=='norms':
            app.open_surface_norms()
        root.after(120000, root.destroy)
        root.mainloop()


if __name__ == '__main__':
    main()
