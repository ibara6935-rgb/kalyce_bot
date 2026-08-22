import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Configuration
TOKEN ="8969625114:AAGCglmq9L_Qa24AvftRdtkl7YeRXdyRB4w"

# Activer les logs
logging.basicConfig(level=logging.INFO)

# Message d'accueil avec avertissement légal
DISCLAIMER = """
⚠️ *Avertissement légal*

Ce bot est fourni "en l'état", sans garantie d'aucune sorte.
L'utilisation de ce bot est à vos propres risques.
En l'utilisant, vous acceptez que le créateur ne puisse être tenu responsable
en cas de perte financière, de vol, ou de tout autre dommage.
"""

# Commande /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"🤖 *Bot Kalyce - Vente USDT*\n\n{DISCLAIMER}\n\n"
        "Commandes disponibles :\n"
        "/invoice [montant] - Créer une facture\n"
        "/status - Voir ton solde\n"
        "/help - Aide",
        parse_mode="Markdown"
    )

# Commande /invoice (simplifiée pour l'instant)
async def create_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        montant = context.args[0]
        await update.message.reply_text(
            f"💰 *Facture USDT créée !*\n\n"
            f"Montant : {montant} USDT\n"
            f"Lien : [Clique ici pour payer](https://t.me/CryptoBot)\n\n"
            f"Envoie ce lien à ton client.",
            parse_mode="Markdown"
        )
    except:
        await update.message.reply_text("Utilisation : /invoice [montant]")

# Commande /status
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📊 Solde USDT : À connecter avec CryptoBot API.")

# Commande /help
async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🆘 *Aide*\n\n"
        "/invoice [montant] - Créer une facture\n"
        "/status - Voir ton solde USDT\n"
        "/help - Cette aide",
        parse_mode="Markdown"
    )

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help))
    app.add_handler(CommandHandler("invoice", create_invoice))
    app.add_handler(CommandHandler("status", status))

    print("🤖 Bot Kalyce lancé avec succès !")
    app.run_polling()

if __name__ == "__main__":
    main() 
