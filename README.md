# 🎮 dy

> **Leveling up one command at a time** - A Telegram bot + mini app for managing attendance, tasks, notes, and announcements.

Meet **[dy](https://t.me/dyDMCBOT)** - my little side project that started as "let me learn FastAPI" and turned into a full-blown Telegram assistant for my institute. It doesn't reply to random chit-chat (only commands - clean, focused, minimal). More features will unlock as I keep learning.

<p align="center">
  <img src="assets/logo.png" alt="dy bot logo" width="200">
</p>

---

## 🧠 What It Does

| Feature | What's happening |
|---|---|
| 📋 **Attendance** | Daily auto-creation (Mon–Sat), QR code scanning for entry/exit |
| 📝 **Tasks** | Create, browse, and submit work - staff gives, interns submits |
| 📒 **Notes** | Share departmental notes with file uploads to Cloudinary |
| 📢 **Info / Announcements** | Broadcast messages - `/info` to see them |
| 👥 **Users** | Role-based (admin / instructor / intern), phone-link to Telegram |
| 🔗 **Phone Linking** | Admin creates users → they `/link` via contact share to connect |
| 💾 **DB Sync** | `/sync` upload a `.db` file to merge data (admin only, schema-validated) |
| 💽 **DB Backup** | `/db` downloads the live database (admin only) |

---

## 🤖 Commands

Everything responds only to commands - no passive replies. Minimal by design.

| Command | Who | What it does |
|---|---|---|
| `/start` | All | Welcome message + mini app button |
| `/me` | All | Your profile info |
| `/info` | All | View announcements |
| `/helpinfo` | All | Interactive help menu |
| `/userinfo` | All | User overview stats |
| `/taskinfo` | All | Browse active tasks (buttons) |
| `/givetask` | Staff ✋ | Create a task (step-by-step wizard) |
| `/submit` | All | Submit your work for a task |
| `/notes` | All | Browse notes (buttons) |
| `/givenotes` | Staff ✋ | Create a note (step-by-step wizard) |
| `/dashboard` | All | Open the web mini app |
| `/link` | All | Link phone to your account |
| `/qr` | Staff ✋ | Generate attendance QR code |
| `/db` | Admin 🔐 | Download database backup |
| `/sync` | Admin 🔐 | Upload & sync a database file |
| `/cancel` | All | Cancel current operation |
| `/skip` | All | Skip current step in wizards |

---

## 🛠️ Tech Stack

```
FastAPI    ⚡  async web framework
aiosqlite  🗄️  SQLite (async)
Telegram   🤖  python-telegram-bot (webhooks)
Cloudinary ☁️  file uploads
APScheduler ⏰  daily attendance cron
Render     🚀  deployment
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
MINI_APP_URL=http://localhost:8000
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
DATABASE_URL=sqlite+aiosqlite:///./dy.db
```

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

## 💡 Philosophy

- **Commands only.** No noise. The bot doesn't reply to every message - it waits for instructions.
- **Minimal.** Every feature has a reason. I'd rather ship fewer things well.
- **Learning-driven.** This whole project is me figuring out async Python, FastAPI, Telegram bots, and deployment. It's messy, it's fun, and it's getting better every commit.

---

## 👨‍💻 About the Dev

I'm **[Yves Dylane](https://github.com/yvesdylane)** - curious dev, always building, always breaking things. This is a side project I actually use, and I keep coming back to add stuff I wish existed.

If you're reading this and have ideas, suggestions, or just want to say hi - hit me up. I'm here to learn.

---

<p align="center">
  <sub>built with ☕ + 🎮 + way too many late nights</sub>
</p>
