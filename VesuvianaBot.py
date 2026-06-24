"""
Bot Telegram per monitorare comunicazioni EAV, riassumerle con un LLM e inviare
aggiornamenti (testo e screenshot) su orari/avvisi ferroviari.
"""
import requests
from bs4 import BeautifulSoup
from datetime import datetime, date
import re
from typing import List, Dict
from telegram import Bot, Update
from telegram.ext import Application, ApplicationBuilder, CommandHandler, ContextTypes
from telegram.error import TelegramError
from dotenv import load_dotenv
import os
import httpx
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from playwright.async_api import async_playwright
import tempfile
import asyncio  # Sleep per attendere il rendering completo delle pagine

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
MODEL = "deepseek-chat"

EXCLUDED_KEYWORDS = ["Sarno", "Poggiomarino", "Baiano", "Acerra", "Nola", "Scafati", "Ottaviano", "Pomigliano",
                     "Piedimonte", "Matese", "Cumana"]
#INCLUDED_KEYWORDS = ["Sorrento", "Castellammare", "Vico Equense", "Sant'Agnello", "Meta", "Piano di Sorrento", "Pompei Scavi", "Ercolano Scavi", "Torre del Greco", "Torre Annunziata"]

BASE_URL = "https://www.eavsrl.it/infomobilita-ferrovia/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; DailyLLMAgent/1.0)"
}

MESI_IT = {
    "GEN": 1, "FEB": 2, "MAR": 3, "APR": 4,
    "MAG": 5, "GIU": 6, "LUG": 7, "AGO": 8,
    "SET": 9, "OTT": 10, "NOV": 11, "DIC": 12
}

SYSTEM_PROMPT = """Sei un assistente che riassume comunicazioni ufficiali di informazioni sulla mobilità ferroviaria. 
Non aggiungere interpretazioni, non dare consigli, non inventare informazioni."""

USER_PROMPT_TEMPLATE = """Ti fornisco una o più comunicazioni di informazioni sulla mobilità ferroviaria.
Produci un riepilogo sintetico per un messaggio Telegram.

Regole:
- ogni punto deve essere abbastanza breve
- se più comunicazioni parlano della stessa linea, accorpale
- non ripetere la data se è sempre la stessa
- se non ci sono disservizi rilevanti, scrivi: "Nessuna criticità rilevante segnalata."

Testo:
<<<
{INPUT}
>>>"""

