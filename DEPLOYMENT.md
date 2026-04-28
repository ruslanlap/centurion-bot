# Deployment Guide

Complete guide for deploying **Centurion Bot** on a VPS, in Docker, or locally.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Telegram Bot Setup](#telegram-bot-setup)
3. [Local Development](#local-development)
4. [Docker Deployment](#docker-deployment)
5. [VPS Deployment (systemd)](#vps-deployment-systemd)
6. [Webhook Mode](#webhook-mode)
7. [MySQL/MariaDB Database](#mysqlmariadb-database)
8. [Environment Variables](#environment-variables)
9. [Makefile Commands](#makefile-commands)
10. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- **Python 3.11+** (for local development)
- **Docker & Docker Compose** (for containerized deployment)
- **A Telegram Bot Token** from [@BotFather](https://t.me/BotFather)
- **Your Telegram User ID** (get it from [@userinfobot](https://t.me/userinfobot))

---

## Telegram Bot Setup

1. Open Telegram and start a chat with [@BotFather](https://t.me/BotFather).
2. Send `/newbot` and follow the instructions to create a new bot.
3. Copy the **bot token** — you'll need it for the `.env` file.
4. **Important:** Disable privacy mode so the bot can see group messages:
   - Send `/mybots` to BotFather
   - Select your bot → Bot Settings → Group Privacy → Turn off
5. Optional: Set the bot's command list:
   ```
   /setcommands
   ```
   Then send:
   ```
   start - Start the bot
   help - Show available commands
   do - Create a task
   tasks - Show tasks
   stats - Show statistics
   due - Show tasks due today
   weekly - Show weekly review
   feedback - Send feedback
   ```

---

## Local Development

```bash
# 1. Clone the repository
git clone https://github.com/ruslanlap/centurion-bot.git
cd centurion-bot

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# 3. Install dependencies
make dev  # or: pip install -e ".[dev]"

# 4. Configure environment
cp .env.example .env
# Edit .env and set your TELEGRAM_BOT_TOKEN and ADMIN_ID

# 5. Run the bot
make run  # or: python -m centurion_bot

# 6. Run tests
make test

# 7. Run linter and type checker
make lint
make typecheck
```

---

## Docker Deployment

### Quick Start

```bash
# 1. Clone and configure
git clone https://github.com/ruslanlap/centurion-bot.git
cd centurion-bot
cp .env.example .env
# Edit .env with your settings

# 2. Build and start
make docker-build
make docker-up

# 3. Check logs
make docker-logs

# 4. Stop
make docker-down
```

### Manual Docker Commands

```bash
# Build
docker compose build

# Start (detached)
docker compose up -d

# View logs
docker compose logs -f bot

# Stop
docker compose down

# Rebuild after code changes
docker compose up -d --build
```

### Data Persistence

The SQLite database is stored in a Docker volume (`bot-data`). Your data persists across container restarts and rebuilds.

To back up the database:
```bash
docker cp centurion-bot:/app/data/centurion.db ./backup.db
```

---

## VPS Deployment (systemd)

For a bare-metal VPS deployment using systemd:

### 1. Setup

```bash
# Install Python 3.11+ (Ubuntu/Debian)
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip git

# Create a dedicated user
sudo useradd -m -s /bin/bash centurion
sudo su - centurion

# Clone and install
git clone https://github.com/ruslanlap/centurion-bot.git
cd centurion-bot
python3.11 -m venv .venv
source .venv/bin/activate
pip install .

# Configure
cp .env.example .env
nano .env  # set TELEGRAM_BOT_TOKEN and ADMIN_ID
```

### 2. Create systemd Service

```bash
sudo tee /etc/systemd/system/centurion-bot.service << 'EOF'
[Unit]
Description=Centurion Telegram Bot
After=network.target

[Service]
Type=simple
User=centurion
Group=centurion
WorkingDirectory=/home/centurion/centurion-bot
EnvironmentFile=/home/centurion/centurion-bot/.env
ExecStart=/home/centurion/centurion-bot/.venv/bin/python -m centurion_bot
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

### 3. Enable and Start

```bash
sudo systemctl daemon-reload
sudo systemctl enable centurion-bot
sudo systemctl start centurion-bot

# Check status
sudo systemctl status centurion-bot

# View logs
sudo journalctl -u centurion-bot -f
```

### 4. Updates

```bash
sudo su - centurion
cd centurion-bot
git pull
source .venv/bin/activate
pip install .
exit
sudo systemctl restart centurion-bot
```

---

## Webhook Mode

For production deployments behind a reverse proxy (nginx, Caddy, etc.):

### 1. Configure `.env`

```env
WEBHOOK_URL="https://your-domain.com"
WEBHOOK_HOST="0.0.0.0"
WEBHOOK_PORT=8080
WEBHOOK_SECRET="your-random-secret-string"
```

### 2. Nginx Configuration

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    location /webhook {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 3. Docker Compose for Webhook

Uncomment the `ports` section in `docker-compose.yml`:

```yaml
services:
  bot:
    # ...
    ports:
      - "8080:8080"
```

---

## MySQL/MariaDB Database

By default, the bot uses SQLite. To use MySQL/MariaDB:

### 1. Install MySQL Extra

```bash
pip install centurion-bot[mysql]
# or in Docker, add to Dockerfile:
# RUN pip install ".[mysql]"
```

### 2. Configure `.env`

```env
DATABASE_URL="mysql+asyncmy://user:password@localhost:3306/centurion?charset=utf8mb4"
```

### 3. Create Database

```sql
CREATE DATABASE centurion CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'centurion'@'%' IDENTIFIED BY 'your-password';
GRANT ALL PRIVILEGES ON centurion.* TO 'centurion'@'%';
FLUSH PRIVILEGES;
```

---

## Environment Variables

| Variable | Required | Default | Description |
| -------- | -------- | ------- | ----------- |
| `TELEGRAM_BOT_TOKEN` | Yes | — | Bot token from BotFather |
| `ADMIN_ID` | Yes | — | Your Telegram user ID |
| `BOT_NAME` | No | `centurion_bot` | Bot username (without @) |
| `DATABASE_URL` | No | `sqlite+aiosqlite:///data/centurion.db` | Database connection URL |
| `LOG_LEVEL` | No | `INFO` | Logging level |
| `WEBHOOK_URL` | No | — | Webhook URL (empty = polling mode) |
| `WEBHOOK_HOST` | No | `0.0.0.0` | Webhook server host |
| `WEBHOOK_PORT` | No | `8080` | Webhook server port |
| `WEBHOOK_SECRET` | No | — | Webhook secret token |
| `DAILY_REMINDER_HOUR` | No | `8` | Hour for daily reminder (UTC) |
| `DAILY_REMINDER_MINUTE` | No | `0` | Minute for daily reminder |
| `WEEKLY_REVIEW_WEEKDAY` | No | `6` | Day for weekly review (0=Mon, 6=Sun) |
| `WEEKLY_REVIEW_HOUR` | No | `18` | Hour for weekly review (UTC) |
| `WEEKLY_REVIEW_MINUTE` | No | `0` | Minute for weekly review |

---

## Makefile Commands

```bash
make help          # Show all available commands
make install       # Install production dependencies
make dev           # Install dev dependencies
make lint          # Run linter (ruff)
make format        # Auto-format code
make typecheck     # Run type checker (mypy)
make test          # Run tests
make run           # Run the bot locally
make docker-build  # Build Docker image
make docker-up     # Start in Docker
make docker-down   # Stop Docker
make docker-logs   # View Docker logs
make clean         # Clean build artifacts
```

---

## Troubleshooting

### Bot not responding to group messages
Make sure privacy mode is **disabled** in BotFather settings. The bot needs to see all messages to register users.

### "Conflict: terminated by other getUpdates request"
Only one instance of the bot can run in polling mode at a time. Stop any other running instances.

### Database locked (SQLite)
SQLite is single-writer. If you see "database is locked" errors, switch to MySQL for production workloads.

### Users not being auto-registered
The auto-registration feature uses `getChatAdministrators` API, which only returns admins. Regular members are registered when they send their first message or when `chat_member` updates are received (requires privacy mode off).

### Webhook not working
1. Ensure your domain has a valid SSL certificate.
2. Check that the webhook URL is accessible from the internet.
3. Verify the `WEBHOOK_SECRET` matches in your `.env` and nginx config.
4. Check logs: `make docker-logs` or `journalctl -u centurion-bot -f`.
