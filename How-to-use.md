# Azure Deployment Guide for UTeM Productivity Bot

Complete guide to deploy the bot on Azure for Students (free tier).

---

## Prerequisites

- Azure for Students account ($100 free credit)
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- Gemini API Key(s) (from [Google AI Studio](https://aistudio.google.com))

---

## Step 1: Sign Up for Azure for Students

1. Go to: https://azure.microsoft.com/en-us/free/students
2. Click **"Start free"**
3. Sign in with your student email (e.g., `B012345678@student.utem.edu.my`)
4. Complete verification via email
5. You get: **$100 credit + 750 free VM hours/month**

---

## Step 2: Create Linux VM in Azure Portal

### 2.1 Navigate to Virtual Machines
- Go to: https://portal.azure.com
- Search **"virtual machines"** in top search bar
- Click **"+ Create"** → **"Azure virtual machine"**

### 2.2 Configure Basics Tab

| Field | Value |
|-------|-------|
| Subscription | Azure for Students |
| Resource group | Create new → `productivity-bot-rg` |
| Virtual machine name | `productivity-bot-vm` |
| Region | `(Asia Pacific) Southeast Asia` |
| Availability options | No infrastructure redundancy required |
| Security type | Standard |
| Image | `Ubuntu Server 22.04 LTS - x64 Gen2` |
| Size | `Standard_B2ats_v2` (free tier eligible) |

### 2.3 Administrator Account

| Field | Value |
|-------|-------|
| Authentication type | SSH public key |
| Username | `azureuser` |
| SSH public key source | Generate new key pair |
| Key pair name | `productivity-bot-key` |

### 2.4 Inbound Port Rules

| Field | Value |
|-------|-------|
| Public inbound ports | Allow selected ports |
| Select inbound ports | SSH (22) |

### 2.5 Disks Tab
- Click **"Next: Disks >"**
- OS disk type: `Standard SSD`
- Check: Delete with VM

### 2.6 Networking Tab
- Click **"Next: Networking >"**
- Leave defaults
- Check: Delete public IP and NIC when VM is deleted

### 2.7 Management Tab
- Click **"Next: Management >"**
- Enable auto-shutdown: `11:00 PM`
- Time zone: `(UTC+08:00) Kuala Lumpur, Singapore`

### 2.8 Create VM
1. Click **"Review + create"**
2. Click **"Create"**
3. **Download the `.pem` key file** when prompted
4. Save to: `C:\Users\YOUR_USERNAME\.ssh\productivity-bot-key.pem`
5. Wait for deployment (~2 minutes)
6. Click **"Go to resource"**
7. **Copy the Public IP address**

---

## Step 3: Configure Network Security Group

Already configured when you selected SSH (22). To verify:
1. In your VM page, click **"Networking"** in left menu
2. Confirm SSH rule exists (port 22)

---

## Step 4: SSH into VM from Windows

### 4.1 Open PowerShell/Terminal
Press `Win + X` → Select **"Terminal"** or **"PowerShell"**

### 4.2 Set Key Permissions
```powershell
icacls "C:\Users\YOUR_USERNAME\.ssh\productivity-bot-key.pem" /inheritance:r
icacls "C:\Users\YOUR_USERNAME\.ssh\productivity-bot-key.pem" /grant:r "%USERNAME%:R"
```

### 4.3 Connect via SSH
```powershell
ssh -i "C:\Users\YOUR_USERNAME\.ssh\productivity-bot-key.pem" azureuser@YOUR_PUBLIC_IP
```
Replace `YOUR_PUBLIC_IP` with your VM's IP address.

### 4.4 Accept Host Key
Type `yes` when prompted about fingerprint.

You should see:
```
Welcome to Ubuntu 22.04 LTS
azureuser@productivity-bot-vm:~$
```

---

## Step 5: Install Python and Dependencies

Run these commands on the VM:

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python, pip, venv, git
sudo apt install -y python3-pip python3-venv git
```

---

## Step 6: Clone Repository and Configure Bot

```bash
# Create app directory
sudo mkdir -p /opt/productivity-bot
sudo chown azureuser:azureuser /opt/productivity-bot
cd /opt/productivity-bot

# Clone your repository
git clone https://github.com/YOUR_USERNAME/productivity.git .

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create data directory
mkdir -p data

# Create .env file
nano .env
```

### Add to .env file:

```env
TELEGRAM_TOKEN=your_telegram_bot_token
GEMINI_API_KEYS=key1,key2,key3,key4,key5,key6,key7,key8,key9,key10
DATABASE_PATH=data/bot.db
ALLOWED_USER_ID=561393547
```

> **Note:** Use `GEMINI_API_KEYS` (comma-separated) for multiple API keys with auto-rotation.

Press `Ctrl+X`, then `Y`, then `Enter` to save.

---

## Step 7: Set Up systemd Service

```bash
sudo nano /etc/systemd/system/productivity-bot.service
```

### Paste this content:

```ini
[Unit]
Description=UTeM Productivity Telegram Bot
After=network.target

[Service]
Type=simple
User=azureuser
WorkingDirectory=/opt/productivity-bot
Environment=PATH=/opt/productivity-bot/venv/bin
EnvironmentFile=/opt/productivity-bot/.env
ExecStart=/opt/productivity-bot/venv/bin/python -m src.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Press `Ctrl+X`, then `Y`, then `Enter` to save.

### Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable productivity-bot
sudo systemctl start productivity-bot
```

---

## Step 8: Verify Bot is Running

```bash
# Check service status
sudo systemctl status productivity-bot

# View live logs
sudo journalctl -u productivity-bot -f
```

You should see:
```
● productivity-bot.service - UTeM Productivity Telegram Bot
     Loaded: loaded
     Active: active (running)
...
Gemini client ready with 10 API key(s)
Initializing database at data/bot.db
Starting bot...
Bot is running. Press Ctrl+C to stop.
```

**Test your bot:** Send `/start` to your Telegram bot!

---

## Quick Reference Commands

| Action | Command |
|--------|---------|
| Check status | `sudo systemctl status productivity-bot` |
| View logs | `sudo journalctl -u productivity-bot -f` |
| Restart bot | `sudo systemctl restart productivity-bot` |
| Stop bot | `sudo systemctl stop productivity-bot` |
| Start bot | `sudo systemctl start productivity-bot` |
| Update code | `cd /opt/productivity-bot && git pull && sudo systemctl restart productivity-bot` |

---

## Troubleshooting

### Bot not starting
```bash
# Check logs for errors
sudo journalctl -u productivity-bot -n 50

# Verify .env file exists and has correct values
cat /opt/productivity-bot/.env
```

### Permission denied errors
```bash
# Fix ownership
sudo chown -R azureuser:azureuser /opt/productivity-bot
```

### Missing dependencies
```bash
cd /opt/productivity-bot
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart productivity-bot
```

### SSH connection refused
- Check VM is running in Azure Portal
- Verify NSG allows port 22
- Confirm you're using correct IP address

---

## API Key Rotation

The bot supports multiple Gemini API keys with automatic rotation:

- Configure keys in `.env`: `GEMINI_API_KEYS=key1,key2,key3,...`
- When one key hits rate limit, bot auto-switches to next key
- Each key gets 60-second cooldown before retry
- With 10 keys (20 RPD each) = **200 requests/day**

---

## Costs

| Resource | Cost |
|----------|------|
| VM (B2ats_v2) | Free (750 hrs/month) |
| Dynamic IP | Free |
| Storage | ~$1.20/month |
| **Total** | **~$1.20/month** from $100 credit |

Your $100 credit lasts approximately **12+ months**.
