from flask import Flask, render_template, request, redirect, session, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

from database import get_db_connection, fetchone_dict, fetchall_dict
from blockchain import BlockchainService

app = Flask(__name__)
app.secret_key = "your_secret_key_here"


def login_required():
    return "user_id" in session


def admin_required():
    return session.get("role") == "admin"


@app.route("/")
def index():
    return redirect("/login")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    username = request.form.get("username")
    password = request.form.get("password")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM users
        WHERE username = ?
    """, (username,))

    user = fetchone_dict(cursor)
    conn.close()

    if user and check_password_hash(user["password_hash"], password):
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["role"] = user["role"]

        if user["role"] == "admin":
            return redirect("/admin")
        else:
            return redirect("/vote")

    return render_template("login.html", error="Sai tài khoản hoặc mật khẩu.")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    username = request.form.get("username")
    password = request.form.get("password")
    confirm_password = request.form.get("confirm_password")

    if not username or not password or not confirm_password:
        return render_template("register.html", error="Vui lòng nhập đầy đủ thông tin.")

    if password != confirm_password:
        return render_template("register.html", error="Mật khẩu xác nhận không khớp.")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM users
        WHERE username = ?
    """, (username,))

    existing_user = fetchone_dict(cursor)

    if existing_user:
        conn.close()
        return render_template("register.html", error="Tên tài khoản đã tồn tại.")

    password_hash = generate_password_hash(password)

    cursor.execute("""
        INSERT INTO users (username, password_hash, role)
        VALUES (?, ?, ?)
    """, (username, password_hash, "voter"))

    conn.commit()
    conn.close()

    return redirect("/login")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/admin")
def admin_page():
    if not login_required() or not admin_required():
        return redirect("/login")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM elections
        ORDER BY id DESC
    """)
    elections = fetchall_dict(cursor)

    cursor.execute("""
        SELECT candidates.*, elections.title AS election_title
        FROM candidates
        JOIN elections ON candidates.election_id = elections.id
        ORDER BY candidates.id DESC
    """)
    candidates = fetchall_dict(cursor)

    conn.close()

    return render_template(
        "admin.html",
        elections=elections,
        candidates=candidates,
        role=session.get("role")
    )


@app.route("/admin/create-election", methods=["POST"])
def create_election():
    if not login_required() or not admin_required():
        return redirect("/login")

    title = request.form.get("title")
    description = request.form.get("description")
    status = request.form.get("status")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO elections (title, description, status, created_at)
        VALUES (?, ?, ?, ?)
    """, (
        title,
        description,
        status,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()

    return redirect("/admin")


@app.route("/admin/add-candidate", methods=["POST"])
def add_candidate():
    if not login_required() or not admin_required():
        return redirect("/login")

    election_id = request.form.get("election_id")
    name = request.form.get("name")
    description = request.form.get("description")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO candidates (election_id, name, description)
        VALUES (?, ?, ?)
    """, (election_id, name, description))

    conn.commit()
    conn.close()

    return redirect("/admin")


@app.route("/admin/update-candidate", methods=["POST"])
def update_candidate():
    if not login_required() or not admin_required():
        return redirect("/login")

    candidate_id = request.form.get("candidate_id")
    election_id = request.form.get("election_id")
    name = request.form.get("name")
    description = request.form.get("description")

    if not candidate_id or not election_id or not name:
        return redirect("/admin")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM blocks
        WHERE candidate_id = ?
    """, (candidate_id,))
    used_in_block = fetchone_dict(cursor)

    if used_in_block and used_in_block["total"] > 0:
        conn.close()
        return """
        <h2>Không thể sửa ứng viên này</h2>
        <p>Ứng viên đã có phiếu bầu trong Blockchain nên không được sửa để tránh sai lệch dữ liệu.</p>
        <a href="/admin">Quay lại trang admin</a>
        """

    cursor.execute("""
        UPDATE candidates
        SET election_id = ?, name = ?, description = ?
        WHERE id = ?
    """, (election_id, name, description, candidate_id))

    conn.commit()
    conn.close()

    return redirect("/admin")


@app.route("/admin/update-election", methods=["POST"])
def update_election():
    if not login_required() or not admin_required():
        return redirect("/login")

    election_id = request.form.get("election_id")
    title = request.form.get("title")
    description = request.form.get("description")
    status = request.form.get("status")

    if not election_id or not title or not status:
        return redirect("/admin")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE elections
        SET title = ?, description = ?, status = ?
        WHERE id = ?
    """, (title, description, status, election_id))

    conn.commit()
    conn.close()

    return redirect("/admin")


@app.route("/admin/delete-candidate", methods=["POST"])
def delete_candidate():
    if not login_required() or not admin_required():
        return redirect("/login")

    candidate_id = request.form.get("candidate_id")

    if not candidate_id:
        return redirect("/admin")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM blocks
        WHERE candidate_id = ?
    """, (candidate_id,))
    used_in_block = fetchone_dict(cursor)

    if used_in_block and used_in_block["total"] > 0:
        conn.close()
        return """
        <h2>Không thể xóa ứng viên này</h2>
        <p>Ứng viên đã có phiếu bầu trong Blockchain nên không được xóa để tránh sai lệch dữ liệu.</p>
        <a href="/admin">Quay lại trang admin</a>
        """

    cursor.execute("""
        DELETE FROM candidates
        WHERE id = ?
    """, (candidate_id,))

    conn.commit()
    conn.close()

    return redirect("/admin")


