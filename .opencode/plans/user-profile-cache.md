# User Profile Picture Cache & Display

## Goal
- Show user profile pictures directly in the admin user list (not just initials)
- Replace the "A" orange box in the mobile header with the admin's profile pic
- Pre-cache all user images locally on first page load
- Cache locally when user uploads photo via bot

## Files to change

### 1. `web/static/js/admin/users.js` — show images in list

In `renderUsers()`, replace the initials circle:
```js
// OLD: colored circle with initials
'<div class="w-9 h-9 rounded-full bg-brand-200 dark:bg-brand-800 ...">' + initials + '</div>'

// NEW: <img> if photo_url exists, initials fallback otherwise
'<div class="w-9 h-9 rounded-full shrink-0 overflow-hidden' + (u.photo_url ? '' : ' bg-brand-200 dark:bg-brand-800 flex items-center justify-center') + '">'
+ (u.photo_url
    ? '<img src="' + u.photo_url + '" class="w-full h-full object-cover" loading="lazy">'
    : '<span class="text-xs font-bold text-brand-700 dark:text-brand-300">' + initials + '</span>')
+ '</div>'
```

### 2. `web/static/js/admin/users.js` — pre-cache on first load

At the end of `loadUsers()` (after `renderUsers()`), trigger eager cache:
```js
// Pre-cache profile images server-side
users.forEach(function (u) {
  if (u.photo_url) {
    var img = new Image();
    img.src = u.photo_url;
  }
});
```
This forces the browser to fetch the image, which triggers the server to create `uploads/cache/users/{id}.jpg` if not already cached.

### 3. `web/templates/admin/index.html` — replace "A" with admin avatar

Line 80 — mobile header:
```html
{% if user.image %}
<img src="/api/admin/users/{{ user.id }}/photo"
     class="w-8 h-8 rounded-lg object-cover border-2 border-brand-500 shrink-0">
{% else %}
<div class="w-8 h-8 rounded-lg bg-brand-500 flex items-center justify-center text-white font-bold text-sm shrink-0">A</div>
{% endif %}
```

### 4. `bot/commands/profile.py` — cache photo on bot upload

In `image_handle_photo`, after `u.image = file_id`, add:
```python
# Cache thumbnail locally
import os
from controllers.face import resize_for_cache

photo_bytes = bytes(photo_bytes)  # already bytearray
thumb = await asyncio.get_running_loop().run_in_executor(None, resize_for_cache, photo_bytes)
cache_dir = "uploads/cache/users"
os.makedirs(cache_dir, exist_ok=True)
cache_path = os.path.join(cache_dir, f"{u.id}.jpg")
with open(cache_path, "wb") as f:
    f.write(thumb)
```

### 5. `routes/api/adminRoutes.py` — (no change needed)

The admin shell already passes `user` to the template, and `user.image` is accessible.

## Verification
- Open admin → mobile header shows admin's profile pic with orange border (or "A" fallback)
- Go to Users page → each user row shows profile pic (or initials fallback)
- First load fetches all images → subsequent loads are instant (cached)
- Upload photo via Telegram bot → cached locally immediately
