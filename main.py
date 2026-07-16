# ==============================================================================
# MAIN.PY - BOT TELEGRAM (VERSIONE AUTONOMA INTEGRATA - SENZA FILE ESTERNI)
# ==============================================================================

import asyncio
import json
import os
import threading
from http.server import SimpleHTTPRequestHandler, HTTPServer
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai
from google.genai import types

# ----------------- CONFIGURAZIONE CHIAVI -----------------
TOKEN_TELEGRAM = "8900344501:AAG_zoxZIAFlCpzOhmwdfdPRuJqfdgmJzSk"
API_KEY_GEMINI = "AIzaSyAHagwQcX2x7Y0i7vOKYcAWW3H1Id745uA"
# ---------------------------------------------------------

client = genai.Client(api_key=API_KEY_GEMINI)

# --- SERVER WEB FITTIZIO PER RENDER ---
def avvia_server_fittizio():
    """Avvia un server HTTP basilare per far credere a Render che sia un sito web."""
    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, format, *args):
            pass # Evita di intasare i log di Render
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Bot Online!")

    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), QuietHandler)
    print(f"🌍 Server web fittizio attivo sulla porta {port}")
    server.serve_forever()

# --- PROMPT INTEGRATO DIRETTAMENTE NEL CODICE ---
def carica_prompt_base():
    """Restituisce la definizione del bot direttamente in memoria."""
    return """
DEFINIZIONE DI BOT:
Colui che non argomenta, non discute e non risponde nel merito, ma procede a provocare con frasi che rientrano nella lista sottostante (o affini):

- tema del sonno ("ma dormi?", "ma non dormi mai?", oppure tutte le gif che richiamano la mancanza di sonno).
- tema delle favole ("belle ste fiabe", "te le inventi", ecc.), usato per denigrare quello che dici senza minimamente entrare nel merito.
- tema del rosicamento ("Malox", "rosica"... questa è troppo facile).
- tema del benaltrismo: invece di rispondere nel merito, si tirano fuori episodi che riguardano altre squadre per far deragliare la discussione. Classico: "eh ma voi avete rubato nel 1992". Il classico "e allora voi?".
- tema azione e reazione: si fa finta di non leggere il 90% delle informazioni e del ragionamento, per aggrapparsi solo alla conclusione più conveniente, bypassando completamente la logica della discussione.
- tema dell'ossessione: quando finiscono gli argomenti si passa direttamente al "sei ossessionato", "ti vive in testa", "pensi solo a quello".
- tema dellA Risata: Nessuna argomentazione, solo "😂😂😂", meme, applausini o faccine per far passare il messaggio come ridicolo senza spiegare il perché.

In sostanza, il bot non risponde a quello che gli viene detto: evita il merito della discussione e prova a spostarla su slogan, meme, provocazioni o frasi fatte.

In base a questa definizione, valuta il messaggio dell'utente.
"""

def analizza_cronologia(lista_messaggi):
    """Chiede a Gemini di identificare l'utente peggiore tra gli ultimi 10 messaggi."""
    prompt_base = carica_prompt_base()
    
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

# --- GESTIONE COMANDI TELEGRAM ---
async def comando_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Pronto ad analizzare. Digita /detector nel gruppo per emettere la sentenza!"
    )

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
    """Gestisce il comando /detector e restituisce solo la sentenza."""
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

    # Risposta diretta, mirata sul peggiore
    testo_risposta = (
        f"<b>{utente_peggiore}</b> è proprio un BOT! 🤖\n\n"
        f"▪️ <b>Punteggio:</b> {bot_score}/100\n"
        f"▪️ <b>Sintomi:</b> {sintomi}"
    )

    await messaggio_attesa.edit_text(testo_risposta, parse_mode='HTML')

# --- AVVIO DELL'APPLICAZIONE ---
def main():
    """Configura e avvia l'applicazione in modo sincrono."""
    # Avvia il server web fittizio in un thread separato così non blocca il bot
    threading.Thread(target=avvia_server_fittizio, daemon=True).start()

    # Creiamo l'applicazione di Telegram
    app = Application.builder().token(TOKEN_TELEGRAM).build()
    
    app.add_handler(CommandHandler("start", comando_start))
    app.add_handler(CommandHandler("detector", analizza_cronologia_comando))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, traccia_messaggi))
    
    print("🤖 BOT ONLINE!")
    
    # run_polling() si occupa autonomamente di gestire il loop
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()

