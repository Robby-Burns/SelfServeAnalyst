import sqlite3
import random
from datetime import datetime, timedelta


def create_dummy_db():
    """Creates a dummy Credit Union database with populated data."""

    conn = sqlite3.connect('credit_union.db')
    cursor = conn.cursor()

    # 1. CLEANUP
    cursor.execute('DROP TABLE IF EXISTS loans')
    cursor.execute('DROP TABLE IF EXISTS accounts')
    cursor.execute('DROP TABLE IF EXISTS members')

    # 2. CREATE TABLES
    # Members: The core identity
    cursor.execute('''
                   CREATE TABLE members
                   (
                       member_id INTEGER PRIMARY KEY,
                       name      TEXT NOT NULL,
                       email     TEXT,
                       age       INTEGER,
                       join_date DATE
                   )
                   ''')

    # Accounts: Checking/Savings (Linked to Member via member_id)
    cursor.execute('''
                   CREATE TABLE accounts
                   (
                       account_id   INTEGER PRIMARY KEY,
                       member_id    INTEGER,
                       account_type TEXT,
                       balance      REAL,
                       open_date    DATE,
                       FOREIGN KEY (member_id) REFERENCES members (member_id)
                   )
                   ''')

    # Loans: Auto/Mortgage (Linked to Member via member_id)
    cursor.execute('''
                   CREATE TABLE loans
                   (
                       loan_id       INTEGER PRIMARY KEY,
                       member_id     INTEGER,
                       loan_type     TEXT,
                       amount        REAL,
                       interest_rate REAL,
                       status        TEXT,
                       FOREIGN KEY (member_id) REFERENCES members (member_id)
                   )
                   ''')

    print("Tables created. Generating fake data...")

    # 3. POPULATE WITH RANDOM DATA
    first_names = ["John", "Jane", "Alice", "Bob", "Charlie", "Diana", "Edward", "Fiona", "George", "Hannah"]
    last_names = ["Smith", "Doe", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez"]

    account_types = ["Checking", "Savings", "Money Market"]
    loan_types = ["Auto", "Mortgage", "Personal", "HELOC"]
    statuses = ["Active", "Paid Off", "Defaulted"]

    # Generate 50 members
    for i in range(1, 51):
        # Create Member
        f_name = random.choice(first_names)
        l_name = random.choice(last_names)
        name = f"{f_name} {l_name}"
        email = f"{f_name.lower()}.{l_name.lower()}@example.com"
        age = random.randint(18, 85)
        # Random join date within last 10 years
        days_ago = random.randint(0, 3650)
        join_date = (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d')

        cursor.execute('INSERT INTO members (name, email, age, join_date) VALUES (?, ?, ?, ?)',
                       (name, email, age, join_date))
        member_id = cursor.lastrowid

        # Create 1-2 Accounts for this member
        for _ in range(random.randint(1, 2)):
            acct_type = random.choice(account_types)
            balance = round(random.uniform(100.00, 50000.00), 2)
            cursor.execute('INSERT INTO accounts (member_id, account_type, balance, open_date) VALUES (?, ?, ?, ?)',
                           (member_id, acct_type, balance, join_date))

        # Randomly assign a Loan (50% chance)
        if random.choice([True, False]):
            l_type = random.choice(loan_types)
            amount = round(random.uniform(5000.00, 300000.00), 2)
            rate = round(random.uniform(2.5, 9.9), 2)
            status = random.choice(statuses)
            cursor.execute(
                'INSERT INTO loans (member_id, loan_type, amount, interest_rate, status) VALUES (?, ?, ?, ?, ?)',
                (member_id, l_type, amount, rate, status))

    conn.commit()
    conn.close()
    print("Database 'credit_union.db' populated successfully!")


if __name__ == "__main__":
    create_dummy_db()