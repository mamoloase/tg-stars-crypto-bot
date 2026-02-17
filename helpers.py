import json ,time,requests,jdatetime ,pytz

class TokenPriceManager:
    def __init__(self, json_path):
        self.tokens = self._load_tokens(json_path)
        self.token_cache = {}    
        self.nobitex_cache = None 

    def _load_tokens(self, path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def get_top_tokens(self, count=5):
        return self.tokens[:count]
    def search_tokens(self, query, normaliza=True):
        if not query:
            return []

        def normalize_persian(text):
            return text.strip().replace('\u200c', '').replace(' ', '').replace("کوین", "")

        matched_tokens = []
        query = normalize_persian(query.lower())

        for token in self.tokens:
            symbol = normalize_persian(token['symbol'].lower())
            english = normalize_persian(token['english_name'].lower())
            persian = normalize_persian(token['persian_name'].lower())

            if (
                query in symbol or
                query in english or
                query in persian
            ):
                matched_tokens.append(token)

        return matched_tokens
    def search_token(self, query, normaliza=True):
        if not query:
            return
        
        def normalize_persian(text):
            return text.strip().replace('\u200c', '').replace(' ', '').replace("کوین", "")

        if normaliza:
            query = normalize_persian(query.lower())

            for token in self.tokens:
                if (
                    token['symbol'].lower() == query or
                    normalize_persian(token['english_name'].lower()).startswith(query) or
                    normalize_persian(token['persian_name'].lower()).startswith(query)
                ):
                    return token
        else:
            query = normalize_persian(query.lower())

            for token in self.tokens:
                if (
                    normalize_persian(token['symbol'].lower()) == query or
                    normalize_persian(token['english_name'].lower()) == query or
                    normalize_persian(token['persian_name'].lower()) == query
                ):
                    return token

        return None


    
    def get_rial_rate_from_wallex(self):
        url = "https://api.wallex.ir/v1/coin-price-list?keys=USDT&fields=quotes.TMN.price"
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            price_str = data["result"]["markets"][0]["quotes"]["TMN"]["price"]
            return float(price_str)
        except Exception as e:
            print("خطا در دریافت نرخ ریال از والکس:", e)
            return
    def get_rial_rate_from_nobitex(self):
        url = "https://apiv2.nobitex.ir/market/stats"
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()

            stats = data.get("stats", {})
            if "usdt-rls" not in stats:
                return

            price_str = stats["usdt-rls"]["latest"]
            return float(price_str) / 10

        except Exception as e:
            print("خطا در دریافت نرخ ریال از نوبیتکس:", e)
            return
    
    def get_rial_rate(self):
        now = time.time()
        if self.nobitex_cache and now - self.nobitex_cache['timestamp'] < 60:
            return self.nobitex_cache['stats']

        try:

            stats = self.get_rial_rate_from_nobitex()
            if not stats:
                stats = self.get_rial_rate_from_wallex()
            if not stats : 
                stats = 0
        except Exception as e:
            print(e)
            return self.nobitex_cache['stats'] if self.nobitex_cache else 0

        self.nobitex_cache = {
            'stats': stats,
            'timestamp': now
        }
        return stats
    
    def get_from_binance(self,symbol):
        url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}USDT"
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            return {
                'price': float(data['lastPrice']),
                'volume': float(data['volume']),
                'change_percent': float(data['priceChangePercent']),
            }
        except Exception as e:
            print(f"Binance خطا برای {symbol}:", e)
            return None

    def get_from_mexc(self, symbol):
        url = f"https://www.mexc.com/open/api/v2/market/ticker?symbol={symbol}_USDT"
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            if data['code'] == 200 and data['data']:
                ticker = data['data'][0]
                return {
                    'price': float(ticker['last']),
                    'volume': float(ticker['volume']),
                    'change_percent': float(ticker['change_rate']) * 100,  # تبدیل به درصد
                }
            else:
                print(f"MEXC خطا برای {symbol}: داده نامعتبر")
                return None
        except Exception as e:
            print(f"MEXC خطا برای {symbol}:", e)
            return None



    def get_token_data(self, symbol):
        now = time.time()
        cached = self.token_cache.get(symbol)
        if cached and now - cached['timestamp'] < 30:
            return cached

      
        data = self.get_from_binance(symbol)
        if data is None:
            data = self.get_from_mexc(symbol)
            if data is None:
                return cached if cached else None

        data['timestamp'] = now
        self.token_cache[symbol] = data
        return data

    def analyze_token(self, symbol, amount):
        rial_rate = self.get_rial_rate()

        if symbol.upper() == "USDT":
            price_usdt = 1.0
            total_usdt = price_usdt * amount
            total_rial = total_usdt * rial_rate

            return {
                'symbol': symbol,
                'price_usdt': price_usdt,
                'amount': amount,
                'total_usdt': total_usdt,
                'total_rial': total_rial,
                'change_percent': 0.0,
                'profit_usdt': 0.0,
                'profit_rial': 0.0,
                'volume': 0.0,
                'rial_rate': rial_rate
            }
        if symbol.upper() == "STARS":
            price_usdt = 0.015
            total_usdt = price_usdt * amount
            total_rial = total_usdt * rial_rate

            return {
                'symbol': symbol,
                'price_usdt': price_usdt,
                'amount': amount,
                'total_usdt': total_usdt,
                'total_rial': total_rial,
                'change_percent': 0.0,
                'profit_usdt': 0.0,
                'profit_rial': 0.0,
                'volume': 0.0,
                'rial_rate': rial_rate
            }

        data = self.get_token_data(symbol)
        if not data:
            return None

        price_usdt = data['price']
        total_usdt = price_usdt * amount
        total_rial = total_usdt * rial_rate
        change_percent = data['change_percent']
        profit_usdt = total_usdt * (change_percent / 100)
        profit_rial = profit_usdt * rial_rate

        return {
            'symbol': symbol,
            'price_usdt': price_usdt,
            'amount': amount,
            'total_usdt': total_usdt,
            'total_rial': total_rial,
            'change_percent': change_percent,
            'profit_usdt': profit_usdt,
            'profit_rial': profit_rial,
            'volume': data['volume'],
            'rial_rate': rial_rate
        }
    
