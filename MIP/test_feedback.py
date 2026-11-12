import math
import tkinter as tk
import openpyxl
import aviatest_v4 as v

def test_isometric_axes_and_reference_plane():
    root=tk.Tk();root.geometry('1100x700')
    try:
        chart=v.IntegralSurface3D(root,{c:[.5,1,1.4] for c in v.ORDER});chart.pack(fill='both',expand=True);root.update()
        o=chart.project(0,0,0)
        vectors=[(p[0]-o[0],p[1]-o[1]) for p in [chart.project(1,0,0),chart.project(0,1,0),chart.project(0,0,1)]]
        for i in range(3):
            a,b=vectors[i],vectors[(i+1)%3]
            angle=math.degrees(math.acos(sum(x*y for x,y in zip(a,b))/(math.hypot(*a)*math.hypot(*b))))
            assert abs(angle-120)<1e-8
        assert chart.find_withtag('norm_plane')
        assert len(chart.find_withtag('curve_within'))==6
        assert len(chart.find_withtag('curve_across'))==3
        assert [chart.itemcget(i,'text') for i in chart.find_withtag('stage')]==['MIN','MED','MAX']
    finally: root.destroy()

def test_curves_pass_samples_and_do_not_bridge_gaps_or_overshoot():
    points=[(i,0,z) for i,z in enumerate([.1,1.4,.3,None,.8,1.1])]
    curves=v.smooth_runs(points)
    assert len(curves)==2
    assert curves[0][0]==points[0] and curves[0][16]==points[1] and curves[0][-1]==points[2]
    assert all(.1-1e-9<=p[2]<=1.4+1e-9 for p in curves[0])
    assert curves[1][0]==points[4]

def test_main_excel_columns_preserve_existing_values_and_zero(tmp_path):
    path=v.base._fixed417_external_excel_path(tmp_path)
    wb=openpyxl.Workbook();ws=wb.active
    ws.cell(4,208,'Должность');ws.cell(5,2,'QA');ws.cell(5,100,123);ws.cell(5,208,'Pilot');wb.save(path);wb.close()
    payload={'session_id':'qa','participant':{'name':'QA','age':30,'gender':'M'},
             'stages':[{'stage':i,'table_pace':0 if i==1 else i/2,'errors':i-1,'duration':10*i} for i in range(1,4)]}
    v.export_f_excel(tmp_path,payload);v.export_f_excel(tmp_path,payload)
    wb=openpyxl.load_workbook(path);ws=wb.worksheets[0]
    try:
        cols=v.ensure_chkt_columns(ws)
        assert len(cols)==9 and min(cols.values())==209
        assert ws.max_column==217 and ws.max_row==5
        assert ws.cell(5,100).value==123 and ws.cell(5,208).value=='Pilot'
        assert ws.cell(5,cols[(1,'table_pace')]).value==0
        assert ws.cell(5,cols[(3,'duration')]).value==30
        assert wb['ЧКТ'].max_row==2
    finally:wb.close()

def test_existing_detail_sheet_backfills_missing_main_values(tmp_path):
    path=v.base._fixed417_external_excel_path(tmp_path)
    wb=openpyxl.Workbook();main=wb.active
    v.ensure_integrated_headers(main)
    cols=v.ensure_chkt_columns(main)
    main.cell(5,2,'QA');main.cell(5,cols[(1,'table_pace')],9.5)
    detail=wb.create_sheet('ЧКТ');detail.append(['session','date','name','age','gender']+list(range(9)))
    detail.append(['qa','2026-11-01','QA',30,'M',0,0,10,.8,1,20,1.2,2,30])
    wb.save(path);wb.close()
    v.prepare_integrated_excel(tmp_path)
    wb=openpyxl.load_workbook(path)
    try:
        ws=wb.worksheets[0]
        assert ws.cell(5,cols[(1,'table_pace')]).value==9.5
        assert ws.cell(5,cols[(1,'errors')]).value==0
        assert ws.cell(5,cols[(3,'duration')]).value==30
    finally:wb.close()
