import datetime,asyncio
import schedule
import time
from telegram import *
from telegram.ext import *

from models import ChatAlert  
from configs import *
from helpers import *

token_price_manager = TokenPriceManager("resources/output.json")
app = ApplicationBuilder().token(config["TOKEN"]).build()


async def check_and_notify():
    now = datetime.datetime.now()
    alerts_to_notify = []

    for alert in ChatAlert.select():
        if not alert.symbols:
            continue
        
        
        if alert.send_hour is not None:
            if is_exact_shamsi_time(alert) and alert.is_due_to_send():
                alerts_to_notify.append((alert.chat_id, alert.symbols))
                alert.last_sent = now
                alert.save()

        elif alert.last_sent is None:
            alerts_to_notify.append((alert.chat_id, alert.symbols))
            alert.last_sent = now
            alert.save()

        else:
            elapsed_minutes = (now - alert.last_sent).total_seconds() / 60
            if elapsed_minutes >= alert.interval_minutes:
                alerts_to_notify.append((alert.chat_id, alert.symbols))
                alert.last_sent = now
                alert.save()

    for chat_id, symbols in alerts_to_notify:
        messages = generate_alert_text(symbols ,token_price_manager)
        try:
            await app.bot.send_message(chat_id=chat_id, text=messages ,parse_mode="HTML")
        except (error.Forbidden ,error.BadRequest) as e:
            try:
                alert = ChatAlert.get(ChatAlert.chat_id == chat_id)
                alert.symbols = []
                alert.save()
            except ChatAlert.DoesNotExist:
                pass

        except Exception as e:
            continue

    return True
def run_async_task():
    asyncio.run(check_and_notify())


schedule.every(1).minutes.do(run_async_task)

if __name__ == "__main__":
    while True:
        
        schedule.run_pending()
        time.sleep(1)
