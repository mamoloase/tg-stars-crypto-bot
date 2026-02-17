import re

from telegram import *
from telegram.ext import *

from configs import *
from helpers import *
from messages import *
from keyboards import *

from models import User as UserEntity ,ChatAlert as ChatAlertEntity ,Balance as BalanceEntity ,CardNumber as CardNumberEntity

token_price_manager = TokenPriceManager("resources/output.json")

async def EventContactHandler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user, created = UserEntity.get_or_create(user_id = update.message.from_user.id)

    if user.phone :
        return

    if update.message.contact.user_id != update.message.from_user.id:
        return await update.message.reply_text("<b>شماره متعلق به شما نیست ❗</b>" , parse_mode = "HTML")

    if not update.message.contact.phone_number.startswith("+98") and \
        not update.message.contact.phone_number.startswith("98"):
        return await update.message.reply_text("<b>متاسفانه به اکانت های خارج از ایران خدمات نمیدهیم ❗</b>" , parse_mode = "HTML")

    user.phone = update.message.contact.phone_number
    user.save()

    await update.message.reply_text(text = "<b>شماره شما با موفقیت تایید شد ✅</b>" , parse_mode = "HTML" ,reply_markup = ReplyKeyboardRemove())

    await update.message.reply_text(text = MESSAGE_PANELMAIN , parse_mode = "HTML" ,reply_markup = KEYBOARD_PANELMAIN)

