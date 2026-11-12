"""Install Aviatest for the current Windows user."""
import argparse
import base64
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox

VERSION = '4.21'
DEFAULT_DIR = Path(os.environ['LOCALAPPDATA']) / 'Programs' / 'Aviatest-MGPU'
RESOURCE_DIR = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent / 'dist'))
EXE_NAME = 'aviatest_v4_21_mgpu_portable.exe'


def install(destination, create_shortcut=True):
    if not str(destination).strip():
        raise ValueError('Укажите полный путь установки.')
    if not Path(destination).expanduser().is_absolute():
        raise ValueError('Укажите полный абсолютный путь, например C:\\Программы\\Авиатест.')
    destination = Path(destination).expanduser().resolve()
    try:
        destination.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryFile(dir=destination) as probe:
            probe.write(b'aviatest-install-check')
            probe.flush()
    except OSError as exc:
        raise OSError(f'Нет возможности записи в папку «{destination}». Выберите доступную папку. {exc}') from exc
    staged = destination / (EXE_NAME + '.installing')
    try:
        shutil.copy2(RESOURCE_DIR / EXE_NAME, staged)
        os.replace(staged, destination / EXE_NAME)
    finally:
        staged.unlink(missing_ok=True)
    if not create_shortcut:
        return destination / EXE_NAME
    # Windows resolves the actual desktop, including a redirected OneDrive desktop.
    script = '''
$desktopPath = [Environment]::GetFolderPath('Desktop')
$shortcutPath = Join-Path $desktopPath 'Авиатест МГПУ.lnk'
$shortcut = (New-Object -ComObject WScript.Shell).CreateShortcut($shortcutPath)
$shortcut.TargetPath = $env:AVIATEST_INSTALL_EXE
$shortcut.WorkingDirectory = $env:AVIATEST_INSTALL_DIR
$shortcut.IconLocation = $env:AVIATEST_INSTALL_EXE + ',0'
$shortcut.Description = 'Авиатест 4.21 — МГПУ'
$shortcut.Save()
if (-not (Test-Path -LiteralPath $shortcutPath)) { throw 'Shortcut was not created' }
'''
    environment = os.environ.copy()
    environment['AVIATEST_INSTALL_EXE'] = str(destination / EXE_NAME)
    environment['AVIATEST_INSTALL_DIR'] = str(destination)
    encoded = base64.b64encode(script.encode('utf-16le')).decode('ascii')
    subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-EncodedCommand', encoded],
                   env=environment, check=True, capture_output=True,
                   creationflags=subprocess.CREATE_NO_WINDOW)
    return destination / EXE_NAME


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--install-dir', type=Path, default=DEFAULT_DIR)
    parser.add_argument('--silent', action='store_true')
    args = parser.parse_args()
    if args.silent:
        install(args.install_dir)
        return
    root = tk.Tk()
    root.title('Установка Авиатест 4.21 — МГПУ')
    root.geometry('760x360')
    root.minsize(600, 320)
    panel = tk.Frame(root, padx=24, pady=20)
    panel.pack(fill='both', expand=True)
    tk.Label(panel, text='Авиатест 4.21 — МГПУ', font=('Segoe UI', 20, 'bold')).pack(anchor='w')
    tk.Label(panel, text='Программа будет установлена точно в указанную папку.\nДанные сохраняются отдельно в %LOCALAPPDATA%\\Aviatest\\aviatest_v4_data.\nНа рабочем столе будет создан ярлык «Авиатест МГПУ».',
             wraplength=565, justify='left').pack(anchor='w', pady=(12, 16))
    path = tk.StringVar(value=str(args.install_dir))
    tk.Entry(panel, textvariable=path, width=80).pack(fill='x')
    def choose():
        chosen = filedialog.askdirectory(parent=root, initialdir=str(Path(path.get()).parent), mustexist=False,
                                         title='Выберите или создайте папку установки')
        if chosen:
            path.set(str(Path(chosen)))
    tk.Button(panel, text='Обзор…', command=choose).pack(anchor='w', pady=8)
    def run_install():
        button.config(state='disabled')
        root.update_idletasks()
        try:
            executable = install(path.get())
        except Exception as error:
            messagebox.showerror('Ошибка установки',
                f'Не удалось завершить установку. Закройте запущенный Авиатест и повторите попытку.\n\n{error}', parent=root)
            button.config(state='normal')
            return
        if messagebox.askyesno('Установка завершена',
                'Ярлык «Авиатест» создан на рабочем столе.\nЗапустить программу?', parent=root):
            subprocess.Popen([str(executable)], cwd=str(executable.parent))
        root.destroy()
    button = tk.Button(panel, text='Установить', command=run_install, font=('Segoe UI', 12, 'bold'), padx=20)
    button.pack(anchor='e', pady=10)
    root.mainloop()


if __name__ == '__main__':
    main()
