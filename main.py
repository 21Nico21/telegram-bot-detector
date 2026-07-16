
# CELLA 3: BOT TELEGRAM (SENTENZA DIRETTA + PUNTEGGIO E SINTOMI)

import asyncio
import nest_asyncio
import json
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai
from google.genai import types

nest_asyncio.apply()

# ----------------- CONFIGURAZIONE -----------------
TOKEN_TELEGRAM = "8900344501:AAG_zoxZIAFlCpzOhmwdfdPRuJqfdgmJzSk"
API_KEY_GEMINI = "AIzaSyAHagwQcX2x7Y0i7vOKYcAWW3H1Id745uA"
# --------------------------------------------------

client = genai.Client(api_key=API_KEY_GEMINI)

def carica_prompt_base(filepath="definizione_bot.txt"):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Errore: File definizione_bot.txt non trovato."

def analizza_cronologia(lista_messaggi):
    prompt_base = carica_prompt_base()
    if "Errore" in prompt_base:
        return {"errore": prompt_base}
    
    cronologia_formattata = ""
    for i, msg in enumerate(lista_messaggi, 1):
        cronologia_formattata += f"Messaggio {i} (inviato da {msg['autore']}): \"{msg['testo']}\"\n"

    prompt_finale = f"""{prompt_base}

Ecco gli ultimi 10 messaggi estratti dal gruppo:
{cronologia_formattata}

In base alla definizione di BOT fornita, stabilisci quale utente si è comportato PIÙ da BOT.
Devi scegliere obbligatoriamente il peggiore tra i nomi presenti nella lista dei messaggi.

Restituisci ESCLUSIVAMENTE un JSON valido con questa esatta struttura:
{{
  "utente_peggiore": "Nome esatto dell'utente",
  "bot_score": numero_da_0_a_100,
  "categorie": ["TEMA_RILEVATO_1", "TEMA_RILEVATO_2"]
}}
"""
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_finale,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1
            )
        )
        return json.loads(response.text)
    except Exception as e:
        return {"errore": str(e)}

async def comando_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Pronto ad analizzare. Digita /detector nel gruppo per emettere la sentenza!"
    )

# Dizionario globale per salvare in RAM gli ultimi messaggi
cronologia_chat = {}

async def traccia_messaggi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Salva in memoria gli ultimi 10 messaggi."""
    if not update.message or not update.message.text:
        return
    
    if update.message.text.startswith('/'):
        return

    chat_id = update.message.chat_id
    autore = update.message.from_user.first_name
    testo = update.message.text

    if chat_id not in cronologia_chat:
        cronologia_chat[chat_id] = []

    cronologia_chat[chat_id].append({"autore": autore, "testo": testo})

    if len(cronologia_chat[chat_id]) > 10:
        cronologia_chat[chat_id].pop(0)

async def analizza_cronologia_comando(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    
    if chat_id not in cronologia_chat or len(cronologia_chat[chat_id]) == 0:
        await update.message.reply_text("❌ Nessun messaggio recente da analizzare.")
        return

    messaggio_attesa = await update.message.reply_text("⏳ Analisi in corso...")

    lista_da_analizzare = cronologia_chat[chat_id]
    dati = analizza_cronologia(lista_da_analizzare)

    if "errore" in dati or "utente_peggiore" not in dati:
        await messaggio_attesa.edit_text("❌ Impossibile completare l'analisi.")
        return

    # Estrazione dati
    utente_peggiore = dati["utente_peggiore"]
    bot_score = dati.get("bot_score", 0)
    categorie_list = dati.get("categorie", [])
    sintomi = ", ".join(categorie_list) if categorie_list else "Nessuno in particolare"

    # Nuova formattazione pulita e diretta
    testo_risposta = (
        f"<b>{utente_peggiore}</b> è proprio un BOT! 🤖\n\n"
        f"▪️ <b>Punteggio:</b> {bot_score}/100\n"
        f"▪️ <b>Sintomi:</b> {sintomi}"
    )

    await messaggio_attesa.edit_text(testo_risposta, parse_mode='HTML')

# Avvio applicazione
async def main():
    app = Application.builder().token(TOKEN_TELEGRAM).build()
    
    app.add_handler(CommandHandler("start", comando_start))
    app.add_handler(CommandHandler("detector", analizza_cronologia_comando))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, traccia_messaggi))
    
    print("🤖 BOT ONLINE (Sentenza dettagliata attiva!)")
    await app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    asyncio.run(main())
