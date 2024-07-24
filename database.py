import sqlite3
import os
import random
import logging
import datetime

os.makedirs('data', exist_ok=True)

accountPINS = logging.getLogger('accountPINS')
accountPINS.setLevel(logging.DEBUG)
# log to file
fh = logging.FileHandler('data/accountPINS.log')
fh.setLevel(logging.DEBUG)
accountPINS.addHandler(fh)

seconds_in_week = 7*24*60*60

token_cache = {}

def random_string(length):
    return ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=length))

def generate_Digits(digits):
    return str(random.randint(pow(10, digits-1), pow(10, digits) - 1))

class Database:
    def __init__(self):
        self.conn = sqlite3.connect('data/database.db', check_same_thread=False)

    def create_table(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                PIN TEXT NOT NULL,
                hidden BOOLEAN DEFAULT 0,
                admin BOOLEAN DEFAULT 0,
                created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tokens (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        # 0 = Current
        # 1 = ISA
        # 2 = storage
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS accounts (
                id TEXT PRIMARY KEY,
                type INTEGER NOT NULL,
                name TEXT NOT NULL,
                user_id TEXT NOT NULL,
                created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                interest_rate REAL DEFAULT 0.05,
                last_interest TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                interest_owed REAL DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                amount INTEGER NOT NULL,
                reference TEXT NOT NULL,
                created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (account_id) REFERENCES accounts
            )
        ''')
        cursor.close()

    def insert_user(self, name, PIN=None, hidden=False, admin=False):
        cursor = self.conn.cursor()
        if not PIN:
            PIN = generate_Digits(6)
        # check if user exists
        cursor.execute('''
            SELECT * FROM users WHERE name = ?
        ''', (name,))
        user = cursor.fetchone()
        if user:
            return None
        id = random_string(10)
        cursor.execute('''
            INSERT INTO users (id, name, PIN, hidden, admin) VALUES (?, ?, ?, ?, ?)
        ''', (id, name, PIN, hidden, admin))
        accountPINS.info(f'User {name} ({id}) has been created with PIN {PIN}')
        cursor.close()
        return id
    
    def time_now(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT CURRENT_TIMESTAMP
        ''')
        fetched = cursor.fetchone()
        cursor.close()
        return datetime.datetime.fromisoformat(fetched[0])

    def calculate_interest(self, account_id):
        account = self.get_account(account_id)
        if not account:
            return None
        last_interest = datetime.datetime.fromisoformat(account[6])
        time_now = self.time_now()
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM transactions WHERE account_id = ? AND created >= ?
        ''', (account_id,last_interest))
        transactions = cursor.fetchall()
        interest = (self.get_balance(account_id, last_interest) * account[5]*((time_now - last_interest).total_seconds()/seconds_in_week)) + account[7]
        for transaction in transactions:
            transaction_date = datetime.datetime.fromisoformat(transaction[4])
            time_to_interest = time_now - transaction_date
            interest += transaction[2] * account[5] * (time_to_interest.total_seconds() / seconds_in_week)
        cursor.close()
        return interest
    
    def get_interest_accumulated(self, account_id):
        account = self.get_account(account_id)
        if not account:
            return None
        time_now = self.time_now()
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM transactions WHERE account_id = ?
        ''', (account_id,))
        transactions = cursor.fetchall()
        if not transactions:
            return None
        interest = account[7]
        for transaction in transactions:
            transaction_date = datetime.datetime.fromisoformat(transaction[4])
            time_to_interest = time_now - transaction_date
            interest += transaction[2] * account[5] * (time_to_interest.total_seconds() / seconds_in_week)
        cursor.close()
        return interest
    
    def give_interest(self, account_id):
        account = self.get_account(account_id)
        if not account:
            return None
        interest = self.calculate_interest(account_id)
        interest_int = int(interest)
        interest_owed = interest - interest_int
        if not interest:
            return None
        cursor = self.conn.cursor()
        if interest_int != 0:
            self.insert_transaction(account_id, interest_int, 'Interest')
        cursor.execute('''
            UPDATE accounts SET last_interest = CURRENT_TIMESTAMP, interest_owed = ? WHERE id = ?
        ''', (interest_owed, account_id))
        cursor.close()
        return interest

    def accumulate_interest(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM accounts
        ''')
        accounts = cursor.fetchall()
        for account in accounts:
            try:
                self.give_interest(account[0])
                self.commit()
            except Exception as e:
                print(e)
                self.conn.rollback()
        cursor.close()

    
    def get_user(self, name):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM users WHERE name = ?
        ''', (name,))
        fetched = cursor.fetchone()
        cursor.close()
        return fetched
    
    def login(self, name, PIN):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM users WHERE name = ? AND PIN = ?
        ''', (name, PIN))
        fetched = cursor.fetchone()
        cursor.close()
        return fetched
    
    def get_user_by_id(self, id):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM users WHERE id = ?
        ''', (id,))
        fetched = cursor.fetchone()
        cursor.close()
        return fetched
    
    def get_users(self, show_hidden=False):
        cursor = self.conn.cursor()
        if show_hidden:
            cursor.execute('''
                SELECT * FROM users
            ''')
        else:
            cursor.execute('''
                SELECT * FROM users WHERE hidden = 0
            ''')
        fetched = cursor.fetchall()
        cursor.close()
        return fetched
    
    def get_accounts(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM accounts WHERE user_id = ?
        ''', (user_id,))
        fetched = cursor.fetchall()
        cursor.close()
        return fetched
    
    def get_account(self, id, user_id = None):
        cursor = self.conn.cursor()
        if user_id:
            cursor.execute('''
                SELECT * FROM accounts WHERE id = ? and user_id = ?
            ''', (id,user_id))
        else:
            cursor.execute('''
                SELECT * FROM accounts WHERE id = ?
            ''', (id,))
        fetched = cursor.fetchone()
        cursor.close()
        return fetched
    
    def insert_account(self, user_id, type, name, interest_rate):
        cursor = self.conn.cursor()
        account_id = generate_Digits(8)
        cursor.execute('''
            INSERT INTO accounts (id, type, name, user_id, interest_rate) VALUES (?, ?, ?, ?, ?)
        ''', (account_id, type, name, user_id, interest_rate))
        return account_id
    
    def get_transactions(self, account_id):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM transactions WHERE account_id = ?
        ''', (account_id,))
        fetched = cursor.fetchall()
        cursor.close()
        return fetched

    def get_balance(self, account_id, before=None):
        cursor = self.conn.cursor()
        if before:
            cursor.execute('''
                SELECT SUM(amount) FROM transactions WHERE account_id = ? AND created < ?
            ''', (account_id, before))
        else:
            cursor.execute('''
                SELECT SUM(amount) FROM transactions WHERE account_id = ?
            ''', (account_id,))
        fetched = cursor.fetchone()[0] or 0
        cursor.close()
        return fetched
    
    def insert_transaction(self, account_id, amount, reference):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO transactions (id, account_id, amount, reference) VALUES (?, ?, ?, ?)
        ''', (random_string(32), account_id, amount, reference))
        cursor.close()
    
    def insert_token(self, user_id):
        cursor = self.conn.cursor()
        token = random_string(100)
        cursor.execute('''
            INSERT INTO tokens (id, user_id) VALUES (?, ?)
        ''', (token, user_id))
        token_cache[token] = (token, user_id)
        return token

    def get_token(self, token):
        if token in token_cache:
            return token_cache[token]
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM tokens WHERE id = ?
        ''', (token,))
        fetched = cursor.fetchone()
        if fetched:
            token_cache[token] = fetched
        cursor.close()
        return fetched
    
    def delete_token(self, token):
        cursor = self.conn.cursor()
        cursor.execute('''
            DELETE FROM tokens WHERE id = ?
        ''', (token,))
        del token_cache[token]
        cursor.close()

    def get_user_by_token(self, token):
        token = self.get_token(token)
        if not token:
            return None
        return self.get_user_by_id(token[1])
    
    def transfer(self, from_account_id, to_account_id, amount, reference):
        """
        0 = Success

        1 = Invalid amount

        2 = Insufficient funds

        3 = Invalid account
        
        4 = Same account
        """
        try:
            if amount < 0:
                return 1
            if from_account_id == to_account_id:    
                return 4
            balance = self.get_balance(from_account_id)
            if balance < amount:
                return 2
            to_account = self.get_account(to_account_id)
            if not to_account:
                return 3
            from_user = self.get_account_owner(from_account_id)
            to_user = self.get_account_owner(to_account_id)
            if reference == '':
                reference_from_account = f'Transfer to {to_user[1]}'
                reference_to_account = f'Transfer from {from_user[1]}'
            else:
                reference_from_account = reference_to_account = reference
            self.insert_transaction(from_account_id, -amount, reference_from_account)
            self.insert_transaction(to_account_id, amount, reference_to_account)
            return 0
        except Exception as e:
            print(e)
            self.conn.rollback()
            return 5
    def get_account_owner(self, account_id):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM users WHERE id = (
                SELECT user_id FROM accounts WHERE id = ?
            )
        ''', (account_id,))
        fetched = cursor.fetchone()
        cursor.close()
        return fetched

    def get_users_first_current_account(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM accounts WHERE user_id = ? AND type = 0
        ''', (user_id,))
        fetched = cursor.fetchone()
        cursor.close()
        return fetched

    def close(self):
        self.conn.close()
    
    def commit(self):
        self.conn.commit()

