"""
Database connection module for Base_1c77 (SQL Server via pyodbc).
"""
import pyodbc
from typing import Optional


def get_connection(server: str, database: str, login: str, password: str) -> pyodbc.Connection:
    conn_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"UID={login};"
        f"PWD={password};"
        f"TrustServerCertificate=yes;"
    )
    return pyodbc.connect(conn_str, timeout=30)


def test_connection(server: str, database: str, login: str, password: str) -> tuple[bool, str]:
    """
    Returns (True, '') on success or (False, error_message) on failure.
    """
    try:
        conn = get_connection(server, database, login, password)
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
    rows = []
    for row in cursor.fetchall():
        rows.append(dict(zip(columns, row)))
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