async def EventMessageHandler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user, created = UserEntity.get_or_create(user_id = update.message.from_user.id)
    # if not user.phone:
    #     await update.message.reply_text(
    #         text = f"""<b>برای استفاده از ربات لطفا ابتدا شماره تلفن خود را تایید کنید ❗</b>""" ,
    #         parse_mode = "HTML",
    #         reply_markup = ReplyKeyboardMarkup(
    #             keyboard = [[KeyboardButton(request_contact = True ,text = "تایید شماره 🔑")]] ,
    #             resize_keyboard = True))
    #     return

    from_user = update.message.from_user
    if user.is_blocked and from_user.id not in config["OWNERS"]:
        return
    
    if update.message.text :
        text = update.message.text
        if text.lower().startswith("/start"):
            await update.message.reply_text(
                text = MESSAGE_PANELMAIN , 
                parse_mode = "HTML" ,
                reply_markup = KEYBOARD_PANELMAIN)
        
        if from_user.id in config["OWNERS"]:
            if text.startswith("/deposit") and len(text.split()) == 4:
                user_id = text.split()[1]
                amount = text.split()[2]
                currency = text.split()[3]
                BalanceEntity.increase_balance(int(user_id) ,currency.upper() ,amount=float(amount))
                return await update.message.reply_text("OK")

            if text.startswith("/withdrawal") and len(text.split()) == 4:
                user_id = text.split()[1]
                amount = text.split()[2]
                currency = text.split()[3]
                BalanceEntity.decrease_balance(int(user_id) ,currency.upper() ,amount=float(amount))
                return await update.message.reply_text("OK")
            if text.startswith("/balance") and len(text.split()) == 3:
                user_id = text.split()[1]
                currency = text.split()[2]
                balance= BalanceEntity.get_or_init_balance(int(user_id) ,currency.upper())
                return await update.message.reply_text(f"balance : {balance}")
            
            if text.startswith("/send") and len(text.split()) == 2 and update.message.reply_to_message:
                user_id = text.split()[1]
                await update.message.reply_to_message.copy(user_id)
                return await update.message.reply_text("OK")
            
            if text.startswith("/block") and len(text.split()) == 2 :
                user_id = text.split()[1]
                UserEntity.block_user(user_id)
                return await update.message.reply_text("OK")
            if text.startswith("/unblock") and len(text.split()) == 2 :
                user_id = text.split()[1]
                UserEntity.unblock_user(user_id)
                return await update.message.reply_text("OK")
            if text.startswith("/card") and len(text.split("\n")) == 3 :
                card = text.split("\n")[1]
                name = text.split("\n")[2]
                CardNumberEntity.set_first_card(name ,card)
                return await update.message.reply_text("OK")
            
        if text.startswith("/market"):
            result_lines = ["<b>بازارهای محبوب ✨</b>\n"]

            for token in token_price_manager.get_top_tokens():
                symbol = token.get("symbol", "BTC")
                symbol_name_en = token.get("english_name", "")
                symbol_name_fa = token.get("persian_name", "")
                info = token_price_manager.analyze_token(symbol, 1)

                if not info:
                    continue

                rial_price = round(info.get("total_rial", 0))
                usdt_price = round(info.get("total_usdt", 0), 2)
                change_percent = info.get("change_percent", 0)
                icon = "🟢" if change_percent > 0 else "🔴" 

                result_lines.append(f"<b>📊 {symbol_name_fa} | {symbol_name_en}</b>")
                result_lines.append(f"<pre>{icon} درصد تغییرات : {change_percent}% روزانه")
                result_lines.append(f"💵 قیمت تومانی : {format_price(rial_price)} تومان")
                result_lines.append(f"💰 قیمت دلاری : {format_price(usdt_price)} دلار</pre>\n")

            await update.message.reply_text(
                text = "\n".join(result_lines) ,
                reply_to_message_id = update.message.id,
                parse_mode = "HTML",
                reply_markup = KEYBOARD_ADDCHATSYMBOL)
            

        elif text.startswith("قیمت") or text.startswith("/"):
            text = convert_persian_digits(text)

            if text.startswith("قیمت"):
                pattern = r"قیمت\s*(?:(\d+(?:\.\d+)?)\s*)?([a-zA-Z\u0600-\u06FF\s]+)"
                match = re.match(pattern, text)
            else:
                pattern = r"/(?:(\d+(?:\.\d+)?))?([a-zA-Z\u0600-\u06FF]+)"
                match = re.match(pattern, text)
                
            if not match:
                return None

            amount_str, symbol = match.groups()
            amount = min(max(float(amount_str) if amount_str else 1.0, 0.00001), 1_000_000_000_000)

            response = generate_price_text(symbol=symbol, amount=amount, token_price_manager=token_price_manager)
            if not response:
                return

            await update.message.reply_text(
                text=response,
                reply_to_message_id=update.message.id,
                parse_mode="HTML"
            )

        elif text.startswith("تبدیل"):
            text = convert_persian_digits(text)

            pattern = r"تبدیل\s*(?:(\d+(?:\.\d+)?)\s*)?([\w\s\u0600-\u06FF]+)\s*به\s*([\w\s\u0600-\u06FF]+)"
            match = re.match(pattern, text)

            if not match:
                return

            amount_str, from_symbol, to_symbol = match.groups()
            amount = float(amount_str) if amount_str else 1.0

            amount = max(min(amount, 10_000_000_000), 0.00001)

            response = generate_convert_text(from_symbol ,to_symbol ,amount ,token_price_manager)

            await update.message.reply_text(
                text=response,
                reply_to_message_id=update.message.id,
                parse_mode="HTML"
            )
        else :
            text = convert_persian_digits(text)

            if user.step and user.step == "get_sell_stars":
                if not text.isnumeric():
                    return await update.message.reply_text(
                        text=MESSAGE_ERROR_INVALID_AMOUNT,
                        parse_mode="HTML" ,
                        reply_markup=KEYBOARD_PANELBACK)
                amount = int(text)
                if amount < 15:
                    return await update.message.reply_text(
                        text=MESSAGE_ERROR_INVALID_AMOUNT,
                        parse_mode="HTML" ,
                        reply_markup=KEYBOARD_PANELBACK)
                token = token_price_manager.search_token("stars")
                balance = BalanceEntity.get_or_init_balance(update.effective_user.id ,token["symbol"])
                
                if balance < amount:
                    return await update.message.reply_text(
                        text=MESSAGE_ERROR_BALANCE_NOT_ENOUGH_STARS
                            .replace("[BALANCE]" ,format_price(balance)),
                        parse_mode="HTML" ,
                        reply_markup=deposit_panel())
                
                info = token_price_manager.analyze_token(symbol = token["symbol"] ,amount = 1)
                
                adjusted_rial = info["total_rial"] * 0.85

                cashback = adjusted_rial * amount

                balance_stars = BalanceEntity.decrease_balance(from_user.id ,token["symbol"] ,amount)
                balance_tnm =BalanceEntity.increase_balance(from_user.id ,"TMN" ,cashback)
                
                user.step = ""
                user.save()
                
                await update.message.reply_text(
                        text=MESSAGE_SELL_STARS_COMPLETED
                            .replace("[AMOUNT]" ,format_price(amount))
                            .replace("[AMOUNT_TMN]" ,format_price(cashback))
                            .replace("[BALANCET]" ,format_price(balance_tnm))
                            .replace("[BALANCES]" ,format_price(balance_stars)),
                        parse_mode="HTML")
                return await update.message.reply_text(
                        text=MESSAGE_BACK_AFTER_TRADE,
                        parse_mode="HTML" ,reply_markup=KEYBOARD_PANELBACK)
            elif user.step and user.step == "support":
                user.step = ""
                user.save()

                await update.message.copy(config["CONTACT_CHATID"],
                    reply_markup = contact_answer_keyboard(from_user.id))
                
                return await update.message.reply_text(text=MESSAGE_SENT_TO_CONTACT,parse_mode="HTML" ,reply_markup=KEYBOARD_PANELBACK)
            elif user.step and user.step.startswith("answer") and from_user.id in config["OWNERS"]:
                user_id = int(user.step.split("_")[1])
                
                user.step = ""
                user.save()

                await context.bot.send_message(user_id,"پیام از طرف پشتیبانی 👇")

                await update.message.copy(user_id,
                    reply_markup = redirect_contact_keyboard())
                return await update.message.reply_text(text = MESSAGE_ANSWER_SENT,parse_mode="HTML" ,reply_markup=KEYBOARD_PANELBACK)

            elif user.step and user.step == "withdrawal_stars":
                if not text.isnumeric():
                    return await update.message.reply_text(
                        text=MESSAGE_ERROR_INVALID_AMOUNTSTARS_WITHDRAWAL,
                        parse_mode="HTML" ,
                        reply_markup=KEYBOARD_PANELBACK)
                amount = int(text)
                if amount < 50:
                    return await update.message.reply_text(
                        text=MESSAGE_ERROR_INVALID_AMOUNTSTARS_WITHDRAWAL,
                        parse_mode="HTML" ,
                        reply_markup=KEYBOARD_PANELBACK)
                token = token_price_manager.search_token("stars")
                balance = BalanceEntity.get_or_init_balance(update.effective_user.id ,token["symbol"])
                
                if balance < amount:
                    return await update.message.reply_text(
                        text=MESSAGE_ERROR_BALANCE_NOT_ENOUGH_STARS
                            .replace("[BALANCE]" ,format_price(balance)),
                        parse_mode="HTML" ,
                        reply_markup=deposit_panel())
                user.step = "get_username"
                user.update_metadata_key("count_s" ,amount)
                return await update.message.reply_text(
                        text=MESSAGE_ENTER_USERNAME_FOR_WITHDRAWAL,
                        parse_mode="HTML" ,
                        reply_markup=KEYBOARD_PANELBACK)
            elif user.step and user.step == "get_username":
                vals = user.get_metadata_dict()

                amount = vals.get("count_s" ,None)
                if not amount:
                    user.step = ""
                    user.save()
                    return
                
                balance = BalanceEntity.get_or_init_balance(update.effective_user.id ,"STARS")
                
                if balance < amount:
                    user.step = ""
                    user.save()
                    return await update.message.reply_text(
                        text=MESSAGE_ERROR_BALANCE_NOT_ENOUGH_STARS
                            .replace("[BALANCE]" ,format_price(balance)),
                        parse_mode="HTML" ,
                        reply_markup=deposit_panel())
                if not text.startswith("@"):
                    return await update.message.reply_text(
                        text=MESSAGE_ERROR_INVALID_USERNAME
                            .replace("[BALANCE]" ,format_price(balance)),
                        parse_mode="HTML" ,
                        reply_markup=KEYBOARD_PANELBACK)
                BalanceEntity.decrease_balance(from_user.id ,"STARS" ,amount)
                
                await context.bot.send_message(
                        chat_id = config["EXCHANGE_ADMIN"],
                        text=MESSAGE_WITHDRAWAL_STARS_ADMIN
                            .replace("[AMOUNT]" ,format_price(amount))
                            .replace("[USERID]" ,str(from_user.id))
                            .replace("[USERNAME]" ,text),
                        parse_mode="HTML")
                
                await update.message.reply_text(
                        text=MESSAGE_WITHDRAWAL_STARS_SUCCESS
                            .replace("[AMOUNT]" ,format_price(amount))
                            .replace("[USERNAME]" ,text),
                        parse_mode="HTML")
                return await update.message.reply_text(
                        text=MESSAGE_BACK_AFTER_WITHDRAWAL,
                        parse_mode="HTML",
                        reply_markup=KEYBOARD_PANELBACK)
                
            elif user.step and user.step == "withdrawal_tmn":
                if not text.isnumeric():
                    return await update.message.reply_text(
                        text=MESSAGE_ERROR_INVALID_AMOUNTTMN_WITHDRAWAL,
                        parse_mode="HTML" ,
                        reply_markup=KEYBOARD_PANELBACK)
                amount = int(text)
                if amount < 50000:
                    return await update.message.reply_text(
                        text=MESSAGE_ERROR_INVALID_AMOUNTTMN_WITHDRAWAL,
                        parse_mode="HTML" ,
                        reply_markup=KEYBOARD_PANELBACK)
                balance = BalanceEntity.get_or_init_balance(update.effective_user.id ,"TMN")
                
                if balance < amount:
                    return await update.message.reply_text(
                        text=MESSAGE_ERROR_BALANCE_NOT_ENOUGH_WITHDRAWAL_TMN
                            .replace("[BALANCE]" ,format_price(balance)),
                        parse_mode="HTML" ,
                        reply_markup=deposit_tmn_panel())
                user.step = "get_cardnumber"
                user.update_metadata_key("count_t" ,amount)
                return await update.message.reply_text(
                        text=MESSAGE_ENTER_CARDNUMBER_FOR_WITHDRAWAL,
                        parse_mode="HTML" ,
                        reply_markup=KEYBOARD_PANELBACK)
            
            elif user.step and user.step == "get_cardnumber":
                vals = user.get_metadata_dict()

                amount = vals.get("count_t" ,None)
                if not amount:
                    user.step = ""
                    user.save()
                    return
                
                balance = BalanceEntity.get_or_init_balance(update.effective_user.id ,"TMN")
                
                if balance < amount:
                    user.step = ""
                    user.save()
                    return await update.message.reply_text(
                        text=MESSAGE_ERROR_BALANCE_NOT_ENOUGH_WITHDRAWAL_TMN
                            .replace("[BALANCE]" ,format_price(balance)),
                        parse_mode="HTML" ,
                        reply_markup=deposit_tmn_panel())
               
                BalanceEntity.decrease_balance(from_user.id ,"TMN" ,amount)
                
                await context.bot.send_message(
                        chat_id = config["EXCHANGE_ADMIN"],
                        text=MESSAGE_WITHDRAWAL_TMN_ADMIN
                            .replace("[AMOUNT]" ,format_price(amount))
                            .replace("[USERID]" ,str(from_user.id))
                            .replace("[CARD]" ,text),
                        parse_mode="HTML")
                
                await update.message.reply_text(
                        text=MESSAGE_WITHDRAWAL_TMN_SUCCESS
                            .replace("[AMOUNT]" ,format_price(amount))
                            .replace("[CARD]" ,text),
                        parse_mode="HTML")
                return await update.message.reply_text(
                        text=MESSAGE_BACK_AFTER_WITHDRAWAL,
                        parse_mode="HTML",
                        reply_markup=KEYBOARD_PANELBACK)

            elif user.step and user.step == "get_buy_stars":
                if not text.isnumeric():
                    return await update.message.reply_text(
                        text=MESSAGE_ERROR_INVALID_AMOUNT,
                        parse_mode="HTML" ,
                        reply_markup=KEYBOARD_PANELBACK)
                amount = int(text)
                if amount < 15:
                    return await update.message.reply_text(
                        text=MESSAGE_ERROR_INVALID_AMOUNT,
                        parse_mode="HTML" ,
                        reply_markup=KEYBOARD_PANELBACK)
                
                token = token_price_manager.search_token("stars")
                info = token_price_manager.analyze_token(symbol = token["symbol"] ,amount = 1)
                adjusted_rial = info["total_rial"] * 1.03
                balance = BalanceEntity.get_or_init_balance(update.effective_user.id ,"TMN")
                
                pay_amount = amount * adjusted_rial
                
                if balance < pay_amount:
                    return await update.message.reply_text(
                        text=MESSAGE_ERROR_BALANCE_NOT_ENOUGH_TMN
                            .replace("[AMOUNT]" ,format_price(amount))
                            .replace("[AMOUNTT]" ,format_price(pay_amount))
                            .replace("[BALANCET]" ,format_price(balance)),
                        parse_mode="HTML" ,
                        reply_markup=deposit_tmn_panel())

                balance_stars = BalanceEntity.increase_balance(from_user.id ,token["symbol"] ,amount)
                balance_tnm =BalanceEntity.decrease_balance(from_user.id ,"TMN" ,pay_amount)
                
                user.step = ""
                user.save()
                
                await update.message.reply_text(
                        text=MESSAGE_BUY_STARS_COMPLETED
                            .replace("[AMOUNT]" ,format_price(amount))
                            .replace("[AMOUNT_TMN]" ,format_price(pay_amount))
                            .replace("[BALANCET]" ,format_price(balance_tnm))
                            .replace("[BALANCES]" ,format_price(balance_stars)),
                        parse_mode="HTML")
                return await update.message.reply_text(
                        text=MESSAGE_BACK_AFTER_TRADE,
                        parse_mode="HTML" ,reply_markup=KEYBOARD_PANELBACK)

            elif user.step and user.step == "deposit_stars":
                
                if not text.isnumeric():
                    return await update.message.reply_text(
                        text=MESSAGE_ERROR_INVALID_AMOUNT,
                        parse_mode="HTML" ,
                        reply_markup=KEYBOARD_PANELBACK)
                
                amount = int(text)
                if amount < 15:
                    return await update.message.reply_text(
                        text=MESSAGE_ERROR_INVALID_AMOUNT,
                        parse_mode="HTML" ,
                        reply_markup=KEYBOARD_PANELBACK)
                prices = [LabeledPrice(label="XTR", amount=amount)]

                await update.message.reply_invoice(
                    title = "افزایش موجودی حساب" ,
                    description = f"""افزایش موجودی حساب به تعداد : {amount} استارز ⭐
                    
در صورتی که از افزایش موجودی حساب خود اطمینان دارید بر روی دکمه پرداخت کلیک کنید 👇""" ,
                    currency = "XTR" ,
                    provider_token="",
                    prices = prices ,
                    payload = "deposit_wallet",
                    reply_markup= payment_stars_keyboard(amount=amount)
                )
                user.step = ""
                user.save()
            else :

                math_pattern = r"(?:(\d+(?:\.\d+)?)\s+)?([\w\u0600-\u06FF\s]+?)\s*([+-])\s*(?:(\d+(?:\.\d+)?)\s+)?([\w\u0600-\u06FF\s]+)"
                
                match = re.match(math_pattern, text)

                if match:
                    amount1_str, symbol1, operator, amount2_str, symbol2 = match.groups()
                    amount1 = float(amount1_str) if amount1_str else 1.0
                    amount2 = float(amount2_str) if amount2_str else 1.0

                    amount1 = min(max(amount1, 0.00001), 1_000_000_000)
                    amount2 = min(max(amount2, 0.00001), 1_000_000_000)
                    if operator not in ['+', '-']:
                        return
                    response = generate_operator_text(symbol1 ,symbol2 ,amount1 ,amount2 ,operator ,token_price_manager)
                    if response:
                        await update.message.reply_text(
                            text=response,
                            reply_to_message_id=update.message.id,
                            parse_mode="HTML"
                        )
                else :
                    pattern = r"(?:(\d+(?:\.\d+)?)\s+)?([\w\u0600-\u06FF]+)(?:\s+([\w\u0600-\u06FF]+))?"
                    match = re.match(pattern, text)

                    if match:
                        amount_str, first_symbol, second_symbol = match.groups()
                        amount = float(amount_str) if amount_str else 1.0
                        amount = min(max(amount, 0.00001), 1_000_000_000)

                        first_token = token_price_manager.search_token(first_symbol ,normaliza=False)
                        second_token = token_price_manager.search_token(second_symbol ,normaliza=False)


                        if not first_token or second_symbol and not second_token:
                            return

                        if second_symbol:
                            response = generate_convert_text(first_token['symbol'], second_token['symbol'], amount, token_price_manager)
                        else:
                            response = generate_price_text(symbol=first_symbol, amount=amount, token_price_manager=token_price_manager)

                        if response:
                            await update.message.reply_text(
                                text=response,
                                reply_to_message_id=update.message.id,
                                parse_mode="HTML"
                            )
            

    if update.message.photo:
        if not user.step or (user.step != "support" and user.step != "answer") :
            await update.message.copy(
                chat_id = config["EXCHANGE_ADMIN"],
                caption = f"<b>💸 واریز جدید توسط : <code>{from_user.id}</code></b>",
                parse_mode="HTML"
            )
            await update.message.reply_text(
                text = MESSAGE_WAIT_DEPOSIT_SENT,
                parse_mode="HTML",
                reply_markup=KEYBOARD_PANELBACK
            )

    if user.step and user.step == "support":
        user.step = ""
        user.save()

        await update.message.copy(config["CONTACT_CHATID"],
            reply_markup = contact_answer_keyboard(from_user.id))
        
        await update.message.reply_text(text=MESSAGE_SENT_TO_CONTACT,parse_mode="HTML" ,reply_markup=KEYBOARD_PANELBACK)
    
    if user.step and user.step.startswith("answer") and from_user.id in config["OWNERS"]:
        user_id = int(user.step.split("_")[1])
        
        user.step = ""
        user.save()

        await context.bot.send_message(user_id,"پیام از طرف پشتیبانی 👇")

        await update.message.copy(user_id,
            reply_markup = redirect_contact_keyboard())
        await update.message.reply_text(text = MESSAGE_ANSWER_SENT,parse_mode="HTML" ,reply_markup=KEYBOARD_PANELBACK)

