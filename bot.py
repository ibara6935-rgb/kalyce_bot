import os
import logging
import sqlite3
import csv
import requests
import threading
from datetime import datetime
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ==================== SERVEUR WEB (KEEP-ALIVE) ====================
app = Flask(__name__)

@app.route('/')
def keep_alive():
    return "Bot Kalyce est en ligne !", 200

def run_web_server():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

thread = threading.Thread(target=run_web_server)
thread.start()

# ==================== CONFIGURATION ====================
TELEGRAM_TOKEN = "8733705622:AAF4d_qQ-v0URqk8OTJp7MP_ZfYsMr468Yg"
CRYPTOBOT_API_KEY = os.getenv("CRYPTOBOT_API_KEY", "en_attente")
ADMIN_ID = 7919997259

DB_NAME = "transactions.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_username TEXT,
            client_id INTEGER,
            montant REAL,
            date TEXT,
            statut TEXT,
            hash_transaction TEXT,
            invoice_id TEXT
        )
    """)
    conn.commit()
    conn.close()

def add_transaction(client_username, client_id, montant, invoice_id="", statut="en attente"):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    date_actuelle = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO transactions (client_username, client_id, montant, date, statut, invoice_id)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (client_username, client_id, montant, date_actuelle, statut, invoice_id))
    conn.commit()
    conn.close()

def get_history(limit=10):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, client_username, montant, date, statut
        FROM transactions
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_all_transactions():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, client_username, client_id, montant, date, statut, hash_transaction
        FROM transactions
        ORDER BY id DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows

def create_cryptobot_invoice(amount, description="Achat USDT"):
    url = "https://pay.crypt.bot/api/createInvoice"
    payload = {
        "asset": "USDT",
        "amount": str(amount),
        "description": description,
        "paid_btn_name": "openBot",
        "paid_btn_url": "https://t.me/kalyce_services_bot"
    }
    headers = {
        "Crypto-Pay-API-Token": CRYPTOBOT_API_KEY,
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json().get("result", {})
    except Exception as e:
        logging.error(f"Erreur CryptoBot: {e}")
        return None

logging.basicConfig(level=logging.INFO)

DISCLAIMER = """
⚠️ *Avertissement légal*
Ce bot est fourni "en l'état", sans garantie d'aucune sorte.
L'utilisation de ce bot est à vos propres risques.
"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"🤖 *Bot Kalyce - Vente USDT*\n\n{DISCLAIMER}\n\n"
        "Commandes :\n"
        "/invoice [montant] - Créer une facture\n"
        "/status - Solde\n"
        "/history - Historique (admin)\n"
        "/export - Exporter CSV (admin)\n"
        "/help - Aide",
        parse_mode="Markdown"
    )

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/invoice [montant] - Créer une facture\n"
        "/status - Solde\n"
        "/history - Historique (admin)\n"
        "/export - Exporter CSV (admin)",
        parse_mode="Markdown"
    )

async def create_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        montant = float(context.args[0])
        user = update.effective_user
        client_username = user.username or "pas de pseudo"
        client_id = user.id

        invoice_data = create_cryptobot_invoice(montant)
        if not invoice_data:
            await update.message.reply_text("❌ Erreur facture.")
            return

        pay_url = invoice_data.get("pay_url")
        add_transaction(client_username, client_id, montant, invoice_data.get("invoice_id"))

        await update.message.reply_text(
            f"💰 *Facture USDT*\n\nMontant : {montant} USDT\n"
            f"Lien : [Clique ici]({pay_url})",
            parse_mode="Markdown"
        )
    except:
        await update.message.reply_text("Utilisation : /invoice [montant]")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📊 Solde : connecte-toi à @CryptoBot.")

async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Admin uniquement.")
        return
    transactions = get_history(10)
    if not transactions:
        await update.message.reply_text("📭 Aucune transaction.")
        return
    message = "📋 *Historique*\n\n"
    for t in transactions:
        message += f"ID: {t[0]} | {t[1]} | {t[2]} USDT | {t[3]} | {t[4]}\n"
    await update.message.reply_text(message, parse_mode="Markdown")

async def export_transactions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Admin uniquement.")
        return
    transactions = get_all_transactions()
    if not transactions:
        await update.message.reply_text("📭 Aucune donnée.")
        return
    filename = f"transactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "Client", "ID Client", "Montant", "Date", "Statut", "Hash"])
        writer.writerows(transactions)
    with open(filename, "rb") as f:
        await update.message.reply_document(document=f, filename=filename)
    os.remove(filename)

def main():
    init_db()
    logging.info("✅ Base OK")
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help))
    app.add_handler(CommandHandler("invoice", create_invoice))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("history", history))
    app.add_handler(CommandHandler("export", export_transactions))
    logging.info("🤖 Bot Kalyce démarré")
    app.run_polling()

if __name__ == "__main__":
    main()
