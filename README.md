# SnippetFinder

A single-page web application for storing, organising, and quickly retrieving code snippets. Developers often reuse the same patterns across projects. SnippetFinder gives them a personal, searchable library where they can save snippets with titles, descriptions, language tags, and keywords. Any snippet can be copied to the clipboard in a single click or keystroke.

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 19 + TypeScript, Vite |
| **Styling** | Plain CSS with CSS custom properties, light/dark theme toggle (persisted in `localStorage`) |
| **Backend** | Python 3, FastAPI|
| **Database** | MongoDB (accessed via Motor async driver) |
| **Data validation** | Pydantic v2 models |

## Features

- **Full CRUD** — create, view, edit, and delete snippets
- **One-click copy** — click anywhere on a code block to copy it. A hover icon and pointer cursor hint at the action, and a copy counter tracks usage
- **Live search** — a debounced search bar (300 ms) queries title, description, code, and tags on the server. Results appear in a dropdown with highlighted keywords and a code preview
- **Keyboard navigation** — use arrow keys to browse results, Enter to copy, and Escape to dismiss
- **Tag system** — organise snippets with comma-separated tags shown as pills
- **Inline editing** — edit a snippet's details without leaving the page
- **Delete confirmation** — a confirmation dialog prevents accidental deletions
- **Error handling** — edits and deletes update the UI immediately, then roll back automatically if the server request fails. The initial load shows a retry button on failure, malformed snippet IDs return controlled API errors, and search terms are escaped before reaching Mongo regex queries
- **Dark mode toggle** — a light/dark switch in the header, saved across sessions via `localStorage`, with a system-preference fallback
- **Responsive design** — the layout adapts from multi-column on desktop to single-column on mobile. The modal becomes a bottom sheet, the "Add Snippet" button collapses to an icon, and the search dropdown goes full-width
- **Loading skeleton** — shimmer placeholder cards match the real card layout while data loads

## Setup and Run

1. In `backend/.env`, set `MONGO_URL` and, if needed, adjust `CORS_ORIGINS` for your frontend origin.
2. Start the backend:

```bash
cd backend
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

3. Start the frontend in a second terminal:

```bash
cd frontend
npm install
npm run dev
```

4. Open the frontend URL shown by Vite, usually `http://localhost:5173`. The backend API runs on `http://127.0.0.1:8000`.

## Folder Structure

```
SnippetFinder/
├── backend/
│   ├── main.py              # FastAPI app entry, env-driven CORS config
│   ├── database.py          # Motor client + MongoDB connection
│   ├── .env                 # Environment variables (Mongo URL, allowed frontend origins)
│   ├── models/
│   │   └── snippet.py       # Pydantic schemas (Create, Update, Response)
│   ├── routers/
│   │   └── snippets.py      # REST endpoints (GET, POST, PUT, DELETE, PATCH copy)
│   └── requirements.txt     # Python dependencies
│
└── frontend/
    ├── index.html            # Single HTML entry point
    ├── vite.config.ts        # Vite dev-server + build config
    └── src/
        ├── main.tsx          # React DOM root
        ├── App.tsx           # Top-level layout (header, grid, skeleton, error state, modal)
        ├── App.css           # Header, search dropdown, skeleton, overlay, grid styles
        ├── index.css         # CSS custom properties (light + dark theme tokens), base typography
        ├── constants.ts      # Shared API base URL
        ├── hooks/
        │   ├── useSnippets.ts  # Snippet state + CRUD handlers with error rollback
        │   ├── useSearch.ts    # Search state, debounce, keyboard navigation
        │   └── useTheme.ts    # Dark mode toggle, localStorage persistence, system-preference fallback
        ├── components/
        │   ├── CodeSnippet.tsx       # Snippet card (view + inline edit modes)
        │   ├── CodeSnippet.css       # Card, code block, copy icon, footer, responsive styles
        │   ├── SearchBar.tsx         # Search input + results dropdown
        │   └── CreateSnippetModal.tsx # Overlay form for new snippets
        └── utils/
            └── search.tsx    # highlight(), getCodeExcerpt(), escapeRegex()
```

## Challenges Overcome

One challenge was making the search dropdown behave correctly when a user clicked a result. I first used `onClick`, but the input lost focus and the dropdown could close before the click finished, so I changed the interaction to `onMouseDown` and kept a small blur delay to make result selection reliable. Another challenge was implementing keyboard shortcuts for the search bar, because Arrow keys, Enter, and Escape already have default browser behaviours inside inputs. I solved this by carefully handling the relevant key events and using `preventDefault()` only where needed, so keyboard navigation works smoothly without interfering with normal typing.