async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.pre_checkout_query
    await query.answer(ok=True)

async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    payment = update.message.successful_payment
    total_amount = payment.total_amount
    token = token_price_manager.search_token("stars")

    balance = BalanceEntity.increase_balance(update.message.from_user.id ,token["symbol"] ,total_amount)
    await update.message.reply_text(
        text = MESSAGE_SUCCESS_DEPOSIT_STARS\
            .replace("[AMOUNT]" ,format_price(total_amount))\
            .replace("[BALANCE]" ,format_price(balance)),
        parse_mode="HTML")
    
    await update.message.reply_text(
        text = MESSAGE_GO_TO_MARKET,
        parse_mode="HTML",reply_markup=KEYBOARD_SELL_IN_MARKET)


async def EventCallbackHandler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    
    chat = update.effective_chat
    from_user = update.effective_user
    if chat.type in (constants.ChatType.GROUP, constants.ChatType.SUPERGROUP):
        admins = await chat.get_administrators()
        
        if not any(admin.user.id == from_user.id for admin in admins):
            return await update.callback_query.answer(MESSAGE_ERROR_NOT_ADMIN, show_alert=True)
        if not any(admin.user.id == config["BOT_ID"] for admin in admins):
            return await update.callback_query.answer(MESSAGE_ERROR_BOT_NOT_ADMIN, show_alert=True)
        
        if update.callback_query.data.startswith("delete_group_alert_"):
            chat_alert, created = ChatAlertEntity.get_or_create(chat_id=chat.id)
            symbol = update.callback_query.data.split("_")[-1].upper()

            if symbol not in chat_alert.symbols:
                return await update.callback_query.answer(MESSAGE_ERROR_CURRENCY_NOTFOUND, show_alert=True)
            chat_alert.remove_symbol(symbol)

            await update.callback_query.edit_message_reply_markup(
                reply_markup=group_alerts_keyboard(chat_alert))
            
        if update.callback_query.data.startswith("add_group_symbol"):
            chat_alert, created = ChatAlertEntity.get_or_create(chat_id=chat.id)
            
            if chat_alert.symbols and not chat_alert.premium:
                return await update.callback_query.answer(MESSAGE_ERROR_LIMIT_ADD_SYMBOL, show_alert=True)
            
            await update.callback_query.edit_message_text(
                text = MESSAGE_GROUP_GET_SYMBOL,
                parse_mode="HTML")
            
        if update.callback_query.data.startswith("change_group_alert_time"):
            
            await update.callback_query.edit_message_text(
                text = MESSAGE_SET_ALERT_TIME,
                parse_mode="HTML")
            
        if update.callback_query.data.startswith("add_chat_symbol"):

            chat_alert , created = ChatAlertEntity.get_or_create(chat_id = chat.id)
            
            await update.callback_query.edit_message_text(
                text = MESSAGE_GROUP_PANEL_SYMBOLS,
                parse_mode="HTML" ,
                reply_markup=group_alerts_keyboard(chat_alert))

    else :
        user, created = UserEntity.get_or_create(user_id = update.callback_query.from_user.id)
        
        # if not user.phone:
        #     return
        if update.callback_query.data.startswith("MainMenu"):

            if user.step:
                user.step = ""
                user.save()
            if update.callback_query.message.invoice:
                await update.callback_query.message.reply_text(
                    text = MESSAGE_PANELMAIN ,
                    parse_mode = "HTML",
                    reply_markup= KEYBOARD_PANELMAIN)

            else :await update.callback_query.edit_message_text(
                text = MESSAGE_PANELMAIN ,
                parse_mode = "HTML",
                reply_markup= KEYBOARD_PANELMAIN)
              

        if update.callback_query.data == "wallet_deposit":
            await update.callback_query.edit_message_reply_markup(
                reply_markup = KEYBOARD_DEOISIT_CURRENCIES)
        if update.callback_query.data == "wallet_withdraw":
            await update.callback_query.edit_message_reply_markup(
                reply_markup = KEYBOARD_WITHDRAWAL_CURRENCIES)

        if update.callback_query.data == "wallet":
            balance_t = BalanceEntity.get_or_init_balance(from_user.id ,"TMN")
            balance_s = BalanceEntity.get_or_init_balance(from_user.id ,"STARS")

            await update.callback_query.edit_message_text(
                MESSAGE_WALLET
                    .replace("[BALANCET]" ,format_price(balance_t))
                    .replace("[BALANCES]" ,format_price(balance_s)),
                parse_mode = "HTML" ,
                link_preview_options = LinkPreviewOptions(is_disabled = True),
                reply_markup = KEYBOARD_PANELWALLET)

        if update.callback_query.data.startswith("profile"):

            await update.callback_query.edit_message_text(
                MESSAGE_PROFILE,
                parse_mode = "HTML" ,
                link_preview_options = LinkPreviewOptions(is_disabled = True),
                reply_markup = KEYBOARD_PANELBACK)
            
        if update.callback_query.data.startswith("markets"):
            user.step = ""
            user.save()
            
            await update.callback_query.edit_message_text(
                MESSAGE_MARKETS,
                parse_mode = "HTML" ,
                link_preview_options = LinkPreviewOptions(is_disabled = True),
                reply_markup = markets_panel())
            
        if update.callback_query.data.startswith("deposit_stars"):
            user.step = update.callback_query.data
            user.save()

            await update.callback_query.edit_message_text(
                MESSAGE_GETDEPOSITSTARS,
                parse_mode = "HTML" ,
                link_preview_options = LinkPreviewOptions(is_disabled = True),
                reply_markup = KEYBOARD_PANELBACK)
            
        if update.callback_query.data.startswith("get_sell_stars"):
            user.step = update.callback_query.data
            user.save()

            await update.callback_query.edit_message_text(
                MESSAGE_GET_COUNT_STARS_FOR_SELL,
                parse_mode = "HTML" ,
                link_preview_options = LinkPreviewOptions(is_disabled = True),
                reply_markup = KEYBOARD_PANELBACK)
        if update.callback_query.data.startswith("get_buy_stars"):
            user.step = update.callback_query.data
            user.save()

            await update.callback_query.edit_message_text(
                MESSAGE_GET_COUNT_STARS_FOR_BUY,
                parse_mode = "HTML" ,
                link_preview_options = LinkPreviewOptions(is_disabled = True),
                reply_markup = KEYBOARD_PANELBACK)
        
        if update.callback_query.data.startswith("sell_stars"):
            token = token_price_manager.search_token("stars")
            info = token_price_manager.analyze_token(symbol = token["symbol"] ,amount = 1)
            
            balance = BalanceEntity.get_or_init_balance(update.effective_user.id ,token["symbol"])
            adjusted_rial = info["total_rial"] * 0.85
            adjusted_usdt = info["total_usdt"] * 0.85

            text = get_sell_currency_message(
                token["persian_name"] ,balance ,adjusted_rial,adjusted_usdt)
            
            await update.callback_query.edit_message_text(
                text,
                parse_mode = "HTML" ,
                link_preview_options = LinkPreviewOptions(is_disabled = True),
                reply_markup = sell_currency_panel())
        
        if update.callback_query.data.startswith("buy_stars"):
            token = token_price_manager.search_token("stars")
            info = token_price_manager.analyze_token(symbol = token["symbol"] ,amount = 1)
            
            balance = BalanceEntity.get_or_init_balance(update.effective_user.id ,"TMN")

            adjusted_rial = info["total_rial"] * 1.03
            adjusted_usdt = info["total_usdt"] * 1.03

            text = get_buy_currency_message(
                token["persian_name"] ,balance ,adjusted_rial,adjusted_usdt)
            
            await update.callback_query.edit_message_text(
                text,
                parse_mode = "HTML" ,
                link_preview_options = LinkPreviewOptions(is_disabled = True),
                reply_markup = buy_currency_panel())
        
        if update.callback_query.data.startswith("withdrawal_stars"):
            user.step = update.callback_query.data
            user.save()

            await update.callback_query.edit_message_text(
                MESSAGE_GET_STARS_FOR_WITHDRAWAL,
                parse_mode = "HTML" ,
                link_preview_options = LinkPreviewOptions(is_disabled = True),
                reply_markup = KEYBOARD_PANELBACK)

        if update.callback_query.data.startswith("withdrawal_tmn"):
            user.step = update.callback_query.data
            user.save()

            await update.callback_query.edit_message_text(
                MESSAGE_GET_TMN_FOR_WITHDRAWAL,
                parse_mode = "HTML" ,
                link_preview_options = LinkPreviewOptions(is_disabled = True),
                reply_markup = KEYBOARD_PANELBACK)

        if update.callback_query.data.startswith("deposit_tmn"):
            card = CardNumberEntity.get_or_create_first()
            
            await update.callback_query.edit_message_text(MESSAGE_DEPOSIT_TOMAN
                .replace("[CARD]" ,card.card_number).replace("[NAME]" ,card.name),
                parse_mode = "HTML" ,
                link_preview_options = LinkPreviewOptions(is_disabled = True),
                reply_markup = KEYBOARD_PANELBACK)  
            
        if update.callback_query.data.startswith("support"):
            user.step = "support"
            user.save()
            if update.callback_query.message.text:
                await update.callback_query.edit_message_text(MESSAGE_PANELSUPPORT,
                    parse_mode = "HTML" ,
                    link_preview_options = LinkPreviewOptions(is_disabled = True),
                    reply_markup = KEYBOARD_PANELBACK)
            else : 
                await update.callback_query.message.reply_text(
                    MESSAGE_PANELSUPPORT,
                    parse_mode = "HTML" ,
                    link_preview_options = LinkPreviewOptions(is_disabled = True),
                    reply_markup = KEYBOARD_PANELBACK)

        if update.callback_query.data.startswith("rules"):
            await update.callback_query.edit_message_text(MESSAGE_RULE ,parse_mode="HTML" ,reply_markup=KEYBOARD_PANELBACK)

        if update.callback_query.data.startswith("profile"):
            await update.callback_query.edit_message_text(f"""<b>اطلاعات حساب کاربری شما  🧢</b>""",
                parse_mode = "HTML" ,
                link_preview_options = LinkPreviewOptions(is_disabled = True),
                reply_markup = KEYBOARD_PANELBACK)
            
        if update.callback_query.from_user.id in config["OWNERS"]:
            if update.callback_query.data.startswith("answer") \
                and len(update.callback_query.data.split("_")) == 2 \
                and update.callback_query.data.split("_")[1].isnumeric():

                user.step = update.callback_query.data
                user.save()

                return await context.bot.send_message(
                    update.callback_query.from_user.id ,MESSAGE_GET_ANSWER,parse_mode="HTML")

        

