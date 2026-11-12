from pathlib import Path
import pytest
import aviatest_v4 as v
from accounts import AccountStore,account_profile,registration_profile
from groups import GroupStore
from storage import seed_configs,participant_directory


def fields():
    return dict(name='Тестовый участник',age='30',education='Высшее',gender='Мужской')


def test_short_profile_leaves_removed_fields_blank():
    data=fields();data.update(flight_hours='123',aircraft_type='Old input',position='Old input')
    profile=registration_profile(v.base,data)
    assert profile.name==data['name'] and profile.age==30 and profile.education=='Высшее'
    assert profile.flight_hours==profile.aircraft_type==profile.position==''


@pytest.mark.parametrize('key,value,message',[
    ('name',' ','ФИО'),('age','','возраст'),('age','0','диапазоне'),
    ('age','121','диапазоне'),('age','-1','целым'),('age','30.5','целым'),
    ('age','nan','целым'),('age','²','целым'),('education','','образование'),('gender','unknown','пол')])
def test_short_profile_validation(key,value,message):
    data=fields();data[key]=value
    with pytest.raises(ValueError,match=message):registration_profile(v.base,data)


def test_legacy_profile_and_results_survive_new_same_name_registration(tmp_path):
    seed_configs(tmp_path,Path(__file__).parent)
    accounts=AccountStore(tmp_path)
    legacy=v.base.UserProfile(name='Тестовый участник',age=30,gender='Мужской',
        education='Высшее',flight_hours='850.5',aircraft_type='Ту-204',position='КВС')
    old=accounts.register('old','qa-old','qa-old',legacy)
    groups=GroupStore(tmp_path)
    old_profile=account_profile(v.base,*old)
    store=v.base.UserProgressStore(participant_directory(tmp_path,old[0]))
    store.save_test_result(old_profile,'A',{'summary':{'tmin_a':.8,'tmedio_a':1.,'tmax_a':1.2}})
    store.mark_completed(old_profile,'A')
    before=store.progress_file.read_bytes()
    new=accounts.register('new','qa-new','qa-new',registration_profile(v.base,fields()))
    assert old[0]!=new[0] and groups.membership(new[0]) is None
    assert accounts.authenticate('old','qa-old')==old
    assert old[1]['flight_hours']=='850.5' and old[1]['aircraft_type']=='Ту-204' and old[1]['position']=='КВС'
    assert store.progress_file.read_bytes()==before
