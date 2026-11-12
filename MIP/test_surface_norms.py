from copy import deepcopy
from pathlib import Path
import math
import tkinter as tk
from types import SimpleNamespace

import pytest
import aviatest_v4 as v
from accounts import AccountStore
from groups import GroupStore
from storage import seed_configs
from surface_norms import accuracy_norm,normalize_surface,read_norms,write_norms
from surface_view import SurfaceCanvas


@pytest.mark.parametrize('value',[0,-1,101,'nan','inf','wrong',True,'1e-320'])
def test_invalid_accuracy_norm(value):
    with pytest.raises(ValueError):accuracy_norm(value)


def test_normalization_preserves_raw_values_and_missing_norms():
    raw={code:[0,.8,1.2] for code in v.ORDER}
    raw['B']=[.95,0,None]
    original=deepcopy(raw)
    values,missing=normalize_surface(raw,[80,None,90])
    assert values['B'][0]==pytest.approx(1.1875) and values['B'][1:]==[None,None] and missing==[2]
    assert values['A']==raw['A'] and values['A'] is not raw['A']
    assert raw==original
    values,missing=normalize_surface(raw,[None]*3)
    assert values['B']==[None]*3 and missing==[1,2,3]
    assert accuracy_norm('82,5')==82.5 and accuracy_norm('') is None
    assert normalize_surface(raw,[80,80,80])[0]['B'][1]==0
    with pytest.raises(ValueError):normalize_surface(raw,[80,80])


def test_group_norm_defaults_copy_and_independence(tmp_path):
    seed_configs(tmp_path,Path(__file__).parent)
    groups=GroupStore(tmp_path)
    assert read_norms(groups.directory(1))==[None]*3
    groups.create(2,4)
    write_norms(groups.directory(2),[80,'85,5',None])
    groups.create(3,6,template=2)
    assert read_norms(groups.directory(3))==[80,85.5,None]
    write_norms(groups.directory(2),[90,95,100])
    assert read_norms(groups.directory(3))==[80,85.5,None]
    account=AccountStore(tmp_path).register('norm-qa','qa-only','qa-only',v.base.UserProfile(name='QA',age=30,gender='Мужской'))
    groups.assign(account[0],2)
    directory,_=groups.prepare_participant(account[0])
    assert read_norms(directory)==[90,95,100]
    (groups.directory(3)/'surface_norms.json').unlink()
    groups.assign(account[0],3)
    directory,_=groups.prepare_participant(account[0])
    assert read_norms(directory)==[None]*3


def test_plane_rotation_reset_colour_and_viewport():
    root=tk.Tk();root.geometry('1366x768')
    values={code:[.25,1.8,.55] for code in v.ORDER}
    try:
        for order,count in ((('A','C','D','B'),12),(v.ORDER,18)):
            chart=SurfaceCanvas(root,values,order=order)
            chart.pack(fill='both',expand=True);root.update()
            assert len(chart.find_withtag('sample'))==count
            assert chart.find_withtag('norm_plane')
            bounds=chart.bbox('surface_raster')
            assert (bounds[2]-bounds[0])/chart.winfo_width()>.45
            assert (bounds[3]-bounds[1])/chart.winfo_height()>.4
            initial=(chart.yaw,chart.pitch,chart.zoom)
            plane=chart.coords(chart.find_withtag('norm_plane')[0])
            chart._drag=(10,10);chart.drag(SimpleNamespace(x=140,y=70));chart.change_zoom(1.3);root.update()
            assert (chart.yaw,chart.pitch,chart.zoom)!=initial
            assert chart.coords(chart.find_withtag('norm_plane')[0])!=plane
            chart.reset_view();root.update()
            assert (chart.yaw,chart.pitch,chart.zoom)==initial
            assert chart.values=={code:values[code] for code in order}
            assert all(',' in chart.itemcget(i,'text') for i in chart.find_withtag('value'))
            assert chart.type(chart.find_withtag('surface_raster')[0])=='image'
            assert len(chart.find_withtag('method_label'))==len(order)
            assert [chart.itemcget(i,'text') for i in chart.find_withtag('stage')]==['min','med','max']
            chart.destroy();root.update()
        from PIL import ImageColor
        low=ImageColor.getrgb(SurfaceCanvas.colour(.5));high=ImageColor.getrgb(SurfaceCanvas.colour(1.5))
        assert low[0]>low[1] and high[1]>high[0] and high[1]>high[2]
    finally:root.destroy()
