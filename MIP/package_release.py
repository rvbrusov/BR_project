"""Package sources and verification logs; never include local participant stores."""
import hashlib
from pathlib import Path
import shutil
import zipfile


def main():
    root = Path(__file__).resolve().parent
    dist = root / 'dist'
    dist.mkdir(exist_ok=True)
    documents = ['ИНСТРУКЦИЯ-v4.21.txt', 'ОТЧЁТ-ПРОВЕРКИ-v4.21.txt']
    for name in documents:
        shutil.copy2(root / name, dist / name)
    excluded = {'_tmp_settings_tables.json', 'apply_feedback.py', 'preview_feedback.py'}
    extensions = {'.py', '.spec', '.ps1', '.ico', '.png', '.jpg', '.xlsx', '.json'}
    files = [p for p in root.iterdir() if p.is_file() and p.name not in excluded and
             (p.suffix in extensions or p.name in documents + ['requirements-build.txt', 'config_schema_version.txt'])]
    files += [p for p in (root / 'assets').rglob('*') if p.is_file() and p.name.lower() != 'thumbs.db']
    files += [root / 'red_black_data/settings.json']
    files += [p for p in (root/'qa').iterdir() if p.is_file() and p.suffix in {'.log','.json','.jpg','.png'}]
    with zipfile.ZipFile(dist / 'Aviatest-v4.21-Source.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            archive.write(path, Path('aviatest_v4_21') / path.relative_to(root))
    names = ['Aviatest-v4.21-MIP-Setup.exe', 'aviatest_v4_21_mip_portable.exe', 'Aviatest-v4.21-Source.zip', *documents]
    sums = [hashlib.sha256((dist / name).read_bytes()).hexdigest() + '  ' + name for name in names]
    (dist / 'SHA256SUMS.txt').write_text('\n'.join(sums) + '\n', encoding='utf-8')
    print('\n'.join(f'{name}: {(dist / name).stat().st_size:,} bytes' for name in names))


if __name__ == '__main__':
    main()
