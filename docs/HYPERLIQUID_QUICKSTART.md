# 🚀 AurumBotX v4.1 - Hyperliquid Quick Start

Guida rapida per avviare AurumBotX su Hyperliquid Testnet in 5 minuti.

---

## 📋 Prerequisiti

- Python 3.11+
- OpenAI API Key
- Connessione internet

---

## ⚡ Setup Rapido

### 1. Clone Repository

```bash
git clone https://github.com/Cryptomalo/AurumBotX-v4.git
cd AurumBotX-v4
```

### 2. Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows
```

### 3. Installa Dipendenze

```bash
pip install -r requirements.txt
```

### 4. Configura API Keys

```bash
# Crea file .env
cat > .env << 'EOF'
OPENAI_API_KEY=your_openai_api_key_here
EOF
```

### 5. Avvia Bot

```bash
python3 src/wallet_runner_hyperliquid.py
```

---

## 📊 Verifica Funzionamento

Il bot dovrebbe mostrare:

```
✅ Hyperliquid testnet connection OK
✅ OpenAI API connection OK
🔄 Starting trading cycle 1...
📊 Analyzing 6 crypto pairs...
```

---

## 🔧 Configurazione Avanzata

### Modifica Parametri

Edita `config/hyperliquid_testnet_10k.json`:

```json
{
  "capital": 10000,
  "cycle_interval_hours": 1,
  "confidence_threshold": 0.75,
  "take_profit_pct": 8.0,
  "stop_loss_pct": 5.0
}
```

### Monitoring

```bash
# Controlla stato bot
bash scripts/monitor.sh

# Monitoring automatico ogni ora
python3 src/hourly_monitor.py
```

---

## 🐛 Troubleshooting

### Bot non si avvia

```bash
# Verifica Python version
python3 --version  # Deve essere 3.11+

# Verifica dipendenze
pip list | grep -E "openai|hyperliquid"
```

### Errore API Key

```bash
# Verifica .env
cat .env

# Test OpenAI
python3 -c "import openai; print('OK')"
```

### Errore Hyperliquid

```bash
# Test connessione testnet
curl https://api.hyperliquid-testnet.xyz/info
```

---

## 📚 Prossimi Step

1. ✅ Bot funzionante in locale
2. 📖 Leggi [Oracle Cloud Deployment](ORACLE_CLOUD_DEPLOYMENT_GUIDE.md)
3. 🚀 Deploy 24/7 su cloud gratuito
4. 📊 Monitora performance

---

## 🆘 Supporto

- GitHub Issues: https://github.com/Cryptomalo/AurumBotX-v4/issues
- Documentation: [README.md](../README.md)

---

**Made with ❤️ by Cryptomalo**
