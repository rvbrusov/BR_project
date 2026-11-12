# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import ast
import sys

ROOT = Path(SPECPATH)
PYROOT = Path(sys.base_prefix)

datas = [
    (str(ROOT / 'fixed428_app_2026-04-25_portable_build.py'), '.'),
    (str(ROOT / 'config_schema_version.txt'), '.'),
    (str(ROOT / 'red_black_data' / 'settings.json'), 'red_black_data'),
]

for cfg in ROOT.glob('*.json'):
    datas.append((str(cfg), '.'))

for source_name in (
    'tensor_matrix_test_2026_04_23_v14.py',
    'orient_final.py',
    'orient_new_v1.py',
    'orient_new_v1_1.py',
    'orient_new_v2.py',
    'orient_new_v2_1.py',
    'orient_new_v3_1.py',
):
    path = ROOT / source_name
    if path.exists():
        datas.append((str(path), '.'))

for image_name in ('counting.png', 'testD_inst.png', 'testB_instr.png'):
    path = ROOT / image_name
    if path.exists():
        datas.append((str(path), '.'))
        datas.append((str(path), 'assets'))

for asset_name in (
    'airplane_sprite.png',
    'tracking_background_doc.png',
    'circle.png',
    'login_background.png',
    'login_shield.png',
    'login_triangle.png',
    'login_institution.png',
    'login_circle.png',
    'intro_exit_label.png',
    'intro_next_label.png',
    'cockpit.png',
    'method_a_instruction_slezh_page1_fixed412.png',
    'method_a_instruction_slezh_page1.png',
    'orient_instruction.png',
):
    path = ROOT / 'assets' / asset_name
    if path.exists():
        datas.append((str(path), 'assets'))

excel_template = ROOT / 'Integrated Data_methods_tracking_header_final.xlsx'
if excel_template.exists():
    datas.append((str(excel_template), '.'))

icon_file = ROOT / 'program_icon.ico'
if icon_file.exists():
    datas.append((str(icon_file), '.'))

binaries = []  # PyInstaller discovers the Tcl/Tk version of the build interpreter.

hiddenimports = [
    'tkinter',
    'tkinter.font',
    'tkinter.ttk',
    'tkinter.messagebox',
    'tkinter.filedialog',
    'tkinter.simpledialog',
    'pygame',
    'pygame.font',
    'pygame.image',
    'pygame.joystick',
    'pygame.transform',
    'PIL',
    'PIL.Image',
    'PIL.ImageTk',
    'PIL.ImageDraw',
    'PIL.ImageFont',
    'PIL.ImageGrab',
    'openpyxl',
    'et_xmlfile',
]

# The legacy base is loaded from a source file at runtime, so collect its imports.
for node in ast.walk(ast.parse((ROOT / 'fixed428_app_2026-04-25_portable_build.py').read_text(encoding='utf-8-sig'))):
    if isinstance(node, ast.Import):
        hiddenimports.extend(alias.name for alias in node.names)
    elif isinstance(node, ast.ImportFrom) and node.module and node.module != '__future__':
        hiddenimports.append(node.module)
hiddenimports = sorted(set(hiddenimports))

excludes = [
    'BeautifulSoup', 'OpenGL', 'PyQt5', 'PyQt6', 'PySide2', 'PySide6',
    'bs4', 'cython', 'defusedxml', 'doctest', 'html5lib', 'lxml',
    'lxml.etree', 'lxml.html', 'lxml.objectify', 'lxml_html_clean', 
    'olefile', 'pdb', 'pygame.docs', 'pygame.examples', 'pygame.tests',
    'tkinter.test', 'unittest',
]

a = Analysis(
    [str(ROOT / 'aviatest_v4_21.py')],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=2,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='aviatest_v4_21_mip_portable',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_dir=str(ROOT / 'upx-5.1.1-win64'),
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon_file) if icon_file.exists() else None,
)

