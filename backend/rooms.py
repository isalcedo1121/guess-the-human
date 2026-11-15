"""Room and submission endpoints. Students never receive answers or host secrets."""

import hashlib
import logging
import secrets
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, StringConstraints, UUID4

from backend.storage import RoomStore

router = APIRouter(prefix="/api/rooms", tags=["rooms"])
logger = logging.getLogger(__name__)


class CreateRoom(BaseModel):
    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=200)]
    rounds: Annotated[int, Field(strict=True, ge=10, le=20, multiple_of=2)] = 20


class SubmitAnswer(BaseModel):
    submission_id: UUID4
    answer: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=280)]


def get_store(request: Request) -> RoomStore:
    store = request.app.state.room_store
    if store is None:
        raise HTTPException(503, "Room storage is not configured.")
    return store


def host_hash(request: Request):
    token = request.cookies.get("gth_host")
    if not token:
        raise HTTPException(403, "Host access required.")
    return hashlib.sha256(token.encode()).hexdigest()


def check_origin(request: Request):
    origin = request.headers.get("origin")
    if origin and origin != str(request.base_url).rstrip("/"):
        raise HTTPException(403, "Request origin not allowed.")


@router.post("", status_code=201)
def create_room(body: CreateRoom, request: Request, response: Response,
                store: RoomStore = Depends(get_store)):
    check_origin(request)
    token = secrets.token_urlsafe(32)
    room = store.create_room(body.question, body.rounds, hashlib.sha256(token.encode()).hexdigest())
    response.set_cookie(
        "gth_host", token, httponly=True, samesite="strict", max_age=86400,
        path=f"/api/rooms/{room['id']}",
        secure=request.app.state.settings.app_env == "production" or request.url.scheme == "https",
    )
    logger.info("Room created: %s", room["id"])
    return room


@router.get("/{room_id}")
def participant_room(room_id: UUID, submission_id: UUID4 | None = None,
                     store: RoomStore = Depends(get_store)):
    return store.get_participant_room(room_id.hex, submission_id.hex if submission_id else None)


@router.get("/{room_id}/host")
def host_room(room_id: UUID, request: Request, store: RoomStore = Depends(get_store)):
    return store.get_host_room(room_id.hex, host_hash(request))


@router.post("/{room_id}/submissions")
def submit_answer(room_id: UUID, body: SubmitAnswer, request: Request,
                  store: RoomStore = Depends(get_store)):
    check_origin(request)
    from backend.moderation import require_clean
    require_clean(body.answer)
    return store.submit_answer(room_id.hex, body.submission_id.hex, body.answer)


@router.post("/{room_id}/close")
def close_room(room_id: UUID, request: Request, store: RoomStore = Depends(get_store)):
    check_origin(request)
    return store.close_room(room_id.hex, host_hash(request))

class Guess(BaseModel):
    answer_id: str
    guess: Annotated[str, StringConstraints(pattern='^(human|ai)$')]

class Advance(BaseModel):
    answer_id: str | None = None

@router.post('/{room_id}/generate')
def generate_answers(room_id: UUID, request: Request, store: RoomStore = Depends(get_store)):
    import time
    from uuid import uuid4
    from backend.game import human_sample, prepare
    from backend.generation import generate
    from backend.moderation import screen_answers
    check_origin(request); token=host_hash(request); attempt=uuid4().hex
    def claim(data):
        if data['status'] != 'closed' and not (data['status']=='generating' and time.time()-data.get('generation_started',0)>180):
            raise HTTPException(409,'Close submissions before generating answers.')
        data.update(status='generating',generation_attempt=attempt,generation_started=time.time())
    store.mutate(room_id.hex,token,claim)
    try:
        host=store.get_host_room(room_id.hex,token)
        all_humans,rejected=screen_answers(request.app.state.settings,store.answers(room_id.hex),host['question'])
        if rejected: store.remove_answers(room_id.hex,token,rejected)
        if not all_humans:
            raise HTTPException(409,'No classroom-appropriate answers remain. Please create a new room.')
        selected=human_sample(all_humans,host['rounds'])
        generated=generate(request.app.state.settings,host['question'],all_humans,len(selected))
        game=prepare(selected,generated)
        def finish(data):
            if data.get('generation_attempt')!=attempt: raise HTTPException(409,'Generation was superseded.')
            data.update(status='ready',game=game)
        return store.mutate(room_id.hex,token,finish)
    except Exception:
        def recover(data):
            if data.get('generation_attempt')==attempt: data['status']='closed'
        store.mutate(room_id.hex,token,recover)
        raise

@router.post('/{room_id}/start')
def start(room_id:UUID,request:Request,store:RoomStore=Depends(get_store)):
    from backend.game import act
    check_origin(request)
    return store.mutate(room_id.hex,host_hash(request),lambda data:act(data,'start'))

@router.post('/{room_id}/guess')
def guess(room_id:UUID,body:Guess,request:Request,store:RoomStore=Depends(get_store)):
    from backend.game import act
    check_origin(request)
    return store.mutate(room_id.hex,host_hash(request),lambda data:act(data,'guess',body.answer_id,body.guess))


class SampleAnswers(BaseModel):
    answers: Annotated[list[Annotated[str, StringConstraints(strip_whitespace=True,min_length=2,max_length=280)]], Field(min_length=1,max_length=20)]

@router.get('/{room_id}/samples')
def sample_answers(room_id:UUID,request:Request,store:RoomStore=Depends(get_store)):
    import json
    from backend.config import PROJECT_ROOT
    room=store.get_host_room(room_id.hex,host_hash(request))
    bank=json.loads((PROJECT_ROOT/'backend/sample_answers.json').read_text())
    return {'answers':bank.get(room['question'],[])}

@router.post('/{room_id}/samples')
def add_samples(room_id:UUID,body:SampleAnswers,request:Request,store:RoomStore=Depends(get_store)):
    check_origin(request)
    from backend.moderation import require_clean
    token=host_hash(request)
    store.get_host_room(room_id.hex,token)
    for answer in body.answers: require_clean(answer)
    return store.add_samples(room_id.hex,token,body.answers)

@router.post('/{room_id}/begin')
def begin(room_id:UUID,request:Request,store:RoomStore=Depends(get_store)):
    check_origin(request)
    room=store.get_host_room(room_id.hex,host_hash(request))
    if room['status']=='open': room=close_room(room_id,request,store)
    if room['status']=='closed': room=generate_answers(room_id,request,store)
    if room['status']=='ready': room=start(room_id,request,store)
    if room['status']!='playing': raise HTTPException(409,'Answers are still being generated. Please wait.')
    return room

@router.post('/{room_id}/{action}')
def advance(room_id:UUID,action:str,body:Advance,request:Request,store:RoomStore=Depends(get_store)):
    from backend.game import act
    if action not in ('next','skip','end'): raise HTTPException(404,'Unknown action.')
    check_origin(request)
    return store.mutate(room_id.hex,host_hash(request),lambda data:act(data,action,body.answer_id))