async def take_screenshot(url: str, alilauro: bool = False, filename_prefix: str = "screenshot") -> Optional[str]:
    """
    Cattura uno screenshot della pagina o di un elemento specifico e lo salva in un file temporaneo.

    Args:
        url: URL da aprire in Playwright.
        alilauro: Se True, rimuove il popup e salva solo la tabella delle partenze.
        filename_prefix: Prefisso per il nome del file temporaneo (solo indicativo).

    Returns:
        Percorso del file temporaneo creato oppure None in caso di errore.
    """
    async def safe_click(description: str, *, selector: Optional[str] = None, role_name: Optional[str] = None) -> None:
        """
        Prova a cliccare un elemento senza interrompere il flusso se non disponibile.
        """
        try:
            locator = None
            if selector:
                locator = page.locator(selector).first
            elif role_name:
                locator = page.get_by_role("button", name=role_name).first

            if locator is None:
                return

            await locator.wait_for(state="visible", timeout=3000)

            try:
                await locator.scroll_into_view_if_needed(timeout=1000)
            except Exception:
                pass

            try:
                await locator.click(timeout=3000)
            except Exception:
                try:
                    await locator.click(timeout=1000, force=True)
                except Exception:
                    await locator.evaluate("(element) => element.click()")
        except Exception as click_error:
            print(f"Skip click '{description}': {click_error}")

    async def remove_elements(selector: str) -> None:
        """
        Rimuove eventuali elementi che possono coprire il contenuto utile nello screenshot.
        """
        try:
            await page.locator(selector).evaluate_all(
                """elements => {
                    for (const element of elements) {
                        element.remove();
                    }
                }"""
            )
        except Exception as remove_error:
            print(f"Skip remove '{selector}': {remove_error}")

    async def hide_elements(selector: str) -> None:
        """
        Nasconde elementi persistenti tramite CSS, utile se vengono reinseriti dinamicamente.
        """
        try:
            await page.add_style_tag(content=f"{selector} {{ display: none !important; visibility: hidden !important; }}")
        except Exception as hide_error:
            print(f"Skip hide '{selector}': {hide_error}")

    temp_file = None
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.goto(url, wait_until="networkidle")
            # Give the page a moment to fully render, especially if there are dynamic elements
            await asyncio.sleep(2) 
            
            temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            if alilauro:
                await safe_click(
                    "close advert",
                    selector="img.sgpb-popup-close-button-2"
                )
                await remove_elements("div.sgpb-popup-overlay, div.sgpb-popup-dialog-main-div-wrapper")
                await safe_click(
                    "close help window",
                    selector="body > div.ahw-wrap.is-open > div.ahw-panel > div.ahw-top > button"
                )
                await safe_click("accept cookies", role_name="Accetta")
                await remove_elements("div.ahw-wrap.is-open")
                await remove_elements("section.iubenda-cs-container, div.iubenda-cs-overlay")
                await page.locator("#tt-arma").wait_for(state="visible", timeout=10000)

                await page.locator("#tt-arma").screenshot(path=temp_file.name) # we capture only the table of the departures

            else:
                await hide_elements("div.InfoSupplementare")
                await remove_elements("div.InfoSupplementare")
                await asyncio.sleep(0.5)
                await remove_elements("div.InfoSupplementare")
                await page.screenshot(path=temp_file.name, full_page=True)

            await browser.close()
            return temp_file.name
    except Exception as e:
        print(f"Error taking screenshot of {url}: {e}")
        if temp_file:
            os.remove(temp_file.name) # Clean up if file was created but error occurred
        return None
    finally:
        if temp_file and not temp_file.closed:
            temp_file.close()


async def send_telegram_message(text: str):
    """
    Invia un messaggio Telegram al chat_id configurato.

    Args:
        text: Testo da inviare (verrà troncato a 4000 caratteri).

    Raises:
        RuntimeError: Se la configurazione è incompleta o l'invio fallisce.
    """
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("CHAT_ID")

    if not token or not chat_id:
        raise RuntimeError("TELEGRAM_TOKEN o CHAT_ID non configurati")

    bot = Bot(token=token)

    try:
        await bot.send_message(
            chat_id=chat_id,
            text=text[:4000],
            disable_web_page_preview=True
        )
    except TelegramError as e:
        raise RuntimeError(f"Errore invio Telegram: {e}")


def parse_data_it(data_str: str) -> Optional[date]:
    """
    Converte una data italiana nel formato '20 GEN 2026' in un oggetto date.

    Args:
        data_str: Stringa contenente la data.

    Returns:
        Date convertita o None se il formato non è riconosciuto.
    """
    match = re.search(r"(\d{1,2})\s+([A-Z]{3})\s+(\d{4})", data_str.upper())
    if not match:
        return None

    giorno, mese_str, anno = match.groups()
    mese = MESI_IT.get(mese_str)
    if not mese:
        return None

    return date(int(anno), mese, int(giorno))