def convert_persian_digits(text):
    persian_digits = "۰۱۲۳۴۵۶۷۸۹"
    english_digits = "0123456789"
    translation_table = str.maketrans(persian_digits, english_digits)
    return text.translate(translation_table)

def format_price(value):
    if isinstance(value, float):
        if value.is_integer():
            return f"{int(value):,}"
        else:
            integer_part = int(value)
            decimal_part = f"{value:.10f}".split('.')[1].rstrip('0')
            if decimal_part:
                if integer_part > 1000:
                    return f"{integer_part:,}"
                elif integer_part > 50:
                    return f"{integer_part:,.2f}"

                return f"{integer_part:,}.{decimal_part}"
            else:
                return f"{integer_part:,}"
    else:
        try:
            ivalue = int(value)
            return f"{ivalue:,}"
        except:
            return str(value)



def get_datetime():
    iran_tz = pytz.timezone("Asia/Tehran")
    now = jdatetime.datetime.now(tz=iran_tz)
    return now.strftime("%Y/%m/%d %H:%M")


def is_exact_shamsi_time(alert):
    now = jdatetime.datetime.now()
    return (
        alert.send_hour is not None and
        now.hour == alert.send_hour
    )


def generate_price_text(symbol,amount, token_price_manager ,time = True):

    token = token_price_manager.search_token(symbol.strip())

    if not token:
        return None
    
    info = token_price_manager.analyze_token(token["symbol"], amount)
    if not info:
        return None
    
    symbol_name_fa = token.get("persian_name", "")
    symbol_name_en = token.get("english_name", "")
    
    profit_rial = round(info.get("profit_rial", 0))
    profit_usdt = info.get("profit_usdt", 0)
    
    rial_price = round(info.get("total_rial", 0))
    usdt_price = info.get("total_usdt", 0)
    
    volume = round(info.get("volume", 0), 2)
    change_percent = info.get("change_percent", 0)
    icon = "🟢" if change_percent > 0 else "🔴"
    
    if usdt_price > 1_000_000:
        usdt_price = round(usdt_price)
        
    lines = [
        f"<pre>⏰ {get_datetime()}</pre>\n",
        f"\n🔺 <b> {symbol_name_fa} | <u>{symbol_name_en}</u></b>",
        f"<pre>📊 ( {format_price(amount)} {symbol_name_fa} )</pre>",
        f"<pre>💵 قیمت تومانی : {format_price(rial_price)} تومان"
    ]
    if not time:
        lines.pop(0)
    if not volume:
        if token["symbol"].upper() == "STARS":
            lines.append(f"💰 قیمت دلاری : {format_price(usdt_price)} دلار</pre>")
        else :
            lines[-1] += "</pre>"
    else:
        lines.append(f"💰 قیمت دلاری : {format_price(usdt_price)} دلار</pre>")
    return "\n".join(lines)

