import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import psycopg  # noqa: E402

from app.core.database import pool  # noqa: E402
from app.core.security import hash_password  # noqa: E402


def main() -> int:
    name = input("Nama kasir: ").strip()
    email = input("Email kasir: ").strip().lower()
    password = getpass.getpass("Password kasir (minimal 12 karakter): ")
    if not name or "@" not in email or len(password) < 12:
        print("GAGAL: nama/email tidak valid atau password kurang dari 12 karakter.", file=sys.stderr)
        return 1
    if password != getpass.getpass("Ulangi password: "):
        print("GAGAL: konfirmasi password berbeda.", file=sys.stderr)
        return 1

    pool.open(wait=True, timeout=15)
    try:
        with pool.connection() as conn:
            if conn.execute("SELECT 1 FROM app.users WHERE role = 'cashier'").fetchone():
                print("GAGAL: akun kasir sudah ada. Script ini tidak mengubah akun yang ada.", file=sys.stderr)
                return 1
            conn.execute(
                "INSERT INTO app.users (name, email, password_hash, role) VALUES (%s, %s, %s, 'cashier')",
                (name, email, hash_password(password)),
            )
    except psycopg.errors.UniqueViolation:
        print("GAGAL: email sudah dipakai akun lain.", file=sys.stderr)
        return 1
    finally:
        pool.close()
    print("Akun kasir berhasil dibuat (password disimpan sebagai hash Argon2).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
