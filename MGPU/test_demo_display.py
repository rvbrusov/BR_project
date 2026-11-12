from types import SimpleNamespace
from pathlib import Path
import json
import pytest
import tkinter as tk
import aviatest_v4 as v
from accounts import AccountStore,account_profile
from demo_accounts import ensure_demo_accounts,DEMO_VALUES,DEMO_REVISION
from storage import seed_configs,participant_directory
from groups import GroupStore
from surface_view import surface_data,SurfaceCanvas
from surface_norms import read_norms
from surface_labels import intersects


def test_selected_id_controls_surface_even_with_previous_participant_store(tmp_path):
    seed_configs(tmp_path,Path(__file__).parent);ensure_demo_accounts(v,tmp_path)
    accounts=AccountStore(tmp_path);groups=GroupStore(tmp_path)
    first=accounts.authenticate('user1','password1')
    stale=v.base.UserProgressStore(participant_directory(tmp_path,first[0]))
    shown=[]
    for i in range(1,6):
        profile=account_profile(v.base,*accounts.authenticate(f'user{i}',f'password{i}'))
        owner=SimpleNamespace(current_profile=profile,data_root=tmp_path,groups=groups,progress_store=stale)
        raw,values,norms,missing,_,_=surface_data(owner)
        assert raw['A']==list(DEMO_VALUES[i-1][0])
        assert all(.9<=x<=1.13 for row in values.values() for x in row)
        assert not missing and norms==[80,80,80]
        shown.append(tuple(tuple(values[c]) for c in v.ORDER))
    assert len(set(shown))==5
    assert read_norms(groups.directory(1))==[None,None,None]
    # The demonstration-only fallback must never grade a real B attempt.
    profile=account_profile(v.base,*first)
    payload=stale.get_test_result(profile,'B');payload['data_source']='real_test'
    stale.save_test_result(profile,'B',payload)
    owner.current_profile=profile
    assert surface_data(owner)[1]['B']==[None]*3


def test_revision_replaces_old_identical_synthetic_data_and_keeps_real_result(tmp_path):
    seed_configs(tmp_path,Path(__file__).parent);ensure_demo_accounts(v,tmp_path)
    accounts=AccountStore(tmp_path)
    for i in range(1,6):
        profile=account_profile(v.base,*accounts.authenticate(f'user{i}',f'password{i}'))
        store=v.base.UserProgressStore(participant_directory(tmp_path,profile.participant_id))
        payload=store.get_test_result(profile,'A');payload['summary']={'tmin_a':.5,'tmedio_a':.5,'tmax_a':.5}
        if i==3:payload['data_source']='real_test'
        store.save_test_result(profile,'A',payload)
    with accounts.connect() as db:db.execute('UPDATE aviatest_demo_accounts SET data_revision=2')
    ensure_demo_accounts(v,tmp_path)
    for i in range(1,6):
        profile=account_profile(v.base,*accounts.authenticate(f'user{i}',f'password{i}'))
        directory=participant_directory(tmp_path,profile.participant_id)
        store=v.base.UserProgressStore(directory)
        values=v.extract_values({c:store.get_test_result(profile,c) for c in v.ORDER})
        assert values['A']==([.5]*3 if i==3 else list(DEMO_VALUES[i-1][0]))
        assert (directory/'backups'/f'before-demo-revision-{DEMO_REVISION}.json').exists()


@pytest.mark.parametrize('yaw',[.2,.7853981633974483,1.6,2.6,4.7])
@pytest.mark.parametrize('order',[v.ORDER,('A','C','D','B')])
@pytest.mark.parametrize('size',[(1920,1080),(1366,768),(1024,600),(820,520)])
def test_axis_titles_do_not_collide_with_axis_labels(order,size,yaw):
    root=tk.Tk();root.geometry(f'{size[0]}x{size[1]}')
    try:
        chart=SurfaceCanvas(root,{c:[.96,1.03,1.08] for c in order},order=order)
        chart.pack(fill='both',expand=True);root.update()
        chart.yaw=yaw;chart.redraw();root.update()
        boxes=chart._axis_boxes
        for _,a,tag in boxes:
            if tag not in ('stage_title','z_title'):continue
            assert all(0<=x<=chart.winfo_width() and 0<=y<=chart.winfo_height() for x,y in a)
            assert not any(intersects(a,b) for _,b,other in boxes if other!=tag),(size,order,tag)
    finally:root.destroy()
