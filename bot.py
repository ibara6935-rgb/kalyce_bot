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

# ==================== SERVEUR WEB (POUR RENDER) ====================
app = Flask(__name__)

@app.route('/')
def keep_alive():
    return "Bot is alive!", 200

def run_web_server():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# Lancer le serveur web dans un thread séparé
thread = threading.Thread(target=run_web_server)
thread.start()

# ==================== CONFIGURATION ====================
TELEGRAM_TOKEN = "8962252323:AAHHkgXUeMwOAGcLEg1Y02C4DitBHOY21Hw"
CRYPTOBOT_API_KEY = os.getenv("CRYPTOBOT_API_KEY", "en_attente")
ADMIN_ID = 7919997259  # Ton ID Telegram

if not TELEGRAM_TOKEN:
    raise ValueError("❌ TELEGRAM_TOKEN manquant")
if not CRYPTOBOT_API_KEY:
    raise ValueError("❌ CRYPTOBOT_API_KEY manquant")

# ==================== BASE DE DONNÉES ====================
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

# ==================== FONCTION CRYPTOBOT ====================
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

# ==================== COMMANDES TELEGRAM ====================
logging.basicConfig(level=logging.INFO)

DISCLAIMER = """
⚠️ *Avertissement légal*

Ce bot est fourni "en l'état", sans garantie d'aucune sorte.
L'utilisation de ce bot est à vos propres risques.
En l'utilisant, vous acceptez que le créateur ne puisse être tenu responsable
en cas de perte financière, de vol, ou de tout autre dommage.
"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"🤖 *Bot Kalyce - Vente USDT*\n\n{DISCLAIMER}\n\n"
        "Commandes disponibles :\n"
        "/invoice [montant] - Créer une facture USDT\n"
        "/status - Voir ton solde\n"
        "/history - Historique (admin)\n"
        "/export - Exporter CSV (admin)\n"
        "/help - Aide",
        parse_mode="Markdown"
    )

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🆘 *Aide*\n\n"
        "/invoice [montant] - Créer une facture\n"
        "/status - Voir ton solde USDT\n"
        "/history - Historique (admin)\n"
        "/export - Exporter CSV (admin)\n"
        "/help - Cette aide",
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
            await update.message.reply_text("❌ Erreur lors de la création de la facture. Vérifie la clé API.")
            return

        invoice_id = invoice_data.get("invoice_id")
        pay_url = invoice_data.get("pay_url")

        add_transaction(client_username, client_id, montant, invoice_id)

        await update.message.reply_text(
            f"💰 *Facture USDT créée !*\n\n"
            f"Montant : {montant} USDT\n"
            f"Lien de paiement : [Clique ici pour payer]({pay_url})\n\n"
            f"Envoie ce lien à ton client.",
            parse_mode="Markdown"
        )
    except (IndexError, ValueError):
        await update.message.reply_text("Utilisation : /invoice [montant] (ex: /invoice 100)")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📊 *Solde USDT*\n\n"
        "Cette fonctionnalité sera bientôt disponible. "
        "Pour l'instant, connecte-toi à @CryptoBot pour voir ton solde.",
        parse_mode="Markdown"
    )

async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ Commande réservée à l'administrateur.")
        return

    transactions = get_history(10)
    if not transactions:
        await update.message.reply_text("📭 Aucune transaction enregistrée.")
        return

    message = "📋 *Historique des transactions (10 dernières)*\n\n"
    for t in transactions:
        message += f"ID: {t[0]} | Client: {t[1]} | Montant: {t[2]} USDT | Date: {t[3]} | Statut: {t[4]}\n"

    await update.message.reply_text(message, parse_mode="Markdown")

async def export_transactions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ Commande réservée à l'administrateur.")
        return

    transactions = get_all_transactions()
    if not transactions:
        await update.message.reply_text("📭 Aucune transaction à exporter.")
        return

    filename = f"transactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "Client", "ID Client", "Montant", "Date", "Statut", "Hash"])
        writer.writerows(transactions)

    with open(filename, "rb") as f:
        await update.message.reply_document(document=f, filename=filename)

    os.remove(filename)

# ==================== LANCEMENT ====================
def main():
    init_db()
    logging.info("✅ Base de données initialisée.")

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("invoice", create_invoice))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("history", history))
    application.add_handler(CommandHandler("export", export_transactions))

    logging.info("🤖 Bot Kalyce lancé avec succès !")
    application.run_polling()

if __name__ == "__main__":
    main()
