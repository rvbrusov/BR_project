import math
import tkinter as tk
from types import SimpleNamespace
import pytest
import aviatest_v4 as v
from approved_surface import SurfaceCanvas

@pytest.mark.parametrize('order',[v.ORDER,('A','C','D','B')])
def test_approved_surface_measurements_legend_floor_and_occlusion(order):
    root=tk.Tk();root.geometry('1200x800')
    values={c:[1.4-i*.08,.9,.3+i*.07] for i,c in enumerate(order)}
    try:
        c=SurfaceCanvas(root,values,order=order);c.pack(fill='both',expand=True);root.update()
        for x,code in enumerate(order):
            for y,z in enumerate(values[code]):assert c.mesh[x*6][y*10][2]==pytest.approx(z)
        assert len(c.find_withtag('sample'))==3*len(order)
        assert len(c.find_withtag('floor_sample'))==3*len(order)
        assert not c.find_withtag('floor_value') and not c.find_withtag('floor_projection')
        assert c.find_withtag('floor_curve_within') and c.find_withtag('floor_curve_across')
        labels=[c.itemcget(i,'text') for i in c.find_withtag('method_label')]
        assert labels==[f'{v.ORDER.index(code)+1} · {dict(zip(v.ORDER,v.TITLES))[code]}' for code in order]
        assert [c.itemcget(i,'text') for i in c.find_withtag('legend_tick')]==['0','0,2','0,4','0,6','0,8','1,0','1,2','1,4','1,6']
        positions=[c.coords(i)[1] for i in c.find_withtag('legend_tick')]
        gaps=[a-b for a,b in zip(positions,positions[1:])]
        assert max(gaps)-min(gaps)<1e-8
        assert c.itemcget(c.find_withtag('norm_tick_highlight')[0],'fill')=='#d9efbf'
        initial=dict(c.stats);depth=c.depth.copy();c.plane=False;c.draw()
        assert all(c.stats[k]==n for k,n in initial.items() if not k.startswith('norm'))
        assert (c.depth==depth).all()
        widths={kind:[float(c.itemcget(i,'width')) for i in c.find_withtag(kind) if 'surface_line' in c.gettags(i)] for kind in ('visible_line','hidden_line')}
        if widths['hidden_line']:assert max(widths['hidden_line'])<min(widths['visible_line'])
        for item in c.find_withtag('stem'):assert c.itemcget(item,'fill')=='#df1218'
        for yaw,pitch in ((1.9,.6),(-.3,1),(-2.4,.4)):
            c.yaw,c.pitch=yaw,pitch;c.draw()
            assert len(c.find_withtag('method_label'))==len(order)
            for pose in c.axis_poses.values():
                a,b=[c.project(*p) for p in pose['axis']];dx,dy=b[0]-a[0],b[1]-a[1]
                angle=-math.radians(pose['angle'])
                assert abs(math.sin(angle)*dx-math.cos(angle)*dy)<1e-7
                px,py=pose['anchor_screen'];xx,yy=pose['screen']
                assert abs((xx-px)*dx+(yy-py)*dy)<1e-7
        assert c.stats['surfaceHidden']!=initial.get('surfaceHidden',0)
        c.reset_view();root.update()
        assert c.yaw==c.INITIAL_YAW and c.pitch==c.INITIAL_PITCH and c.zoom==1
    finally:root.destroy()

def test_display_names_keep_storage_keys():
    assert v.ORDER==('A','C','D','E','F','B')
    assert v.TITLES[2]=='Счётно-логическая деятельность'
    assert [v.base.TEST_LABELS[c] for c in v.ORDER]==[f'Тест {i}' for i in range(1,7)]

def test_legacy_widget_captions_are_numbered_without_changing_variables():
    from display_names import install_display_names,display_text
    install_display_names()
    assert display_text('ТЕСТ F · Тест B · Тест А')=='ТЕСТ 5 · Тест 6 · Тест 1'
    root=tk.Tk()
    try:
        label=tk.Label(root,text='Тест C · Запоминание фигур');label.pack()
        assert label.cget('text')=='Тест 2 · Запоминание фигур'
        label.configure(text='Тест D');assert label.cget('text')=='Тест 3'
        root.title('СПР — Тест B');assert root.title()=='СПР — Тест 6'
        variable=tk.StringVar(value='A');assert variable.get()=='A'
    finally:root.destroy()
