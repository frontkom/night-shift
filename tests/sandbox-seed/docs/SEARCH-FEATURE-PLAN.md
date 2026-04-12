# Search Feature Plan

Add full-text search across users and companies.

## Phase 1: Search UI component (done)

Add a search input to the header that filters results client-side as the user types. Show results in a dropdown below the input.

- Search input with debounced onChange
- Dropdown with highlighted matching text
- Keyboard navigation (arrow keys, enter to select)

## Phase 2: Search API endpoint with filtering (pending)

Move search logic server-side. Create a `/api/search` endpoint that accepts a query string and optional filters (type, date range, status).

- `GET /api/search?q=term&type=user&status=active`
- Return paginated results with total count
- Add PostgreSQL full-text search index

## Phase 3: Search results caching (pending)

Cache frequent search queries to reduce database load. Use an LRU cache with TTL, and invalidate on data changes.

- In-memory LRU cache (max 1000 entries, 5 min TTL)
- Cache invalidation on user/company create/update/delete
- Cache hit/miss metrics logging