def generate_alert_text(symbols ,token_price_manager):
    messages = []
    for symbol in symbols:
        text = generate_price_text(symbol, 1, token_price_manager, time=False)
        if text : 
            messages.append(text)

    return f"<pre>⏰ {get_datetime()}</pre>\n"  + "\n".join(messages)

def generate_convert_text(from_symbol ,to_symbol , amount, token_price_manager):
    to_token = token_price_manager.search_token(to_symbol)
    from_token = token_price_manager.search_token(from_symbol)

    if not to_token or not from_token:
        return None
    
    to_info = token_price_manager.analyze_token(to_token["symbol"], amount)
    from_info = token_price_manager.analyze_token(from_token["symbol"], amount)
    
    if not to_info or not from_info:
        return None
    
    to_symbol_name_en = to_token.get("english_name", "")
    from_symbol_name_en = from_token.get("english_name", "")

    to_usdt_price = to_info.get("total_usdt", 0)
    from_rial_price = from_info.get("total_rial", 0)
    from_usdt_price = from_info.get("total_usdt", 0)

    converted_amount = (amount * from_usdt_price) / to_usdt_price

    lines = [
        f"<pre>⏰ {get_datetime()}</pre>\n",
        f"\n🔺 <b> تبدیل <u>{from_symbol_name_en}</u> به <u>{to_symbol_name_en}</u></b>",
        f"<pre>📊 {format_price(amount)} {from_symbol_name_en} -> {format_price(converted_amount)} {to_symbol_name_en}</pre>\n",
        f"<pre>💵 قیمت تومانی : {format_price(from_rial_price)} تومان",
        f"💰 قیمت دلاری : {format_price(from_usdt_price)} دلار</pre>"
    ]

    return "\n".join(lines)
    
def generate_operator_text(from_symbol ,to_symbol , from_amount ,to_amount,operator ,token_price_manager):
    to_token = token_price_manager.search_token(to_symbol)
    from_token = token_price_manager.search_token(from_symbol)

    if not to_token or not from_token:
        return None
    
    to_info = token_price_manager.analyze_token(to_token["symbol"], to_amount)
    from_info = token_price_manager.analyze_token(from_token["symbol"], from_amount)
    
    if not to_info or not from_info:
        return None
    
    to_symbol_name_en = to_token.get("english_name", "")
    from_symbol_name_en = from_token.get("english_name", "")

    to_usdt_price = to_info.get("total_usdt", 0)
    to_rial_price = to_info.get("total_rial", 0)
    from_rial_price = from_info.get("total_rial", 0)
    from_usdt_price = from_info.get("total_usdt", 0)

    result_rial = to_rial_price + from_rial_price if operator == "+" else from_rial_price - to_rial_price
    result_usdt = to_usdt_price + from_usdt_price if operator == "+" else from_usdt_price - to_usdt_price
    
    operator_text = "جمع" if operator == "+" else "تفریق"
    operator_split = "با" if operator == "+" else "از"
    
    lines = [
        f"<pre>⏰ {get_datetime()}</pre>\n",
        f"\n🔺 <b> {operator_text} <u>{from_symbol_name_en}</u> <code>{from_amount}</code> {operator_split} <u>{to_symbol_name_en}</u> <code>{to_amount}</code></b>\n",
        f"<pre>💵 قیمت تومانی : {format_price(result_rial)} تومان",
        f"💰 قیمت دلاری : {format_price(result_usdt)} دلار</pre>"
    ]

    return "\n".join(lines)
    