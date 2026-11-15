from html.parser import HTMLParser

import pytest
from fastapi.testclient import TestClient

from app import create_app
from backend.config import Settings


@pytest.fixture
def client():
    with TestClient(create_app(Settings(_env_file=None, app_env="test"))) as client:
        yield client


def test_health_does_not_expose_configuration(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_room_creation_requires_storage_configuration(client):
    assert client.post("/api/rooms", json={"question": "Example"}).status_code == 503


class AssetLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "script" and "src" in attrs:
            self.urls.append(attrs["src"])
        if tag == "link" and "href" in attrs:
            self.urls.append(attrs["href"])


@pytest.mark.parametrize("url, form_id", [("/", "setup-form"), ("/room/11111111111141118111111111111111", "answer-form")])
def test_pages_and_their_assets_load_from_any_working_directory(client, tmp_path, monkeypatch, url, form_id):
    monkeypatch.chdir(tmp_path)
    response = client.get(url)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert f'id="{form_id}"' in response.text

    links = AssetLinks()
    links.feed(response.text)
    assert links.urls
    for asset in links.urls:
        assert asset.startswith("/static/")
        resource = client.get(asset)
        assert resource.status_code == 200
        assert resource.content
        assert not resource.headers["content-type"].startswith("text/html")


def test_question_bank_is_available_to_the_frontend(client):
    response = client.get("/static/questions.json")

    assert response.status_code == 200
    questions = response.json()
    assert questions
    assert len(questions) == len(set(questions))
    assert all(isinstance(question, str) and 2 <= len(question) <= 200 for question in questions)


@pytest.mark.parametrize("url", [
    "/.env", "/.env.example", "/app.py", "/backend/config.py",
    "/static/%2e%2e/.env.example",
])
def test_source_and_environment_files_are_not_public(client, url):
    assert client.get(url).status_code == 404


def test_presets_are_in_the_initial_html_and_custom_is_last(client):
    class QuestionOptions(HTMLParser):
        def __init__(self):super().__init__();self.in_select=False;self.values=[]
        def handle_starttag(self,tag,attrs):
            attrs=dict(attrs)
            if tag=='select':self.in_select=attrs.get('id')=='question-select'
            if tag=='option' and self.in_select:self.values.append(attrs['value'])
        def handle_endtag(self,tag):
            if tag=='select':self.in_select=False
    page=client.get('/');parser=QuestionOptions();parser.feed(page.text)
    assert parser.values==client.get('/static/questions.json').json()+['custom']
    assert len(parser.values)==6
    assert '<option value="20" selected>' in page.text
    assert 'balance-note' not in page.text
    assert 'human answers ·' not in page.text
    assert page.headers['cache-control']=='no-store'
    assert client.get('/static/host.js').headers['cache-control']=='no-store'


def test_game_sound_files_are_served_as_audio(client):
    for key in ('correct', 'wrong1', 'wrong2', 'wrong3', 'win', 'lose'):
        response = client.get(f'/static/sounds/{key}.mp3')
        assert response.status_code == 200
        assert response.headers['content-type'] == 'audio/mpeg'
        assert len(response.content) > 9000
