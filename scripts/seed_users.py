"""
Seed team accounts with generated strong passwords and retire the old demo login.

    python scripts/seed_users.py                 # create the accounts in SEED_ACCOUNTS (skips existing)
    python scripts/seed_users.py --reset         # also issue new passwords for accounts that already exist
    python scripts/seed_users.py --retire-demo   # also deactivate admin@infosys.com

Passwords are never printed. They are written to seed_credentials.local.txt (git-ignored) next to
this project; hand them out over a secure channel, then delete the file. Each person should change
their password on first sign-in (POST /auth/change-password).

To seed real people instead of the role accounts below, create seed_accounts.local.json:
    [{"name": "Jane Doe", "email": "jane.doe@infosys.com", "role": "bid_author"}, ...]
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app.core.database import SessionLocal  # noqa: E402
from app.core.security import generate_strong_password, hash_password  # noqa: E402
from app.models.user import User  # noqa: E402

DEMO_EMAIL = "admin@infosys.com"
SEED_ACCOUNTS = [
    {"name": "Social Value Administrator", "email": "sv.admin@infosys.com", "role": "superadmin"},
    {"name": "Social Value Bid Author", "email": "sv.bidauthor@infosys.com", "role": "bid_author"},
    {"name": "Social Value Reviewer", "email": "sv.reviewer@infosys.com", "role": "reviewer"},
]
ACCOUNTS_FILE = os.path.join(BASE_DIR, "seed_accounts.local.json")
CREDENTIALS_FILE = os.path.join(BASE_DIR, "seed_credentials.local.txt")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="issue new passwords for existing accounts")
    parser.add_argument("--retire-demo", action="store_true", help=f"deactivate {DEMO_EMAIL}")
    args = parser.parse_args()

    accounts = SEED_ACCOUNTS
    if os.path.exists(ACCOUNTS_FILE):
        with open(ACCOUNTS_FILE, encoding="utf-8") as f:
            accounts = json.load(f)

    issued = []
    with SessionLocal() as db:
        for acct in accounts:
            email = acct["email"].lower().strip()
            user = db.query(User).filter(User.email == email).first()
            if user and not args.reset:
                print(f"skip   {email} (exists; use --reset for a new password)")
                continue
            password = generate_strong_password()
            if user:
                user.password_hash = hash_password(password)
                user.role = acct["role"]
                user.is_active = True
                print(f"reset  {email} ({acct['role']})")
            else:
                db.add(User(name=acct["name"], email=email, password_hash=hash_password(password),
                            role=acct["role"], is_active=True))
                print(f"create {email} ({acct['role']})")
            issued.append((email, acct["role"], password))

        if args.retire_demo:
            demo = db.query(User).filter(User.email == DEMO_EMAIL).first()
            if demo:
                demo.is_active = False
                # Also scramble the hash so the old password is useless even if reactivated.
                demo.password_hash = hash_password(generate_strong_password(32))
                print(f"retire {DEMO_EMAIL} (deactivated)")
        db.commit()

    if issued:
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        with open(CREDENTIALS_FILE, "a", encoding="utf-8") as f:
            f.write(f"# Issued {stamp}. Share securely, then delete this file.\n")
            for email, role, password in issued:
                f.write(f"{email}\t{role}\t{password}\n")
        print(f"\n{len(issued)} password(s) written to {CREDENTIALS_FILE}")


if __name__ == "__main__":
    main()
