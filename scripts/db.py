"""Peralatan database proyek. Jalankan dari root: python scripts/db.py --help."""
import argparse
import getpass
import hashlib
import os
from pathlib import Path
import sys

import psycopg
from psycopg import sql
from dotenv import load_dotenv
from pwdlib import PasswordHash

ROOT = Path(__file__).resolve().parents[1]
TABLES = (
    'users', 'categories', 'menus', 'restaurant_tables', 'ordering_sessions',
    'customer_accesses', 'orders', 'order_items', 'order_adjustments', 'payments',
)
load_dotenv(ROOT / '.env', override=False, interpolate=False)


def connect(as_app=False):
    prefix = 'DB_APP_' if as_app else 'DB_ADMIN_'
    values = {
        'host': os.getenv('DB_HOST', ''),
        'port': os.getenv('DB_PORT', '5432'),
        'dbname': os.getenv('DB_NAME', 'postgres'),
        'user': os.getenv(prefix + 'USER', ''),
        'password': os.getenv(prefix + 'PASSWORD', ''),
        'sslmode': os.getenv('DB_SSLMODE', 'require'),
        'connect_timeout': 10,
        'application_name': 'trio_saung_db_tools',
    }
    if any(not values[k] or 'ISI_' in values[k] for k in ('host', 'user', 'password')):
        raise ValueError('Lengkapi .env; masih ada nilai kosong/ISI_.')
    if os.getenv('DB_SSLROOTCERT'):
        values['sslrootcert'] = os.environ['DB_SSLROOTCERT']
    return psycopg.connect(**values)


def check(as_app=False):
    with connect(as_app) as conn:
        row = conn.execute('SELECT current_database(), current_user, current_timestamp').fetchone()
        print('Koneksi OK. Database:', row[0], '| role:', row[1], '| waktu:', row[2])
        if as_app:
            count = conn.execute('SELECT count(*) FROM app.menus').fetchone()[0]
            print('Role aplikasi dapat membaca katalog. Jumlah menu:', count)


def migration_files():
    paths = sorted((ROOT / 'database/migrations').glob('*.sql'))
    if not paths:
        raise ValueError('Folder migrasi kosong.')
    return paths


def checksum(path):
    # Normalisasi CRLF agar checkout Git di Windows tidak merusak checksum.
    return hashlib.sha256(path.read_text(encoding='utf-8').encode('utf-8')).hexdigest()


def migrate():
    with connect() as conn:
        # Semua migrasi pending + ledger commit bersama; satu error rollback semua.
        conn.execute('SET LOCAL lock_timeout = \'10s\'')
        conn.execute('SET LOCAL statement_timeout = \'60s\'')
        conn.execute('SELECT pg_advisory_xact_lock(714021, 1)')
        conn.execute('CREATE SCHEMA IF NOT EXISTS app_meta')
        conn.execute('REVOKE ALL ON SCHEMA app_meta FROM PUBLIC')
        conn.execute('''CREATE TABLE IF NOT EXISTS app_meta.schema_migrations (
            filename text PRIMARY KEY,
            sha256 text NOT NULL,
            applied_at timestamptz NOT NULL DEFAULT now()
        )''')
        conn.execute('REVOKE ALL ON app_meta.schema_migrations FROM PUBLIC')
        applied = dict(conn.execute('SELECT filename, sha256 FROM app_meta.schema_migrations').fetchall())
        files = migration_files()
        names = {p.name for p in files}
        if set(applied) - names:
            raise ValueError('Ada migrasi database yang tidak tersedia di checkout ini. Pull versi repo yang benar.')
        for path in files:
            digest = checksum(path)
            if path.name in applied:
                if applied[path.name] != digest:
                    raise ValueError('Checksum berbeda: ' + path.name + '. Pulihkan file asli, lalu buat migrasi baru.')
                print('SKIP', path.name)
                continue
            if applied and path.name < max(applied):
                raise ValueError('Migrasi baru harus memiliki nomor setelah migrasi yang sudah diterapkan.')
            conn.execute(path.read_text(encoding='utf-8'), prepare=False)
            conn.execute('INSERT INTO app_meta.schema_migrations(filename, sha256) VALUES (%s,%s)', (path.name, digest))
            print('APPLY', path.name, '(commit setelah semua langkah berhasil)')
    print('Migrasi selesai dan sudah commit.')


