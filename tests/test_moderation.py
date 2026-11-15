import json
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app import create_app
from backend.config import Settings
from backend.game import act, prepare, view
from backend.generation import GeneratedAnswer, validate_notes, validate_outputs
from backend.moderation import contains_profanity, contains_text_art, screen_answers
from backend.storage import RoomError, RoomStore


@pytest.mark.parametrize('text', [
    'fuck you bitch', 'B-1-T-C-H', 'b i t c h', 'b.i.t.c.h', 'b!tch',
    'b\u200bitch', 'ｂ１ｔｃｈ', 'bítch', 'bіtch', 'f u c k', 'F*CK', 'SH1T!',
])
def test_common_obfuscations_are_blocked(text):
    assert contains_profanity(text)


@pytest.mark.parametrize('text', ['My assignment is for class.', 'I assess the classic solution.',
                                   'I live in Scunthorpe.', 'i ask chatgpt bc im cooked', 'I use a shell.',
                                   'My friend Dick helps me debug.', 'I care for an ass on a farm.',
                                   'I keep a cock with the hens.'])
def test_harmless_substrings_and_slang_are_allowed(text):
    assert not contains_profanity(text)


@pytest.mark.parametrize('text', ['(=^..^=)', '8===D', '卐 卐', '卍 test', '!!!', '😂😂'])
def test_text_art_and_symbol_only_answers_are_blocked(text):
    assert contains_text_art(text)


@pytest.mark.parametrize('text', ['C++', "print('hello')", 'lol 😂', 'i dont know', 'I like tutoring kids.'])
def test_words_code_and_inline_emoji_remain_valid(text):
    assert not contains_text_art(text)


def test_submission_and_samples_reject_profanity_without_writes():
    store=Mock();room_id=uuid4().hex
    with TestClient(create_app(Settings(_env_file=None),store)) as client:
        for text in ('fuck you bitch','B-1-T-C-H','(=^..^=)','8===D','卐 卐'):
            response=client.post(f'/api/rooms/{room_id}/submissions',json={'submission_id':str(uuid4()),'answer':text})
            assert response.status_code==422 and text not in response.text
        client.cookies.set('gth_host','test-token')
        assert client.post(f'/api/rooms/{room_id}/samples',json={'answers':['B-1-T-C-H']}).status_code==422
        store.submit_answer.assert_not_called();store.add_samples.assert_not_called()


def test_ai_screen_preserves_original_writing_and_excludes_flagged_answers():
    answers=['i usally debug agian bc thats easier','A threatening message','B-1-T-C-H','(=^..^=)']
    client=Mock();client.models.generate_content.return_value.text=json.dumps({'decisions':[{'id':1,'allowed':False},{'id':0,'allowed':True}]})
    with patch('backend.moderation.genai.Client') as provider:
        provider.return_value.__enter__.return_value=client
        accepted,rejected=screen_answers(Settings(_env_file=None,gemini_api_key='test-placeholder'),answers,'A classroom question?')
    assert accepted==answers[:1] and set(rejected)==set(answers[1:])
    sent=json.loads(client.models.generate_content.call_args.kwargs['contents'])
    assert sent['answers'][0]['text']==answers[0] and len(sent['answers'])==2
    assert sent['question']=='A classroom question?'


@pytest.mark.parametrize('decisions', [[], [{'id':0,'allowed':True},{'id':0,'allowed':True}],
                                        [{'id':99,'allowed':True}], [{'id':0,'allowed':'yes'}]])
def test_incomplete_or_invalid_ai_decisions_fail_closed(decisions):
    client=Mock();client.models.generate_content.return_value.text=json.dumps({'decisions':decisions})
    with patch('backend.moderation.genai.Client') as provider:
        provider.return_value.__enter__.return_value=client
        with pytest.raises(RoomError) as exc:
            screen_answers(Settings(_env_file=None,gemini_api_key='test-placeholder'),['safe answer'])
    assert exc.value.status_code==503


def room_client(answers):
    room_id=uuid4().hex
    state=dict(status='closed',rounds=20,question='Question?',submission_count=len(answers))
    store=Mock();store.answers.return_value=answers
    store.get_host_room.side_effect=lambda *args:RoomStore.host_view(room_id,state)
    def mutate(room,token,operation):operation(state);return RoomStore.host_view(room_id,state)
    store.mutate.side_effect=mutate
    return room_id,state,store


def test_flagged_answers_are_removed_before_sampling_and_never_reach_chameleon():
    room_id,state,store=room_client(['safe student answer','unsafe student answer'])
    def remove(*args):state['submission_count']-=1
    store.remove_answers.side_effect=remove
    generated=[dict(text='A screened AI answer',style='Basic',level=2)]
    with TestClient(create_app(Settings(_env_file=None),store)) as client:
        client.cookies.set('gth_host','test-token')
        with patch('backend.moderation.screen_answers',return_value=(['safe student answer'],['unsafe student answer'])), patch('backend.generation.generate',return_value=generated) as generator:
            response=client.post(f'/api/rooms/{room_id}/generate')
    assert response.status_code==200 and state['status']=='ready'
    assert response.json()['submission_count']==1
    assert generator.call_args.args[2]==['safe student answer']
    store.remove_answers.assert_called_once()
    assert {row['text'] for row in state['game']['remaining']}=={'safe student answer','A screened AI answer'}


def test_screening_outage_restores_closed_room_without_creating_a_game():
    room_id,state,store=room_client(['safe answer'])
    with TestClient(create_app(Settings(_env_file=None),store)) as client:
        client.cookies.set('gth_host','test-token')
        with patch('backend.moderation.screen_answers',side_effect=RoomError(503,'Screening unavailable')), patch('backend.generation.generate') as generator:
            assert client.post(f'/api/rooms/{room_id}/generate').status_code==503
        generator.assert_not_called();store.remove_answers.assert_not_called()
    assert state['status']=='closed' and 'game' not in state


def test_all_rejected_answers_leave_no_game_and_a_corrected_count():
    room_id,state,store=room_client(['unsafe answer'])
    def remove(*args):state['submission_count']=0
    store.remove_answers.side_effect=remove
    with TestClient(create_app(Settings(_env_file=None),store)) as client:
        client.cookies.set('gth_host','test-token')
        with patch('backend.moderation.screen_answers',return_value=([],['unsafe answer'])), patch('backend.generation.generate') as generator:
            assert client.post(f'/api/rooms/{room_id}/generate').status_code==409
        generator.assert_not_called()
    assert state['status']=='closed' and state['submission_count']==0 and 'game' not in state


@pytest.mark.parametrize('old_version', [None, 1])
def test_old_unscreened_games_cannot_return_answers_or_accept_actions(old_version):
    game=prepare(['safe human'],[dict(text='safe AI',style='Basic',level=2)])
    del game['moderation_version']
    if old_version is not None:game['moderation_version']=old_version
    state={'status':'ready','game':game}
    with pytest.raises(RoomError):view(state)
    with pytest.raises(RoomError):act(state,'start')
    assert state['status']=='ready'


def test_unsafe_generated_text_and_notes_are_rejected():
    with pytest.raises(ValueError):validate_outputs(['B-1-T-C-H'],[],set())
    with pytest.raises(ValueError):validate_notes([GeneratedAnswer(text='Safe answer',explanation='I used the word shit.')],set())
