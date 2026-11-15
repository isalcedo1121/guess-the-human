# Assets

The application favicon and stylesheet are served from `frontend/static/`.
The editable architecture diagram is in `diagrams/architecture.mmd`.
No screenshots or standalone reference documents are required to run the app.

The six MP3 recordings in `frontend/static/sounds/` come from the supplied
`sounds.zip`. Each was verified byte-for-byte against the original mockup’s
embedded audio; archive metadata was excluded.

| Served file | Original file | Trigger |
| --- | --- | --- |
| `correct.mp3` | `yay.mp3` | Correct guess |
| `wrong1.mp3`, `wrong2.mp3`, `wrong3.mp3` | Same names | Wrong guesses, rotating |
| `win.mp3` | `end win.mp3` | Results at 70% or higher |
| `lose.mp3` | `end lose.mp3` | Other results |
