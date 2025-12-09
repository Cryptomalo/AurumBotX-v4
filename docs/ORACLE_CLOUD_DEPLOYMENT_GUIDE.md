# ☁️ Oracle Cloud Always Free - Deployment Guide

Guida completa per deploy di AurumBotX su Oracle Cloud Infrastructure (OCI) con tier **Always Free** (€0/mese, forever).

---

## 🎯 Perché Oracle Cloud?

| Feature | Oracle Cloud | Railway.app | Heroku |
|---------|-------------|-------------|--------|
| **Costo** | €0 forever | €5/mese | €7/mese |
| **CPU** | 4 OCPU (ARM) | 0.5 vCPU | 1 dyno |
| **RAM** | 24 GB | 512 MB | 512 MB |
| **Storage** | 200 GB | 1 GB | 512 MB |
| **Uptime** | 99.95% | 99% | 95% |

**Verdetto**: Oracle Cloud Always Free è imbattibile per bot 24/7.

---

## 📋 Prerequisiti

1. Account Oracle Cloud (gratuito, no carta credito richiesta)
2. SSH client (già presente su Linux/Mac)
3. 60 minuti di tempo

---

## 🚀 Step 1: Crea VM Instance

### 1.1 Login Oracle Cloud

1. Vai su https://cloud.oracle.com
2. Click **Sign In** → **Cloud Account Name**: inserisci il tuo
3. Login con email/password

### 1.2 Crea Compute Instance

1. Menu **☰** → **Compute** → **Instances**
2. Click **Create Instance**
3. Configurazione:

```
Name: aurumbot-prod
Image: Ubuntu 22.04 (Always Free eligible)
Shape: VM.Standard.A1.Flex (ARM)
  - OCPU: 2
  - Memory: 12 GB
Networking: Default VCN (auto-created)
SSH Keys: Generate new key pair → Download private key
```

4. Click **Create**
5. Attendi 2-3 minuti per provisioning

### 1.3 Configura Firewall

1. Instance details → **Subnet** → **Default Security List**
2. Click **Add Ingress Rule**:

```
Source CIDR: 0.0.0.0/0
Destination Port: 22
Description: SSH access
```

3. Click **Add Ingress Rule** (opzionale per monitoring web):

```
Source CIDR: 0.0.0.0/0
Destination Port: 8080
Description: Monitoring dashboard
```

---

## 🔐 Step 2: Connessione SSH

### 2.1 Ottieni IP Pubblico

1. Instance details → copia **Public IP Address** (es: 140.238.x.x)

### 2.2 Connetti via SSH

```bash
# Linux/Mac
chmod 600 ~/Downloads/ssh-key-*.key
ssh -i ~/Downloads/ssh-key-*.key ubuntu@140.238.x.x

# Windows (PowerShell)
ssh -i C:\Users\YourName\Downloads\ssh-key-*.key ubuntu@140.238.x.x
```

---

## 📦 Step 3: Installa Dipendenze

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11
sudo apt install -y python3.11 python3.11-venv python3-pip git

# Verify
python3.11 --version  # Should show 3.11.x
```

---

## 🤖 Step 4: Deploy AurumBotX

### 4.1 Clone Repository

```bash
cd ~
git clone https://github.com/Cryptomalo/AurumBotX-v4.git
cd AurumBotX-v4
```

### 4.2 Setup Virtual Environment

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4.3 Configura API Keys

```bash
cat > .env << 'EOF'
OPENAI_API_KEY=your_openai_api_key_here
EOF
```

### 4.4 Test Manuale

```bash
# Test rapido (Ctrl+C dopo 1 ciclo)
python3 src/wallet_runner_hyperliquid.py
```

Dovresti vedere:

```
✅ Hyperliquid testnet connection OK
✅ OpenAI API connection OK
🔄 Starting trading cycle 1...
```

---

## 🔄 Step 5: Systemd Service (24/7 Autostart)

### 5.1 Crea Service File

```bash
sudo tee /etc/systemd/system/aurumbot.service > /dev/null << 'EOF'
[Unit]
Description=AurumBotX Trading Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/AurumBotX-v4
Environment="PATH=/home/ubuntu/AurumBotX-v4/venv/bin"
ExecStart=/home/ubuntu/AurumBotX-v4/venv/bin/python3 src/wallet_runner_hyperliquid.py
Restart=always
RestartSec=10
StandardOutput=append:/home/ubuntu/AurumBotX-v4/logs/bot.log
StandardError=append:/home/ubuntu/AurumBotX-v4/logs/bot_error.log

