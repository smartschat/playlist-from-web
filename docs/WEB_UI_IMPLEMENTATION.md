# Web UI Implementation Status

This document tracks the implementation of a web UI for the playlist-from-web project using Svelte 5 + FastAPI.

## Overview

The web UI allows users to:
- View and manage extracted playlists
- Edit tracks, blocks, and playlist metadata
- Manage Spotify integration (view misses, re-map tracks, rename playlists)
- Import new URLs and manage crawl results

## Current State

### Branch
- Working branch: `feature/web-ui`
- Base branch: `main`

### Completed Work

#### Phase 1: Backend Foundation ✅

**Dependencies Added** (`pyproject.toml`):
```toml
"fastapi>=0.115.0",
"uvicorn[standard]>=0.32.0",
```

**Directory Structure Created**:
```
src/app/web/
├── __init__.py
├── api/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app factory
│   ├── routes/
│   │   ├── __init__.py
│   │   └── playlists.py        # /api/playlists endpoints
│   └── services/
│       ├── __init__.py
│       └── data_service.py     # Data file CRUD operations
```

**Files Implemented**:

1. **`src/app/web/api/main.py`**
   - FastAPI app factory with CORS middleware
   - Health check endpoint: `GET /api/health`
   - Serves static files from `frontend/dist/` in production
   - Includes playlists router

2. **`src/app/web/api/services/data_service.py`**
   - `DataService` class for JSON file operations
   - Methods:
     - `list_parsed_playlists()` - List all parsed playlists with metadata
     - `get_parsed_playlist(slug)` - Load a parsed playlist by slug
     - `save_parsed_playlist(slug, data)` - Save changes to a parsed playlist
     - `delete_parsed_playlist(slug, also_spotify)` - Delete playlist files
     - `get_spotify_artifact(slug)` - Load Spotify artifact
     - `save_spotify_artifact(slug, data)` - Save Spotify artifact
     - `list_crawls()` - List all crawl results
     - `get_crawl(slug)` - Load a crawl result

3. **`src/app/web/api/routes/playlists.py`**
   - `GET /api/playlists` - List all parsed playlists with metadata
   - `GET /api/playlists/{slug}` - Get a parsed playlist by slug
   - `PUT /api/playlists/{slug}` - Update a parsed playlist
   - `DELETE /api/playlists/{slug}` - Delete a parsed playlist

4. **`src/app/cli.py`** (modified)
   - Added `serve` command:
     ```bash
     uv run python -m app serve
     uv run python -m app serve --port 8080 --reload
     ```

**API Endpoints Available**:
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/playlists` | List all parsed playlists |
| GET | `/api/playlists/{slug}` | Get single playlist |
| PUT | `/api/playlists/{slug}` | Update playlist |
| DELETE | `/api/playlists/{slug}` | Delete playlist |

---

#### Phase 2: Frontend Foundation ✅

**Project Initialized**:
```
src/app/web/frontend/
├── package.json
├── vite.config.ts              # Configured with /api proxy
├── tsconfig.json
├── node_modules/
├── src/
│   ├── main.ts
│   ├── app.css                 # Minimal reset styles
│   ├── App.svelte              # Root component
│   ├── lib/
│   │   ├── api.ts              # Fetch wrapper for /api/*
│   │   └── types.ts            # TypeScript types
│   └── routes/
│       ├── Dashboard.svelte    # Dashboard view
│       └── PlaylistDetail.svelte # Read-only playlist detail view
└── public/
```

**Files Implemented**:

1. **`vite.config.ts`**
   ```typescript
   export default defineConfig({
     plugins: [svelte()],
     server: {
       proxy: {
         '/api': 'http://localhost:8000'
       }
     },
     build: {
       outDir: 'dist'
     }
   })
   ```

2. **`src/lib/types.ts`**
   - TypeScript interfaces mirroring Python models:
     - `Track` - Single track with artist, title, album, spotify_uri
     - `TrackBlock` - Block with title, context, tracks array
     - `ParsedPlaylist` - Full parsed page data
     - `PlaylistSummary` - Summary for list view
     - `SpotifyPlaylist` - Spotify playlist metadata
     - `SpotifyArtifact` - Full Spotify artifact
     - `CrawlSummary` - Crawl result summary

3. **`src/lib/api.ts`**
   - `fetchJson<T>()` - Generic fetch wrapper with error handling
   - `listPlaylists()` - Fetch playlist summaries
   - `getPlaylist(slug)` - Fetch single playlist
   - `updatePlaylist(slug, data)` - Update playlist
   - `deletePlaylist(slug, alsoSpotify)` - Delete playlist
   - `healthCheck()` - Health check

4. **`src/routes/Dashboard.svelte`**
   - Displays all parsed playlists as cards
   - Shows: source name, block count, track count, miss count
   - Status badge: "Parsed" or "Imported"
   - Filter input for searching
   - Responsive grid layout
   - "View" button navigates to playlist detail

5. **`src/routes/PlaylistDetail.svelte`**
   - Read-only view of a single playlist
   - Breadcrumb navigation back to Dashboard
   - Shows playlist name, block count, track count
   - "View source" link to original URL
   - Displays all blocks with their tracks in tables

6. **`src/App.svelte`**
   - Root component with hash-based routing
   - Routes: `#/` (Dashboard), `#/playlist/{slug}` (PlaylistDetail)
   - Global styles for body

