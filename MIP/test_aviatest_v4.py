from types import SimpleNamespace
import tkinter as tk
import pytest
import aviatest_v4 as v


def test_missing_measurements_are_gaps_and_zero_is_preserved():
    values=v.extract_values({'A':{'summary':{'tmin_a':0,'tmedio_a':'nan','tmax_a':'oops'}}})
    assert values['A']==[0,None,None]
    assert values['C']==[None]*3
    assert values['F']==[None]*3


@pytest.mark.parametrize('value',[float('inf'),float('-inf'),-1,True,{},''])
def test_invalid_numbers_are_not_plotted(value):
    assert v.number(value) is None


def test_count_stage_values_and_orientation_accuracy():
    result=v.extract_values({'D':{'summary':{'stages':{'1':{'t_value':.8},'2':{'t_value':1.2}}}},
                             'B':{'stages':{'1':{'tasks':0,'accuracy_pct':0},'2':{'tasks':10,'accuracy_pct':0},'3':{'accuracy_pct':150}}}})
    assert result['D']==[.8,1.2,None]
    assert result['B']==[None,0,None]


def test_count_summary_zero_is_not_replaced_by_fallback():
    assert v.extract_values({'D':{'summary':{'tmin_c':0,'stages':{'1':{'t_value':9}}}}})['D'][0]==0


def test_colour_scale_has_contrast_and_fixed_numeric_anchors():
    chart=v.IntegralSurface3D
    assert len({chart.colour(x/4) for x in range(9)})==9
    assert chart.colour(2)==chart.colour(10)
    assert chart.colour(0)=='#732317'
    assert chart.colour(1.5)=='#0fa63d'


def test_sixth_test_round_trip_and_restart(tmp_path):
    profile=v.base.UserProfile(name='QA Test',age='30',gender='M')
    store=v.base.UserProgressStore(tmp_path)
    for code in 'ABCDE':
        store.mark_completed(profile,code)
    assert store.next_test_code(profile)=='F'
    owner=SimpleNamespace(current_profile=profile,current_session=SimpleNamespace(session_id='qa',name='QA Test',age='30',gender='M'),base_dir=tmp_path,progress_store=store)
    stages=[{'stage':i,'table_pace':i/2,'errors':0,'duration':10} for i in range(1,4)]
    payload=v.f_payload(owner,stages)
    v.persist_f(owner,payload)
    store=v.base.UserProgressStore(tmp_path)
    assert store.next_test_code(profile) is None
    assert store.get_test_result(profile,'F')['stages']==stages
    assert v.extract_values({'F':store.get_test_result(profile,'F')})['F']==[.5,1,1.5]
    store.reset_progress(profile)
    # Restart unlocks the sequence but retains the previous results, as in v2/v3.
    assert store.get_test_result(profile,'F')['stages']==stages
    assert store.next_test_code(profile)=='A'


def test_partial_f_is_not_marked_complete(tmp_path):
    owner=SimpleNamespace()
    with pytest.raises(ValueError):v.persist_f(owner,{'stages':[{'stage':1}]})


def test_f_excel_keeps_existing_sheet_and_deduplicates_session(tmp_path):
    import openpyxl
    path=v.base._fixed417_external_excel_path(tmp_path)
    wb=openpyxl.Workbook();wb.active['A1']='Existing A–E';wb.save(path);wb.close()
    payload={'session_id':'one','participant':{'name':'QA','age':30,'gender':'M'},'completed_at':'2026-11-01',
             'stages':[{'stage':i,'table_pace':i/2,'errors':0,'duration':10} for i in range(1,4)]}
    v.export_f_excel(tmp_path,payload);v.export_f_excel(tmp_path,payload)
    wb=openpyxl.load_workbook(path)
    try:
        assert wb.worksheets[0]['A1'].value=='Existing A–E'
        assert wb['ЧКТ'].max_row==2
        assert wb['ЧКТ']['F2'].value==.5
        assert wb['ЧКТ']['L2'].value==1.5
    finally:wb.close()


def test_surface_rotation_zoom_and_missing_cells():
    root=tk.Tk();root.geometry('1100x700')
    try:
        values={code:[.5,1,2] for code in v.ORDER}
        chart=v.IntegralSurface3D(root,values);chart.pack(fill='both',expand=True);root.update()
        assert len(chart.find_withtag('sample'))==18
        assert chart.find_withtag('surface')
        assert len(chart.find_withtag('method'))==6
        before=chart.project(1,1,1)
        chart._drag=(0,0);chart.drag(SimpleNamespace(x=120,y=35));root.update()
        assert chart.project(1,1,1)!=before
        chart.change_zoom(100);root.update();assert chart.zoom==1.65
        chart.reset_view();root.update();assert chart.zoom==1
        chart.values={code:[None]*3 for code in v.ORDER};chart.redraw();root.update()
        assert not chart.find_withtag('sample') and not chart.find_withtag('surface')
        chart.values['A']=[0,None,None];chart.redraw();root.update()
        assert len(chart.find_withtag('sample'))==1
        assert not chart.find_withtag('surface')
    finally:root.destroy()
