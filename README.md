# ⚔️ OUTER AGOGE Bot v2 — Smart Channel Tracker

No commands needed for daily tracking.
Just post in the right channel. The bot handles the rest.

---

## How It Works

| Channel | What happens when you post |
|---|---|
| GM | GM logged automatically for you |
| Accountability | Report logged automatically |
| Business Wins | Bot reads your message, extracts the money amount, logs it |
| Fitness Wins | Fitness activity logged |

**Slash commands** are only for viewing data and admin actions.

---

## SETUP — 4 Steps

### Step 1 — Create the bot

1. Message **@BotFather** on Telegram
2. Send `/newbot` → name it `Outer Agoge` → username: `OuterAgogeBot`
3. Copy the **token** it gives you

### Step 2 — Disable privacy mode (critical)

Still in @BotFather:
1. Send `/setprivacy`
2. Select your bot
3. Choose **Disable**

This allows the bot to read all group messages, not just commands.

### Step 3 — Get your Telegram User ID

1. Message **@userinfobot** directly
2. It replies with your ID (e.g. `123456789`)

### Step 4 — Deploy on Railway

1. Go to **railway.app** → sign up → New Project → Deploy from GitHub
2. Push this folder to a GitHub repo, connect it
3. In Railway → **Variables** tab, add:

```
BOT_TOKEN   = (your token from BotFather)
ADMIN_IDS   = (your Telegram user ID)
DB_PATH     = /app/outer_agoge.db
```

4. Add a **Volume**: Railway project → Add Volume → Mount path: `/app`
   This keeps your data permanently across restarts.

5. Make sure the service runs with `python bot.py` (Procfile handles this)

### Step 5 — Add bot to group and register channels

1. Add your bot to the Outer Agoge Telegram group
2. Make it **admin** (Send Messages permission is enough)
3. Go into each topic and register it — run these commands **inside each topic**:

```
In the GM topic:             /setup gm
In Accountability topic:     /setup accountability
In Business Wins topic:      /setup business
In Fitness Wins topic:       /setup fitness
In Lifestyle Wins topic:     /setup lifestyle
```

Run `/setup` with no arguments to verify all channels are registered.

### Step 6 — Members send /start

Each member DMs the bot `/start` once so it knows who they are.
After that, everything works automatically from group posts.

---

## Commands

### Everyone
```
/lb           Current month money-in leaderboard
/streak       GM and report streaks for all Spartans
/mystats      Your personal stats and badge history
/hall         Hall of Record — all titles ever earned
/members      List of all registered Spartans
/moneyin X    Manual money-in (if bot didn't detect your amount)
/help         Show commands
```

### Admin only
```
/setup <type>                       Register a topic channel
/badge @user CONQUEROR|GLADIATOR|SHIELD   Award a title
/challenge <description>            Post a new fitness challenge
/winner @user                       Declare challenge winner (auto-awards Gladiator)
/moneyin @user <amount>             Submit money-in for someone else
/removemoneyin @user                Remove a money-in entry
```

---

## Smart Money Detection

The bot understands all these formats in Business Wins posts:
- `$1,300` / `$1300` / `$1.3k`
- `1300$` / `1.3K$`
- `€500`
- `Amount: 1300`
- `Closed a deal for $2,000`
- `Made $848 this month`
- `1500 USD`

If it can't detect an amount, it tells you and prompts `/moneyin <amount>`.

---

## The Three Titles

| Title | How it's awarded |
|---|---|
| 💰 THE CONQUEROR | Highest total money-in that month — auto-calculated |
| 🏛 THE GLADIATOR | Fitness challenge winner — admin runs `/winner @user` |
| 🛡 THE SHIELD | Brotherhood vote — admin runs `/badge @user SHIELD` |

Default title for everyone: **SPARTAN**

---

*OUTER AGOGE — Forged in discipline. Bound by brotherhood.*
