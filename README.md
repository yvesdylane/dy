# 🎮 dy

> **Leveling up one command at a time** — A Telegram bot + mini app for managing attendance, tasks, notes, and announcements.

Meet **[dy](https://t.me/dyDMCBOT)** — a side project that started as "let me play with the Telegram Bot API" and grew into a full assistant for my institute. It doesn't reply to random chit-chat (only commands — clean, focused, minimal).

<p align="center">
  <img src="previouse/assets/logo.png" alt="dy bot logo" width="200">
</p>

---

## 🧠 What It Does

| Feature | What's happening |
|---|---|
| 📋 **Attendance** | Daily auto-creation (Mon–Sat), QR code scanning for entry/exit |
| 📝 **Tasks** | Create, browse, and submit work — staff gives, interns submit |
| 📒 **Notes** | Share departmental notes with file uploads |
| 📢 **Info / Announcements** | Broadcast messages — `/info` to see them |
| 🙊 **Anonymous Complaints** | `/complain` to submit feedback — no identity stored |
| ✈️ **Leave Requests** | `/leave` to apply, staff review & approve/reject |
| 👥 **Users** | Role-based (admin / instructor / intern), phone-link to Telegram |
| 🔗 **Phone Linking** | Admin creates users → they `/link` via contact share to connect |
| 💾 **DB Sync** | `/sync` upload a `.db` file to merge data — also re-uploads all files to the storage group |
| 💽 **DB Backup** | `/db` downloads the live database (admin only) |
| 🖼️ **Profile Pic** | `/image` upload a profile photo — stored in the Telegram group, shown on `/me` |

---

## 🤖 Commands

Everything responds only to commands — no passive replies. Minimal by design.

| Command | Who | What it does |
|---|---|---|
| `/start` | All | Welcome message + mini app button |
| `/me` | All | Your profile info + photo |
| `/info` | All | View announcements with file attachments |
| `/helpinfo` | All | Interactive help menu |
| `/userinfo` | All | User overview stats |
| `/taskinfo` | All | Browse active tasks (buttons) |
| `/givetask` | Staff ✋ | Create a task (step-by-step wizard) |
| `/submit` | All | Submit your work for a task |
| `/notes` | All | Browse notes (buttons) |
| `/givenotes` | Staff ✋ | Create a note (step-by-step wizard) |
| `/leave` | Interns | Apply for leave (date picker + reason) |
| `/complain` | All | Submit anonymous complaint or advice |
| `/dashboard` | All | Open the web mini app |
| `/link` | All | Link phone to your account |
| `/qr` | Staff ✋ | Generate attendance QR code |
| `/image` | All | Upload profile picture |
| `/db` | Admin 🔐 | Download database backup |
| `/sync` | Admin 🔐 | Upload & sync a database file |
| `/cancel` | All | Cancel current operation |
| `/skip` | All | Skip current step in wizards |

---

## 🛠️ Tech Stack

```
FastAPI        ⚡  async web framework
aiosqlite      🗄️  SQLite (async)
Telegram       🤖  python-telegram-bot (webhooks)
Telegram Group 🗂️  file storage (replaced Cloudinary)
APScheduler    ⏰  daily attendance cron
Render         🚀  deployment
```

---

## 🚀 Local Setup

### 1. Clone

```bash
git clone https://github.com/yvesdylane/dy.git
cd dy
```

### 2. Environment

Create `.env` at the project root:

```
TELEGRAM_TOKEN=your_bot_token
TELEGRAM_GROUP_ID=-1001234567890
MINI_APP_URL=http://localhost:8000
DATABASE_URL=sqlite+aiosqlite:///./dy.db
```

The bot must be added as a member of the Telegram group used for file storage. Its ID can be obtained from any message forwarded to the bot.

### 3. Install & Run

```bash
uv sync
uv run python main.py
```

The app will be at `http://localhost:8000`, bot webhook at `/telegram`, dashboard at `/app`.

### 4. Deploy (Render)

| Setting | Value |
|---|---|
| **Build Command** | `uv sync --frozen && uv cache prune --ci` |
| **Start Command** | `uv run python main.py` |
| **Env vars** | Same as `.env` above (set `MINI_APP_URL` to `https://your-app.onrender.com`) |

---

## 💾 Sync & Backup

- **`/sync`** — Upload a `.db` file. The bot merges users, attendance, tasks, submissions, notes, info, creation codes, complaints, and leave requests. After merging, it re-uploads every file found in the old DB (profile images, task attachments, submission files, note/info attachments) to the current storage group and updates all `file_id` references automatically.

- **`/db`** — Download the current live database for manual backup.

---

## 💡 Philosophy

- **Commands only.** No noise. The bot doesn't reply to every message — it waits for instructions.
- **Minimal.** Every feature has a reason. I'd rather ship fewer things well.
- **Play-driven.** This whole project is me messing around with the Telegram Bot API, async Python, and webhooks. It's messy, it's fun, and it's getting better every commit.
- We intentionally use the libsql_experimental synchronous dialect wrapped with asyncio.to_thread() because the current aiolibsql async dialect causes cursor read failures with Turso. Revisit this only after confirming the async driver is stable.
---

## 👨‍💻 About the Dev

I'm **[Yves Dylane](https://github.com/yvesdylane)** — curious dev, always building, always breaking things. This is a side project I actually use, and I keep coming back to add stuff I wish existed.

If you're reading this and have ideas, suggestions, or just want to say hi — hit me up. I'm here to learn.

---

<p align="center">
  ⭐ If you find dy useful, <a href="https://github.com/yvesdylane/dy">star the repo</a> — it really helps!
</p>

---

<p align="center">
  <sub>built with ☕ + 🎮 + way too many late nights</sub>
</p>
