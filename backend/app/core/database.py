from fastapi import Depends
from psycopg.conninfo import make_conninfo
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.core import config

_conninfo_args = {
    "host": config.DB_HOST,
    "port": config.DB_PORT,
    "dbname": config.DB_NAME,
    "user": config.DB_APP_USER,
    "password": config.DB_APP_PASSWORD,
    "sslmode": config.DB_SSLMODE,
    "connect_timeout": 10,
    "application_name": "trio_saung_backend",
}
if config.DB_SSLROOTCERT:
    _conninfo_args["sslrootcert"] = config.DB_SSLROOTCERT

pool = ConnectionPool(
    conninfo=make_conninfo(**_conninfo_args),
    min_size=1,
    max_size=5,
    # dict_row: hasil query  dict -> row["name"].
    kwargs={"row_factory": dict_row, "prepare_threshold": None},
    open=False,
)


def get_db():
    """Dependency FastAPI: satu koneksi = satu transaksi per request.

    Keluar normal -> COMMIT. Terjadi exception (termasuk HTTPException) -> ROLLBACK.
    """
    with pool.connection() as conn:
        yield conn

# untuk client tidak pernah menerima "berhasil" untuk data yang ternyata gagal disimpan.
DbConn = Depends(get_db, scope="function")
