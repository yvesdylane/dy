# Pass Page — Entry/Exit Mode Dropdown

## Changes

### 1. `controllers/passController.py`
- `_pool: dict[str, tuple[datetime, str]]` — stores `(expiry, mode)` per code
- `_current_mode` tracks the active session mode
- `start_pass(mode="entry")` — saves mode with each code
- `get_active_codes()` — includes `mode` in response
- `use_code(code_str)` → `(valid, mode)` instead of `bool`

### 2. `routes/api/pass_codes.py`
- `POST /api/admin/codes/pass/start` — reads `mode` from JSON body (default `"entry"`)

### 3. `web/templates/admin/sections/pass.html` (NEW)
- Standalone page rendered by route `/admin/page/pass`
- Dropdown (Entry/Exit) next to Start button
- Stop button, status text, code grid with 60s countdown

### 4. `web/static/js/admin/pass.js` (NEW)
- `loadPass()` — fetches active codes, renders grid with countdown
- `startPass()` — POSTs mode along with start request
- `stopPass()` — clears codes
- Animated countdown via `requestAnimationFrame`

### 5. `web/templates/admin/sections/registers.html`
- Add `<select>` dropdown (Entry/Exit) next to Start button in `#attPassTab`

### 6. `web/static/js/admin/registers.js`
- `startPass()` — reads dropdown value, sends mode in POST body

## Flow
1. Admin selects **Entry** or **Exit** from dropdown
2. Clicks **Start** → 16 codes generated with that mode (shown on cards)
3. Student uses a code (via Telegram bot) → system reads the code's mode
4. Entry mode → sets `enter_at` on today's `InternAttendance`
5. Exit mode → sets `left_at` on today's `InternAttendance`
6. Prevents accidental double-marking in same session
