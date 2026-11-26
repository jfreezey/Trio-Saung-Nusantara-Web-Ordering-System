import argparse
from contextlib import contextmanager
import getpass
import hashlib
import os
from pathlib import Path
import ssl
import sys

import pg8000.dbapi as pg
from pg8000.native import identifier, literal
from dotenv import load_dotenv
from pwdlib import PasswordHash


ROOT = Path(__file__).resolve().parents[1]

TABLES = (
    'users',
    'categories',
    'menus',
    'restaurant_tables',
    'ordering_sessions',
    'customer_accesses',
    'orders',
    'order_items',
    'order_adjustments',
    'payments',
)

load_dotenv(ROOT / '.env', override=False, interpolate=False)


class QueryResult:
    def __init__(self, rows):
        self.rows = rows

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows


class Database:
    def __init__(self, connection):
        self.connection = connection

    def execute(self, statement, params=None):
        cursor = self.connection.cursor()

        try:
            if params is None:
                cursor.execute(statement)
            else:
                cursor.execute(statement, params)

            rows = cursor.fetchall() if cursor.description else []
            return QueryResult(rows)
        finally:
            cursor.close()

    def rollback(self):
        self.connection.rollback()


def ssl_settings():
    mode = os.getenv('DB_SSLMODE', 'require').strip().lower()
    root_cert = os.getenv('DB_SSLROOTCERT', '').strip()

    if mode == 'disable':
        if (
            os.getenv('APP_ENV') not in ('development', 'test')
            or os.getenv('DB_HOST') not in ('localhost', '127.0.0.1')
        ):
            raise ValueError(
                'DB_SSLMODE=disable hanya diizinkan untuk database lokal.'
            )

        return False

    if mode not in ('require', 'verify-ca', 'verify-full'):
        raise ValueError(
            'DB_SSLMODE harus require, verify-ca, verify-full, atau disable.'
        )

    if root_cert:
        cert_path = Path(root_cert).expanduser()

        if not cert_path.is_absolute():
            cert_path = ROOT / cert_path

        if not cert_path.is_file():
            raise ValueError('File DB_SSLROOTCERT tidak ditemukan.')

        context = ssl.create_default_context(cafile=str(cert_path))
    else:
        context = ssl.create_default_context()

    if mode == 'verify-full':
        # Memverifikasi sertifikat dan hostname server.
        return context

    if mode == 'verify-ca' or root_cert:
        # Memverifikasi sertifikat tanpa memeriksa hostname.
        context.check_hostname = False
        return context

    # DB_SSLMODE=require: TLS wajib, tanpa verifikasi identitas server.
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context


@contextmanager
def connect(as_app=False):
    prefix = 'DB_APP_' if as_app else 'DB_ADMIN_'

    host = os.getenv('DB_HOST', '')
    user = os.getenv(prefix + 'USER', '')
    password = os.getenv(prefix + 'PASSWORD', '')

    if any(
        not value or 'ISI_' in value
        for value in (host, user, password)
    ):
        raise ValueError('Lengkapi .env; masih ada nilai kosong/ISI_.')

    try:
        port = int(os.getenv('DB_PORT', '5432'))
    except ValueError:
        raise ValueError('DB_PORT harus berupa angka.') from None

    if not 1 <= port <= 65535:
        raise ValueError('DB_PORT harus antara 1 dan 65535.')

    connection = pg.connect(
        host=host,
        port=port,
        database=os.getenv('DB_NAME', 'postgres'),
        user=user,
        password=password,
        ssl_context=ssl_settings(),
        timeout=10,
        application_name='trio_saung_db_tools',
    )

    try:
        cursor = connection.cursor()

        try:
            cursor.execute('SET standard_conforming_strings = on')
        finally:
            cursor.close()

        yield Database(connection)
        connection.commit()

    except BaseException:
        try:
            connection.rollback()
        except Exception:
            # Jangan menutupi error awal jika koneksi sudah terputus.
            pass

        raise

    finally:
        connection.close()


def check(as_app=False):
    with connect(as_app) as conn:
        row = conn.execute(
            'SELECT current_database(), current_user, current_timestamp'
        ).fetchone()

        print(
            'Koneksi OK. Database:',
            row[0],
            '| role:',
            row[1],
            '| waktu:',
            row[2],
        )

        if as_app:
            count = conn.execute(
                'SELECT count(*) FROM app.menus'
            ).fetchone()[0]

            print(
                'Role aplikasi dapat membaca katalog. Jumlah menu:',
                count,
            )