async def GroupEventMessageHandler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message.text:
        return
    text = update.message.text.lower()
    
    if text.startswith("/market"):
        result_lines = ["<b>بازارهای محبوب ✨</b>\n"]

        for token in token_price_manager.get_top_tokens():
            symbol = token.get("symbol", "BTC")
            symbol_name_en = token.get("english_name", "")
            symbol_name_fa = token.get("persian_name", "")
            info = token_price_manager.analyze_token(symbol, 1)

            if not info:
                continue

            rial_price = round(info.get("total_rial", 0))
            usdt_price = round(info.get("total_usdt", 0), 2)
            change_percent = info.get("change_percent", 0)
            icon = "🟢" if change_percent > 0 else "🔴" 

            result_lines.append(f"<b>📊 {symbol_name_fa} | {symbol_name_en}</b>")
            result_lines.append(f"<pre>{icon} درصد تغییرات : {change_percent}% روزانه")
            result_lines.append(f"💵 قیمت تومانی : {format_price(rial_price)} تومان")
            result_lines.append(f"💰 قیمت دلاری : {format_price(usdt_price)} دلار</pre>\n")

        await update.message.reply_text(
            text = "\n".join(result_lines) ,
            reply_to_message_id = update.message.id,
            parse_mode = "HTML",
            reply_markup = KEYBOARD_ADDCHATSYMBOL)
    elif text.startswith("/al_h") or text.startswith("/al_i"):
        admins = await update.message.chat.get_administrators()
        
        if not any(admin.user.id == config["BOT_ID"] for admin in admins) \
            or not any(admin.user.id == update.message.from_user.id for admin in admins):
            return
        chat_alert , created = ChatAlertEntity.get_or_create(chat_id = update.message.chat.id)
        
        number = text.replace("/al_h" ,"").replace("/al_i" ,"").strip()
        
        if not number.isnumeric():
            
            return await update.message.reply_text(
                text = MESSAGE_ERROR_NUMBER_INVALID ,
                parse_mode = "HTML")
        number = int(number)

        if text.startswith("/al_h"):
            if number < 0 or number > 24:
                return await update.message.reply_text(
                    text = MESSAGE_ERROR_TIME_INVALID ,
                    parse_mode = "HTML")
            if number == 24:
                number = 0

            chat_alert.send_hour = number
            chat_alert.save()

        if text.startswith("/al_i"):
            if not chat_alert.premium and number < 5:
                return await update.message.reply_text(
                    text = MESSAGE_ERROR_LIMIT_MININTERVAL ,
                    parse_mode = "HTML")
            
            if not chat_alert.premium and number > 120:
                return await update.message.reply_text(
                    text = MESSAGE_ERROR_LIMIT_MAXINTERVAL ,
                    parse_mode = "HTML")
            
            number = min ( max(number , 1) , 60 * 4) 
            chat_alert.send_hour = None
            chat_alert.interval_minutes = number
            chat_alert.save()
        return await update.message.reply_text(
            text = MESSAGE_ALERT_TIME_CHANGED ,
            parse_mode = "HTML")
    
    elif text.startswith("راهنما") or text.startswith("/help"):
        await update.message.reply_text(
            text = MESSAGE_PANELGROUPHELP ,
            parse_mode = "HTML")
        
    elif text.startswith("لیست هشدار"):
        admins = await update.message.chat.get_administrators()
        
        if not any(admin.user.id == config["BOT_ID"] for admin in admins) \
            or not any(admin.user.id == update.message.from_user.id for admin in admins):
            return
        chat_alert , created = ChatAlertEntity.get_or_create(chat_id = update.message.chat.id)

        await update.message.reply_text(
            text = MESSAGE_GROUP_PANEL_SYMBOLS,
            parse_mode="HTML" ,
            reply_markup=group_alerts_keyboard(chat_alert))
    elif text.startswith("هشدار"):
        admins = await update.message.chat.get_administrators()
        
        if not any(admin.user.id == config["BOT_ID"] for admin in admins) \
            or not any(admin.user.id == update.message.from_user.id for admin in admins):
            return
        
        symbol = text.replace("هشدار", "").strip()
        token = token_price_manager.search_token(symbol)
        if not token:
            return await update.message.reply_text(
                text = MESSAGE_ERROR_CURRENCY_NOTFOUND,
                reply_to_message_id = update.message.id,
                parse_mode = "HTML")
        symbol = token.get("symbol", "BTC")

        chat_alert , created = ChatAlertEntity.get_or_create(chat_id = update.message.chat.id)
        
        if chat_alert.symbols and not chat_alert.premium:
            return await update.message.reply_text(
                text = f"<b>{MESSAGE_ERROR_LIMIT_ADD_SYMBOL}</b>",
                reply_to_message_id = update.message.id,
                parse_mode = "HTML")
        if chat_alert.premium and len(chat_alert.symbols) >= 5:
            return await update.message.reply_text(
                text = f"<b>{MESSAGE_ERROR_LIMIT_PREMIUM_ADD_SYMBOL}</b>",
                reply_to_message_id = update.message.id,
                parse_mode = "HTML")

        if symbol.upper() in chat_alert.symbols:
            return await update.message.reply_text(
                text = MESSAGE_ERROR_CURRENCY_ALREADY_EXISTS,
                reply_to_message_id = update.message.id,
                parse_mode = "HTML")
        
        alert = ChatAlertEntity.add_or_update_alert(chat_id = update.message.chat.id ,new_symbols=[symbol.upper()])
        
        await update.message.reply_text(
            text = f"<b>ارز {symbol.upper()} با موفقیت به لیست هشدار اضافه شد ✅</b>",
            reply_to_message_id = update.message.id,
            parse_mode = "HTML",
            reply_markup = group_alerts_keyboard(alert))
        
    elif text.startswith("قیمت") or text.startswith("/"):
        text = convert_persian_digits(text)

        if text.startswith("قیمت"):
            pattern = r"قیمت\s*(?:(\d+(?:\.\d+)?)\s*)?([a-zA-Z\u0600-\u06FF\s]+)"
            match = re.match(pattern, text)
        else:
            pattern = r"/(?:(\d+(?:\.\d+)?))?([a-zA-Z\u0600-\u06FF]+)"
            match = re.match(pattern, text)
            
        if not match:
            return None

        amount_str, symbol = match.groups()
        amount = min(max(float(amount_str) if amount_str else 1.0, 0.00001), 1_000_000_000_000)

        response = generate_price_text(symbol=symbol, amount=amount, token_price_manager=token_price_manager)
        if not response:
            return

        await update.message.reply_text(
            text=response,
            reply_to_message_id=update.message.id,
            parse_mode="HTML"
        )

    elif text.startswith("تبدیل"):
        text = convert_persian_digits(text)

        pattern = r"تبدیل\s*(?:(\d+(?:\.\d+)?)\s*)?([\w\s\u0600-\u06FF]+)\s*به\s*([\w\s\u0600-\u06FF]+)"
        match = re.match(pattern, text)

        if not match:
            return

        amount_str, from_symbol, to_symbol = match.groups()
        amount = float(amount_str) if amount_str else 1.0

        amount = max(min(amount, 10_000_000_000), 0.00001)

        response = generate_convert_text(from_symbol ,to_symbol ,amount ,token_price_manager)

        await update.message.reply_text(
            text=response,
            reply_to_message_id=update.message.id,
            parse_mode="HTML"
        )
    else :
        text = convert_persian_digits(text)

        math_pattern = r"(?:(\d+(?:\.\d+)?)\s+)?([\w\u0600-\u06FF\s]+?)\s*([+-])\s*(?:(\d+(?:\.\d+)?)\s+)?([\w\u0600-\u06FF\s]+)"
        
        match = re.match(math_pattern, text)

        if match:
            amount1_str, symbol1, operator, amount2_str, symbol2 = match.groups()
            amount1 = float(amount1_str) if amount1_str else 1.0
            amount2 = float(amount2_str) if amount2_str else 1.0

            amount1 = min(max(amount1, 0.00001), 1_000_000_000)
            amount2 = min(max(amount2, 0.00001), 1_000_000_000)
            if operator not in ['+', '-']:
                return
            response = generate_operator_text(symbol1 ,symbol2 ,amount1 ,amount2 ,operator ,token_price_manager)
            if response:
                await update.message.reply_text(
                    text=response,
                    reply_to_message_id=update.message.id,
                    parse_mode="HTML"
                )
        else :
            pattern = r"(?:(\d+(?:\.\d+)?)\s+)?([\w\u0600-\u06FF]+)(?:\s+([\w\u0600-\u06FF]+))?"
            match = re.match(pattern, text)

            if match:
                amount_str, first_symbol, second_symbol = match.groups()
                amount = float(amount_str) if amount_str else 1.0
                amount = min(max(amount, 0.00001), 1_000_000_000)

                first_token = token_price_manager.search_token(first_symbol ,normaliza=False)
                second_token = token_price_manager.search_token(second_symbol ,normaliza=False)


                if not first_token or second_symbol and not second_token:
                    return

                if second_symbol:
                    response = generate_convert_text(first_token['symbol'], second_token['symbol'], amount, token_price_manager)
                else:
                    response = generate_price_text(symbol=first_symbol, amount=amount, token_price_manager=token_price_manager)

                if response:
                    await update.message.reply_text(
                        text=response,
                        reply_to_message_id=update.message.id,
                        parse_mode="HTML"
                    )

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"Exception : {context.error}")
    await context.bot.send_message(
        chat_id = config["DEVELOPER_ADMIN"],
        text = f"Exception : <pre>{context.error}</pre>",
        parse_mode = "HTML"
    )
