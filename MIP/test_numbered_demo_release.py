import json,math
from pathlib import Path
from types import SimpleNamespace
import pytest
import tkinter as tk
import aviatest_v4 as v
from accounts import AccountStore,account_profile
from demo_accounts import ensure_demo_accounts
from storage import seed_configs,participant_directory
from groups import GroupStore
from surface_view import surface_data
from display_names import display_text,legacy_labels,install_runtime_names

def test_declined_labels_ranges_and_legacy_mapping():
    assert display_text('Запуск Теста A. Результаты теста B. Методика C.')=='Запуск Теста 1. Результаты теста 6. Методика 2.'
    assert display_text('Тесты A–F')=='Тесты 1, 2, 3, 4, 5, 6'
    with legacy_labels():
        assert display_text('Тест B · тест C · тест D')=='Тест 2 · тест 3 · тест 4'
    assert display_text('Тест B')=='Тест 6'
    assert display_text('Фильтры: тесты=A,B,C')=='Фильтры: тесты=1, 2, 6'

def test_readonly_variable_labels_update_without_rewriting_source():
    install_runtime_names(v)
    root=tk.Tk()
    try:
        original=tk.StringVar(value='Результаты теста B')
        label=tk.Label(root,textvariable=original);label.pack();root.update()
        assert label.getvar(label.cget('textvariable'))=='Результаты теста 6'
        assert original.get()=='Результаты теста B'
        original.set('Фильтры: тесты=A,C');root.update()
        assert label.getvar(label.cget('textvariable'))=='Фильтры: тесты=1, 2'
        label.destroy();original.set('После закрытия')
    finally:root.destroy()

@pytest.mark.parametrize('damage',['missing','zeros'])
def test_current_revision_demo_damage_repaired_but_real_results_preserved(tmp_path,damage):
    seed_configs(tmp_path,Path(__file__).parent);ensure_demo_accounts(v,tmp_path)
    accounts=AccountStore(tmp_path)
    profile=account_profile(v.base,*accounts.authenticate('user1','password1'))
    directory=participant_directory(tmp_path,profile.participant_id);store=v.base.UserProgressStore(directory)
    with accounts.connect() as db:before=db.execute('SELECT * FROM accounts ORDER BY login').fetchall()
    real={'data_source':'real_test','test_code':'D','summary':{'tmin_c':0,'tmedio_c':.8,'tmax_c':.9}}
    store.save_test_result(profile,'D',real)
    records=store._load()
    if damage=='missing':records[profile.key]['results'].pop('C')
    else:
        for field in ('tmin_b','tmedio_b','tmax_b'):records[profile.key]['results']['C']['summary'][field]=0
    store._save(records);damaged=store.progress_file.read_bytes()
    ensure_demo_accounts(v,tmp_path)
    payload=store.get_test_result(profile,'C')
    assert v.extract_values({'C':payload})['C']==[1.10,1.01,.95]
    assert store.get_test_result(profile,'D')['summary']==real['summary']
    assert any(p.read_bytes()==damaged for p in (directory/'backups').glob('before-demo-repair-*'))
    with accounts.connect() as db:assert db.execute('SELECT * FROM accounts ORDER BY login').fetchall()==before
    healthy=store.progress_file.read_bytes();ensure_demo_accounts(v,tmp_path)
    assert store.progress_file.read_bytes()==healthy

def test_pygame_captions_font_and_excel_headers_are_numbered():
    install_runtime_names(v)
    pg=v.base.pygame;pg.init();pg.display.set_mode((320,200))
    try:
        pg.display.set_caption('СПР — Тест А: слежение')
        assert pg.display.get_caption()[0]=='СПР — Тест 1: слежение'
        f=pg.font.SysFont('Arial',18)
        assert f.size('Тест A')==f.size('Тест 1')
        assert pg.image.tobytes(f.render('Тест A',True,'black'),'RGB')==pg.image.tobytes(f.render('Тест 1',True,'black'),'RGB')
    finally:pg.quit()
    for context in (None,'legacy'):
        if context:
            with legacy_labels():headers=v.v2._excel_headers()
        else:headers=v.v2._excel_headers()
        assert headers[104][0]=='Тест 2'
        assert headers[120][0].startswith('Тест 3')
        assert headers[123][0].startswith('Тест 4')
        assert headers[187][0].startswith('Тест 6')

def test_visible_custom_tabs_match_numbered_pages_and_clicks(tmp_path):
    from mode_ui import install_modes
    seed_configs(tmp_path,Path(__file__).parent);v.base._runtime_app_dir=lambda:tmp_path
    install_modes(v);root=tk.Tk();root.geometry('1366x900')
    try:
        app=v.base.StartPageApp(root)
        app.fields['login'].set('admin');app.fields['password'].set('nowayin!');app._new_submit();root.update()
        labels=[item['label'] for item in app._fixed416_research_tab_items]
        assert [label.cget('text') for label in labels]==[f'Тест {i}' for i in range(1,7)]
        for label in labels:
            assert label.winfo_ismapped()
            label.event_generate('<Button-1>');root.update()
            assert app.research_tabs.tab(app.research_tabs.select(),'text')==label.cget('text')
        app.groups.create(2,4);app.select_group_settings(2);root.update()
        assert [item['label'].cget('text') for item in app._fixed416_research_tab_items]==['Тест 1','Тест 2','Тест 3','Тест 6']
    finally:root.destroy()