def migration_files():
    paths = sorted((ROOT / 'database/migrations').glob('*.sql'))

    if not paths:
        raise ValueError('Folder migrasi kosong.')

    return paths


def checksum(path):
    # read_text menormalisasi CRLF agar checksum konsisten di Windows.
    content = path.read_text(encoding='utf-8')
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

def matches_migration(path, recorded, current):
    # Versi main dan foundation dari 0001 hanya berbeda pada komentar.
    return recorded == current or (
        path.name == "0001_initial_schema.sql"
        and recorded == "52c3fa6364e85e4686db0d3919ea77b01e90bd808abe81de295f0d712186685d"
        and current == "0d81191a66c449608d0d777bd26ec8aae270d302e43d6d6a1cf6b7a1bb3b10a8"
    )

def migrate():
    with connect() as conn:
        # Semua migrasi pending dan ledger di-commit bersama.
        # Jika ada kegagalan, seluruh transaksi di-rollback.
        conn.execute("SET LOCAL lock_timeout = '10s'")
        conn.execute("SET LOCAL statement_timeout = '60s'")
        conn.execute('SELECT pg_advisory_xact_lock(714021, 1)')

        conn.execute('CREATE SCHEMA IF NOT EXISTS app_meta')
        conn.execute('REVOKE ALL ON SCHEMA app_meta FROM PUBLIC')

        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS app_meta.schema_migrations (
                filename text PRIMARY KEY,
                sha256 text NOT NULL,
                applied_at timestamptz NOT NULL DEFAULT now()
            )
            '''
        )

        conn.execute(
            'REVOKE ALL ON app_meta.schema_migrations FROM PUBLIC'
        )

        applied = dict(
            conn.execute(
                'SELECT filename, sha256 FROM app_meta.schema_migrations'
            ).fetchall()
        )

        files = migration_files()
        names = {path.name for path in files}

        if set(applied) - names:
            raise ValueError(
                'Ada migrasi database yang tidak tersedia di checkout ini. '
                'Pull versi repo yang benar.'
            )

        for path in files:
            digest = checksum(path)

            if path.name in applied:
                if not matches_migration(path, applied[path.name], digest):
                    raise ValueError(
                        'Checksum berbeda: '
                        + path.name
                        + '. Pulihkan file asli, lalu buat migrasi baru.'
                    )

                print('SKIP', path.name)
                continue

            if applied and path.name < max(applied):
                raise ValueError(
                    'Migrasi baru harus memiliki nomor setelah migrasi '
                    'yang sudah diterapkan.'
                )

            conn.execute(path.read_text(encoding='utf-8'))

            conn.execute(
                '''
                INSERT INTO app_meta.schema_migrations(filename, sha256)
                VALUES (%s, %s)
                ''',
                (path.name, digest),
            )

            print(
                'APPLY',
                path.name,
                '(commit setelah semua langkah berhasil)',
            )

    print('Migrasi selesai dan sudah commit.')


def status():
    with connect() as conn:
        row = conn.execute(
            "SELECT to_regclass('app_meta.schema_migrations')"
        ).fetchone()

        if row[0] is None:
            print('Belum ada migrasi tercatat.')
            return

        applied = dict(
            conn.execute(
                'SELECT filename, sha256 FROM app_meta.schema_migrations'
            ).fetchall()
        )

        files = migration_files()
        mismatch = False

        for path in files:
            if path.name not in applied:
                state = 'PENDING'
            elif matches_migration(path, applied[path.name], checksum(path)):
                state = 'APPLIED'
            else:
                state = 'CHANGED'

            if state == 'CHANGED':
                mismatch = True

            print(state, path.name)

        local_names = {path.name for path in files}

        for name in sorted(set(applied) - local_names):
            print('MISSING LOCAL FILE', name)
            mismatch = True

        if mismatch:
            raise ValueError(
                'Riwayat file dan database berbeda; '
                'jangan menjalankan migrasi berikutnya.'
            )


def require_development():
    if os.getenv('APP_ENV') not in ('development', 'test'):
        raise ValueError(
            'Perintah ini hanya untuk APP_ENV=development atau test.'
        )


def seed():
    require_development()

    path = ROOT / 'database/seeds/001_demo_catalog.sql'

    with connect() as conn:
        conn.execute(path.read_text(encoding='utf-8'))

    print(
        'Seed selesai: 3 kategori, 6 menu, 3 meja pada database baru. '
        'Tidak menimpa ID yang sudah ada.'
    )


def verify():
    with connect() as conn:
        rows = conn.execute(
            '''
            SELECT tablename, rowsecurity
            FROM pg_tables
            WHERE schemaname = 'app'
            '''
        ).fetchall()

        actual = dict(rows)

        if any(
            table not in actual or not actual[table]
            for table in TABLES
        ):
            raise ValueError(
                'Tabel inti belum lengkap atau RLS belum aktif.'
            )

        print('OK: 10 tabel inti dan RLS aktif.')

        for table in (
            'categories',
            'menus',
            'restaurant_tables',
            'users',
            'orders',
            'payments',
        ):
            count = conn.execute(
                f'SELECT count(*) FROM app.{identifier(table)}'
            ).fetchone()[0]

            print(table + ':', count)

        # Inkonsistensi berikut harus dicegah oleh transaksi FastAPI.
        issues = conn.execute(
            '''
            SELECT 'payment_status', count(*)
            FROM app.ordering_sessions s
            LEFT JOIN app.payments p ON p.session_id = s.id
            WHERE (s.status = 'paid') <> (p.id IS NOT NULL)

            UNION ALL

            SELECT 'takeaway_fulfillment', count(*)
            FROM app.orders o
            JOIN app.ordering_sessions s ON s.id = o.session_id
            WHERE s.session_type = 'takeaway'
              AND o.fulfillment_type <> 'takeaway'

            UNION ALL

            SELECT 'payment_total', count(*)
            FROM app.payments p
            WHERE p.total_amount <> COALESCE(
                (
                    SELECT sum(i.unit_price_snapshot * i.quantity)
                    FROM app.orders o
                    JOIN app.order_items i ON i.order_id = o.id
                    WHERE o.session_id = p.session_id
                ),
                0
            )

            UNION ALL

            SELECT 'cancelled_session_has_items', count(*)
            FROM app.ordering_sessions s
            WHERE s.status = 'cancelled'
              AND EXISTS (
                  SELECT 1
                  FROM app.orders o
                  JOIN app.order_items i ON i.order_id = o.id
                  WHERE o.session_id = s.id
                    AND i.quantity > 0
              )

            UNION ALL

            SELECT 'order_status_or_empty', count(*)
            FROM app.orders o
            WHERE NOT EXISTS (
                SELECT 1
                FROM app.order_items i
                WHERE i.order_id = o.id
            )
            OR (
                (o.status = 'cancelled')
                <> (
                    NOT EXISTS (
                        SELECT 1
                        FROM app.order_items i
                        WHERE i.order_id = o.id
                          AND i.quantity > 0
                    )
                )
            )
            '''
        ).fetchall()

        for label, count in issues:
            print(label + ':', count)

        if any(count for _, count in issues):
            raise ValueError(
                'Ditemukan inkonsistensi transaksi. '
                'Periksa implementasi backend.'
            )

    print(
        'Verifikasi struktur dan konsistensi dasar OK; '
        'ini bukan tes API atau konkurensi.'
    )


def provision_app():
    password = getpass.getpass(
        'Password BARU untuk role database trio_app '
        '(minimal 20 karakter): '
    )

    confirmation = getpass.getpass('Ulangi password role: ')

    if len(password) < 20 or password != confirmation:
        raise ValueError(
            'Password terlalu pendek atau konfirmasi berbeda.'
        )

    with connect() as conn:
        conn.execute('SELECT pg_advisory_xact_lock(714021, 2)')

        exists = conn.execute(
            "SELECT 1 FROM pg_roles WHERE rolname = 'trio_app'"
        ).fetchone()

        if exists:
            raise ValueError(
                'Role trio_app sudah ada. Script tidak mereset '
                'password/izin role yang sudah ada.'
            )

        conn.execute(
            'CREATE ROLE trio_app LOGIN PASSWORD '
            + literal(password)
            + ' NOSUPERUSER NOCREATEDB NOCREATEROLE '
            'NOINHERIT NOBYPASSRLS'
        )

        conn.execute('GRANT USAGE ON SCHEMA app TO trio_app')

        # Tidak memberikan CREATE, DELETE, TRUNCATE, atau akses migrasi.
        for table in TABLES:
            if table in ('payments', 'order_adjustments'):
                privilege = 'SELECT, INSERT'
            else:
                privilege = 'SELECT, INSERT, UPDATE'

            conn.execute(
                f'GRANT {privilege} '
                f'ON app.{identifier(table)} TO trio_app'
            )

            conn.execute(
                f'CREATE POLICY backend_access '
                f'ON app.{identifier(table)} '
                'TO trio_app USING (true) WITH CHECK (true)'
            )

    print(
        'Role trio_app berhasil dibuat. '
        'Simpan password di DB_APP_PASSWORD; jangan ke Git.'
    )


def bootstrap_admin():
    name = input('Nama admin: ').strip()
    email = input('Email admin: ').strip().lower()

    password = getpass.getpass(
        'Password admin aplikasi (minimal 12 karakter): '
    )

    if not name or '@' not in email or len(password) < 12:
        raise ValueError(
            'Nama/email tidak valid atau password terlalu pendek.'
        )

    if password != getpass.getpass('Ulangi password admin: '):
        raise ValueError('Konfirmasi password berbeda.')

    digest = PasswordHash.recommended().hash(password)

    with connect() as conn:
        conn.execute('SELECT pg_advisory_xact_lock(714021, 3)')

        exists = conn.execute(
            "SELECT 1 FROM app.users WHERE role = 'admin'"
        ).fetchone()

        if exists:
            raise ValueError(
                'Admin sudah ada. Bootstrap tidak mengubah '
                'password akun yang ada.'
            )

        conn.execute(
            '''
            INSERT INTO app.users(name, email, password_hash, role)
            VALUES (%s, %s, %s, 'admin')
            ''',
            (name, email, digest),
        )

    print(
        'Admin berhasil dibuat menggunakan hash Argon2. '
        'Endpoint login tetap perlu dibuat backend.'
    )


def test_constraints():
    # Hanya untuk database tes lokal, bukan Supabase development bersama.
    if (
        os.getenv('APP_ENV') != 'test'
        or os.getenv('DB_NAME') != 'trio_test'
        or os.getenv('DB_HOST') not in ('localhost', '127.0.0.1')
    ):
        raise ValueError(
            'Test tulis hanya boleh pada database lokal trio_test '
            'dengan APP_ENV=test.'
        )

    path = ROOT / 'database/checks/constraints.sql'

    with connect() as conn:
        conn.execute(path.read_text(encoding='utf-8'))
        conn.rollback()

    print('Tes constraint lulus; data tes di-rollback.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument(
        'command',
        choices=[
            'check',
            'check-app',
            'status',
            'migrate',
            'seed',
            'verify',
            'provision-app',
            'bootstrap-admin',
            'test-constraints',
        ],
    )

    args = parser.parse_args()

    print(
        'Target:',
        os.getenv('DB_TARGET_LABEL', 'belum diberi label'),
    )

    actions = {
        'check': check,
        'check-app': lambda: check(True),
        'status': status,
        'migrate': migrate,
        'seed': seed,
        'verify': verify,
        'provision-app': provision_app,
        'bootstrap-admin': bootstrap_admin,
        'test-constraints': test_constraints,
    }

    try:
        actions[args.command]()

    except (ValueError, pg.Error, OSError, ImportError) as exc:
        if isinstance(exc, ValueError):
            print('GAGAL:', str(exc), file=sys.stderr)
        else:
            details = (
                exc.args[0]
                if exc.args and isinstance(exc.args[0], dict)
                else {}
            )

            # Jangan mencetak exception lengkap agar credential
            # tidak ikut muncul dalam output.
            print(
                'Database/driver gagal:',
                type(exc).__name__,
                '| SQLSTATE:',
                details.get('C', 'connection'),
                file=sys.stderr,
            )

            if details.get('n'):
                print(
                    'Constraint:',
                    details['n'],
                    file=sys.stderr,
                )

            print(
                'Periksa koneksi, konfigurasi .env, '
                'file SQL, dan dukungan SSL Python.',
                file=sys.stderr,
            )

        return 1

    return 0


if __name__ == '__main__':
    raise SystemExit(main())