**NPM Dependencies Installed**:
- `svelte` (v5)
- `vite`
- `@sveltejs/vite-plugin-svelte`
- `typescript`
- `svelte-dnd-action` (for drag-and-drop in Phase 3)

---

### Running the Application

**Development Mode** (two terminals):

Terminal 1 - Backend:
```bash
cd /Users/sebastian/projects/playlist-from-web
uv run python -m app serve --reload
# Runs on http://localhost:8000
```

Terminal 2 - Frontend:
```bash
cd /Users/sebastian/projects/playlist-from-web/src/app/web/frontend
npm run dev
# Runs on http://localhost:5173
# Proxies /api/* to backend
```

**Access the UI**: Open http://localhost:5173 in your browser.

---

## Planned Work

### Phase 3: Playlist Editing ✅

**Goal**: Enable inline editing of tracks and blocks.

**Frontend Components Created**:

1. **`src/components/TrackRow.svelte`**
   - Single track row in a table
   - Double-click to edit artist/title/album inline
   - Delete button with confirmation
   - Drag handle for reordering
   - Press Enter to save, Escape to cancel

2. **`src/components/BlockCard.svelte`**
   - Displays a single block (title, context, track list)
   - Double-click to edit block title and context
   - Delete block button
   - Uses drag-and-drop via `svelte-dnd-action` for track reordering
   - Includes AddTrackForm for adding new tracks

3. **`src/components/AddTrackForm.svelte`**
   - Form to add a new track to a block
   - Fields: artist (required), title (required), album (optional)
   - Cancel/Add buttons

4. **`src/routes/PlaylistDetail.svelte`** (extended)
   - Edit mode toggle button
   - Save Changes / Cancel buttons
   - "Unsaved changes" badge indicator
   - Add Block button in edit mode
   - Browser beforeunload warning for unsaved changes
   - Error banner for save failures

**Features Implemented**:
- Double-click on track/block field to edit inline
- Press Enter to save, Escape to cancel
- Drag-and-drop track reordering with `svelte-dnd-action`
- Add new track button per block
- Delete track/block with confirmation
- Save button persists changes via PUT /api/playlists/{slug}
- Unsaved changes indicator
- Discard changes confirmation when canceling edit mode

---

### Phase 4: Spotify Integration ✅

**Goal**: View and manage Spotify mappings.

**Backend Changes** (`src/app/spotify_client.py`):
Add new methods:
```python
def update_playlist_details(self, playlist_id: str, name: str = None, description: str = None) -> Dict
def replace_playlist_tracks(self, playlist_id: str, uris: List[str]) -> Dict
def remove_tracks(self, playlist_id: str, uris: List[str]) -> Tuple[int, List[str]]
def unfollow_playlist(self, playlist_id: str) -> Dict
def get_playlist(self, playlist_id: str) -> Dict
```

