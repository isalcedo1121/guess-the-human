from copy import deepcopy
from unittest.mock import Mock, patch
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from app import create_app
from backend.config import Settings
from backend.game import human_sample,prepare,act,view
from backend.generation import validate_outputs,generate
from backend.storage import RoomError


def data():
    return dict(status='ready',game=prepare(['human one','human two'],[
        dict(text='mocked AI one',style='Basic',level=1),dict(text='mocked AI two',style='Slang',level=3)]))

def test_balance_and_sampling():
    assert len(human_sample([str(i) for i in range(60)],10))==5
    assert len(human_sample(['only one'],20))==1
    with pytest.raises(RoomError):human_sample([],10)
    g=data()['game'];assert sum(x['actual']=='ai' for x in g['remaining'])==2
    assert len(set(x['id'] for x in g['remaining']))==4


def test_full_game_and_double_click():
    d=data();act(d,'start');seen=set()
    while d['status']=='playing':
        current=d['game']['current'];assert current['id'] not in seen;seen.add(current['id'])
        assert 'actual' not in view(d)['current']
        act(d,'guess',current['id'],current['actual']);act(d,'guess',current['id'],current['actual'])
        assert view(d)['current']['correct']
        act(d,'next',current['id'])
    result=view(d);assert result['assessed']==4 and result['correct']==4 and result['accuracy']==100


def test_wrong_score_and_adaptation():
    d=data();act(d,'start')
    while d['game']['current']['actual']!='ai':act(d,'skip',d['game']['current']['id'])
    current=d['game']['current'];act(d,'guess',current['id'],'human')
    assert d['game']['level']==1 and view(d)['incorrect']==1
    act(d,'end');assert view(d)['ai_missed']==1


def test_stale_and_premature_actions():
    d=data();act(d,'start')
    with pytest.raises(RoomError):act(d,'next',d['game']['current']['id'])
    with pytest.raises(RoomError):act(d,'guess','stale','human')
    act(d,'end');assert view(d)['accuracy']==0

@pytest.mark.parametrize('texts',[[''],['x'*281],['same','same'],['HUMAN ANSWER']])
def test_output_guardrails(texts):
    with pytest.raises(ValueError):validate_outputs(texts,['human answer'],set())


def test_gemini_failure_is_not_faked():
    settings=Settings(_env_file=None,gemini_api_key='test-placeholder')
    with patch('backend.generation.genai.Client',side_effect=RuntimeError('mock outage')):
        with pytest.raises(RoomError) as exc:generate(settings,'Question?',['human'],1)
    assert exc.value.status_code==502


def test_api_validation_authorization_and_failure():
    store=Mock();settings=Settings(_env_file=None,app_env='test')
    with TestClient(create_app(settings,store)) as client:
        assert client.post('/api/rooms',json={'question':' ','rounds':10}).status_code==422
        assert client.post('/api/rooms',json={'question':'valid','rounds':11}).status_code==422
        for answer in ('','  ','x'*281):
            assert client.post('/api/rooms/'+uuid4().hex+'/submissions',json={'submission_id':str(uuid4()),'answer':answer}).status_code==422
        assert client.get('/api/rooms/'+uuid4().hex+'/host').status_code==403
        assert client.post('/api/rooms',headers={'Origin':'https://other.example'},json={'question':'hello','rounds':10}).status_code==403
        from google.api_core.exceptions import ServiceUnavailable
        store.submit_answer.side_effect=ServiceUnavailable('mock outage')
        assert client.post('/api/rooms/'+uuid4().hex+'/submissions',json={'submission_id':str(uuid4()),'answer':'valid answer'}).status_code==503
        store.create_room.assert_not_called()


def test_transaction_read_conflict_retries():
    from backend.storage import run_transaction
    from google.api_core.exceptions import Aborted
    callback=Mock(side_effect=[Aborted('conflict'),{'accepted':True}])
    with patch('backend.storage.time.sleep'):
        assert run_transaction(Mock(),callback)=={'accepted':True}
    assert callback.call_count==2


def test_generation_failure_restores_closed_room():
    store=Mock();state=dict(status='closed',rounds=10,question='Question?')
    def mutate(room,token,operation):
        operation(state);return dict(state)
    store.mutate.side_effect=mutate
    store.get_host_room.return_value=state
    store.answers.return_value=['human answer']
    with TestClient(create_app(Settings(_env_file=None),store)) as client:
        client.cookies.set('gth_host','test-token')
        with patch('backend.moderation.screen_answers',return_value=(['human answer'],[])), patch('backend.generation.generate',side_effect=RoomError(502,'mocked provider outage')):
            response=client.post('/api/rooms/'+uuid4().hex+'/generate')
        assert response.status_code==502 and state['status']=='closed'


def test_adaptation_up_and_unique_humans():
    assert len(human_sample(['same','same'],10))==1
    d=data();act(d,'start')
    while d['game']['current']['actual']!='ai':act(d,'skip',d['game']['current']['id'])
    row=d['game']['current'];act(d,'guess',row['id'],'ai')
    assert d['game']['level']==3
    act(d,'end');assert view(d)['ai_caught']==1


def test_randomized_order_with_reproducible_seeds():
    import random
    state=random.getstate()
    try:
        random.seed(1);first=[x['text'] for x in data()['game']['remaining']]
        random.seed(2);second=[x['text'] for x in data()['game']['remaining']]
        assert first!=second and sorted(first)==sorted(second)
    finally:random.setstate(state)


def test_begin_closes_generates_and_starts_in_one_request():
    from backend.storage import RoomStore
    store=Mock();rid=uuid4().hex
    state=dict(status='open',rounds=10,question='Custom question?',submission_count=3)
    store.get_host_room.side_effect=lambda *args:RoomStore.host_view(rid,state)
    def close(*args):state['status']='closed';return RoomStore.host_view(rid,state)
    store.close_room.side_effect=close
    def mutate(room,token,operation):operation(state);return RoomStore.host_view(rid,state)
    store.mutate.side_effect=mutate;store.answers.return_value=['one human','two human','three human']
    mocked=[dict(text=f'mocked AI {i}',style='Basic',level=2,explanation='Test fixture') for i in range(3)]
    with TestClient(create_app(Settings(_env_file=None),store)) as client:
        client.cookies.set('gth_host','test-token')
        with patch('backend.moderation.screen_answers',return_value=(store.answers.return_value,[])), patch('backend.generation.generate',return_value=mocked) as generate_mock:
            first=client.post('/api/rooms/'+rid+'/begin')
            assert first.status_code==200 and first.json()['status']=='playing'
            assert first.json()['game']['round']==1 and first.json()['game']['total']==6
            assert 'actual' not in first.json()['game']['current']
            assert client.post('/api/rooms/'+rid+'/begin').json()==first.json()
            generate_mock.assert_called_once()


def test_sample_endpoints_require_host_and_validate_answers():
    store=Mock();rid=uuid4().hex
    with TestClient(create_app(Settings(_env_file=None),store)) as client:
        assert client.get('/api/rooms/'+rid+'/samples').status_code==403
        assert client.post('/api/rooms/'+rid+'/samples',json={'answers':['valid sample']}).status_code==403
        client.cookies.set('gth_host','test-token')
        for answers in ([],[' '],['x'*281],['valid']*21):
            assert client.post('/api/rooms/'+rid+'/samples',json={'answers':answers}).status_code==422
        store.add_samples.assert_not_called()
