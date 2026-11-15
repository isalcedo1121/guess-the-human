"""Live Firestore/Gemini verification using synthetic participants; never prints keys/cookies."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import json
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
from fastapi.testclient import TestClient
from app import create_app
from backend.config import Settings


def run():
    evidence={'mode':'real Firestore and real Gemini; synthetic human inputs','examples':[]}
    app=create_app(Settings())
    with TestClient(app) as host:
        created=host.post('/api/rooms',json={'question':"What do you do when your code doesn't work?",'rounds':10})
        assert created.status_code==201,created.text
        room=created.json();rid=room['id'];base='/api/rooms/'+rid
        try:
            texts=['I take a walk then come back with coffee.','print every variable until the bug confesses','I ask my rubber duck to review the loop.','undo the last change and run it again','I read the error twice and check the docs']
            def submit(text):
                with TestClient(app) as student:
                    sid=str(uuid4());body={'submission_id':sid,'answer':text}
                    assert student.get(base+'/host').status_code==403
                    assert student.post(base+'/submissions',json=body).status_code==200
                    assert student.post(base+'/submissions',json=body).status_code==200
                    assert student.get(base).json().keys()=={'question','status','submitted'}
            with ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(submit,texts))
            assert host.get(base+'/host').json()['submission_count']==5
            evidence['examples'].append({'input':texts,'accepted_count':5,'duplicate_retries':'count remains 5','independent_sessions':5})
            assert host.post(base+'/close').status_code==200
            with TestClient(app) as late:
                assert late.post(base+'/submissions',json={'submission_id':str(uuid4()),'answer':'late answer'}).status_code==409
            generated=host.post(base+'/generate')
            evidence['generation_status']=generated.status_code
            if generated.status_code!=200:
                evidence['generation_error']=generated.json();return evidence
            stored=app.state.room_store.rooms.document(rid).get().to_dict()
            ai=[x for x in stored['game']['remaining'] if x['actual']=='ai']
            evidence['examples'].append({'model':Settings().gemini_model,'real_ai_outputs':ai})
            result=host.post(base+'/start').json()
            total=0
            while result['status']=='playing':
                current=result['game']['current'];assert 'actual' not in current
                guessed=host.post(base+'/guess',json={'answer_id':current['id'],'guess':'human'})
                assert guessed.status_code==200,guessed.text
                assert host.post(base+'/guess',json={'answer_id':current['id'],'guess':'human'}).json()==guessed.json()
                result=host.post(base+'/next',json={'answer_id':current['id']}).json();total+=1
            assert result['game']['correct']==5 and result['game']['incorrect']==5
            assert total==10 and result['game']['accuracy']==50
            evidence['examples'].append({'guesses':'human for every round','result':result['game']})
            evidence['end_to_end']='passed'
        finally:
            ref=app.state.room_store.rooms.document(rid)
            for doc in ref.collection('submissions').stream():doc.reference.delete()
            ref.delete()
    return evidence

if __name__=='__main__':
    result=run()
    Path('evidence/live_examples.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))

    sys.exit(0 if result.get('end_to_end') == 'passed' else 1)
