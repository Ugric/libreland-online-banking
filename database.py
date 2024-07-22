import sqlite3
import os
import random
import logging

os.makedirs('data', exist_ok=True)

accountPINS = logging.getLogger('accountPINS')
accountPINS.setLevel(logging.DEBUG)
# log to file
fh = logging.FileHandler('data/accountPINS.log')
fh.setLevel(logging.DEBUG)
accountPINS.addHandler(fh)

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
    
    def get_users(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM users
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
    
    def get_account(self, id, user_id):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM accounts WHERE id = ? and user_id = ?
        ''', (id,user_id))
        fetched = cursor.fetchone()
        cursor.close()
        return fetched
    
    def insert_account(self, user_id, type, name):
        cursor = self.conn.cursor()
        account_id = generate_Digits(16)
        cursor.execute('''
            INSERT INTO accounts (id, type, name, user_id) VALUES (?, ?, ?, ?)
        ''', (account_id, type, name, user_id))
        return account_id
    
    def get_transactions(self, account_id):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM transactions WHERE account_id = ?
        ''', (account_id,))
        fetched = cursor.fetchall()
        cursor.close()
        return fetched

    def get_balance(self, account_id):
        cursor = self.conn.cursor()
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
        return token

    def get_token(self, token):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM tokens WHERE id = ?
        ''', (token,))
        fetched = cursor.fetchone()
        cursor.close()
        return fetched
    
    def delete_token(self, token):
        cursor = self.conn.cursor()
        cursor.execute('''
            DELETE FROM tokens WHERE id = ?
        ''', (token,))
        cursor.close()

    def get_user_by_token(self, token):
        token = self.get_token(token)
        if not token:
            return None
        return self.get_user_by_id(token[1])

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
            },
            {
                'type': 2,
                'name': 'Bonus',
                'initial': 10,
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
        account_id = db.insert_account(user_id, account['type'], account['name'])
        db.insert_transaction(account_id, account['initial'], 'Initial balance')
db.commit()