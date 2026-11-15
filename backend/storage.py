"""Firestore room storage. Submission receipts and counts change atomically."""

import hmac
import json
import time
import random
from google.api_core.exceptions import Aborted
from uuid import uuid4

from google.cloud import firestore
from google.oauth2 import service_account

from backend.config import Settings


class RoomError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def connect_store(settings: Settings):
    if not settings.firebase_project_id:
        return None
    if settings.firebase_service_account_json:
        credentials = service_account.Credentials.from_service_account_info(
            json.loads(settings.firebase_service_account_json.get_secret_value())
        )
    elif settings.google_application_credentials:
        credentials = service_account.Credentials.from_service_account_file(
            settings.google_application_credentials
        )
    else:
        return None
    return RoomStore(firestore.Client(
        project=settings.firebase_project_id, credentials=credentials
    ))


def room_data(snapshot):
    if not snapshot.exists:
        raise RoomError(404, "Room not found.")
    return snapshot.to_dict()


def check_host(data, token_hash):
    if not hmac.compare_digest(data["host_token_hash"], token_hash):
        raise RoomError(403, "Host access required.")


def run_transaction(client, callback):
    # Firestore's decorator retries commit conflicts, but read conflicts can escape it.
    for attempt in range(5):
        try:
            return callback(client.transaction(max_attempts=5))
        except Aborted:
            if attempt == 4: raise
            time.sleep(.05 * (attempt + 1) + random.random() * .05)


class RoomStore:
    def __init__(self, client):
        self.client = client
        self.rooms = client.collection("rooms")

    @staticmethod
    def host_view(room_id, data):
        result = {"id": room_id, **{
            key: data[key] for key in ("question", "rounds", "status", "submission_count")
        }}
        if data.get("game") is not None:
            from backend.game import view
            result["game"] = view(data)
        return result

    def create_room(self, question, rounds, token_hash):
        room_id = uuid4().hex
        data = {
            "question": question, "rounds": rounds, "status": "open",
            "submission_count": 0, "host_token_hash": token_hash,
            "created_at": firestore.SERVER_TIMESTAMP,
        }
        self.rooms.document(room_id).create(data, timeout=10, retry=None)
        return self.host_view(room_id, data)

    def get_participant_room(self, room_id, submission_id=None):
        reference = self.rooms.document(room_id)
        data = room_data(reference.get(timeout=10, retry=None))
        submitted = False
        if submission_id:
            submitted = reference.collection("submissions").document(submission_id).get(
                timeout=10, retry=None
            ).exists
        return {"question": data["question"], "status": data["status"], "submitted": submitted}

    def get_host_room(self, room_id, token_hash):
        data = room_data(self.rooms.document(room_id).get(timeout=10, retry=None))
        check_host(data, token_hash)
        if data['status'] == 'generating' and time.time() - data.get('generation_started', 0) > 180:
            def recover(current):
                if current['status'] == 'generating' and time.time() - current.get('generation_started', 0) > 180:
                    current['status'] = 'closed'
            return self.mutate(room_id, token_hash, recover)
        return self.host_view(room_id, data)

    def submit_answer(self, room_id, submission_id, answer):
        room_ref = self.rooms.document(room_id)
        submission_ref = room_ref.collection("submissions").document(submission_id)

        @firestore.transactional
        def submit(transaction):
            data = room_data(room_ref.get(transaction=transaction, timeout=10, retry=None))
            receipt = submission_ref.get(transaction=transaction, timeout=10, retry=None)
            # A retry can recover an accepted receipt even after submissions close.
            if receipt.exists:
                if receipt.to_dict()["answer"] != answer:
                    raise RoomError(409, "This browser has already submitted an answer.")
                return {"accepted": True}
            if data["status"] != "open":
                raise RoomError(409, "Submissions are closed.")
            transaction.create(submission_ref, {
                "answer": answer, "created_at": firestore.SERVER_TIMESTAMP,
            })
            transaction.update(room_ref, {"submission_count": data["submission_count"] + 1})
            return {"accepted": True}

        return run_transaction(self.client, submit)

    def close_room(self, room_id, token_hash):
        reference = self.rooms.document(room_id)

        @firestore.transactional
        def close(transaction):
            data = room_data(reference.get(transaction=transaction, timeout=10, retry=None))
            check_host(data, token_hash)
            if data["status"] == "open":
                transaction.update(reference, {
                    "status": "closed", "closed_at": firestore.SERVER_TIMESTAMP,
                })
                data["status"] = "closed"
            return self.host_view(room_id, data)

        return run_transaction(self.client, close)

    def mutate(self, room_id, token_hash, operation):
        reference = self.rooms.document(room_id)
        @firestore.transactional
        def update(transaction):
            data = room_data(reference.get(transaction=transaction, timeout=10, retry=None))
            check_host(data, token_hash)
            operation(data)
            transaction.update(reference, {key: data[key] for key in
                ('status','game','generation_attempt','generation_started') if key in data})
            return self.host_view(room_id, data)
        return run_transaction(self.client, update)

    def answers(self, room_id):
        return [x.to_dict()['answer'] for x in self.rooms.document(room_id).collection('submissions').stream(timeout=10)]


    def add_samples(self, room_id, token_hash, answers):
        import hashlib
        reference = self.rooms.document(room_id)
        # Stable IDs make a repeated click or lost response safe to retry.
        references = [(reference.collection('submissions').document(
            'sample-' + hashlib.sha256(text.encode()).hexdigest()), text)
            for text in dict.fromkeys(answers)]
        @firestore.transactional
        def add(transaction):
            data = room_data(reference.get(transaction=transaction, timeout=10, retry=None))
            check_host(data, token_hash)
            if data['status'] != 'open': raise RoomError(409, 'Submissions are closed.')
            missing = [(ref,text) for ref,text in references
                       if not ref.get(transaction=transaction,timeout=10,retry=None).exists]
            for ref,text in missing:
                transaction.create(ref, {'answer':text, 'origin':'host_sample',
                                         'created_at':firestore.SERVER_TIMESTAMP})
            data['submission_count'] += len(missing)
            transaction.update(reference, {'submission_count':data['submission_count']})
            return self.host_view(room_id,data)
        return run_transaction(self.client,add)