async def EventInlineQueryHandler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query.lower()
    pattern = r"(?:(\d+(?:\.\d+)?)\s+)?([\w\u0600-\u06FF]+)$"
    
    match = re.match(pattern, query)
    results = []

    if match:
        amount_str, symbol_text = match.groups()
        amount = float(amount_str) if amount_str else 1.0
        amount = min(max(amount, 0.00001), 1_000_000_000)

        for token in token_price_manager.search_tokens(symbol_text)[:3]:
            text = generate_price_text(token['symbol'] ,amount ,token_price_manager)
            results.append(
                InlineQueryResultArticle(
                    id=token['symbol'],
                    title=f'قیمت {format_price(amount)} {token['persian_name']}',
                    description = f"دریافت قیمت لحظه ای {format_price(amount)} {token['persian_name']}",
                    input_message_content=InputTextMessageContent(text ,parse_mode = "HTML"),
                    reply_markup = KEYBOARD_INLINECHAT ,
                )
            )

    await update.inline_query.answer(results, cache_time=60)

app = ApplicationBuilder().token(config["TOKEN"]).build()

app.add_error_handler(error_handler)

app.add_handler(MessageHandler(
    filters.ChatType.PRIVATE & (
        filters.TEXT | filters.PHOTO | filters.VIDEO
    ),
    callback=EventMessageHandler
))
app.add_handler(
    MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback)
)
app.add_handler(PreCheckoutQueryHandler(
    callback=precheckout_callback
))
app.add_handler(MessageHandler(
    filters.ChatType.GROUPS & filters.TEXT,
    callback=GroupEventMessageHandler
))
app.add_handler(InlineQueryHandler(
    callback=EventInlineQueryHandler
))


app.add_handler(MessageHandler(
    filters=filters.CONTACT & filters.ChatType.PRIVATE, 
    callback=EventContactHandler))

app.add_handler(CallbackQueryHandler(
    callback=EventCallbackHandler,
))


app.run_polling()