**Backend Routes** (`src/app/web/api/routes/spotify.py`):
```
POST   /api/spotify/search                     # Search track {artist, title}
GET    /api/spotify/{slug}                     # Get spotify artifact
POST   /api/spotify/{slug}/remap               # Re-run Spotify mapping
POST   /api/spotify/{slug}/tracks/{idx}/assign # Assign URI to track
PUT    /api/spotify/playlists/{pid}            # Update playlist name/description
POST   /api/spotify/playlists/{pid}/sync       # Sync tracks to Spotify
DELETE /api/spotify/playlists/{pid}            # Unfollow playlist
```

**Frontend Components**:

1. **`src/routes/SpotifyPanel.svelte`**
   - Shows Spotify artifact for a playlist
   - Tabs: Created Playlists | Misses
   - List of created playlists with links
   - List of misses (tracks that failed to match)

2. **`src/components/SpotifySearchModal.svelte`**
   - Modal for manually searching Spotify
   - Input: artist, title
   - Shows search results
   - Click to assign URI to track

3. **`src/components/MissRow.svelte`**
   - Single miss row
   - Shows: block, artist, title
   - "Search" button opens SpotifySearchModal
   - "Ignore" button to skip

4. **`src/components/SpotifyPlaylistCard.svelte`**
   - Shows created playlist info
   - Edit name button
   - Sync tracks button
   - Delete/unfollow button
   - Link to Spotify

**Features**:
- View all misses for a playlist
- Manually search and assign Spotify URIs
- Re-run full Spotify mapping
- Rename Spotify playlists
- Sync local changes to Spotify
- Delete/unfollow playlists

---

### Phase 5: Import & Crawl

**Goal**: Import new URLs and manage crawl results from the UI.

**Backend Routes** (`src/app/web/api/routes/imports.py`):
```
POST   /api/import/preview         # Run dev mode, return parsed data
POST   /api/import/execute         # Full import, return spotify result
```

**Backend Routes** (`src/app/web/api/routes/crawls.py`):
```
GET    /api/crawls                 # List all crawl results
GET    /api/crawls/{slug}          # Get crawl detail
POST   /api/crawls/{slug}/reprocess/{idx}  # Retry failed URL
```

**Frontend Components**:

1. **`src/routes/Import.svelte`**
   - URL input field
   - Options: dev mode, force re-fetch
   - "Preview" button → shows parsed blocks before import
   - "Import" button → full import to Spotify
   - Progress/status display

2. **`src/routes/CrawlList.svelte`**
   - List all crawl results
   - Shows: index URL, date, success/skipped/failed counts

3. **`src/routes/CrawlDetail.svelte`**
   - Shows all discovered links from a crawl
   - Status per link: success, skipped, failed
   - "Reprocess" button for failed links
   - Link to view imported playlist

4. **`src/components/ImportProgress.svelte`**
   - Progress bar during import
   - Status messages
   - Error display

**Features**:
- Preview parsed data before creating playlists
- Full import with progress indication
- View all crawl results
- Retry failed URLs from a crawl
- Link to resulting playlists

---

### Phase 6: Production Setup

**Goal**: Single command to serve both API and frontend.

**Changes**:

1. **Build frontend for production**:
   ```bash
   cd src/app/web/frontend
   npm run build
   # Outputs to dist/
   ```

2. **FastAPI serves static files** (already configured in `main.py`):
   ```python
   frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
   if frontend_dist.exists():
       app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
   ```

3. **Single serve command**:
   ```bash
   uv run python -m app serve
   # Serves API at /api/* and frontend at /*
   ```

4. **Update `.gitignore`**:
   ```
   src/app/web/frontend/node_modules/
   src/app/web/frontend/dist/
   ```

5. **Add build script to package.json or Makefile**:
   ```bash
   # Build frontend and run server
   cd src/app/web/frontend && npm run build
   cd ../../../.. && uv run python -m app serve
   ```

---

## File Summary

### Files Created (Phase 1-4)

