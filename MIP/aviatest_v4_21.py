"""Version 4.21 entry point. The six methods and their calculations remain in v4.3."""
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

import aviatest_v4 as v
from storage import prepare_storage
from mode_ui import install_modes


def main():
    from display_names import install_runtime_names
    install_runtime_names(v)
    v.base._enable_windows_dpi_awareness()
    root = tk.Tk()
    root.withdraw()
    app_dir = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
    resources = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
    try:
        data = prepare_storage(app_dir, resources)
        v.base._runtime_app_dir = lambda: data
        install_modes(v)
        app=v.base.StartPageApp(root)
    except Exception as exc:
        messagebox.showerror('Авиатест — ошибка запуска', f'Не удалось открыть данные программы.\n\n{exc}', parent=root)
        root.destroy()
        return
    root.deiconify()
    if len(sys.argv)==3 and sys.argv[1]=='--verify-release':
        output=Path(sys.argv[2]);output.mkdir(parents=True,exist_ok=True)
        try:
            from release_acceptance import audit_installed
            audit_installed(root,app,output)
        except Exception:
            import traceback
            (output/'failure.txt').write_text(traceback.format_exc(),encoding='utf-8')
            root.destroy();raise SystemExit(1)
        root.destroy();return
    root.mainloop()


if __name__ == '__main__':
    main()
