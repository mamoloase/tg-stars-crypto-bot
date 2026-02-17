from configs import *
from telegram import InlineKeyboardMarkup ,InlineKeyboardButton

KEYBOARD_PANELMAIN = InlineKeyboardMarkup([
    [InlineKeyboardButton(text = "بازار ها 🪙",callback_data = "markets")],
    [InlineKeyboardButton(text = "کیف پول من 💳",callback_data = "wallet")],
    [InlineKeyboardButton(text = "پشتیبانی 📞",callback_data = "support"),
     InlineKeyboardButton(text = "افزودن به گروه ➕",url = config["BOT_LINK"] + "/?startgroup=new")],
    [InlineKeyboardButton(text = "کانال اطلاع رسانی 📢",url = config["CHANNEL_LINK"])],
])

KEYBOARD_PANELBACK = InlineKeyboardMarkup([
    [InlineKeyboardButton(text = "بازگشت 🔙",callback_data = "MainMenu")],
])

KEYBOARD_DEOISIT_CURRENCIES = InlineKeyboardMarkup([
    [InlineKeyboardButton(text = "واریز استارز ⭐",callback_data = "deposit_stars"),
     InlineKeyboardButton(text = "واریز تومان 💸",callback_data = "deposit_tmn")],
    [InlineKeyboardButton(text = "🔙",callback_data = "wallet")],
])

KEYBOARD_WITHDRAWAL_CURRENCIES = InlineKeyboardMarkup([
    [InlineKeyboardButton(text = "برداشت استارز ⭐",callback_data = "withdrawal_stars"),
     InlineKeyboardButton(text = "برداشت تومان 💸",callback_data = "withdrawal_tmn")],
    [InlineKeyboardButton(text = "🔙",callback_data = "wallet")],
])
KEYBOARD_PANELWALLET = InlineKeyboardMarkup([
    [InlineKeyboardButton(text = "واریز 📥",callback_data = "wallet_deposit"),
     InlineKeyboardButton(text = "برداشت 📤",callback_data = "wallet_withdraw")],
    [InlineKeyboardButton(text = "🔙",callback_data = "MainMenu")],
])
KEYBOARD_SELL_IN_MARKET = InlineKeyboardMarkup([
    [InlineKeyboardButton(text = "شروع معامله ⭐",callback_data = "markets")],
])
KEYBOARD_ADDCHATSYMBOL = InlineKeyboardMarkup([
    [InlineKeyboardButton(text = "ارسال خودکار قیمت ⏰",callback_data = "add_chat_symbol") ],
    
    [InlineKeyboardButton(text = "کانال اطلاع رسانی 📢",url = config["CHANNEL_LINK"]),
     InlineKeyboardButton(text = "افزودن به گروه ➕",url = config["BOT_LINK"] + "/?startgroup=new")]
])

KEYBOARD_INLINECHAT = InlineKeyboardMarkup([
    [InlineKeyboardButton(text = "خرید و فروش استارز ⭐",url = config["BOT_LINK"] + "/?start") ],
    
    [InlineKeyboardButton(text = "کانال اطلاع رسانی 📢",url = config["CHANNEL_LINK"]),
     InlineKeyboardButton(text = "افزودن به گروه ➕",url = config["BOT_LINK"] + "/?startgroup=new")]
])


def contact_answer_keyboard(user_id):
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("پاسخ ✏️" ,callback_data=f"answer_{user_id}")]
        ]
    ) 
def redirect_contact_keyboard(text = "پاسخ ✏️"):
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(text ,callback_data=f"support")]
        ]
    ) 

def group_alerts_keyboard(alert):
    keyboard = []
    
    for symbol in alert.get_symbols():
        keyboard.append([InlineKeyboardButton(text=symbol, callback_data=f"NONE"),
            InlineKeyboardButton(text="❌", callback_data=f"delete_group_alert_{symbol}")])
    if not keyboard:
        keyboard.append([InlineKeyboardButton(text="هیچ ارزی انتخاب نشده است ❗", callback_data="NONE")])
    keyboard.append([InlineKeyboardButton(text="افزودن ارز ➕", callback_data=f"add_group_symbol"),
        InlineKeyboardButton(text="تغییر زمان ⏰", callback_data=f"change_group_alert_time")])
    keyboard.append([InlineKeyboardButton(text = f"ارسال در {alert.send_hour}:00" if alert.send_hour is not None else f"ارسال هر {alert.interval_minutes} دقیقه", callback_data=f"change_group_alert_time")])

    return InlineKeyboardMarkup(
        keyboard
    ) 

def markets_panel(merkets = []):
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("خرید استارز 🟢" ,callback_data=f"buy_stars"),
                InlineKeyboardButton("فروش استارز 🔴" ,callback_data=f"sell_stars")],
            [InlineKeyboardButton("🔙" ,callback_data=f"MainMenu")]
        ],
    ) 

def sell_currency_panel():
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("فروش  🔴" ,callback_data=f"get_sell_stars"),
                InlineKeyboardButton("افزایش موجودی 📥" ,callback_data=f"deposit_stars")],
            [InlineKeyboardButton("🔙" ,callback_data=f"markets")],
        ],

    ) 
def buy_currency_panel():
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("خرید  🟢" ,callback_data=f"get_buy_stars"),
                InlineKeyboardButton("افزایش موجودی 📥" ,callback_data=f"deposit_tmn")],
            [InlineKeyboardButton("🔙" ,callback_data=f"markets")],
        ],
    ) 
def deposit_panel():
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("افزایش موجودی 📥" ,callback_data=f"deposit_stars")],
            [InlineKeyboardButton("🔙" ,callback_data=f"markets")],
        ],

    ) 
def deposit_tmn_panel():
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("افزایش موجودی 📥" ,callback_data=f"deposit_tmn")],
            [InlineKeyboardButton("🔙" ,callback_data=f"markets")],
        ],

    ) 
def payment_stars_keyboard(amount):
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(f"پرداخت {amount} ⭐" ,pay=True)],
            [InlineKeyboardButton(f"🔙" ,callback_data="MainMenu")],
        ],

    ) 