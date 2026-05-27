# Snippet Finder

A single-page web application where developers can save, organise, and share code snippets. Users can create an account, store snippets with titles, descriptions, language tags, and keywords, group them into collections, and search across everything in real time. Any snippet can be copied to the clipboard in one click. Snippets can be kept private or made public for others to browse.

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 19 + TypeScript, Vite |
| **Styling** | Plain CSS with CSS custom properties, light/dark theme |
| **Backend** | Python 3.11, FastAPI |
| **Database** | MongoDB (Motor async driver) |
| **Auth** | JWT (python-jose), bcrypt password hashing (passlib) |
| **Data validation** | Pydantic v2 |
| **Tests** | pytest, pytest-asyncio |

## How to Run

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
JWT_SECRET=<any long random string>
```

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

## Folder Structure

```
snippet-finder/
│
├── backend/
│   ├── main.py                  # FastAPI app entry point, CORS configuration
│   ├── database.py              # Motor client, MongoDB collection references
│   ├── conftest.py              # pytest fixtures (test DB setup, auth helpers)
│   ├── import_snippets.py       # Utility script to seed sample data
│   ├── requirements.txt         # Python dependencies
│   │
│   ├── models/
│   │   ├── snippet.py           # Pydantic schemas for snippet (Create, Update, Response)
│   │   ├── collection.py        # Pydantic schemas for collection
│   │   └── user.py              # Pydantic schemas for user and auth tokens
│   │
│   ├── routers/
│   │   ├── snippets.py          # Snippet CRUD + visibility toggle + copy counter
│   │   ├── collections.py       # Collection CRUD + add/remove snippets
│   │   ├── auth.py              # Register and login endpoints, JWT issuance
│   │   ├── users.py             # Profile read, update username/email/password, delete account
│   │   └── admin.py             # Admin-only routes: list all users and snippets, force delete
│   │
│   ├── utils/
│   │   ├── security.py          # JWT creation and verification, auth dependencies
│   │   ├── password_rules.py    # Password validation (length, complexity)
│   │   └── user_lookup.py       # Shared helper to resolve owner_id to username
│   │
│   └── tests/
│       ├── fakes.py             # In-memory fake collections for unit tests
│       ├── test_auth.py         # Register, login, token validation tests
│       ├── test_snippets.py     # Snippet CRUD, visibility, ownership tests
│       ├── test_collections.py  # Collection CRUD, snippet membership tests
│       ├── test_users.py        # Profile update, account deletion tests
│       ├── test_admin.py        # Admin access control tests
│       ├── test_models.py       # Pydantic schema validation tests
│       └── test_security.py     # JWT and password hashing tests
│
└── frontend/
    ├── index.html               # Single HTML entry point (SPA)
    ├── vite.config.ts           # Vite dev server and build configuration
    │
    └── src/
        ├── main.tsx             # React DOM root, wraps app in AuthProvider and BrowserRouter
        ├── App.tsx              # App shell: header, navigation, routing, auth modal trigger
        ├── App.css              # Header, search dropdown, layout, skeleton, overlay styles
        ├── index.css            # CSS custom properties (light/dark theme tokens), base typography
        ├── constants.ts         # API base URL
        │
        ├── context/
        │   └── AuthContext.tsx  # Shared auth state (token, user, login, logout, register)
        │                        # Using React Context so all components share one auth instance
        │
        ├── hooks/
        │   ├── useAuth.ts       # Re-exports useAuthContext — consumed by every component
        │   ├── useSnippets.ts   # Snippet list state, pagination, CRUD handlers, optimistic updates
        │   ├── useCollections.ts# Collection list state, pagination, CRUD handlers
        │   ├── useSearch.ts     # Search query state, 300ms debounce, keyboard navigation
        │   ├── useLanguages.ts  # Fetches distinct language list for the filter bar
        │   ├── useAdmin.ts      # Admin panel data (all users, all snippets)
        │   ├── useTheme.ts      # Dark/light mode toggle, persisted in localStorage
        │   └── useFocusTrap.ts  # Traps keyboard focus inside modals (accessibility)
        │
        ├── components/
        │   ├── SnippetsPage.tsx          # Main snippets listing page (grid + filter + pagination)
        │   ├── CollectionsPage.tsx       # Collections listing page
        │   ├── CollectionPage.tsx        # Individual collection detail page with its snippets
        │   ├── ProfilePage.tsx           # Public profile: another user's snippets and collections
        │   ├── SettingsPage.tsx          # Account settings: update profile, change password, delete account
        │   ├── AdminPanel.tsx            # Admin view: manage all users and snippets
        │   ├── AdminPanel.css
        │   ├── AuthModal.tsx             # Login / register modal with focus trap
        │   ├── CodeSnippet.tsx           # Snippet card (view mode + inline edit mode)
        │   ├── CodeSnippet.css
        │   ├── CollectionCard.tsx        # Collection card with edit and visibility controls
        │   ├── CollectionCard.css
        │   ├── CollectionPage.css
        │   ├── ProfilePage.css
        │   ├── SearchBar.tsx             # Search input and live results dropdown
        │   ├── CreateSnippetModal.tsx    # Modal form for creating a new snippet
        │   ├── CreateCollectionModal.tsx # Modal form for creating a new collection
        │   ├── AddToCollectionModal.tsx  # Modal for adding a snippet to one of the user's collections
        │   ├── DeleteDialog.tsx          # Confirmation dialog for destructive actions
        │   ├── LanguageFilter.tsx        # Scrollable chip bar for filtering by language
        │   ├── LanguageFilter.css
        │   ├── LanguageSelect.tsx        # Dropdown + free-text input for picking a language
        │   ├── Pagination.tsx            # Page controls (prev/next/numbered)
        │   ├── Pagination.css
        │   ├── FormField.tsx             # Wrapper that pairs an input with its error message
        │   └── Icons.tsx                 # SVG icon components
        │
        ├── types/
        │   ├── snippet.ts       # Snippet TypeScript interface (shared across components and hooks)
        │   └── collection.ts    # Collection TypeScript interface
        │
        └── utils/
            ├── auth.ts          # localStorage helpers for token and user, authHeaders builder
            ├── search.tsx       # highlight() — wraps matched text in <mark>, getCodeExcerpt()
            └── author.ts        # Shared helper to format owner display name
```

## Workload

This is an individual submission. All work was completed by **Shirley Yi**.