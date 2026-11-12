"""Integration smoke test in real Tk windows, using only temporary participant data."""
import sys
import tempfile
import tkinter as tk
from pathlib import Path
from types import SimpleNamespace
from datetime import datetime

sys.path.insert(0,str(Path(__file__).resolve().parent))
import aviatest_v4 as v
v.base._enable_windows_dpi_awareness()

out=Path(__file__).resolve().parent
errors=[]
with tempfile.TemporaryDirectory(prefix='aviatest_v4_ui_') as folder:
    v.base._runtime_app_dir=lambda:Path(folder)
    root=tk.Tk()
    root.report_callback_exception=lambda *args:errors.append(args)
    app=v.base.StartPageApp(root)
    app.current_profile=v.base.UserProfile(name='Демонстрационный участник',age='30',gender='Мужской')
    app.current_session=v.base.SessionInfo('qa',app.current_profile.name,30,'Мужской',datetime.now())
    app.progress_store=v.base.UserProgressStore(Path(folder))
    app.researcher_mode_enabled=True
    app.build_menu_ui();root.update()
    assert set(app.menu_buttons)==set('ABCDEF')
    assert app.integral_results_btn.winfo_ismapped()
    top=v.launch_f(app);root.update()
    child=top._red_black
    # Complete all stages by passing the actual target sequence to the real click handler.
    child.session=[];child.training=False
    old_clock=v.rb.time.perf_counter
    clock=[100.0]
    def tick():
        clock[0]+=.5
        return clock[0]
    v.rb.time.perf_counter=tick
    try:
        for stage in range(1,4):
            child.start_stage(stage);root.update()
            for cell in list(child.sequence):child.click_cell(cell)
            assert child.pending_stage_result['stage']==stage
            child.open_pending_result();root.update()
        assert app.progress_store.get_test_result(app.current_profile,'F')
        assert len(v.collect_values(app,app.current_profile)['F'])==3
        saved_count=len(app.progress_store.get_progress(app.current_profile)['history'])
        child.save_result()
        assert len(app.progress_store.get_progress(app.current_profile)['history'])==saved_count
        child.show_final();root.update()
    finally:
        v.rb.time.perf_counter=old_clock
    child.close();root.update()
    # Published preview uses demonstration values, never participant measurements.
    payloads={'A':{'summary':dict(tmin_a=1.14,tmedio_a=.8,tmax_a=2.41)},
              'C':{'summary':dict(tmin_b=.7,tmedio_b=1.31,tmax_b=1.55)},
              'D':{'summary':dict(tmin_c=.7,tmedio_c=.68,tmax_c=1.21)},
              'E':{'summary':dict(tmin_d=0,tmedio_d=0,tmax_d=0)},
              'F':{'stages':[dict(stage=i,table_pace=0) for i in range(1,4)]},
              'B':{'stages':{str(i):dict(tasks=10,accuracy_pct=0) for i in range(1,4)}}}
    for code,payload in payloads.items():app.progress_store.save_test_result(app.current_profile,code,payload)
    graph=v.show_integral(app);graph.geometry('1220x900+50+30');root.update()
    graph._surface._drag=(0,0);graph._surface.drag(SimpleNamespace(x=90,y=20));root.update()
    assert len(graph._surface.find_withtag('sample'))==18
    graph.destroy();root.update()
    root.destroy()
assert not errors,errors
print('PASS: startup, six-card menu, ChKT all three stages, persistence, idempotent save, final results, 3D, rotation, close; no Tk callback exceptions')