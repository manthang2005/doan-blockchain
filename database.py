import pyodbc


def get_db_connection():
    conn = pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=localhost;"
        "DATABASE=VotingDB;"
        "Trusted_Connection=yes;"
    )
    return conn


def fetchone_dict(cursor):
    row = cursor.fetchone()
    if row is None:
        return None

    columns = [column[0] for column in cursor.description]
    return dict(zip(columns, row))


def fetchall_dict(cursor):
    rows = cursor.fetchall()
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row)) for row in rows]