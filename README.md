# 🖤 Black Pearl Telegram Bot

A feature-rich Telegram bot built with Python, designed as a personal channel bridge between users and the admin, with daily content, Persian calendar, astronomical data, and Hafez fortune-telling.The key highlight of this project is that it was free and didn't rely on any paid resources—though for larger-scale projects, you could certainly opt for paid or superior alternatives. With this project, we demonstrated that it is possible to get the job done using only the bare minimum.


---

## ✨ Features


- **📜 Daily History** — A curated historical fact or event, once per day
- **🧠 Daily Wisdom** — A philosophical quote from thinkers like Camus, Nietzsche, Sartre, Marcus Aurelius, and more, once per day
- **📖 Hafez Fortune** — Random selection from all 495 Hafez poems with traditional interpretations
- **📅 Today's Date** — Shamsi (Solar Hijri) and Gregorian dates, moon phase, zodiac sign, and current season
- **🔭 Tonight's Sky** — Real-time astronomical report including moon phase, upcoming lunar events, next solstice/equinox, planet positions and rise/set times, visible constellations, and navigation stars — all calculated for Tehran
- **🗄️ Persistent DB** — Message mappings backed up to a private Telegram group, restored automatically on restart
- **📨 Messaging** — Users can send messages to the admin with or without revealing their identity (anonymous mode with unique persistent code)
- **↩️ Two-way replies** — Admin can reply directly to forwarded messages; users receive responses with a reply button for follow-up

---

## 🗂️ Project Structure

```
black-pearl-telegram-bot/
├── core/
│   ├── main.py           # Bot logic, handlers, webhook/polling
│   ├── astronomy.py      # Skyfield-based astronomical calculations
│   ├── hafez.py          # 495 Hafez poems with fortune interpretations
│   ├── history.py        # Daily history facts
│   └── philosophy.py     # Daily philosophical quotes
├── docs/
│   └── .gitkeep
├── de421.bsp             # NASA ephemeris file (required by Skyfield)
├── .env.example          # Environment variable template
├── .gitignore
├── LICENSE
├── README.md
└── requirements.txt
```

---

## ⚙️ Requirements

- Python 3.10+
- A Telegram Bot Token from [@BotFather](https://t.me/BotFather)
- A private Telegram group for database backup (bot must be admin with pin permission) or you can just use a normal database

---

## 🚀 Setup & Installation

**1. Clone the repository**
```bash
git clone https://github.com/ArsMantech/black-pearl-python-telegram-bot.git
cd black-pearl-telegram-bot
```

**2. Install dependencies**
```bash
python -m pip install -r requirements.txt
```

**3. Configure environment variables**

Copy `.env.example` to `.env` and fill in your values:
```bash
cp .env.example .env
```

```env
BOT_TOKEN=your_bot_token_here
ADMIN_ID=your_telegram_user_id
BACKUP_GROUP_ID=your_private_group_id
WEBHOOK_URL=                      # Leave empty for local polling
WEBHOOK_SECRET=your_random_webhook_secret
```

**4. Run locally**
```bash
python core/main.py
```

The bot will run in polling mode when `WEBHOOK_URL` is not set.

---

## ☁️ Deployment (Render)

1. Push the repository to GitHub
2. Create a new **Web Service** on [Render](https://render.com)
3. Connect your GitHub repository
4. Set the **Start Command** to:
   ```
   python core/main.py
   ```
5. Add the following **Environment Variables** in Render dashboard:
   - `BOT_TOKEN`
   - `ADMIN_ID`
   - `BACKUP_GROUP_ID`
   - `WEBHOOK_URL` → your Render service URL (e.g. `https://your-app.onrender.com`)
   - `WEBHOOK_SECRET` → a random secret string used to authenticate Telegram webhook requests

6. To keep the free instance alive, set up a monitor on [UptimeRobot](https://uptimerobot.com) pinging your service URL every 5 minutes.

---

## 🔐 Environment Variables

| Variable | Description |
|----------|-------------|
| `BOT_TOKEN` | Telegram bot token from BotFather |
| `ADMIN_ID` | Your Telegram numeric user ID |
| `BACKUP_GROUP_ID` | Numeric ID of the private backup group |
| `WEBHOOK_URL` | Public URL for webhook mode (leave empty for polling) |
| `WEBHOOK_SECRET` | Secret used to authenticate webhook requests; required with `WEBHOOK_URL` |

## 🔒 Privacy and Security

- Never commit `.env`, `db.json`, virtual environments, or generated Python cache files.
- The bot stores Telegram user IDs, names, message mappings, and daily usage data in `db.json`.
- Anonymous messages hide the sender from the admin interface, but the bot still stores the sender ID internally so replies can be delivered.
- For production deployment, use persistent storage for `db.json`; ephemeral hosting storage can lose it on restart or redeploy.


---

## 🛠️ Tech Stack

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) v21.6
- [Skyfield](https://rhodesmill.org/skyfield/) — astronomical calculations
- [jdatetime](https://github.com/slashmili/python-jalali) — Shamsi calendar
- [Flask](https://flask.palletsprojects.com/) — webhook server
- NASA DE421 ephemeris

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
