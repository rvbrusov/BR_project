from pathlib import Path
import json
import pytest

import aviatest_v4 as v
from accounts import AccountStore, account_profile
from groups import GroupStore, group_progress_store
from storage import seed_configs, participant_directory


def setup(tmp_path):
    seed_configs(tmp_path, Path(__file__).parent)
    return AccountStore(tmp_path)


def profile():
    return v.base.UserProfile(name='Group QA',age=30,gender='Мужской')


def test_existing_active_new_pending_and_restart(tmp_path):
    accounts=setup(tmp_path)
    old=accounts.register('existing','old-only','old-only',profile())
    groups=GroupStore(tmp_path)
    assert groups.membership(old[0]) == {'number':1,'test_count':6}
    new=accounts.register('new','new-only','new-only',profile())
    assert groups.membership(new[0]) is None
    assert GroupStore(tmp_path).membership(new[0]) is None
    with pytest.raises(ValueError,match='ожидает назначения'):
        groups.prepare_participant(new[0])
    assert not participant_directory(tmp_path,new[0]).exists()
    groups.create(25,4)
    groups.assign(new[0],25)
    assert GroupStore(tmp_path).codes(new[0]) == tuple('ACDB')
    assert accounts.authenticate('existing','old-only') == old
    assert accounts.authenticate('new','new-only') == new
    assert (tmp_path/'backups/before_groups_v45.sqlite3').exists()


def test_independent_settings_and_attempt_snapshot(tmp_path):
    accounts=setup(tmp_path)
    groups=GroupStore(tmp_path)
    for number,count in ((2,4),(3,4),(87,6)):
        groups.create(number,count)
    orientation=groups.directory(2)/'orientation_config.json'
    data=json.loads(orientation.read_text(encoding='utf-8-sig'))
    data['stage_1_time_s']=37
    orientation.write_text(json.dumps(data),encoding='utf-8')
    assert json.loads((groups.directory(1)/orientation.name).read_text(encoding='utf-8-sig'))['stage_1_time_s'] != 37
    first=accounts.register('first','a','a',profile())
    second=accounts.register('second','b','b',profile())
    groups.assign(first[0],2);groups.assign(second[0],87)
    directory,member=groups.prepare_participant(first[0])
    other,_=groups.prepare_participant(second[0])
    assert json.loads((directory/orientation.name).read_text())['stage_1_time_s']==37
    assert json.loads((other/orientation.name).read_text())['stage_1_time_s']!=37
    user=account_profile(v.base,*first)
    store=group_progress_store(v.base,directory,groups.codes(first[0]),member)
    store.save_test_result(user,'A',{'summary':{'tmin_a':.8,'tmedio_a':1.,'tmax_a':1.2}})
    result=store.get_test_result(user,'A')
    assert result['study_group']=={'number':2,'test_count':4}
    assert result['group_settings'][orientation.name]['stage_1_time_s']==37
    with pytest.raises(ValueError,match='недоступна'):
        store.save_test_result(user,'F',{'stages':[]})
    for code in 'ABCD':store.mark_completed(user,code)
    assert store.next_test_code(user) is None
    before=store.progress_file.read_bytes()
    groups.assign(first[0],87)
    assert store.progress_file.read_bytes()==before
    assert set(store._load()[user.key]['results'])=={'A'}


@pytest.mark.parametrize('number', [0,-1,'../1','a','1.5','1000000000'])
def test_invalid_group_numbers(tmp_path,number):
    groups=GroupStore(tmp_path)
    with pytest.raises(ValueError):groups.create(number,4)


def test_invalid_duplicate_variant_and_atomic_assignment(tmp_path):
    accounts=setup(tmp_path);groups=GroupStore(tmp_path)
    with pytest.raises(ValueError,match='уже существует'):groups.create(1,6)
    with pytest.raises(ValueError,match='четыре или шесть'):groups.create(2,5)
    row=accounts.register('pending','a','a',profile())
    with pytest.raises(ValueError,match='не найдена'):groups.assign(row[0],99)
    with pytest.raises(ValueError,match='Участник не найден'):groups.assign_many([row[0],'missing'],1)
    assert groups.membership(row[0]) is None


def test_four_and_six_surface_geometry():
    import tkinter as tk
    root=tk.Tk();root.geometry('1100x700')
    try:
        values={code:[.4,1.7,.2] for code in v.ORDER}
        for codes,count in ((('A','C','D','B'),12),(v.ORDER,18)):
            chart=v.IntegralSurface3D(root,values,order=codes)
            chart.pack(fill='both',expand=True);root.update()
            assert len(chart.find_withtag('sample'))==count
            assert len(chart.find_withtag('method'))==len(codes)
            assert set(chart.values)==set(codes)
            assert chart.find_withtag('surface')
            chart.destroy();root.update()
    finally:root.destroy()