users = [
    {
        'name': 'admin',
        'hidden': True,
        'admin': True,
        'accounts': [
            {
                'type': 2,
                'name': 'Reserve',
                'initial': 286,
                'interest': 0,
            },
            {
                'type': 2,
                'name': 'Bonus',
                'initial': 10,
                'interest': 0,
            }
        ]
    },
    {
        'name': 'Ugric',
        'admin': True,
        'accounts': [
            {
                'type': 0,
                'name': 'Current',
                'initial': 36,
            },
            {
                'type': 1,
                'name': 'ISA',
                'initial': 0,
                'interest': 0.1,
            },
        ]
    },
    {
        'name': 'Mjreacts_YT',
        'accounts': [
            {
                'type': 0,
                'name': 'Current',
                'initial': 159,
            },
            {
                'type': 1,
                'name': 'ISA',
                'initial': 0,
                'interest': 0.1,
            },
        ]
    },
    {
        'name': 'Yellowgem11',
        'accounts': [
            {
                'type': 0,
                'name': 'Current',
                'initial': 36,
            },
            {
                'type': 1,
                'name': 'ISA',
                'initial': 228,
                'interest': 0,
            },
        ]
    },
    {
        'name': 'Az3rt_',
        'accounts': [
            {
                'type': 0,
                'name': 'Current',
                'initial': 819,
            },
            {
                'type': 1,
                'name': 'ISA',
                'initial': 0,
                'interest': 0.1,
            },
        ]
    },
    {
        'name': 'Sami2048',
        'accounts': [
            {
                'type': 0,
                'name': 'Current',
                'initial': 105,
            },
            {
                'type': 1,
                'name': 'ISA',
                'initial': 0,
                'interest': 0.1,
            },
        ]
    },
    {
        'name': 'fairwillp',
        'accounts': [
            {
                'type': 0,
                'name': 'Current',
                'initial': 563,
            },
            {
                'type': 1,
                'name': 'ISA',
                'initial': 0,
                'interest': 0.1,
            },
        ]
    },
    {
        'name': 'John Doe',
        'hidden': True,
        'accounts': [
            {
                'type': 2,
                'name': 'John Doe',
                'initial': -533,
                'interest': 0,
            },
        ]
    },
    {
        'name': 'Turbopig911',
        'accounts': [
            {
                'type': 0,
                'name': 'Current',
                'initial': 0,
            },
            {
                'type': 1,
                'name': 'ISA',
                'initial': 644,
                'interest': 0,
            },
        ]
    }
]

db = Database()
db.create_table()
db.commit()

for user in users:
    user_id = db.insert_user(user['name'], hidden=user.get('hidden', False), admin=user.get('admin', False))
    if not user_id:
        continue
    for account in user.get('accounts', []):
        account_id = db.insert_account(user_id, account['type'], account['name'], account.get('interest', 0.05))
        db.insert_transaction(account_id, account['initial']*100, 'Initial balance')
db.commit()