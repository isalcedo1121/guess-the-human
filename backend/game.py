"""Pure game rules: balanced sampling, hidden identities, scoring and selection."""
import random
from uuid import uuid4
from backend.storage import RoomError

MODERATION_VERSION = 1


def require_screened(game):
    if game and game.get('moderation_version') != MODERATION_VERSION:
        raise RoomError(409, 'Please create a new room to use submission screening.')

def human_sample(answers, rounds):
    answers = list(dict.fromkeys(answers))
    count = min(len(answers), rounds // 2)
    if not count:
        raise RoomError(409, 'At least one human answer is required.')
    return random.sample(answers, count)


def prepare(humans, generated):
    if len(humans) != len(generated):
        raise RoomError(502, 'Generated response count does not match the game length.')
    pool = [dict(text=text, actual='human', level=2, style=None) for text in humans]
    pool += [dict(text=x['text'], actual='ai', level=x['level'], style=x['style'], explanation=x.get('explanation')) for x in generated]
    for row in pool:
        row['id'] = uuid4().hex
    random.shuffle(pool)
    return dict(remaining=pool, current=None, history=[], level=2, revealed=False, total=len(pool), moderation_version=MODERATION_VERSION)


def advance(game):
    available = game['remaining']
    if not available:
        game['current'] = None
        return False
    candidate = random.choice(available)
    if candidate['actual'] == 'ai':
        ai = [x for x in available if x['actual'] == 'ai']
        distance = min(abs(x['level'] - game['level']) for x in ai)
        candidate = random.choice([x for x in ai if abs(x['level'] - game['level']) == distance])
    available.remove(candidate)
    game['current'] = candidate
    game['revealed'] = False
    return True


def act(data, action, answer_id=None, guess=None):
    game = data.get('game')
    require_screened(game)
    if action == 'start':
        if data['status'] != 'ready': raise RoomError(409, 'Answers are not ready.')
        advance(game); data['status'] = 'playing'
        return
    if data['status'] != 'playing': raise RoomError(409, 'The game is not playing.')
    if action == 'end':
        data['status'] = 'finished'; return
    if not game['current'] or game['current']['id'] != answer_id:
        raise RoomError(409, 'This answer is no longer current. Refresh the page.')
    if action == 'guess':
        if game['revealed']: return
        row = game['current']
        row['correct'] = guess == row['actual']
        game['history'].append({**row, 'guess': guess})
        game['revealed'] = True
        if row['actual'] == 'ai':
            game['level'] = max(1, min(3, game['level'] + (1 if row['correct'] else -1)))
    elif action in ('next', 'skip'):
        if action == 'next' and not game['revealed']: raise RoomError(409, 'Make a guess first.')
        if not advance(game): data['status'] = 'finished'
    else: raise RoomError(400, 'Unknown game action.')


def view(data):
    require_screened(data['game'])
    game = data['game']; history = game['history']
    correct = sum(x['correct'] for x in history)
    current = game['current']
    safe_current = None
    if current:
        safe_current = {key: current[key] for key in ('id','text')}
        if game['revealed']:
            safe_current.update({key: current[key] for key in ('actual','correct','style')})
    return dict(current=safe_current, revealed=game['revealed'], total=game['total'],
                round=game['total']-len(game['remaining']), correct=correct,
                incorrect=len(history)-correct, assessed=len(history),
                accuracy=round(100*correct/len(history)) if history else 0,
                ai_caught=sum(x['actual']=='ai' and x['correct'] for x in history),
                ai_missed=sum(x['actual']=='ai' and not x['correct'] for x in history),
                humans_accused=sum(x['actual']=='human' and not x['correct'] for x in history),
                history=history if data['status']=='finished' else [])