@app.route("/vote")
def vote_page():
    if not login_required():
        return redirect("/login")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM elections
        WHERE status = 'open'
        ORDER BY id DESC
    """)
    elections = fetchall_dict(cursor)

    conn.close()

    return render_template(
        "vote.html",
        elections=elections,
        username=session.get("username"),
        role=session.get("role")
    )


@app.route("/vote/<int:election_id>")
def vote_detail(election_id):
    if not login_required():
        return redirect("/login")

    user_id = session["user_id"]

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM elections
        WHERE id = ?
    """, (election_id,))
    election = fetchone_dict(cursor)

    cursor.execute("""
        SELECT *
        FROM candidates
        WHERE election_id = ?
    """, (election_id,))
    candidates = fetchall_dict(cursor)

    cursor.execute("""
        SELECT *
        FROM voter_status
        WHERE user_id = ? AND election_id = ?
    """, (user_id, election_id))
    voter_status = fetchone_dict(cursor)

    conn.close()

    has_voted = voter_status is not None and bool(voter_status["has_voted"])

    return render_template(
        "vote.html",
        election=election,
        candidates=candidates,
        has_voted=has_voted,
        username=session.get("username"),
        role=session.get("role")
    )


@app.route("/submit-vote", methods=["POST"])
def submit_vote():
    if not login_required():
        return redirect("/login")

    if session.get("role") == "admin":
        return "Admin không được phép bỏ phiếu."

    user_id = session["user_id"]
    election_id = int(request.form.get("election_id"))
    candidate_id = int(request.form.get("candidate_id"))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM elections
        WHERE id = ?
    """, (election_id,))
    election = fetchone_dict(cursor)

    if election is None:
        conn.close()
        return "Cuộc bỏ phiếu không tồn tại."

    if election["status"] != "open":
        conn.close()
        return "Cuộc bỏ phiếu đã đóng."

    cursor.execute("""
        SELECT *
        FROM candidates
        WHERE id = ? AND election_id = ?
    """, (candidate_id, election_id))
    candidate = fetchone_dict(cursor)

    if candidate is None:
        conn.close()
        return "Ứng viên không hợp lệ."

    cursor.execute("""
        SELECT *
        FROM voter_status
        WHERE user_id = ? AND election_id = ?
    """, (user_id, election_id))
    voter_status = fetchone_dict(cursor)

    if voter_status and bool(voter_status["has_voted"]):
        conn.close()
        return "Bạn đã bỏ phiếu rồi."

    BlockchainService.create_vote_block(election_id, candidate_id, user_id)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if voter_status:
        cursor.execute("""
            UPDATE voter_status
            SET has_voted = ?, voted_at = ?
            WHERE user_id = ? AND election_id = ?
        """, (1, now, user_id, election_id))
    else:
        cursor.execute("""
            INSERT INTO voter_status (
                user_id,
                election_id,
                has_voted,
                voted_at
            )
            VALUES (?, ?, ?, ?)
        """, (user_id, election_id, 1, now))

    conn.commit()
    conn.close()

    return redirect(f"/vote/{election_id}")


@app.route("/result")
def result_page():
    if not login_required():
        return redirect("/login")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM elections
        ORDER BY id DESC
    """)
    elections = fetchall_dict(cursor)

    conn.close()

    return render_template(
        "result.html",
        elections=elections,
        role=session.get("role")
    )


@app.route("/result/<int:election_id>")
def result_detail(election_id):
    if not login_required():
        return redirect("/login")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM elections
        WHERE id = ?
    """, (election_id,))
    election = fetchone_dict(cursor)

    cursor.execute("""
        SELECT 
            candidates.id,
            candidates.name,
            COUNT(blocks.id) AS total_votes
        FROM candidates
        LEFT JOIN blocks ON candidates.id = blocks.candidate_id
        WHERE candidates.election_id = ?
        GROUP BY candidates.id, candidates.name
        ORDER BY total_votes DESC
    """, (election_id,))
    results = fetchall_dict(cursor)

    conn.close()

    return render_template(
        "result.html",
        election=election,
        results=results,
        role=session.get("role")
    )


@app.route("/blockchain")
def blockchain_page():
    if not login_required():
        return redirect("/login")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            blocks.*,
            candidates.name AS candidate_name,
            elections.title AS election_title
        FROM blocks
        JOIN candidates ON blocks.candidate_id = candidates.id
        JOIN elections ON blocks.election_id = elections.id
        ORDER BY blocks.block_index ASC
    """)
    blocks = fetchall_dict(cursor)

    conn.close()

    is_valid, message = BlockchainService.validate_chain()

    return render_template(
        "blockchain.html",
        blocks=blocks,
        is_valid=is_valid,
        message=message,
        role=session.get("role")
    )


@app.route("/api/blockchain/validate")
def validate_blockchain_api():
    is_valid, message = BlockchainService.validate_chain()

    return jsonify({
        "is_valid": is_valid,
        "message": message
    })


if __name__ == "__main__":
    app.run(debug=True)