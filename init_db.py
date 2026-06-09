from database import get_db_connection, fetchone_dict
from werkzeug.security import generate_password_hash
from datetime import datetime


def init_database():
    conn = get_db_connection()
    cursor = conn.cursor()

    admin_password = generate_password_hash("admin123")
    voter_password = generate_password_hash("123456")

    users = [
        ("admin", admin_password, "admin"),
        ("sv001", voter_password, "voter"),
        ("sv002", voter_password, "voter")
    ]

    for username, password_hash, role in users:
        cursor.execute("""
            SELECT * FROM users WHERE username = ?
        """, (username,))
        existing_user = fetchone_dict(cursor)

        if existing_user is None:
            cursor.execute("""
                INSERT INTO users (username, password_hash, role)
                VALUES (?, ?, ?)
            """, (username, password_hash, role))

    cursor.execute("""
        SELECT * FROM elections WHERE title = ?
    """, ("Bầu lớp trưởng",))
    election = fetchone_dict(cursor)

    if election is None:
        cursor.execute("""
            INSERT INTO elections (title, description, status, created_at)
            VALUES (?, ?, ?, ?)
        """, (
            "Bầu lớp trưởng",
            "Cuộc bỏ phiếu chọn lớp trưởng học kỳ này",
            "open",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

    conn.commit()

    cursor.execute("""
        SELECT * FROM elections WHERE title = ?
    """, ("Bầu lớp trưởng",))
    election = fetchone_dict(cursor)

    if election:
        election_id = election["id"]

        candidates = [
            ("Mẫn Văn Thắng", "Ứng viên số 1"),
            ("Nguyễn Ngọc Tiến", "Ứng viên số 2"),
            ("Lương Tuấn Minh", "Ứng viên số 3")
        ]

        for name, description in candidates:
            cursor.execute("""
                SELECT * FROM candidates
                WHERE election_id = ? AND name = ?
            """, (election_id, name))
            existing_candidate = fetchone_dict(cursor)

            if existing_candidate is None:
                cursor.execute("""
                    INSERT INTO candidates (election_id, name, description)
                    VALUES (?, ?, ?)
                """, (election_id, name, description))

    conn.commit()
    conn.close()

    print("SQL Server database initialized successfully!")


if __name__ == "__main__":
    init_database()