def collect_infomobilita_oggi(max_pages: int = 10) -> List[Dict]:
    """
    Raccoglie tutte le notizie:
    - del giorno corrente
    - di tipo 'Infomobilità Ferrovia'
    - di tipo 'Linee Vesuviane - ...'
    Naviga automaticamente la paginazione e il link "leggi di più".

    Args:
        max_pages: Numero massimo di pagine da scansionare.

    Returns:
        Lista di dizionari con titolo, data, testo e URL della notizia.
    """
    oggi = date.today()
    risultati = []

    for page in range(1, max_pages + 1):
        print(f"Navigo pagina {page}")
        url = BASE_URL if page == 1 else f"{BASE_URL}page/{page}/"

        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        # Cerca gli articoli di notizie reali, che sono dentro un contenitore
        # più grande che è anch'esso un <article>
        container = soup.find("div", class_="card-columns")
        if not container:
            # Fallback se la struttura cambia
            container = soup

        articoli = container.find_all("article", recursive=False)

        if not articoli:
            break

        stop_scansione = False

        for art in articoli:
            # Trova il link "Leggi di più"
            read_more_link = art.find("a", class_="read-more")
            article_url = read_more_link["href"] if read_more_link else None

            titolo_tag = art.find("h4", class_="card-title")
            titolo_txt = titolo_tag.get_text(strip=True) if titolo_tag else ""

            # Estrazione data
            data_notizia = parse_data_it(art.get_text(strip=True))
            if not data_notizia:
                continue

            # Se la notizia è più vecchia di oggi → stop totale
            if data_notizia < oggi:
                print("Trovata data non di oggi. Mi fermo")
                stop_scansione = True
                break

            # Estrai il testo: prima quello completo dalla pagina dell'articolo,
            # poi come fallback il riassunto.
            testo = ""
            if article_url:
                try:
                    print(f"Navigo articolo: {article_url}")
                    art_resp = requests.get(article_url, headers=HEADERS, timeout=10)
                    art_resp.raise_for_status()
                    art_soup = BeautifulSoup(art_resp.text, "html.parser")
                    content = art_soup.find("section", class_="entry-content")
                    if content:
                        testo = content.get_text(separator=" ", strip=True)
                except requests.RequestException as e:
                    print(f"Errore nel leggere l'articolo {article_url}: {e}")

            # Se non è stato possibile leggere il testo completo, usa il testo del wrapper
            if not testo:
                testo = art.get_text(separator=" ", strip=True)

            # Filtro per parole chiave
            text_lower = testo.lower()
            has_excluded = any(keyword.lower() in text_lower for keyword in EXCLUDED_KEYWORDS)
            #has_included = any(keyword.lower() in text_lower for keyword in INCLUDED_KEYWORDS)

            if has_excluded:  #and not has_included:
                print(f"Testo '{text_lower[:100]}...' contiene keyword esclusa e non inclusa. Scarto.")
                continue

            # Filtro categorie
            if (
                    "infomobilità ferrovia" in text_lower
                    or "linee vesuviane" in text_lower
            ):
                risultati.append({
                    "titolo": titolo_txt,
                    "data": data_notizia.isoformat(),
                    "testo": testo,
                    "url": article_url
                })

        if stop_scansione:
            break

    return risultati


def build_llm_input(notizie: list[dict]) -> str:
    """
    Costruisce il testo da fornire al modello LLM a partire dalle notizie raccolte.

    Args:
        notizie: Lista di notizie normalizzate.

    Returns:
        Stringa pronta per il prompt utente dell'LLM.
    """
    blocchi = []

    for i, n in enumerate(notizie, start=1):
        blocchi.append(
            f"""
            NOTIZIA {i}
            Titolo: {n.get("titolo")}
            Data: {n.get("data")}
            Testo:
            {n.get("testo")}
            """
        )

    return "\n".join(blocchi)


async def deepseek_chat(system_prompt: str, user_prompt: str) -> str:
    """
    Invoca l'API DeepSeek con prompt di sistema e utente.

    Args:
        system_prompt: Prompt di sistema.
        user_prompt: Prompt utente con le notizie formattate.

    Returns:
        Risposta testuale del modello.
    """
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY non configurata")

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.2,
        "max_tokens": 500
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            DEEPSEEK_API_URL,
            headers=headers,
            json=payload
        )

    if response.status_code != 200:
        raise RuntimeError(
            f"Errore DeepSeek {response.status_code}: {response.text}"
        )

    data = response.json()

    return data["choices"][0]["message"]["content"].strip()


async def summarize_with_llm(raw_text: str) -> str:
    """
    Genera un riepilogo LLM a partire dal testo grezzo.

    Args:
        raw_text: Testo delle notizie aggregate.

    Returns:
        Riassunto sintetico pronto per l'invio Telegram.
    """
    user_prompt = USER_PROMPT_TEMPLATE.format(INPUT=raw_text)
    print("User prompt:")
    print(user_prompt)
    return await deepseek_chat(SYSTEM_PROMPT, user_prompt)


