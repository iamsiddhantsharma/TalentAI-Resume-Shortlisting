"""
TalentAI — HR Account Management CLI

Allows system administrators to provision, list, and reset passwords for authorized HR team accounts.

Usage:
    python -m app.cli.manage_hr create --username hr_lead --email hr@company.com --name "Jane Doe"
    python -m app.cli.manage_hr list
    python -m app.cli.manage_hr reset-password --username hr_lead
"""

import argparse
import asyncio
import getpass
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.auth.auth_service import auth_service
from app.database.collections import MongoCollections
from app.database.mongodb import mongodb


async def cmd_create(args):
    await mongodb.connect()
    try:
        username = args.username.strip().lower()
        email = args.email.strip().lower()
        name = args.name.strip()

        if len(username) < 3:
            print("Error: Username must be at least 3 characters long.", file=sys.stderr)
            return 1

        password = args.password
        if not password:
            password = getpass.getpass(f"Enter password for HR user '{username}' (min 8 chars): ")
            if len(password) < 8:
                print("Error: Password must be at least 8 characters long.", file=sys.stderr)
                return 1
            confirm = getpass.getpass("Confirm password: ")
            if password != confirm:
                print("Error: Passwords do not match.", file=sys.stderr)
                return 1
        else:
            if len(password) < 8:
                print("Error: Password must be at least 8 characters long.", file=sys.stderr)
                return 1

        user = await auth_service.create_hr_user(
            username=username,
            password=password,
            full_name=name,
            email=email,
        )
        print(f"Successfully created HR user: {user['username']} ({user['full_name']})")
        return 0
    except Exception as e:
        print(f"Error creating user: {e}", file=sys.stderr)
        return 1
    finally:
        await mongodb.disconnect()


async def cmd_list(args):
    await mongodb.connect()
    try:
        users = await auth_service.list_hr_users()
        print("\n" + "=" * 60)
        print("TALENTAI — AUTHORIZED HR TEAM ACCOUNTS")
        print("=" * 60)
        if not users:
            print("No HR users registered yet.")
        for u in users:
            status = "Active" if u.get("is_active", True) else "Inactive"
            last_login = u.get("last_login_at") or "Never"
            print(f"- Username:   {u['username']}")
            print(f"  Name:       {u.get('full_name', '-')}")
            print(f"  Email:      {u.get('email', '-')}")
            print(f"  Role:       {u.get('role', 'hr')}")
            print(f"  Status:     {status}")
            print(f"  Last Login: {last_login}")
            print("-" * 60)
        return 0
    finally:
        await mongodb.disconnect()


async def cmd_reset_password(args):
    await mongodb.connect()
    try:
        username = args.username.strip().lower()
        user = await auth_service.get_user_by_username(username)
        if not user:
            print(f"Error: HR user '{username}' not found.", file=sys.stderr)
            return 1

        password = args.password
        if not password:
            password = getpass.getpass(f"Enter new password for HR user '{username}' (min 8 chars): ")
            if len(password) < 8:
                print("Error: Password must be at least 8 characters long.", file=sys.stderr)
                return 1
            confirm = getpass.getpass("Confirm new password: ")
            if password != confirm:
                print("Error: Passwords do not match.", file=sys.stderr)
                return 1
        else:
            if len(password) < 8:
                print("Error: Password must be at least 8 characters long.", file=sys.stderr)
                return 1

        db = mongodb.get_database()
        users_col = db[MongoCollections.HR_USERS]
        new_hash = auth_service.hash_password(password)
        await users_col.update_one({"username": username}, {"$set": {"password_hash": new_hash}})

        # Invalidate all existing sessions for this user
        sessions_col = db[MongoCollections.HR_SESSIONS]
        await sessions_col.delete_many({"user_id": str(user["_id"])})

        print(f"Successfully updated password for HR user '{username}'. Active sessions cleared.")
        return 0
    finally:
        await mongodb.disconnect()


def main():
    parser = argparse.ArgumentParser(description="TalentAI HR User Management CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # create
    create_parser = subparsers.add_parser("create", help="Create a new HR team user account")
    create_parser.add_argument("--username", required=True, help="Username")
    create_parser.add_argument("--email", default="hr@talentai.local", help="Email address")
    create_parser.add_argument("--name", default="HR Team Member", help="Full name")
    create_parser.add_argument("--password", default=None, help="Optional password (prompted if omitted)")

    # list
    subparsers.add_parser("list", help="List all registered HR users")

    # reset-password
    reset_parser = subparsers.add_parser("reset-password", help="Reset password for an HR user")
    reset_parser.add_argument("--username", required=True, help="Username")
    reset_parser.add_argument("--password", default=None, help="Optional new password (prompted if omitted)")

    args = parser.parse_args()

    if args.command == "create":
        code = asyncio.run(cmd_create(args))
    elif args.command == "list":
        code = asyncio.run(cmd_list(args))
    elif args.command == "reset-password":
        code = asyncio.run(cmd_reset_password(args))
    else:
        parser.print_help()
        code = 1

    sys.exit(code)


if __name__ == "__main__":
    main()
