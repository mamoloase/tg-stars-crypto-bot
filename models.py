import json
from peewee import *
from configs import *
from datetime import datetime
from decimal import Decimal


db = SqliteDatabase('sqlite3.db')

class BaseModel(Model):
    class Meta:
        database = db


class ChatAlert(BaseModel):
    chat_id = IntegerField(unique=True)
    symbols_raw = TextField(null=True, default='[]')
    last_sent = DateTimeField(null=True)
    premium = BooleanField(default=False)
    interval_minutes = IntegerField(default=30)
    send_hour = IntegerField(null=True ,default=None)


    @property
    def symbols(self):
        try:
            return json.loads(self.symbols_raw or '[]')
        except json.JSONDecodeError:
            return []

    @symbols.setter
    def symbols(self, value):
        try:
            self.symbols_raw = json.dumps(value)
        except TypeError:
            self.symbols_raw = '[]'

    @classmethod
    def add_or_update_alert(cls, chat_id, new_symbols):
        alert, created = cls.get_or_create(chat_id=chat_id, defaults={'symbols_raw': '[]'})

        new_symbols = list(set(new_symbols or []))

        if not created:
            existing = set(alert.symbols)
            updated = existing.union(new_symbols)
            alert.symbols = list(updated)
        else:
            alert.symbols = new_symbols

        alert.last_sent = datetime.utcnow()
        alert.save()
        return alert

    def remove_symbol(self, symbol):
        updated = [s for s in self.symbols if s != symbol]
        self.symbols = updated
        self.save()

    def clear_symbols(self):
        self.symbols = []
        self.save()

    def get_symbols(self):
        return self.symbols

    def has_symbol(self, symbol):
        return symbol in self.symbols

    def is_due_to_send(self):
        if not self.last_sent:
            return True
        elapsed_minutes = (datetime.now() - self.last_sent).total_seconds() / 60
        return elapsed_minutes >= self.interval_minutes

class User(BaseModel):
    user_id = BigIntegerField(unique = True)
    is_blocked = BooleanField(default = False)
    step = CharField(null = True)
    phone = CharField(null = True)
    metadata = TextField(null=True)
    
    @classmethod
    def block_user(cls, user_id):
        user = cls.select().where(cls.user_id == user_id).first()
        if user:
            user.is_blocked = True
            user.save()
            return True  
        return False 
    @classmethod
    def unblock_user(cls, user_id):
        user = cls.select().where(cls.user_id == user_id).first()
        if user:
            user.is_blocked = False
            user.save()
            return True 
        return False 
    
    def get_metadata_dict(self):
        if self.metadata:
            try:
                return json.loads(self.metadata)
            except :pass
        return {}

    def set_metadata_dict(self, data_dict):
        self.metadata = json.dumps(data_dict)
        self.save()

    def update_metadata_key(self, key, value):
        meta = self.get_metadata_dict()
        meta[key] = value
        self.set_metadata_dict(meta)

    def delete_metadata_key(self, key):
        meta = self.get_metadata_dict()
        if key in meta:
            del meta[key]
            self.set_metadata_dict(meta)

    def clear_metadata(self):
        self.metadata = json.dumps({})
        self.save()


class Balance(BaseModel):
    user_id = BigIntegerField()
    currency = CharField(null=True)
    balance = DecimalField()

    @classmethod
    def get_or_init_balance(cls, user_id, currency):
        currency = currency.upper()

        obj, created = cls.get_or_create(
            user_id=user_id,
            currency=currency,
            defaults={'balance': 0}
        )
        return obj.balance
    @classmethod
    def increase_balance(cls, user_id, currency, amount):
        currency = currency.upper()
        obj, _ = cls.get_or_create(
            user_id=user_id,
            currency=currency,
            defaults={'balance': Decimal('0')}
        )
        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))

        obj.balance += amount
        obj.save()
        return obj.balance

    @classmethod
    def decrease_balance(cls, user_id, currency, amount):
        currency = currency.upper()
        obj, _ = cls.get_or_create(
            user_id=user_id,
            currency=currency,
            defaults={'balance': Decimal('0')}
        )
        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))

        if obj.balance >= amount:
            obj.balance -= amount
            obj.save()
            return obj.balance
        else:
            raise ValueError("موجودی کافی نیست.")


class CardNumber(BaseModel):
    name = TextField()
    card_number = TextField()
    
    @classmethod
    def get_or_create_first(cls):
        obj = cls.select().first()
        if not obj:
            obj = cls.create(name="", card_number="")
        return obj

    @classmethod
    def set_first_card(cls, name, card_number):
        obj = cls.select().first()
        if obj:
            obj.name = name
            obj.card_number = card_number
            obj.save()
        else:
            obj = cls.create(name=name, card_number=card_number)
        return obj



db.connect()
db.create_tables([User,ChatAlert ,Balance ,CardNumber])