def status():
    with connect() as conn:
        if conn.execute("SELECT to_regclass('app_meta.schema_migrations')").fetchone()[0] is None:
            print('Belum ada migrasi tercatat.')
            return
        applied = dict(conn.execute('SELECT filename, sha256 FROM app_meta.schema_migrations').fetchall())
        files = migration_files()
        mismatch = False
        for path in files:
            state = 'PENDING' if path.name not in applied else ('APPLIED' if applied[path.name] == checksum(path) else 'CHANGED')
            mismatch = mismatch or state == 'CHANGED'
            print(state, path.name)
        for name in sorted(set(applied) - {p.name for p in files}):
            print('MISSING LOCAL FILE', name)
            mismatch = True
        if mismatch:
            raise ValueError('Riwayat file dan database berbeda; jangan menjalankan migrasi berikutnya.')


def require_development():
    if os.getenv('APP_ENV') not in ('development', 'test'):
        raise ValueError('Perintah ini hanya untuk APP_ENV=development atau test.')


def seed():
    require_development()
    with connect() as conn:
        conn.execute((ROOT / 'database/seeds/001_demo_catalog.sql').read_text(encoding='utf-8'), prepare=False)
    print('Seed selesai: 3 kategori, 6 menu, 3 meja pada database baru. Tidak menimpa ID yang sudah ada.')


def verify():
    with connect() as conn:
        rows = conn.execute("SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname='app'").fetchall()
        actual = dict(rows)
        if any(t not in actual or not actual[t] for t in TABLES):
            raise ValueError('Tabel inti belum lengkap atau RLS belum aktif.')
        print('OK: 10 tabel inti dan RLS aktif.')
        for t in ('categories', 'menus', 'restaurant_tables', 'users', 'orders', 'payments'):
            n = conn.execute(sql.SQL('SELECT count(*) FROM app.{}').format(sql.Identifier(t))).fetchone()[0]
            print(t + ':', n)
        # Temukan inkonsistensi yang harus dicegah transaksi FastAPI.
        issues = conn.execute('''
            SELECT 'payment_status', count(*) FROM app.ordering_sessions s
              LEFT JOIN app.payments p ON p.session_id=s.id
              WHERE (s.status='paid') <> (p.id IS NOT NULL)
            UNION ALL
            SELECT 'takeaway_fulfillment', count(*) FROM app.orders o
              JOIN app.ordering_sessions s ON s.id=o.session_id
              WHERE s.session_type='takeaway' AND o.fulfillment_type<>'takeaway'
            UNION ALL
            SELECT 'payment_total', count(*) FROM app.payments p
              WHERE p.total_amount <> COALESCE((SELECT sum(i.unit_price_snapshot*i.quantity)
                FROM app.orders o JOIN app.order_items i ON i.order_id=o.id WHERE o.session_id=p.session_id),0)
            UNION ALL
            SELECT 'cancelled_session_has_items', count(*) FROM app.ordering_sessions s
              WHERE s.status='cancelled' AND EXISTS (SELECT 1 FROM app.orders o
                JOIN app.order_items i ON i.order_id=o.id WHERE o.session_id=s.id AND i.quantity>0)
            UNION ALL
            SELECT 'order_status_or_empty', count(*) FROM app.orders o
              WHERE NOT EXISTS (SELECT 1 FROM app.order_items i WHERE i.order_id=o.id)
                OR (o.status='cancelled') <> NOT EXISTS (
                  SELECT 1 FROM app.order_items i WHERE i.order_id=o.id AND i.quantity>0)
        ''').fetchall()
        for label, n in issues:
            print(label + ':', n)
        if any(n for _, n in issues):
            raise ValueError('Ditemukan inkonsistensi transaksi. Periksa implementasi backend.')
    print('Verifikasi struktur dan konsistensi dasar OK; ini bukan tes API atau konkurensi.')


