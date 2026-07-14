import sqlite3
import os
import random
import logging
import datetime

os.makedirs("data/ads", exist_ok=True)

accountPINS = logging.getLogger("accountPINS")
accountPINS.setLevel(logging.DEBUG)
# log to file
fh = logging.FileHandler("data/accountPINS.log")
fh.setLevel(logging.DEBUG)
accountPINS.addHandler(fh)

seconds_in_day = 24 * 60 * 60

token_cache = {}

# Advert status codes
AD_STATUS_ACTIVE = 0
AD_STATUS_HIT_LIMIT = 1
AD_STATUS_DISABLED = 2

# Global rate used to compute advert cost-per-view: (duration * weight * ad_cost_per_second) / 100
# Default 0.01 represents 0.0001 libros charged per second of duration per view.
ad_cost_per_second_per_100_views = 1.0


def random_string(length):
    return "".join(
        random.choices(
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=length
        )
    )


def generate_Digits(digits):
    return str(random.randint(pow(10, digits - 1), pow(10, digits) - 1))


class Database:
    def __init__(self):
        self.conn = sqlite3.connect("data/database.db", check_same_thread=False)

    def create_table(self):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                PIN TEXT NOT NULL,
                hidden BOOLEAN DEFAULT 0,
                admin BOOLEAN DEFAULT 0,
                created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tokens (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """
        )
        # 0 = Current
        # 1 = ISA
        # 2 = storage
        cursor.execute(
            """
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
        """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                amount INTEGER NOT NULL,
                reference TEXT NOT NULL,
                created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (account_id) REFERENCES accounts
            )
        """
        )
        # status: 0 = active, 1 = hit_limit, 2 = disabled
        # spend_limit: max total amount ("limit" is a reserved SQL word, renamed)
        # total_spent: running total charged against this ad, compared to spend_limit
        # weight: relative likelihood of being picked. 1 = baseline, 0.5 = half as likely, 2 = double
        # reference: display name/label for the ad, set by the owner
        # cost_owed: fractional-cent remainder not yet charged, carried forward
        #            each view (mirrors accounts.interest_owed)
        # cost per view is NOT stored - computed on demand via get_ad_cost()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS adverts (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                duration INTEGER NOT NULL,
                spend_limit INTEGER NOT NULL,
                total_spent INTEGER NOT NULL DEFAULT 0,
                status INTEGER NOT NULL DEFAULT 0,
                weight REAL NOT NULL DEFAULT 1,
                reference TEXT DEFAULT '',
                cost_owed REAL NOT NULL DEFAULT 0,
                created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (account_id) REFERENCES accounts
            )
        """
        )
        # Migration: cost_owed was added after adverts first went into
        # production, so existing databases need it added on top.
        cursor.execute("PRAGMA table_info(adverts)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        if "cost_owed" not in existing_columns:
            cursor.execute(
                "ALTER TABLE adverts ADD COLUMN cost_owed REAL NOT NULL DEFAULT 0"
            )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS advert_costs (
                id TEXT PRIMARY KEY,
                advert_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                amount INTEGER NOT NULL,
                created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (advert_id) REFERENCES adverts (id),
                FOREIGN KEY (account_id) REFERENCES accounts (id)
            )
        """
        )
        cursor.close()

    def insert_user(self, name, PIN=None, hidden=False, admin=False):
        cursor = self.conn.cursor()
        if not PIN:
            PIN = generate_Digits(6)
        # check if user exists
        cursor.execute(
            """
            SELECT * FROM users WHERE name = ?
        """,
            (name,),
        )
        user = cursor.fetchone()
        if user:
            return None
        id = random_string(10)
        cursor.execute(
            """
            INSERT INTO users (id, name, PIN, hidden, admin) VALUES (?, ?, ?, ?, ?)
        """,
            (id, name, PIN, hidden, admin),
        )
        accountPINS.info(f"User {name} ({id}) has been created with PIN {PIN}")
        cursor.close()
        return id

    def time_now(self):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT CURRENT_TIMESTAMP
        """
        )
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
        cursor.execute(
            """
            SELECT * FROM transactions WHERE account_id = ? AND created >= ?
        """,
            (account_id, last_interest),
        )
        transactions = cursor.fetchall()
        interest = (
            self.get_balance(account_id, last_interest)
            * account[5]
            * ((time_now - last_interest).total_seconds() / seconds_in_day)
        ) + account[7]
        for transaction in transactions:
            transaction_date = datetime.datetime.fromisoformat(transaction[4])
            time_to_interest = time_now - transaction_date
            interest += (
                transaction[2]
                * account[5]
                * (time_to_interest.total_seconds() / seconds_in_day)
            )
        cursor.close()
        return interest

    def get_interest_accumulated(self, account_id):
        account = self.get_account(account_id)
        if not account:
            return None
        time_now = self.time_now()
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT * FROM transactions WHERE account_id = ?
        """,
            (account_id,),
        )
        transactions = cursor.fetchall()
        if not transactions:
            return None
        interest = account[7]
        for transaction in transactions:
            transaction_date = datetime.datetime.fromisoformat(transaction[4])
            time_to_interest = time_now - transaction_date
            interest += (
                transaction[2]
                * account[5]
                * (time_to_interest.total_seconds() / seconds_in_day)
            )
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
            self.insert_transaction(account_id, interest_int, "Interest")
        cursor.execute(
            """
            UPDATE accounts SET last_interest = CURRENT_TIMESTAMP, interest_owed = ? WHERE id = ?
        """,
            (interest_owed, account_id),
        )
        cursor.close()
        return interest

    def accumulate_interest(self):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT * FROM accounts
        """
        )
        accounts = cursor.fetchall()
        for account in accounts:
            try:
                self.give_interest(account[0])
                self.commit()
            except Exception as e:
                print(e)
                self.conn.rollback()
        cursor.close()

    def accumulate_advert_costs(self):
        adverts = self.get_adverts()

        for advert in adverts:
            advert_id = advert[0]
            account_id = advert[1]

            cost_owed = self.get_advert_cost_owed(advert_id)
            cost_to_charge = int(cost_owed)

            print(cost_to_charge)

            if cost_to_charge == 0:
                continue

            balance = self.get_balance(account_id)
            if balance < cost_to_charge:
                continue

            self.insert_transaction(
                account_id,
                -cost_to_charge,
                "Advert display costs",
            )

            if ad_revenue_account_id:
                self.insert_transaction(
                    ad_revenue_account_id,
                    cost_to_charge,
                    f"{account_id}'s advertising costs",
                )

            self.insert_advert_cost(advert_id, account_id, cost_to_charge)

            remainder = cost_owed - cost_to_charge
            new_total_spent = advert[4] + cost_to_charge

            cursor = self.conn.cursor()
            cursor.execute(
                """
                UPDATE adverts
                SET total_spent = ?, cost_owed = ?
                WHERE id = ?
                """,
                (new_total_spent, remainder, advert_id),
            )
            cursor.close()

            if new_total_spent >= advert[3]:
                self.set_advert_status(advert_id, AD_STATUS_HIT_LIMIT)

        self.commit()

    def get_user(self, name):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT * FROM users WHERE name = ?
        """,
            (name,),
        )
        fetched = cursor.fetchone()
        cursor.close()
        return fetched

    def login(self, name, PIN):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT * FROM users WHERE name = ? AND PIN = ?
        """,
            (name, PIN),
        )
        fetched = cursor.fetchone()
        cursor.close()
        return fetched

    def get_user_by_id(self, id):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT * FROM users WHERE id = ?
        """,
            (id,),
        )
        fetched = cursor.fetchone()
        cursor.close()
        return fetched

    def get_users(self, show_hidden=False):
        cursor = self.conn.cursor()
        if show_hidden:
            cursor.execute(
                """
                SELECT * FROM users
            """
            )
        else:
            cursor.execute(
                """
                SELECT * FROM users WHERE hidden = 0
            """
            )
        fetched = cursor.fetchall()
        cursor.close()
        return fetched

    def get_accounts(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT * FROM accounts WHERE user_id = ?
        """,
            (user_id,),
        )
        fetched = cursor.fetchall()
        cursor.close()
        return fetched

    def get_account(self, id, user_id=None):
        cursor = self.conn.cursor()
        if user_id:
            cursor.execute(
                """
                SELECT * FROM accounts WHERE id = ? and user_id = ?
            """,
                (id, user_id),
            )
        else:
            cursor.execute(
                """
                SELECT * FROM accounts WHERE id = ?
            """,
                (id,),
            )
        fetched = cursor.fetchone()
        cursor.close()
        return fetched

    def insert_account(self, user_id, type, name, interest_rate):
        cursor = self.conn.cursor()
        account_id = generate_Digits(8)
        cursor.execute(
            """
            INSERT INTO accounts (id, type, name, user_id, interest_rate) VALUES (?, ?, ?, ?, ?)
        """,
            (account_id, type, name, user_id, interest_rate),
        )
        return account_id

    def change_interest(self, account_id, new_interest):
        cursor = self.conn.cursor()
        self.give_interest(account_id)
        cursor.execute(
            """
            UPDATE accounts SET interest_rate = ? WHERE id = ?
        """,
            (new_interest, account_id),
        )
        cursor.close()

    def get_transactions(self, account_id):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT * FROM transactions WHERE account_id = ?
        """,
            (account_id,),
        )
        fetched = cursor.fetchall()
        cursor.close()
        return fetched

    def get_balance(self, account_id, before=None):
        cursor = self.conn.cursor()
        if before:
            cursor.execute(
                """
                SELECT SUM(amount) FROM transactions WHERE account_id = ? AND created < ?
            """,
                (account_id, before),
            )
        else:
            cursor.execute(
                """
                SELECT SUM(amount) FROM transactions WHERE account_id = ?
            """,
                (account_id,),
            )
        fetched = cursor.fetchone()[0] or 0
        cursor.close()
        return fetched

    def insert_transaction(self, account_id, amount, reference):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO transactions (id, account_id, amount, reference) VALUES (?, ?, ?, ?)
        """,
            (random_string(32), account_id, amount, reference),
        )
        cursor.close()

    def insert_token(self, user_id):
        cursor = self.conn.cursor()
        token = random_string(100)
        cursor.execute(
            """
            INSERT INTO tokens (id, user_id) VALUES (?, ?)
        """,
            (token, user_id),
        )
        token_cache[token] = (token, user_id)
        return token

    def get_token(self, token):
        if not token:
            return None
        if token in token_cache:
            return token_cache[token]
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT * FROM tokens WHERE id = ?
        """,
            (token,),
        )
        fetched = cursor.fetchone()
        if fetched:
            token_cache[token] = fetched
        cursor.close()
        return fetched

    def delete_token(self, token):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            DELETE FROM tokens WHERE id = ?
        """,
            (token,),
        )
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
            if reference == "":
                reference_from_account = f"Transfer to {to_user[1]}"
                reference_to_account = f"Transfer from {from_user[1]}"
            else:
                reference_from_account = f"Transfer to {to_user[1]}: {reference}"
                reference_to_account = f"Transfer from {from_user[1]}: {reference}"
            self.insert_transaction(from_account_id, -amount, reference_from_account)
            self.insert_transaction(to_account_id, amount, reference_to_account)
            return 0
        except Exception as e:
            print(e)
            self.conn.rollback()
            return 5

    def get_account_owner(self, account_id):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT * FROM users WHERE id = (
                SELECT user_id FROM accounts WHERE id = ?
            )
        """,
            (account_id,),
        )
        fetched = cursor.fetchone()
        cursor.close()
        return fetched

    def get_users_first_current_account(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT * FROM accounts WHERE user_id = ? AND type = 0
        """,
            (user_id,),
        )
        fetched = cursor.fetchone()
        cursor.close()
        return fetched

    # ------------------------------------------------------------------
    # Adverts
    # ------------------------------------------------------------------

    def insert_advert(
        self, account_id, duration, spend_limit, weight=1.0, reference=""
    ):
        """
        Creates a new advert owned by account_id.

        duration: how long (seconds) the ad is shown for per selection.
        spend_limit: total amount that can be spent on this ad before it's
                     auto-marked as hit_limit.
        weight: relative likelihood of being picked versus other active ads.
                1 = baseline, 0.5 = half as likely, 2 = double as likely.
        reference: display name/label for the ad.

        Cost is NOT stored here — it's computed on demand via get_ad_cost(),
        using the current global ad_cost_per_second, so rate changes apply
        to existing ads immediately.
        """
        cursor = self.conn.cursor()
        advert_id = random_string(16)
        cursor.execute(
            """
            INSERT INTO adverts (id, account_id, duration, spend_limit, weight, reference)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (advert_id, account_id, duration, spend_limit, weight, reference),
        )
        cursor.close()
        return advert_id

    def update_advert(self, advert_id, duration=None, weight=None, reference=None):
        """
        Updates editable fields on an advert (duration, weight, reference).
        Only fields that are not None are changed. Does not touch
        spend_limit, status, or total_spent — use top_up_advert() and
        set_advert_status()/disable_advert() for those.
        """
        advert = self.get_advert(advert_id)
        if not advert:
            return None
        new_duration = duration if duration is not None else advert[2]
        new_weight = weight if weight is not None else advert[6]
        new_reference = reference if reference is not None else advert[7]
        cursor = self.conn.cursor()
        cursor.execute(
            """
            UPDATE adverts SET duration = ?, weight = ?, reference = ? WHERE id = ?
        """,
            (new_duration, new_weight, new_reference, advert_id),
        )
        cursor.close()
        return advert_id

    def get_ad_cost_100_views(self, advert_id):
        advert = self.get_advert(advert_id)
        if not advert:
            return 0.0

        duration = advert[2]
        weight = advert[6]

        # Cost added for 100 views
        return float(duration * weight * ad_cost_per_second_per_100_views)

    def get_ad_cost(self, advert_id):
        advert = self.get_advert(advert_id)
        if not advert:
            return 0.0

        duration = advert[2]
        weight = advert[6]

        # Cost added for one view
        return float(duration * weight * ad_cost_per_second_per_100_views) / 100

    def get_advert(self, advert_id):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT * FROM adverts WHERE id = ?
        """,
            (advert_id,),
        )
        fetched = cursor.fetchone()
        cursor.close()
        return fetched

    def get_adverts(self, account_id=None, status=None):
        cursor = self.conn.cursor()
        query = "SELECT * FROM adverts WHERE 1=1"
        params = []
        if account_id is not None:
            query += " AND account_id = ?"
            params.append(account_id)
        if status is not None:
            query += " AND status = ?"
            params.append(status)
        cursor.execute(query, params)
        fetched = cursor.fetchall()
        cursor.close()
        return fetched

    def get_active_adverts(self):
        """Returns all adverts currently eligible to be shown (status = active)."""
        return self.get_adverts(status=AD_STATUS_ACTIVE)

    def set_advert_status(self, advert_id, status):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            UPDATE adverts SET status = ? WHERE id = ?
        """,
            (status, advert_id),
        )
        cursor.close()

    def disable_advert(self, advert_id):
        self.set_advert_status(advert_id, AD_STATUS_DISABLED)

    def top_up_advert(self, advert_id, new_spend_limit):
        """
        Raises an advert's spend_limit (e.g. owner adds more budget).
        If the ad had hit its limit and the new limit is above what's
        already been spent, it's automatically reactivated to active.
        """
        advert = self.get_advert(advert_id)
        if not advert:
            return None
        cursor = self.conn.cursor()
        cursor.execute(
            """
            UPDATE adverts SET spend_limit = ? WHERE id = ?
        """,
            (new_spend_limit, advert_id),
        )
        cursor.close()
        advert = self.get_advert(advert_id)
        if advert[5] == AD_STATUS_HIT_LIMIT and advert[4] < new_spend_limit:
            self.set_advert_status(advert_id, AD_STATUS_ACTIVE)
        return advert_id

    def pick_weighted_advert(self, adverts):
        """
        Given a list of advert rows (as returned by get_active_adverts),
        picks one at random using the `weight` column so that an ad with
        weight 2 is twice as likely to be picked as one with weight 1,
        and one with weight 0.5 is half as likely.
        Returns None if the list is empty or all weights are 0.
        """
        if not adverts:
            return None
        weights = [advert[6] for advert in adverts]  # weight column
        if sum(weights) <= 0:
            return None
        return random.choices(adverts, weights=weights, k=1)[0]

    def get_advert_cost_owed(self, advert_id):
        """
        Fetches cost_owed by column name rather than tuple position.
        Needed because on databases where this column was added via the
        ALTER TABLE migration (existing production DBs), it lands at the
        end of the row; on freshly created tables it's defined earlier in
        the schema. Reading by name sidesteps that inconsistency.
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT cost_owed FROM adverts WHERE id = ?
        """,
            (advert_id,),
        )
        fetched = cursor.fetchone()
        cursor.close()
        if fetched is None:
            return 0.0
        try:
            return float(fetched[0]) if fetched[0] is not None else 0.0
        except (TypeError, ValueError):
            return 0.0

    def select_advert(self):
        """
        Picks an active advert (weighted by `weight`), and accrues the cost
        computed by get_ad_cost() into that advert's cost_owed remainder.

        This updates the database with the new accrued cost so that
        accumulate_advert_costs() can later charge the whole units.
        """
        candidates = list(self.get_active_adverts())

        while candidates:
            advert = self.pick_weighted_advert(candidates)
            if advert is None:
                return None

            advert_id = advert[0]
            account_id = advert[1]
            raw_cost = self.get_ad_cost(advert_id)

            existing_owed = self.get_advert_cost_owed(advert_id)
            new_cost_owed = existing_owed + raw_cost

            # Simple check: If they owe money but their balance is negative or empty,
            # we skip this ad so they don't rack up debt they can't pay.
            cost_to_charge = int(new_cost_owed)
            if cost_to_charge > 0:
                balance = self.get_balance(account_id)
                if balance < cost_to_charge:
                    # Can't afford the charge due, remove from candidates and try another
                    candidates = [a for a in candidates if a[0] != advert_id]
                    continue

            try:
                cursor = self.conn.cursor()
                # Update the running cost accumulator in the DB
                cursor.execute(
                    """
                        UPDATE adverts SET cost_owed = ? WHERE id = ?
                        """,
                    (new_cost_owed, advert_id),
                )
                cursor.close()
                self.commit()  # Make sure we commit the view accrual!

                return self.get_advert(advert_id)
            except Exception as e:
                print(e)
                self.conn.rollback()
                return None

        return None

    def insert_advert_cost(self, advert_id, account_id, amount):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO advert_costs (id, advert_id, account_id, amount) VALUES (?, ?, ?, ?)
        """,
            (random_string(32), advert_id, account_id, amount),
        )
        cursor.close()

    def get_advert_costs(self, advert_id):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT * FROM advert_costs WHERE advert_id = ?
        """,
            (advert_id,),
        )
        fetched = cursor.fetchall()
        cursor.close()
        return fetched

    def close(self):
        self.conn.close()

    def commit(self):
        self.conn.commit()


user = {
    "name": "admin",
    "hidden": True,
    "admin": True,
    "accounts": [
        {
            "type": 2,
            "name": "Reserve",
            "initial": 0,
            "interest": 0,
        },
        {
            "type": 2,
            "name": "Bonus",
            "initial": 0,
            "interest": 0,
        },
        {
            "type": 0,
            "name": "Revenue",
            "initial": 0,
            "interest": 0,
        },
    ],
}

admin_id = None

db = Database()
db.create_table()
db.commit()


user_id = db.insert_user(
    user["name"], hidden=user.get("hidden", False), admin=user.get("admin", False)
)
if user_id:
    admin_id = user_id
    for account in user.get("accounts", []):
        account_id = db.insert_account(
            user_id, account["type"], account["name"], account.get("interest", 0.05)
        )
        db.insert_transaction(account_id, account["initial"] * 100, "Initial balance")
else:
    admin_id = db.get_user(user["name"])[0]

ad_revenue_account_id = None
try:
    ad_revenue_account_id = db.get_users_first_current_account(admin_id)[0]
except:
    pass

db.commit()