async def run_update():
    """
    Flusso principale: raccoglie notizie, genera sintesi LLM e invia il messaggio Telegram.
    """
    print("=== Avvio raccolta Infomobilità EAV ===")

    try:
        notizie = collect_infomobilita_oggi()

        if not notizie:
            msg = "Nessuna comunicazione Infomobilità Ferrovia / Linee Vesuviane per oggi."
            await send_telegram_message(msg)
            print("Nessuna notizia trovata. Messaggio inviato.")
            return

        parti_messaggio = ["📢 Infomobilità EAV Linea Napoli Sorrento – Oggi\n"]

        for n in notizie:
            parti_messaggio.append(f"📅 {n['data']}")
            if n.get("titolo"):
                parti_messaggio.append(f"{n['titolo']}")
            parti_messaggio.append(n["testo"])
            if n.get("url"):
                parti_messaggio.append(n["url"])
            parti_messaggio.append("-" * 30)

        raw_input = build_llm_input(notizie)
        print("\n--- Input per LLM ---\n")
        print(raw_input)
        print("\n---------------------\n")
        riassunto = await summarize_with_llm(raw_input)

        final_msg = "📢 Infomobilità EAV - Linea Napoli - Sorrento – Sintesi\n\n" + riassunto
        await send_telegram_message(final_msg)

        print(f"Inviate {len(notizie)} notizie via Telegram.")

    except Exception as e:
        print("ERRORE durante l'esecuzione")
        print(type(e).__name__, str(e))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comando /start: conferma che il bot è attivo.
    """
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text="Bot avviato. Usa /update per recuperare le notizie.")


async def update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comando /update: avvia subito l'aggiornamento manuale.
    """
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Avvio aggiornamento...")
    await run_update()


async def post_init(application: Application):
    """
    Configura gli scheduler giornalieri dopo l'inizializzazione del bot.
    """
    scheduler = AsyncIOScheduler()
    scheduler.add_job(scheduled_morning, 'cron', hour=6, minute=15)
    scheduler.add_job(scheduled_morning2, 'cron', hour=7, minute=00)
    scheduler.add_job(scheduled_evening, 'cron', hour=17, minute=0)
    scheduler.start()

async def scheduled_morning():
    """
    Job mattutino: invia aggiornamento notizie e screenshot partenze Sorrento.
    """
    await run_update()
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("CHAT_ID")
    if not token or not chat_id:
        print("TELEGRAM_TOKEN o CHAT_ID non configurati per la funzione schedulata.")
        return
    bot = Bot(token=token)
    await send_teleindicatori_screenshot(bot, chat_id, station_id=62, train_type="P", station_name="Sorrento")

async def scheduled_morning2():
    """
    Job mattutino: invia aggiornamento notizie e screenshot Alilauro.
    """
    await run_update()
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("CHAT_ID")
    if not token or not chat_id:
        print("TELEGRAM_TOKEN o CHAT_ID non configurati per la funzione schedulata.")
        return
    bot = Bot(token=token)
    await send_alilauro_screenshot(bot, chat_id)

async def scheduled_evening():
    """
    Job serale: invia aggiornamento notizie e screenshot Napoli + Alilauro.
    """
    await run_update()
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("CHAT_ID")
    if not token or not chat_id:
        print("TELEGRAM_TOKEN o CHAT_ID non configurati per la funzione schedulata.")
        return
    bot = Bot(token=token)
    await send_teleindicatori_screenshot(bot, chat_id, station_id=59, train_type="A", station_name="Meta")
    await send_alilauro_screenshot(bot, chat_id)