def provision_app():
    password = getpass.getpass('Password BARU untuk role database trio_app (minimal 20 karakter): ')
    if len(password) < 20 or password != getpass.getpass('Ulangi password role: '):
        raise ValueError('Password terlalu pendek atau konfirmasi berbeda.')
    with connect() as conn:
        conn.execute('SELECT pg_advisory_xact_lock(714021, 2)')
        exists = conn.execute("SELECT 1 FROM pg_roles WHERE rolname='trio_app'").fetchone()
        if exists:
            raise ValueError('Role trio_app sudah ada. Script tidak mereset password/izin role yang sudah ada.')
        conn.execute(sql.SQL('CREATE ROLE trio_app LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS').format(sql.Literal(password)))
        conn.execute('GRANT USAGE ON SCHEMA app TO trio_app')
        # Tidak memberikan CREATE, DELETE, TRUNCATE, atau akses migrasi.
        for t in TABLES:
            privilege = 'SELECT, INSERT' if t in ('payments', 'order_adjustments') else 'SELECT, INSERT, UPDATE'
            conn.execute(sql.SQL('GRANT ' + privilege + ' ON app.{} TO trio_app').format(sql.Identifier(t)))
            conn.execute(sql.SQL('CREATE POLICY backend_access ON app.{} TO trio_app USING (true) WITH CHECK (true)').format(sql.Identifier(t)))
    print('Role trio_app berhasil dibuat. Simpan password di DB_APP_PASSWORD; jangan ke Git.')


def bootstrap_admin():
    name = input('Nama admin: ').strip()
    email = input('Email admin: ').strip().lower()
    password = getpass.getpass('Password admin aplikasi (minimal 12 karakter): ')
    if not name or '@' not in email or len(password) < 12:
        raise ValueError('Nama/email tidak valid atau password terlalu pendek.')
    if password != getpass.getpass('Ulangi password admin: '):
        raise ValueError('Konfirmasi password berbeda.')
    digest = PasswordHash.recommended().hash(password)
    with connect() as conn:
        conn.execute('SELECT pg_advisory_xact_lock(714021, 3)')
        if conn.execute("SELECT 1 FROM app.users WHERE role='admin'").fetchone():
            raise ValueError('Admin sudah ada. Bootstrap tidak mengubah password akun yang ada.')
        conn.execute("INSERT INTO app.users(name,email,password_hash,role) VALUES (%s,%s,%s,'admin')", (name,email,digest))
    print('Admin berhasil dibuat menggunakan hash Argon2. Endpoint login tetap perlu dibuat backend.')


def test_constraints():
    # Sengaja dibatasi ke database test lokal, bukan Supabase development bersama.
    if os.getenv('APP_ENV') != 'test' or os.getenv('DB_NAME') != 'trio_test' or os.getenv('DB_HOST') not in ('localhost','127.0.0.1'):
        raise ValueError('Test tulis hanya boleh pada database lokal trio_test dengan APP_ENV=test.')
    with connect() as conn:
        conn.execute((ROOT / 'database/checks/constraints.sql').read_text(encoding='utf-8'), prepare=False)
        conn.rollback()
    print('Tes constraint lulus; data tes di-rollback.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['check','check-app','status','migrate','seed','verify','provision-app','bootstrap-admin','test-constraints'])
    args = parser.parse_args()
    print('Target:', os.getenv('DB_TARGET_LABEL','belum diberi label'))
    actions = {'check': check, 'check-app': lambda: check(True), 'status': status,
               'migrate': migrate, 'seed': seed, 'verify': verify,
               'provision-app': provision_app, 'bootstrap-admin': bootstrap_admin,
               'test-constraints': test_constraints}
    try:
        actions[args.command]()
    except (ValueError, psycopg.Error) as exc:
        if isinstance(exc, ValueError):
            print('GAGAL:', str(exc), file=sys.stderr)
        else:
            # Tidak mencetak exception/DSN lengkap: hindari kebocoran credential.
            print('Database gagal:', type(exc).__name__, '| SQLSTATE:', exc.sqlstate or 'connection', file=sys.stderr)
            if exc.diag.constraint_name:
                print('Constraint:', exc.diag.constraint_name, file=sys.stderr)
            print('Lihat bagian troubleshooting di docs/TUTORIAL.md.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