| File | Description |
|------|-------------|
| `src/app/web/__init__.py` | Web package init |
| `src/app/web/api/__init__.py` | API package init |
| `src/app/web/api/main.py` | FastAPI app factory |
| `src/app/web/api/routes/__init__.py` | Routes package init |
| `src/app/web/api/routes/playlists.py` | Playlist CRUD endpoints |
| `src/app/web/api/routes/spotify.py` | Spotify API endpoints |
| `src/app/web/api/services/__init__.py` | Services package init |
| `src/app/web/api/services/data_service.py` | Data file operations |
| `src/app/web/frontend/*` | Svelte project (Vite) |
| `src/app/web/frontend/src/lib/types.ts` | TypeScript types |
| `src/app/web/frontend/src/lib/api.ts` | API client |
| `src/app/web/frontend/src/routes/Dashboard.svelte` | Dashboard view |
| `src/app/web/frontend/src/routes/PlaylistDetail.svelte` | Playlist detail with editing |
| `src/app/web/frontend/src/components/TrackRow.svelte` | Track row with inline editing |
| `src/app/web/frontend/src/components/BlockCard.svelte` | Block card with editing |
| `src/app/web/frontend/src/components/AddTrackForm.svelte` | Form to add new tracks |
| `src/app/web/frontend/src/components/SpotifyPanel.svelte` | Spotify integration panel |
| `src/app/web/frontend/src/components/SpotifySearchModal.svelte` | Spotify search modal |
| `src/app/web/frontend/src/components/SpotifyPlaylistCard.svelte` | Spotify playlist card |
| `src/app/web/frontend/src/components/MissRow.svelte` | Miss row with search action |

### Files Modified

| File | Change |
|------|--------|
| `pyproject.toml` | Added fastapi, uvicorn dependencies |
| `src/app/cli.py` | Added `serve` command |
| `src/app/spotify_client.py` | Added playlist management methods |

### Files to Create (Future Phases)

| File | Phase | Description |
|------|-------|-------------|
| `src/app/web/api/routes/imports.py` | 5 | Import endpoints |
| `src/app/web/api/routes/crawls.py` | 5 | Crawl endpoints |
| `src/app/web/frontend/src/routes/Import.svelte` | 5 | Import form view |
| `src/app/web/frontend/src/routes/CrawlList.svelte` | 5 | Crawl list view |
| `src/app/web/frontend/src/routes/CrawlDetail.svelte` | 5 | Crawl detail view |

---

## Testing

### Manual Testing Checklist

#### Phase 1 & 2 (Current)
- [x] Backend starts without errors: `uv run python -m app serve`
- [x] Health check works: `curl http://localhost:8000/api/health`
- [x] Playlists list works: `curl http://localhost:8000/api/playlists`
- [x] Frontend starts: `npm run dev`
- [x] Frontend proxies API calls
- [x] Dashboard displays playlist cards
- [x] Filter input filters playlists
- [x] Playlist cards show correct data
- [x] View button navigates to playlist detail
- [x] Playlist detail shows all blocks and tracks
- [x] Breadcrumb navigation back to dashboard works

#### Phase 3 (Completed)
- [x] Can edit track artist/title/album (double-click)
- [x] Can add new track
- [x] Can delete track
- [x] Can reorder tracks with drag-and-drop
- [x] Can edit block title/context
- [x] Can add/delete blocks
- [x] Save persists changes
- [x] Unsaved changes warning

#### Phase 4 (Completed)
- [x] Spotify panel shows misses
- [x] Can search Spotify manually
- [x] Can assign URI to miss
- [x] Can re-map playlist
- [x] Can rename Spotify playlist
- [x] Can delete Spotify playlist

#### Phase 5 (Planned)
- [ ] Can enter URL and preview
- [ ] Can import new URL
- [ ] Import shows progress
- [ ] Crawl list shows all crawls
- [ ] Can view crawl details
- [ ] Can reprocess failed URLs

---

## Notes

- The frontend uses Svelte 5 with TypeScript
- Simple hash-based routing implemented in App.svelte (Dashboard + PlaylistDetail views)
- `svelte-dnd-action` is installed but not yet used
- CORS is configured for localhost:5173 (Vite dev server)
- Production mode serves frontend from `dist/` directory