async def send_alilauro_screenshot(bot: Bot,target_chat_id: str):
    """
    Genera e invia uno screenshot della tabella partenze Alilauro.

    Args:
        bot: Istanza Bot già inizializzata.
        target_chat_id: Chat ID destinatario.
    """
    await bot.send_message(chat_id=target_chat_id,
                           text=f"Generazione screenshot Alilauro...")
    url = "https://www.alilauro.it/it/"
    screenshot_path = await take_screenshot(url, True)
    if screenshot_path:
        try:
            with open(screenshot_path, 'rb') as f:
                await bot.send_photo(chat_id=target_chat_id, photo=f)
        except Exception as e:
            await bot.send_message(chat_id=target_chat_id, text=f"Errore nell'invio della foto: {e}")
        finally:
            os.remove(screenshot_path)
    else:
        await bot.send_message(chat_id=target_chat_id, text="Errore nella creazione dello screenshot.")


async def send_teleindicatori_screenshot(bot: Bot, target_chat_id: str, station_id: int, train_type: str, station_name: str):
    """
    Genera e invia uno screenshot dei teleindicatori EAV per una stazione.

    Args:
        bot: Istanza Bot già inizializzata.
        target_chat_id: Chat ID destinatario.
        station_id: ID stazione EAV.
        train_type: "P" per partenze o "A" per arrivi.
        station_name: Nome leggibile della stazione.
    """
    arrival_departure_text = "partenze" if train_type == "P" else "arrivi"
    await bot.send_message(chat_id=target_chat_id, text=f"Generazione screenshot {arrival_departure_text} {station_name}...")
    url = f"https://orariotreni.eavsrl.it/teleindicatori/?stazione={station_id}&tipo={train_type}"
    screenshot_path = await take_screenshot(url)
    if screenshot_path:
        try:
            with open(screenshot_path, 'rb') as f:
                await bot.send_photo(chat_id=target_chat_id, photo=f)
        except Exception as e:
            await bot.send_message(chat_id=target_chat_id, text=f"Errore nell'invio della foto: {e}")
        finally:
            os.remove(screenshot_path)
    else:
        await bot.send_message(chat_id=target_chat_id, text="Errore nella creazione dello screenshot.")

async def alilauro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comando /alilauro: invia lo screenshot Alilauro nella chat corrente.
    """
    await send_alilauro_screenshot(context.bot, str(update.effective_chat.id))

async def psorrento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comando /psorrento: invia le partenze Sorrento nella chat corrente.
    """
    await send_teleindicatori_screenshot(context.bot, str(update.effective_chat.id), station_id=62, train_type="P", station_name="Sorrento")

async def asorrento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comando /asorrento: invia gli arrivi Sorrento nella chat corrente.
    """
    await send_teleindicatori_screenshot(context.bot, str(update.effective_chat.id), station_id=62, train_type="A", station_name="Sorrento")

async def pnapoli(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comando /pnapoli: invia le partenze Napoli nella chat corrente.
    """
    await send_teleindicatori_screenshot(context.bot, str(update.effective_chat.id), station_id=1, train_type="P", station_name="Napoli")

async def anapoli(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comando /anapoli: invia gli arrivi Napoli nella chat corrente.
    """
    await send_teleindicatori_screenshot(context.bot, str(update.effective_chat.id), station_id=1, train_type="A", station_name="Napoli")

def main():
    """
    Entry point: inizializza il bot, registra i comandi e avvia il polling.
    """
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_TOKEN non configurato")

    application = ApplicationBuilder().token(token).post_init(post_init).build()

    start_handler = CommandHandler('start', start)
    update_handler = CommandHandler('update', update)
    psorrento_handler = CommandHandler('psorrento', psorrento)
    asorrento_handler = CommandHandler('asorrento', asorrento)
    pnapoli_handler = CommandHandler('pnapoli', pnapoli)
    anapoli_handler = CommandHandler('anapoli', anapoli)
    alilauro_handler = CommandHandler('alilauro', alilauro)

    application.add_handler(start_handler)
    application.add_handler(update_handler)
    application.add_handler(psorrento_handler)
    application.add_handler(asorrento_handler)
    application.add_handler(pnapoli_handler)
    application.add_handler(anapoli_handler)
    application.add_handler(alilauro_handler)

    application.run_polling()


if __name__ == "__main__":
    main()
