# Centurion Bot

A Telegram task-management bot for groups. Assign tasks, track deadlines, get daily reminders and weekly reviews — all inside your Telegram group chat.

> built with **aiogram 3**, **SQLAlchemy 2**, **Pydantic Settings**, and **APScheduler**.

## Features

- **Task management** — create, assign, complete, and track tasks with due dates
- **Group & private chat** — assign tasks in groups or via private conversation with the bot
- **Inline calendar** — pick due dates with an interactive calendar widget
- **Daily reminders** — automatic daily digest of overdue and upcoming tasks
- **Weekly review** — weekly summary of created/completed tasks, user rankings
- **Due date editing** — request due date changes with accept/deny workflow
- **Auto-registration** — when added to a group, the bot automatically registers all admins (no need for each user to write a message first)
- **User tracking** — automatically registers users who send messages or join the group
- **Feedback system** — users can send feedback; admin can view, reply, and close
- **Announcements** — admin can broadcast messages to all users
- **Statistics** — personal and group task statistics
- **Privacy** — user data is cleaned up when they leave a group
- **Recurring tasks** — create tasks that auto-generate on a schedule (daily/weekly/monthly)
- **Task priorities** — set priority (🔴 high / 🟡 medium / 🟢 low) with `!high` or `!low` flags
- **Escalation** — overdue high-priority tasks trigger automatic alerts to the group and admin
- **Team check-ins** — daily status reports (done/plan/blockers) with streak tracking
- **Check-in reports** — admin can see who checked in and who hasn't

## Tech Stack

| Component     | Technology                       |
| ------------- | -------------------------------- |
| Bot framework | aiogram 3.x (async)              |
| Database      | SQLAlchemy 2.0 + aiosqlite       |
| Config        | Pydantic Settings                |
| Scheduler     | APScheduler                      |
| Logging       | structlog                        |
| Linter        | Ruff                             |
| Type checker  | mypy                             |
| Tests         | pytest + pytest-asyncio          |
| Container     | Docker + Docker Compose          |

## Quick Start

```bash
# Clone
git clone https://github.com/ruslanlap/centurion-bot.git
cd centurion-bot

# Setup
cp .env.example .env
# Edit .env with your TELEGRAM_BOT_TOKEN and ADMIN_ID

# Install & run
make install
make run
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for full deployment instructions.

## Commands

### User Commands

| Command | Description |
| ------- | ----------- |
| `/start` | Start the bot and show help |
| `/help` | Show available commands |
| `/do <title>` | Create a task (private: select group & assignee) |
| `/do <title> @user in N days` | Create a task in group chat |
| `/do <title> !high` | Create a high-priority task |
| `/tasks` | Show your tasks (private) or group tasks |
| `/stats` | Show your or group statistics |
| `/due` | Trigger daily task overview |
| `/weekly` | Trigger weekly review |
| `/repeat <title> daily\|weekly\|monthly` | Create a recurring task |
| `/repeats` | List active recurring tasks |
| `/checkin` | Submit daily check-in report |
| `/checkin_report` | View today's check-in reports |
| `/feedback <text>` | Send feedback to the admin |

### Admin Commands

| Command | Description |
| ------- | ----------- |
| `/admin_stats` | Show bot-wide statistics |
| `/admin_announce <text>` | Broadcast message to all users |
| `/admin_feedback_show` | List unresolved feedback |
| `/admin_feedback_reply <id> <text>` | Reply to feedback |
| `/admin_feedback_close <id>` | Mark feedback as resolved |

## License

MIT
