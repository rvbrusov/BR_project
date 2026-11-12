from pathlib import Path
import importlib.util
import pytest
import aviatest_v4 as v
from accounts import AccountStore,account_profile
from demo_accounts import ensure_demo_accounts
from groups import GroupStore
from storage import participant_directory,seed_configs
from surface_view import surface_data
from types import SimpleNamespace


def test_user7_exact_letter_values_and_complete_profile(tmp_path):
    seed_configs(tmp_path,Path(__file__).parent);assert ensure_demo_accounts(v,tmp_path)=={'user1','user2','user3','user4','user5','user7'}
    accounts=AccountStore(tmp_path);profile=account_profile(v.base,*accounts.authenticate('user7','password7'))
    groups=GroupStore(tmp_path);store=v.base.UserProgressStore(participant_directory(tmp_path,profile.participant_id))
    owner=SimpleNamespace(current_profile=profile,data_root=tmp_path,groups=groups,progress_store=store)
    _,values,norms,missing,group,error=surface_data(owner)
    expected={'A':[1.4,1.03,.5],'C':[1.2,1.01,.4],'D':[1.2,.8,.3],'E':[.8,.7,.5],'F':[1.04,.98,.8],'B':[1.05,.8,.7]}
    for code,triple in expected.items():assert values[code]==pytest.approx(triple)
    assert norms==[80,80,80] and not missing and not error and group['test_count']==6
    assert store.next_test_code(profile) is None
    assert 'Испытуемый 7' in profile.name
    assert accounts.authenticate('user7','wrong') is None
    assert accounts.authenticate('user6','password6') is None


def test_upgrade_adds_seventh_without_rewriting_five_or_their_groups(tmp_path):
    source=Path(__file__).parent.parent/'aviatest_v4_18_mip/demo_accounts.py'
    spec=importlib.util.spec_from_file_location('previous_demo_accounts',source);old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
    seed_configs(tmp_path,Path(__file__).parent);old.ensure_demo_accounts(v,tmp_path)
    accounts=AccountStore(tmp_path);groups=GroupStore(tmp_path);groups.create(2,4)
    first=accounts.authenticate('user1','password1');groups.assign(first[0],2)
    with accounts.connect() as db:before=db.execute('SELECT * FROM accounts ORDER BY login').fetchall()
    files={p:p.read_bytes() for p in (tmp_path/'participants').rglob('*') if p.is_file()}
    ensure_demo_accounts(v,tmp_path);groups=GroupStore(tmp_path)
    with accounts.connect() as db:after=db.execute("SELECT * FROM accounts WHERE login!='user7' ORDER BY login").fetchall()
    assert before==after
    assert all(p.read_bytes()==data for p,data in files.items())
    assert groups.membership(first[0])['number']==2
    seventh=accounts.authenticate('user7','password7');assert groups.membership(seventh[0])['test_count']==6


def test_existing_user7_is_never_claimed_or_password_reset(tmp_path):
    accounts=AccountStore(tmp_path);profile=v.base.UserProfile(name='Existing real user seven',age=35,gender='Мужской')
    existing=accounts.register('user7','existing-only','existing-only',profile)
    seed_configs(tmp_path,Path(__file__).parent);assert len(ensure_demo_accounts(v,tmp_path))==5
    assert accounts.authenticate('user7','existing-only')==existing
    assert accounts.authenticate('user7','password7') is None
    with accounts.connect() as db:assert not db.execute("SELECT 1 FROM aviatest_demo_accounts WHERE login='user7'").fetchone()
