#!/bin/bash
# Installation script for UTeM Student Assistant Bot
# Run as root: sudo bash install.sh

set -e

# Configuration
BOT_USER="utem-bot"
BOT_DIR="/opt/utem-bot"
REPO_URL="https://github.com/yourusername/utem-bot.git"

echo "=== UTeM Student Assistant Bot Installation ==="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo)"
    exit 1
fi

# Update system
echo "Updating system packages..."
apt update && apt upgrade -y

# Install dependencies
echo "Installing dependencies..."
apt install -y python3 python3-pip python3-venv git sqlite3

# Set timezone
echo "Setting timezone to Malaysia..."
timedatectl set-timezone Asia/Kuala_Lumpur

# Create bot user (if doesn't exist)
if ! id "$BOT_USER" &>/dev/null; then
    echo "Creating bot user..."
    useradd --system --shell /bin/false --home-dir "$BOT_DIR" "$BOT_USER"
fi

# Create installation directory
echo "Setting up installation directory..."
mkdir -p "$BOT_DIR"
mkdir -p "$BOT_DIR/data"
mkdir -p "$BOT_DIR/logs"
mkdir -p "$BOT_DIR/backups"

# Clone repository (or copy files if local)
if [ -d ".git" ]; then
    echo "Copying local files..."
    cp -r . "$BOT_DIR/"
else
    echo "Cloning from repository..."
    git clone "$REPO_URL" "$BOT_DIR"
fi

# Create virtual environment
echo "Creating Python virtual environment..."
cd "$BOT_DIR"
python3 -m venv venv

# Install Python dependencies
echo "Installing Python dependencies..."
"$BOT_DIR/venv/bin/pip" install --upgrade pip
"$BOT_DIR/venv/bin/pip" install -r requirements.txt

# Set up environment file
if [ ! -f "$BOT_DIR/.env" ]; then
    echo "Creating .env file from example..."
    cp "$BOT_DIR/.env.example" "$BOT_DIR/.env"
    echo "IMPORTANT: Edit $BOT_DIR/.env with your API keys!"
fi

# Set permissions
echo "Setting permissions..."
chown -R "$BOT_USER:$BOT_USER" "$BOT_DIR"
chmod 600 "$BOT_DIR/.env"
chmod +x "$BOT_DIR/deploy/backup.sh"

# Install systemd service
echo "Installing systemd service..."
cp "$BOT_DIR/deploy/utem-bot.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable utem-bot

# Set up backup cron job
echo "Setting up backup cron job..."
(crontab -l 2>/dev/null; echo "0 2 * * * $BOT_DIR/deploy/backup.sh >> $BOT_DIR/logs/backup.log 2>&1") | crontab -

echo ""
echo "=== Installation Complete ==="
echo ""
echo "Next steps:"
echo "1. Edit $BOT_DIR/.env with your TELEGRAM_TOKEN and GEMINI_API_KEY"
echo "2. Start the bot: sudo systemctl start utem-bot"
echo "3. Check status: sudo systemctl status utem-bot"
echo "4. View logs: journalctl -u utem-bot -f"
echo ""
