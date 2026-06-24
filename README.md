# Snippet Finder

A full-stack app for saving, organizing, and searching code snippets — with an AI-assisted entry mode that auto-fills metadata from pasted code.

**[Live demo →](https://snippet-finder-lja6.vercel.app/)**

Create an account, save snippets with titles, descriptions, language, and tags, group them into collections, and search across everything in real time. Snippets can be kept private or shared publicly. Copy any snippet to the clipboard in one click.

## Highlights

- **AI-assisted snippet entry** — paste code into a separate "AI" tab and OpenAI (structured outputs, schema-validated via Pydantic) fills in the title, language, description, and tags for review before saving. Nothing is auto-saved; the model never touches anything but the form fields.
- **Abuse-resistant by design** — the AI endpoint sits behind auth, a per-user sliding-window rate limit, and a global daily cap (closing the "just register another account" bypass), backed by a hard monthly budget cap on the OpenAI account itself.
- **Real auth & access control** — JWT sessions, bcrypt password hashing, ownership and visibility rules enforced on the backend (private-by-default snippets, admin override, public-on-deletion handling for orphaned content).
- **Deployed full-stack on free infrastructure** — React/Vite on Vercel, FastAPI on Render, MongoDB Atlas — wired together with environment-based config (CORS, API base URL) so the same codebase runs locally or in production with no code changes.
- **Tested**: 130+ pytest tests covering auth, ownership, visibility, admin access, and the AI endpoint (mocked OpenAI calls, no real API spend in CI), built test-first (red → green commits).

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 19 + TypeScript, Vite |
| **Styling** | Plain CSS with CSS custom properties, light/dark theme |
| **Backend** | Python 3.11, FastAPI |
| **Database** | MongoDB (Motor async driver) |
| **AI** | OpenAI API (`gpt-4o-mini`, structured outputs) |
| **Auth** | JWT (python-jose), bcrypt password hashing (passlib) |
| **Data validation** | Pydantic v2 |
| **Tests** | pytest, pytest-asyncio |
| **Deployment** | Vercel (frontend), Render (backend), MongoDB Atlas (database) |

## Getting Started

### Prerequisites

- Python 3.11
- Node.js 18+
- A running MongoDB instance (local or Atlas). Copy the connection string for the next step.

### Backend

```bash
cd backend
python3.11 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file in `backend/`:

```
MONGO_URL=<your MongoDB connection string>
SECRET_KEY=<any long random string, 32+ characters>
OPENAI_API_KEY=<your OpenAI API key>   # optional — only needed for AI auto-fill
```

> `OPENAI_API_KEY` powers the **AI tab** in the New Snippet dialog: paste code,
> click Generate, and it fills in title, language, description, and tags for
> you to review. Get a key at [platform.openai.com](https://platform.openai.com).
> The rest of the app runs fine without it.

Start the server:

```bash
uvicorn main:app --reload
```

The API runs at `http://127.0.0.1:8000`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open the URL shown by Vite, usually `http://localhost:5173`.

### Tests

```bash
cd backend
pytest
```

### Deploying your own copy

- **Backend → Render**: connect this repo, use the included [`render.yaml`](render.yaml) blueprint (New → Blueprint). Set `MONGO_URL`, `SECRET_KEY`, `OPENAI_API_KEY`, and `CORS_ORIGINS` (your deployed frontend origin) in the Render dashboard.
- **Frontend → Vercel**: import this repo with root directory `frontend`, set `VITE_API_URL` to your Render backend URL. [`vercel.json`](frontend/vercel.json) handles the SPA fallback rewrite so client-side routes survive a page refresh.

## Project Structure

```
snippet-finder/
├── backend/
│   ├── main.py              # FastAPI app entry point, CORS configuration
│   ├── database.py          # Motor client, MongoDB collection references
│   ├── models/               # Pydantic schemas (snippet, collection, user, AI metadata)
│   ├── routers/              # snippets, collections, auth, users, admin — one router per resource
│   ├── utils/                 # JWT/auth, password rules, AI client, rate limiting
│   └── tests/                 # pytest suite, one file per router/module
│
└── frontend/
    └── src/
        ├── App.tsx            # App shell: header, navigation, routing
        ├── context/           # Shared auth state (AuthContext)
        ├── hooks/             # Snippets, collections, search, theme, admin data
        ├── components/        # Pages, modals, cards, and form controls
        ├── types/             # Shared TypeScript interfaces
        └── utils/              # Auth token helpers, search highlighting
```
