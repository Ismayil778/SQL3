"""
Database connection module for Base_1c77 (SQL Server via pyodbc).
Supports both Windows Authentication and SQL Server Authentication.
"""
import pyodbc


def get_connection(
    server: str,
    database: str,
    login: str = "",
    password: str = "",
    windows_auth: bool = False,
) -> pyodbc.Connection:
    if windows_auth:
        conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"Trusted_Connection=yes;"
            f"TrustServerCertificate=yes;"
        )
    else:
        conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"UID={login};"
            f"PWD={password};"
            f"TrustServerCertificate=yes;"
        )
    return pyodbc.connect(conn_str, timeout=30)


def test_connection(
    server: str,
    database: str,
    login: str = "",
    password: str = "",
    windows_auth: bool = False,
) -> tuple[bool, str]:
    """Returns (True, '') on success or (False, error_message) on failure."""
    try:
        conn = get_connection(server, database, login, password, windows_auth)
        conn.close()
        return True, ""
    except pyodbc.Error as e:
        return False, str(e)


def execute_query(conn: pyodbc.Connection, sql: str, params=None) -> list[dict]:
    """Execute a SELECT query and return list of row dicts."""
    cursor = conn.cursor()
    if params:
        cursor.execute(sql, params)
    else:
        cursor.execute(sql)
    columns = [col[0] for col in cursor.description]
    rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
    cursor.close()
    return rows


def execute_nonquery(conn: pyodbc.Connection, sql: str, params=None) -> None:
    """Execute a non-SELECT statement (CREATE, INSERT, DROP, etc.)."""
    cursor = conn.cursor()
    if params:
        cursor.execute(sql, params)
    else:
        cursor.execute(sql)
    conn.commit()
    cursor.close()
