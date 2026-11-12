"""End-to-end surface and group norm editor checks on isolated demo data."""
import math
from pathlib import Path
import tempfile
import tkinter as tk
from tkinter import ttk
from types import SimpleNamespace

import aviatest_v4 as v
from mode_ui import install_modes,descendants
from storage import seed_configs
from surface_norms import read_norms,write_norms


def button(parent,text):
    return next(w for w in descendants(parent) if isinstance(w,(tk.Button,ttk.Button)) and w.cget('text')==text)


def main():
    errors=[]
    with tempfile.TemporaryDirectory(prefix='aviatest46_surface_') as folder:
        directory=Path(folder);seed_configs(directory,Path(__file__).parent)
        v.base._runtime_app_dir=lambda:directory;v.base._enable_windows_dpi_awareness();install_modes(v)
        root=tk.Tk();root.report_callback_exception=lambda *args:errors.append(args)
        app=v.base.StartPageApp(root)
        root.attributes('-fullscreen',False);root.geometry('1366x768+0+0');root.update()
        def login(name,password):
            app.show_mode_selection();app.fields['login'].set(name);app.fields['password'].set(password)
            app._new_submit();root.update()
        assert read_norms(app.groups.directory(1))==[None]*3
        login('admin','nowayin!')
        app.groups.create(2,4);app.select_group_settings(2);root.update()
        editor=app.open_surface_norms();root.update()
        assert [field.get() for field in editor._norm_fields]==['','','']
        editor._norm_fields[0].set('0');button(editor,'Сохранить').invoke();root.update()
        assert editor.winfo_exists() and editor._norm_status.get()
        assert read_norms(app.groups.directory(2))==[None]*3
        for field,value in zip(editor._norm_fields,('80','85,5','90')):field.set(value)
        button(editor,'Сохранить').invoke();root.update()
        assert not editor.winfo_exists()
        assert read_norms(app.groups.directory(2))==[80,85.5,90]
        assert read_norms(app.groups.directory(1))==[None]*3
        app.groups.create(3,6,template=2)
        write_norms(app.groups.directory(2),[75,75,75])
        assert read_norms(app.groups.directory(3))==[80,85.5,90]
        first_id,_=app.accounts.authenticate('user1','password1')
        app.groups.assign(first_id,2)
        login('user1','password1')
        raw=v.collect_values(app,app.current_profile)
        v.v2._export_integrated_payload(app.base_dir,app.progress_store.get_test_result(app.current_profile,'B'))
        original_json=app.progress_store.progress_file.read_bytes()
        excel=v.base._fixed417_external_excel_path(app.base_dir)
        original_excel=excel.read_bytes()
        top=app.show_integral_results();root.update()
        chart=top._surface
        assert bool(top.attributes('-fullscreen'))
        assert chart.winfo_height()/top.winfo_height()>.65
        assert chart.order==('A','C','D','B') and len(chart.find_withtag('sample'))==12
        assert math.isclose(chart.values['B'][0],raw['B'][0]/.75)
        assert top._surface_raw['B']==raw['B'] and top._surface_norms==[75,75,75]
        initial=(chart.yaw,chart.pitch,chart.zoom)
        chart._drag=(0,0);chart.drag(SimpleNamespace(x=140,y=55));chart.change_zoom(1.3);root.update()
        assert (chart.yaw,chart.pitch,chart.zoom)!=initial
        button(top,'Исходный вид').invoke();root.update()
        assert (chart.yaw,chart.pitch,chart.zoom)==initial
        table_top=top._show_table();root.update()
        table=table_top._data_table
        assert len(table.get_children())==12
        rows=[table.item(item,'values') for item in table.get_children()]
        accuracy=[row for row in rows if 'ориентация' in row[0]]
        assert len(accuracy)==3 and all('%' in row[2] and '75' in row[3] for row in accuracy)
        button(table_top,'Закрыть').invoke();root.update()
        button(top,'Закрыть').invoke();root.update()
        assert app.progress_store.progress_file.read_bytes()==original_json and excel.read_bytes()==original_excel
        login('user2','password2')
        top=app.show_integral_results();root.update()
        assert len(top._surface.order)==6 and len(top._surface.find_withtag('sample'))==18
        assert top._surface.values['B']==[.77/.8,.82/.8,.86/.8] and top._surface_norms==[80]*3
        assert all(value is not None for value in top._surface_raw['B'])
        table_top=top._show_table();root.update()
        rows=[table_top._data_table.item(item,'values') for item in table_top._data_table.get_children()]
        assert len(rows)==18 and all('80' in row[3] for row in rows if 'ориентация' in row[0])
        button(table_top,'Закрыть').invoke();button(top,'Закрыть').invoke();root.update()
        assert app.open_surface_norms() is None and not app.admin_authenticated and app.active_account is None
        login('admin','nowayin!');app.select_group_settings(1);root.update()
        editor=app.open_surface_norms();root.update()
        for field,value in zip(editor._norm_fields,('60','70','80')):field.set(value)
        button(editor,'Сохранить').invoke();root.update()
        login('user2','password2')
        for scale in (100,125,150):
            root.tk.call('tk','scaling',(96/72)*scale/100)
            top=app.show_integral_results();top.attributes('-fullscreen',False)
            top.geometry('1366x768+0+0');root.update()
            assert len(top._surface.find_withtag('sample'))==18
            assert top._surface.winfo_height()/top.winfo_height()>.65
            for text in ('Исходный вид','Таблица','Закрыть'):
                control=button(top,text)
                assert control.winfo_rootx()+control.winfo_width()<=top.winfo_rootx()+top.winfo_width()
                assert control.winfo_ismapped()
            button(top,'Закрыть').invoke();root.update()
            login('admin','nowayin!');app.select_group_settings(1);root.update()
            editor=app.open_surface_norms();root.update()
            save=button(editor,'Сохранить')
            assert save.winfo_rooty()+save.winfo_height()<=editor.winfo_rooty()+editor.winfo_height()
            button(editor,'Отмена').invoke();root.update()
            login('user2','password2')
        root.destroy();assert not errors,errors
    print('PASS: blank production defaults; per-stage group norm editor/validation/copy/isolation; normalized four/six surfaces; true alpha plane; fullscreen plot with approved title and controls; rotation/zoom/isometric reset; optional raw-value table; missing norms ungraded; JSON and Excel unchanged; protected norm editor; Tk scaling 100/125/150; no callback errors.')


if __name__=='__main__':main()