[Install]
WantedBy=multi-user.target
EOF
```

### 5.2 Abilita e Avvia Service

```bash
# Crea directory logs
mkdir -p ~/AurumBotX-v4/logs

# Reload systemd
sudo systemctl daemon-reload

# Enable autostart
sudo systemctl enable aurumbot

# Start service
sudo systemctl start aurumbot

# Check status
sudo systemctl status aurumbot
```

Dovresti vedere:

```
● aurumbot.service - AurumBotX Trading Bot
     Loaded: loaded
     Active: active (running)
```

---

## 📊 Step 6: Monitoring

### 6.1 Verifica Logs

```bash
# Tail live logs
tail -f ~/AurumBotX-v4/logs/bot.log

# Check errors
tail -f ~/AurumBotX-v4/logs/bot_error.log

# Systemd journal
sudo journalctl -u aurumbot -f
```

### 6.2 Monitoring Script

```bash
# Controlla stato bot
bash ~/AurumBotX-v4/scripts/monitor.sh

# Output atteso:
# ✅ Bot Status: RUNNING (PID: 12345)
# 📊 Cycles: 24 | Trades: 8 | Win Rate: 75%
# 💰 Capital: €10,450 (+4.5%)
```

### 6.3 Cron Job per Report Automatici

```bash
# Aggiungi monitoring orario
crontab -e

# Aggiungi questa riga:
0 * * * * cd /home/ubuntu/AurumBotX-v4 && /home/ubuntu/AurumBotX-v4/venv/bin/python3 src/hourly_monitor.py >> logs/monitor.log 2>&1
```

---

## 🔧 Gestione Service

```bash
# Start
sudo systemctl start aurumbot

# Stop
sudo systemctl stop aurumbot

# Restart
sudo systemctl restart aurumbot

# Status
sudo systemctl status aurumbot

# Logs
sudo journalctl -u aurumbot -n 100
```

---

## 🐛 Troubleshooting

### Bot non si avvia

```bash
# Check service status
sudo systemctl status aurumbot

# Check logs
tail -100 ~/AurumBotX-v4/logs/bot_error.log

# Test manuale
cd ~/AurumBotX-v4
source venv/bin/activate
python3 src/wallet_runner_hyperliquid.py
```

### Errore API Key

```bash
# Verifica .env
cat ~/AurumBotX-v4/.env

# Riconfigura
cd ~/AurumBotX-v4
nano .env  # Modifica OPENAI_API_KEY
sudo systemctl restart aurumbot
```

### VM si riavvia

Il service si riavvia automaticamente grazie a `systemd`:

```bash
# Verifica autostart
sudo systemctl is-enabled aurumbot  # Deve dire "enabled"
```

---

## 🎯 Checklist Finale

- [ ] VM Oracle Cloud creata (Always Free tier)
- [ ] SSH funzionante
- [ ] Python 3.11 installato
- [ ] Repository clonato
- [ ] Dipendenze installate
- [ ] API keys configurate
- [ ] Systemd service attivo
- [ ] Autostart abilitato
- [ ] Monitoring funzionante
- [ ] Logs verificati

---

## 📈 Performance Attese

| Metrica | Target | Monitoraggio |
|---------|--------|--------------|
| Uptime | 99.9% | `systemctl status` |
| Cicli/giorno | 24 | `monitor.sh` |
| Trade/giorno | 4-8 | `state.json` |
| Win Rate | 70%+ | `monitor.sh` |
| ROI/mese | +20-40% | `state.json` |

---

## 🆘 Supporto

- GitHub Issues: https://github.com/Cryptomalo/AurumBotX-v4/issues
- Oracle Cloud Docs: https://docs.oracle.com/en-us/iaas/

---

**Made with ❤️ by Cryptomalo**
