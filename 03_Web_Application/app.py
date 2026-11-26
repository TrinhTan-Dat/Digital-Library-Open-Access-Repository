import time
from datetime import date, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector

app = Flask(__name__)
app.secret_key = "ptit_digital_library_int1313_secret"

# =====================================================================
# CẤU HÌNH KẾT NỐI MYSQL (Điền mật khẩu MySQL trên máy bạn vào password)
# =====================================================================
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "MatKhauMoi123",
    "database": "digital_library",
    "charset": "utf8mb4",
}

ROLE_LABELS = {
    "Administrator": "Quản trị viên",
    "Library staff": "Nhân viên thư viện",
    "Faculty": "Giảng viên / NCV",
    "Student": "Sinh viên",
    "Member": "Thành viên",
}


def get_db():
    return mysql.connector.connect(**DB_CONFIG)


def next_id_num(cur, table, col, prefix):
    cur.execute(
        f"SELECT COALESCE(MAX(CAST(SUBSTRING({col}, %s) AS UNSIGNED)), 0) + 1 AS next_num "
        f"FROM {table} WHERE {col} LIKE %s",
        (len(prefix) + 1, prefix + "%"),
    )
    row = cur.fetchone()
    return int(row["next_num"] if isinstance(row, dict) else row[0])


def next_id(cur, table, col, prefix, width):
    num = next_id_num(cur, table, col, prefix)
    return f"{prefix}{num:0{width}d}"


# =====================================================================
# XÁC THỰC & PHÂN QUYỀN THEO VAI TRÒ (NFR-02, NFR-03)
# =====================================================================
def fetch_demo_user_by_role(conn, role_name):
    cur = conn.cursor(dictionary=True)
    cur.execute(
        """
        SELECT r.member_id, r.name, r.status, r.member_role,
               ua.username, ua.permission_level, ua.account_status
        FROM v_member_role r
        LEFT JOIN user_account ua ON ua.member_id = r.member_id
        WHERE r.member_role = %s AND r.status = 'Active'
        ORDER BY (ua.account_status = 'Active') DESC, r.member_id ASC
        LIMIT 1
        """,
        (role_name,),
    )
    row = cur.fetchone()
    cur.close()
    return row


def get_current_user(conn=None):
    user = session.get("user")
    if user:
        return user
    # Mặc định tự động vào vai trò Quản trị viên khi mở web lần đầu để demo nhanh
    own_conn = False
    try:
        if conn is None:
            conn = get_db()
            own_conn = True
        admin_row = fetch_demo_user_by_role(conn, "Administrator")
        if admin_row:
            user = {
                "member_id": admin_row["member_id"],
                "name": admin_row["name"],
                "role": admin_row["member_role"],
                "username": admin_row["username"] or admin_row["member_id"],
                "permission_level": admin_row["permission_level"] or "Private",
            }
            session["user"] = user
            return user
    except mysql.connector.Error:
        pass
    finally:
        if own_conn and conn is not None:
            conn.close()
    return {
        "member_id": "MEM0371",
        "name": "Quản trị hệ thống",
        "role": "Administrator",
        "username": "admin",
        "permission_level": "Private",
    }


def has_role(user, allowed_roles):
    return user.get("role") in allowed_roles


@app.context_processor
def inject_globals():
    user = session.get("user")
    if not user:
        user = {
            "member_id": "MEM0371",
            "name": "Quản trị viên",
            "role": "Administrator",
            "username": "admin",
            "permission_level": "Private",
        }
    return {
        "current_user": user,
        "role_labels": ROLE_LABELS,
        "is_admin": user.get("role") == "Administrator",
        "is_staff": user.get("role") in ("Administrator", "Library staff"),
        "is_faculty_plus": user.get("role") in ("Administrator", "Library staff", "Faculty"),
    }


@app.route("/login", methods=["GET", "POST"])
def login():
    try:
        conn = get_db()
    except mysql.connector.Error as err:
        return render_template("error.html", error=str(err), config=DB_CONFIG), 500

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT ua.account_id, ua.member_id, ua.username, ua.password_hash,
                   ua.permission_level, ua.account_status,
                   r.name, r.member_role, r.status AS member_status
            FROM user_account ua
            JOIN v_member_role r ON r.member_id = ua.member_id
            WHERE ua.username = %s OR ua.member_id = %s
            LIMIT 1
            """,
            (username, username),
        )
        acc = cur.fetchone()
        cur.close()
        conn.close()

        if not acc:
            flash("Không tìm thấy tài khoản (nhập username hoặc member_id hợp lệ).", "danger")
            return redirect(url_for("login"))
        if acc["account_status"] != "Active":
            flash(f"Tài khoản {acc['username']} đang ở trạng thái {acc['account_status']} (NFR-02).", "danger")
            return redirect(url_for("login"))
        if password and password != acc["password_hash"] and password != "123456":
            flash("Mật khẩu không đúng (gợi ý demo: dùng đúng password_hash trong CSDL hoặc nhập '123456').", "danger")
            return redirect(url_for("login"))

        session["user"] = {
            "member_id": acc["member_id"],
            "name": acc["name"],
            "role": acc["member_role"],
            "username": acc["username"],
            "permission_level": acc["permission_level"],
        }
        flash(
            f"Đăng nhập thành công: {acc['name']} ({ROLE_LABELS.get(acc['member_role'], acc['member_role'])}).",
            "success",
        )
        return redirect(url_for("index"))

    demo_accounts = []
    for rname in ("Administrator", "Library staff", "Faculty", "Student"):
        row = fetch_demo_user_by_role(conn, rname)
        if row:
            demo_accounts.append(row)
    conn.close()
    return render_template("login.html", demo_accounts=demo_accounts)


@app.route("/switch_role/<role_name>")
def switch_role(role_name):
    if role_name not in ("Administrator", "Library staff", "Faculty", "Student"):
        flash("Vai trò không hợp lệ.", "danger")
        return redirect(url_for("index"))
    try:
        conn = get_db()
    except mysql.connector.Error as err:
        return render_template("error.html", error=str(err), config=DB_CONFIG), 500

    row = fetch_demo_user_by_role(conn, role_name)
    conn.close()
    if row:
        session["user"] = {
            "member_id": row["member_id"],
            "name": row["name"],
            "role": row["member_role"],
            "username": row["username"] or row["member_id"],
            "permission_level": row["permission_level"] or "Open",
        }
        flash(
            f"Đã chuyển phiên làm việc sang {ROLE_LABELS.get(role_name, role_name)}: "
            f"{row['name']} ({row['member_id']}, quyền tài liệu số: {session['user']['permission_level']}).",
            "success",
        )
    else:
        flash(f"Không tìm thấy tài khoản hoạt động cho vai trò {role_name}.", "danger")

    return redirect(request.referrer or url_for("index"))


# =====================================================================
# 1. TRANG CHỦ: TRA CỨU TỐI ƯU (<200ms) & QUẢN LÝ TÀI LIỆU (FR-01, FR-02, FR-11, NFR-01)
# =====================================================================
@app.route("/", methods=["GET", "POST"])
def index():
    try:
        conn = get_db()
    except mysql.connector.Error as err:
        return render_template("error.html", error=str(err), config=DB_CONFIG), 500

    user = get_current_user(conn)
    cur = conn.cursor(dictionary=True)

    if request.method == "POST":
        action = request.form.get("action", "add_doc")

        if action == "add_doc":
            if not has_role(user, ("Administrator", "Library staff", "Faculty")):
                flash("Từ chối phân quyền (NFR-03): Sinh viên không có quyền thêm tài liệu.", "danger")
                cur.close()
                conn.close()
                return redirect(url_for("index"))

            title = request.form.get("title", "").strip()
            pub_year = request.form.get("publication_year", "").strip()
            isbn = request.form.get("isbn", "").strip() or None
            language = request.form.get("language", "Vietnamese").strip()
            doc_type = request.form.get("type", "BOOK").strip()
            publisher_id = request.form.get("publisher_id", "").strip() or None
            employee_code = request.form.get("employee_code", "").strip()
            description = request.form.get("description", "").strip() or None
            author_id = request.form.get("author_id", "").strip() or None
            category_id = request.form.get("category_id", "").strip() or None

            try:
                init_copies = int(request.form.get("init_copies", "0") or 0)
                if init_copies < 0 or init_copies > 50:
                    raise ValueError("Số bản sao ban đầu phải từ 0 đến 50.")

                doc_id = next_id(cur, "document", "document_id", "DOC", 5)
                cur.execute(
                    """
                    INSERT INTO document (
                        document_id, title, publication_year, ISBN,
                        description, `language`, `type`, publisher_id, employee_code
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        doc_id, title, int(pub_year), isbn,
                        description, language, doc_type, publisher_id, employee_code,
                    ),
                )

                if author_id:
                    cur.execute(
                        "INSERT INTO document_author (document_id, author_id, author_order) VALUES (%s, %s, 1)",
                        (doc_id, author_id),
                    )
                if category_id:
                    cur.execute(
                        "INSERT INTO document_category (document_id, category_id) VALUES (%s, %s)",
                        (doc_id, category_id),
                    )

                created_copies = []
                if init_copies > 0:
                    start_num = next_id_num(cur, "physical_copy", "copy_id", "COP")
                    for i in range(init_copies):
                        cid = f"COP{start_num + i:05d}"
                        cur.execute(
                            """
                            INSERT INTO physical_copy (copy_id, document_id, status, `condition`)
                            VALUES (%s, %s, 'Available', 'Mới')
                            """,
                            (cid, doc_id),
                        )
                        created_copies.append(cid)

                conn.commit()
                msg = f"Thêm tài liệu thành công: {doc_id}"
                if created_copies:
                    msg += f" kèm {len(created_copies)} bản sao ({created_copies[0]} .. {created_copies[-1]})"
                flash(msg + ".", "success")
            except (mysql.connector.Error, ValueError) as err:
                conn.rollback()
                flash(f"MySQL từ chối thêm tài liệu: {getattr(err, 'msg', str(err))}", "danger")

        elif action == "add_copy":
            if not has_role(user, ("Administrator", "Library staff")):
                flash("Từ chối phân quyền (NFR-03): Chỉ nhân viên thư viện / quản trị viên được quản lý kho bản sao.", "danger")
                cur.close()
                conn.close()
                return redirect(url_for("index"))

            document_id = request.form.get("document_id", "").strip()
            condition = request.form.get("condition", "Mới").strip() or "Mới"
            try:
                quantity = int(request.form.get("quantity", "1") or 1)
                if quantity < 1 or quantity > 50:
                    raise ValueError("Số lượng bản sao thêm mỗi lần phải từ 1 đến 50.")
                start_num = next_id_num(cur, "physical_copy", "copy_id", "COP")

                created_copies = []
                for i in range(quantity):
                    cid = f"COP{start_num + i:05d}"
                    cur.execute(
                        """
                        INSERT INTO physical_copy (copy_id, document_id, status, `condition`)
                        VALUES (%s, %s, 'Available', %s)
                        """,
                        (cid, document_id, condition),
                    )
                    created_copies.append(cid)

                conn.commit()
                flash(
                    f"Đã nhập thêm {quantity} bản sao cho {document_id}: {', '.join(created_copies)} (Available).",
                    "success",
                )
            except (mysql.connector.Error, ValueError) as err:
                conn.rollback()
                flash(f"Lỗi khi thêm bản sao: {getattr(err, 'msg', str(err))}", "danger")

        elif action == "update_copy":
            if not has_role(user, ("Administrator", "Library staff")):
                flash("Từ chối phân quyền (NFR-03): Chỉ nhân viên thư viện / quản trị viên được sửa bản sao.", "danger")
                cur.close()
                conn.close()
                return redirect(url_for("index"))

            copy_id = request.form.get("copy_id", "").strip()
            new_status = request.form.get("status", "Available").strip()
            new_condition = request.form.get("condition", "").strip() or None
            try:
                cur.execute(
                    "UPDATE physical_copy SET status = %s, `condition` = COALESCE(%s, `condition`) WHERE copy_id = %s",
                    (new_status, new_condition, copy_id),
                )
                if cur.rowcount == 0:
                    flash(f"Không tìm thấy bản sao có mã {copy_id}.", "danger")
                else:
                    conn.commit()
                    flash(f"Đã cập nhật bản sao {copy_id} sang trạng thái {new_status}.", "success")
            except mysql.connector.Error as err:
                conn.rollback()
                flash(f"Lỗi cập nhật bản sao: {err.msg}", "danger")

        cur.close()
        conn.close()
        return redirect(url_for("index"))

    # --- TÌM KIẾM TỐI ƯU HIỆU NĂNG NFR-01 (< 200 ms) ---
    # Lọc trên bảng document có INDEX trước để lấy tối đa 50 mã document_id,
    # sau đó mới đọc từ View v_document_catalog cho đúng 50 dòng đó.
    q = request.args.get("q", "").strip()
    doc_type = request.args.get("type", "").strip()
    pub_year_filter = request.args.get("year", "").strip()
    cat_filter = request.args.get("category", "").strip()
    only_avail = request.args.get("avail", "")
    sort_dir = request.args.get("sort", "asc")

    id_sql = "SELECT d.document_id FROM document d WHERE 1=1"
    params = []

    if q:
        like = f"%{q}%"
        id_sql += (
            " AND (d.title LIKE %s OR d.ISBN LIKE %s OR d.document_id LIKE %s"
            " OR EXISTS (SELECT 1 FROM document_author da JOIN author a ON a.author_id = da.author_id"
            "            WHERE da.document_id = d.document_id AND a.author_name LIKE %s)"
            " OR EXISTS (SELECT 1 FROM document_category dc JOIN category c ON c.category_id = dc.category_id"
            "            WHERE dc.document_id = d.document_id AND c.cate_name LIKE %s))"
        )
        params.extend([like, like, like, like, like])

    if doc_type:
        id_sql += " AND d.`type` = %s"
        params.append(doc_type)

    if pub_year_filter.isdigit():
        id_sql += " AND d.publication_year = %s"
        params.append(int(pub_year_filter))

    if cat_filter:
        id_sql += (
            " AND EXISTS (SELECT 1 FROM document_category dc"
            "             WHERE dc.document_id = d.document_id AND dc.category_id = %s)"
        )
        params.append(cat_filter)

    if only_avail == "1":
        id_sql += (
            " AND EXISTS (SELECT 1 FROM physical_copy pc"
            "             WHERE pc.document_id = d.document_id AND pc.status = 'Available')"
        )

    order_clause = "DESC" if sort_dir == "desc" else "ASC"
    id_sql += f" ORDER BY d.document_id {order_clause} LIMIT 50"

    t0 = time.perf_counter()
    cur.execute(id_sql, params)
    matched_ids = [r["document_id"] for r in cur.fetchall()]

    if matched_ids:
        placeholders = ", ".join(["%s"] * len(matched_ids))
        cur.execute(
            f"SELECT * FROM v_document_catalog WHERE document_id IN ({placeholders}) "
            f"ORDER BY document_id {order_clause}",
            matched_ids,
        )
        docs = cur.fetchall()
    else:
        docs = []
    query_ms = round((time.perf_counter() - t0) * 1000, 2)

    cur.execute(
        """
        SELECT
            (SELECT COUNT(*) FROM document) AS total_docs,
            (SELECT COUNT(*) FROM physical_copy WHERE status = 'Available') AS avail_copies,
            (SELECT COUNT(*) FROM loan WHERE status IN ('ACTIVE', 'OVERDUE')) AS active_loans,
            (SELECT COUNT(*) FROM fine WHERE status = 'Unpaid') AS unpaid_fines
        """
    )
    stats = cur.fetchone()

    cur.execute("SELECT publisher_id, pub_name FROM publisher ORDER BY publisher_id")
    publishers = cur.fetchall()

    cur.execute("SELECT employee_code, `position` FROM library_staff ORDER BY employee_code")
    staffs = cur.fetchall()

    cur.execute("SELECT category_id, cate_name FROM category ORDER BY cate_name")
    categories = cur.fetchall()

    cur.execute("SELECT author_id, author_name FROM author ORDER BY author_id LIMIT 100")
    authors_sample = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "index.html",
        docs=docs,
        stats=stats,
        publishers=publishers,
        staffs=staffs,
        categories=categories,
        authors_sample=authors_sample,
        q=q,
        doc_type=doc_type,
        pub_year_filter=pub_year_filter,
        cat_filter=cat_filter,
        only_avail=only_avail,
        sort_dir=sort_dir,
        query_ms=query_ms,
    )


# =====================================================================
# 1B. CHI TIẾT & QUẢN TRỊ TÀI LIỆU (Sửa/Xóa FR-01, Bản sao FR-02, Tác giả FR-12)
# =====================================================================
@app.route("/document/<doc_id>", methods=["GET", "POST"])
def document_detail(doc_id):
    try:
        conn = get_db()
    except mysql.connector.Error as err:
        return render_template("error.html", error=str(err), config=DB_CONFIG), 500

    user = get_current_user(conn)
    cur = conn.cursor(dictionary=True)

    if request.method == "POST":
        action = request.form.get("action")

        if action == "update_doc":
            if not has_role(user, ("Administrator", "Library staff")):
                flash("Từ chối phân quyền (NFR-03): Chỉ thủ thư / quản trị viên được sửa tài liệu.", "danger")
                cur.close()
                conn.close()
                return redirect(url_for("document_detail", doc_id=doc_id))

            title = request.form.get("title", "").strip()
            pub_year = request.form.get("publication_year", "").strip()
            isbn = request.form.get("isbn", "").strip() or None
            language = request.form.get("language", "Vietnamese").strip()
            doc_type = request.form.get("type", "BOOK").strip()
            publisher_id = request.form.get("publisher_id", "").strip() or None
            employee_code = request.form.get("employee_code", "").strip()
            description = request.form.get("description", "").strip() or None

            try:
                cur.execute(
                    """
                    UPDATE document
                    SET title = %s, publication_year = %s, ISBN = %s,
                        description = %s, `language` = %s, `type` = %s,
                        publisher_id = %s, employee_code = %s
                    WHERE document_id = %s
                    """,
                    (
                        title, int(pub_year), isbn, description,
                        language, doc_type, publisher_id, employee_code, doc_id,
                    ),
                )
                conn.commit()
                flash(f"Đã cập nhật thông tin tài liệu {doc_id}.", "success")
            except (mysql.connector.Error, ValueError) as err:
                conn.rollback()
                flash(f"MySQL từ chối cập nhật tài liệu: {getattr(err, 'msg', str(err))}", "danger")

        elif action == "delete_doc":
            if not has_role(user, ("Administrator", "Library staff")):
                flash("Từ chối phân quyền (NFR-03): Chỉ thủ thư / quản trị viên được xóa tài liệu.", "danger")
                cur.close()
                conn.close()
                return redirect(url_for("document_detail", doc_id=doc_id))

            try:
                cur.execute("DELETE FROM document WHERE document_id = %s", (doc_id,))
                conn.commit()
                cur.close()
                conn.close()
                flash(f"Đã xóa hoàn toàn tài liệu {doc_id}.", "success")
                return redirect(url_for("index"))
            except mysql.connector.Error as err:
                conn.rollback()
                flash(
                    f"MySQL chặn xóa tài liệu để bảo vệ toàn vẹn dữ liệu (NFR-05): {err.msg}",
                    "danger",
                )

        elif action == "add_copy":
            if not has_role(user, ("Administrator", "Library staff")):
                flash("Từ chối phân quyền (NFR-03): Chỉ thủ thư / quản trị viên được thêm bản sao.", "danger")
            else:
                condition = request.form.get("condition", "Mới").strip() or "Mới"
                try:
                    quantity = int(request.form.get("quantity", "1") or 1)
                    if quantity < 1 or quantity > 50:
                        raise ValueError("Số lượng thêm phải từ 1 đến 50.")
                    start_num = next_id_num(cur, "physical_copy", "copy_id", "COP")
                    created = []
                    for i in range(quantity):
                        cid = f"COP{start_num + i:05d}"
                        cur.execute(
                            "INSERT INTO physical_copy (copy_id, document_id, status, `condition`) VALUES (%s, %s, 'Available', %s)",
                            (cid, doc_id, condition),
                        )
                        created.append(cid)
                    conn.commit()
                    flash(f"Đã thêm {quantity} bản sao: {', '.join(created)}.", "success")
                except (mysql.connector.Error, ValueError) as err:
                    conn.rollback()
                    flash(f"Lỗi thêm bản sao: {getattr(err, 'msg', str(err))}", "danger")

        elif action == "update_copy":
            if not has_role(user, ("Administrator", "Library staff")):
                flash("Từ chối phân quyền (NFR-03).", "danger")
            else:
                copy_id = request.form.get("copy_id", "").strip()
                status_val = request.form.get("status", "Available").strip()
                cond_val = request.form.get("condition", "").strip() or None
                try:
                    cur.execute(
                        "UPDATE physical_copy SET status = %s, `condition` = %s WHERE copy_id = %s AND document_id = %s",
                        (status_val, cond_val, copy_id, doc_id),
                    )
                    conn.commit()
                    flash(f"Đã cập nhật bản sao {copy_id} -> {status_val}.", "success")
                except mysql.connector.Error as err:
                    conn.rollback()
                    flash(f"Lỗi cập nhật bản sao: {err.msg}", "danger")

        elif action == "delete_copy":
            if not has_role(user, ("Administrator", "Library staff")):
                flash("Từ chối phân quyền (NFR-03).", "danger")
            else:
                copy_id = request.form.get("copy_id", "").strip()
                try:
                    cur.execute(
                        "DELETE FROM physical_copy WHERE copy_id = %s AND document_id = %s",
                        (copy_id, doc_id),
                    )
                    conn.commit()
                    flash(f"Đã xóa bản sao {copy_id}.", "success")
                except mysql.connector.Error as err:
                    conn.rollback()
                    flash(f"MySQL chặn xóa bản sao (đã có lịch sử mượn - NFR-05): {err.msg}", "danger")

        elif action == "add_author":
            if not has_role(user, ("Administrator", "Library staff", "Faculty")):
                flash("Từ chối phân quyền (NFR-03): Sinh viên không được sửa danh sách tác giả.", "danger")
            else:
                author_id = request.form.get("author_id", "").strip()
                try:
                    author_order = int(request.form.get("author_order", "1"))
                    cur.execute(
                        "INSERT INTO document_author (document_id, author_id, author_order) VALUES (%s, %s, %s)",
                        (doc_id, author_id, author_order),
                    )
                    conn.commit()
                    flash(f"Đã liên kết tác giả {author_id} ở thứ tự {author_order} (FR-12).", "success")
                except (mysql.connector.Error, ValueError) as err:
                    conn.rollback()
                    flash(f"MySQL chặn liên kết tác giả (BR12/BR13): {getattr(err, 'msg', str(err))}", "danger")

        elif action == "remove_author":
            if not has_role(user, ("Administrator", "Library staff", "Faculty")):
                flash("Từ chối phân quyền (NFR-03).", "danger")
            else:
                author_id = request.form.get("author_id", "").strip()
                try:
                    cur.execute(
                        "DELETE FROM document_author WHERE document_id = %s AND author_id = %s",
                        (doc_id, author_id),
                    )
                    conn.commit()
                    flash(f"Đã gỡ tác giả {author_id} khỏi tài liệu.", "success")
                except mysql.connector.Error as err:
                    conn.rollback()
                    flash(f"Lỗi gỡ tác giả: {err.msg}", "danger")

        elif action == "add_category":
            if not has_role(user, ("Administrator", "Library staff")):
                flash("Từ chối phân quyền (NFR-03).", "danger")
            else:
                category_id = request.form.get("category_id", "").strip()
                try:
                    cur.execute(
                        "INSERT INTO document_category (document_id, category_id) VALUES (%s, %s)",
                        (doc_id, category_id),
                    )
                    conn.commit()
                    flash(f"Đã gắn thể loại {category_id} cho tài liệu.", "success")
                except mysql.connector.Error as err:
                    conn.rollback()
                    flash(f"Lỗi gắn thể loại: {err.msg}", "danger")

        elif action == "remove_category":
            if not has_role(user, ("Administrator", "Library staff")):
                flash("Từ chối phân quyền (NFR-03).", "danger")
            else:
                category_id = request.form.get("category_id", "").strip()
                try:
                    cur.execute(
                        "DELETE FROM document_category WHERE document_id = %s AND category_id = %s",
                        (doc_id, category_id),
                    )
                    conn.commit()
                    flash(f"Đã gỡ thể loại {category_id}.", "success")
                except mysql.connector.Error as err:
                    conn.rollback()
                    flash(f"Lỗi gỡ thể loại: {err.msg}", "danger")

        cur.close()
        conn.close()
        return redirect(url_for("document_detail", doc_id=doc_id))

    cur.execute("SELECT * FROM document WHERE document_id = %s", (doc_id,))
    doc = cur.fetchone()
    if not doc:
        cur.close()
        conn.close()
        flash(f"Không tìm thấy tài liệu {doc_id}.", "danger")
        return redirect(url_for("index"))

    cur.execute(
        "SELECT copy_id, status, `condition` FROM physical_copy WHERE document_id = %s ORDER BY copy_id",
        (doc_id,),
    )
    copies = cur.fetchall()

    cur.execute(
        """
        SELECT da.author_id, da.author_order, a.author_name, a.person_id,
               CASE WHEN um.member_id IS NOT NULL THEN 1 ELSE 0 END AS is_member
        FROM document_author da
        JOIN author a ON a.author_id = da.author_id
        LEFT JOIN university_member um ON um.person_id = a.person_id
        WHERE da.document_id = %s
        ORDER BY da.author_order
        """,
        (doc_id,),
    )
    doc_authors = cur.fetchall()

    cur.execute(
        """
        SELECT dc.category_id, c.cate_name
        FROM document_category dc
        JOIN category c ON c.category_id = dc.category_id
        WHERE dc.document_id = %s
        ORDER BY c.cate_name
        """,
        (doc_id,),
    )
    doc_categories = cur.fetchall()

    cur.execute(
        """
        SELECT dr.digital_id, dr.file_format, dr.`size`, dr.upload_date,
               dr.access_level, oal.license_name
        FROM digital_resource dr
        LEFT JOIN open_access_license oal ON oal.license_id = dr.license_id
        WHERE dr.document_id = %s
        ORDER BY dr.digital_id
        """,
        (doc_id,),
    )
    doc_digitals = cur.fetchall()

    cur.execute("SELECT publisher_id, pub_name FROM publisher ORDER BY publisher_id")
    publishers = cur.fetchall()

    cur.execute("SELECT employee_code, `position` FROM library_staff ORDER BY employee_code")
    staffs = cur.fetchall()

    cur.execute("SELECT category_id, cate_name FROM category ORDER BY cate_name")
    all_categories = cur.fetchall()

    cur.execute("SELECT author_id, author_name, person_id FROM author ORDER BY author_id LIMIT 150")
    all_authors = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "document_detail.html",
        doc=doc,
        copies=copies,
        doc_authors=doc_authors,
        doc_categories=doc_categories,
        doc_digitals=doc_digitals,
        publishers=publishers,
        staffs=staffs,
        all_categories=all_categories,
        all_authors=all_authors,
    )


# =====================================================================
# 2. MƯỢN & TRẢ SÁCH VẬT LÝ (FR-03, FR-04, FR-05, FR-06, BR01-BR07, BR15)
# =====================================================================
@app.route("/loans", methods=["GET", "POST"])
def loans():
    try:
        conn = get_db()
    except mysql.connector.Error as err:
        return render_template("error.html", error=str(err), config=DB_CONFIG), 500

    user = get_current_user(conn)
    cur = conn.cursor(dictionary=True)

    if request.method == "POST":
        action = request.form.get("action")

        if not has_role(user, ("Administrator", "Library staff")):
            flash(
                "Từ chối phân quyền (NFR-03): Chỉ Nhân viên thư viện / Quản trị viên được lập phiếu mượn, trả sách hoặc báo mất.",
                "danger",
            )
            cur.close()
            conn.close()
            return redirect(url_for("loans"))

        if action == "borrow":
            member_id = request.form.get("member_id", "").strip()
            copy_id = request.form.get("copy_id", "").strip()
            staff_id = request.form.get("staff_id", "").strip()
            borrow_date = request.form.get("borrow_date", "").strip() or str(date.today())
            due_date = request.form.get("due_date", "").strip()

            try:
                loan_id = next_id(cur, "loan", "loan_id", "LOA", 5)
                cur.execute(
                    """
                    INSERT INTO loan (loan_id, member_id, copy_id, staff_id, borrow_date, due_date)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (loan_id, member_id, copy_id, staff_id, borrow_date, due_date),
                )
                conn.commit()
                flash(
                    f"Tạo phiếu mượn thành công: {loan_id} (Trigger đã tự động chuyển bản sao {copy_id} sang Borrowed).",
                    "success",
                )
            except mysql.connector.Error as err:
                conn.rollback()
                flash(f"MySQL chặn giao dịch: {err.msg}", "danger")

        elif action == "return":
            loan_id = request.form.get("loan_id", "").strip()
            ret_date = request.form.get("return_date", "").strip() or None
            try:
                cur.execute("SELECT fine_id FROM fine WHERE loan_id = %s", (loan_id,))
                had_fine = cur.fetchone() is not None
                cur.callproc("sp_return_loan", [loan_id, ret_date])
                for _ in cur.stored_results():
                    pass
                conn.commit()

                cur.execute("SELECT fine_id, amount FROM fine WHERE loan_id = %s", (loan_id,))
                gen_fine = cur.fetchone()
                if gen_fine and not had_fine:
                    flash(
                        f"Đã trả sách phiếu {loan_id}. Vì trễ hạn, Trigger trg_loan_au vừa tự sinh biên lai phạt "
                        f"{gen_fine['fine_id']} số tiền {gen_fine['amount']:,.0f} VNĐ (5.000đ/ngày - BR10).",
                        "success",
                    )
                elif gen_fine and had_fine:
                    flash(
                        f"Đã trả sách phiếu {loan_id} (bản sao đã chuyển về Available). "
                        f"Phiếu này đã có sẵn biên lai phạt {gen_fine['fine_id']} ({gen_fine['amount']:,.0f} VNĐ).",
                        "success",
                    )
                else:
                    flash(
                        f"Đã trả sách đúng hạn cho phiếu {loan_id}. Bản sao đã tự động chuyển về Available.",
                        "success",
                    )
            except mysql.connector.Error as err:
                conn.rollback()
                flash(f"Lỗi khi trả sách: {err.msg}", "danger")

        elif action == "mark_lost":
            loan_id = request.form.get("loan_id", "").strip()
            try:
                cur.execute(
                    "UPDATE loan SET status = 'LOST' WHERE loan_id = %s AND status IN ('ACTIVE', 'OVERDUE')",
                    (loan_id,),
                )
                if cur.rowcount == 0:
                    flash(f"Phiếu {loan_id} không ở trạng thái đang mượn để báo mất.", "danger")
                else:
                    conn.commit()
                    flash(
                        f"Đã báo mất sách cho phiếu {loan_id}. Trigger trg_loan_au đã tự đổi trạng thái bản sao sang Lost.",
                        "success",
                    )
            except mysql.connector.Error as err:
                conn.rollback()
                flash(f"Lỗi báo mất sách: {err.msg}", "danger")

        elif action == "mark_overdue":
            try:
                cur.callproc("sp_mark_overdue_loans")
                for _ in cur.stored_results():
                    pass
                conn.commit()
                flash("Đã chạy thủ tục sp_mark_overdue_loans() để cập nhật các phiếu quá hạn.", "success")
            except mysql.connector.Error as err:
                conn.rollback()
                flash(f"Lỗi cập nhật quá hạn: {err.msg}", "danger")

        cur.close()
        conn.close()
        return redirect(url_for("loans"))

    status_filter = request.args.get("status", "OPEN")
    member_filter = request.args.get("member", "").strip()
    prefill_copy = request.args.get("copy_id", "").strip()

    # Nếu đang là Sinh viên / Giảng viên thì chỉ xem lịch sử mượn của chính mình
    restricted_self = not has_role(user, ("Administrator", "Library staff"))

    sql = """
        SELECT l.loan_id, l.member_id, pe.name AS member_name,
               l.copy_id, d.document_id, d.title, l.borrow_date, l.due_date,
               l.return_date, l.status
        FROM loan l
        JOIN university_member m ON m.member_id = l.member_id
        JOIN person pe           ON pe.person_id = m.person_id
        JOIN physical_copy pc    ON pc.copy_id = l.copy_id
        JOIN document d          ON d.document_id = pc.document_id
        WHERE 1=1
    """
    params = []
    if restricted_self:
        sql += " AND l.member_id = %s"
        params.append(user["member_id"])
    if status_filter == "OPEN":
        sql += " AND l.status IN ('ACTIVE', 'OVERDUE')"
    elif status_filter in ("ACTIVE", "OVERDUE", "RETURNED", "LOST"):
        sql += " AND l.status = %s"
        params.append(status_filter)

    if member_filter and not restricted_self:
        sql += " AND (l.member_id LIKE %s OR pe.name LIKE %s OR l.loan_id LIKE %s OR l.copy_id LIKE %s)"
        like = f"%{member_filter}%"
        params.extend([like, like, like, like])

    sql += " ORDER BY l.loan_id DESC LIMIT 50"
    cur.execute(sql, params)
    loan_rows = cur.fetchall()

    if restricted_self:
        cur.execute(
            "SELECT * FROM v_overdue_loans WHERE member_id = %s ORDER BY days_overdue DESC LIMIT 15",
            (user["member_id"],),
        )
    else:
        cur.execute("SELECT * FROM v_overdue_loans ORDER BY days_overdue DESC LIMIT 15")
    overdue_rows = cur.fetchall()

    cur.execute(
        """
        SELECT ls.member_id, pe.name, ls.employee_code
        FROM library_staff ls
        JOIN university_member m ON m.member_id = ls.member_id
        JOIN person pe           ON pe.person_id = m.person_id
        ORDER BY ls.member_id
        """
    )
    staff_list = cur.fetchall()

    cur.close()
    conn.close()

    today_str = str(date.today())
    default_due = str(date.today() + timedelta(days=14))

    return render_template(
        "loans.html",
        loan_rows=loan_rows,
        overdue_rows=overdue_rows,
        staff_list=staff_list,
        status_filter=status_filter,
        member_filter=member_filter,
        prefill_copy=prefill_copy,
        today_str=today_str,
        default_due=default_due,
        restricted_self=restricted_self,
    )


# =====================================================================
# 3. TIỀN PHẠT & THANH TOÁN (FR-06, FR-07, BR10, BR11, BR16)
# =====================================================================
@app.route("/fines", methods=["GET", "POST"])
def fines():
    try:
        conn = get_db()
    except mysql.connector.Error as err:
        return render_template("error.html", error=str(err), config=DB_CONFIG), 500

    user = get_current_user(conn)
    cur = conn.cursor(dictionary=True)

    if request.method == "POST":
        action = request.form.get("action", "pay")

        if not has_role(user, ("Administrator", "Library staff")):
            flash("Từ chối phân quyền (NFR-03): Chỉ thủ thư / quản trị viên được xử lý tiền phạt và thanh toán.", "danger")
            cur.close()
            conn.close()
            return redirect(url_for("fines"))

        if action == "pay":
            fine_id = request.form.get("fine_id", "").strip()
            amount = request.form.get("amount", "").strip()
            method = request.form.get("method", "Tiền mặt").strip()

            try:
                payment_id = next_id(cur, "payment", "payment_id", "PAY", 4)
                cur.execute(
                    """
                    INSERT INTO payment (payment_id, fine_id, amount, method)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (payment_id, fine_id, float(amount), method),
                )
                conn.commit()
                flash(
                    f"Thanh toán thành công ({payment_id}). Trigger đã tự chuyển khoản phạt {fine_id} sang Paid.",
                    "success",
                )
            except (mysql.connector.Error, ValueError) as err:
                conn.rollback()
                flash(f"MySQL chặn thanh toán: {getattr(err, 'msg', str(err))}", "danger")

        elif action == "create_fine":
            loan_id = request.form.get("loan_id", "").strip()
            amount = request.form.get("amount", "").strip()
            reason = request.form.get("reason", "").strip() or "Làm mất / hư hỏng tài liệu"

            try:
                fine_id = next_id(cur, "fine", "fine_id", "FIN", 4)
                cur.execute(
                    """
                    INSERT INTO fine (fine_id, loan_id, amount, reason, status)
                    VALUES (%s, %s, %s, %s, 'Unpaid')
                    """,
                    (fine_id, loan_id, float(amount), reason),
                )
                conn.commit()
                flash(f"Đã lập biên lai phạt {fine_id} cho phiếu {loan_id}.", "success")
            except (mysql.connector.Error, ValueError) as err:
                conn.rollback()
                flash(f"MySQL từ chối lập phạt: {getattr(err, 'msg', str(err))}", "danger")

        elif action == "waive_fine":
            fine_id = request.form.get("fine_id", "").strip()
            try:
                cur.execute(
                    "UPDATE fine SET status = 'Waived' WHERE fine_id = %s AND status = 'Unpaid'",
                    (fine_id,),
                )
                if cur.rowcount == 0:
                    flash(f"Khoản phạt {fine_id} không ở trạng thái Unpaid để miễn giảm.", "danger")
                else:
                    conn.commit()
                    flash(f"Đã miễn giảm (Waived) khoản phạt {fine_id}.", "success")
            except mysql.connector.Error as err:
                conn.rollback()
                flash(f"Lỗi miễn giảm phạt: {err.msg}", "danger")

        cur.close()
        conn.close()
        return redirect(url_for("fines"))

    restricted_self = not has_role(user, ("Administrator", "Library staff"))
    status_filter = request.args.get("status", "Unpaid")

    sql = """
        SELECT f.fine_id, f.loan_id, l.member_id, pe.name AS member_name,
               f.amount, f.reason, f.issued_date, f.status
        FROM fine f
        JOIN loan l              ON l.loan_id = f.loan_id
        JOIN university_member m ON m.member_id = l.member_id
        JOIN person pe           ON pe.person_id = m.person_id
        WHERE 1=1
    """
    params = []
    if restricted_self:
        sql += " AND l.member_id = %s"
        params.append(user["member_id"])
    if status_filter in ("Unpaid", "Paid", "Waived"):
        sql += " AND f.status = %s"
        params.append(status_filter)
    sql += " ORDER BY f.fine_id DESC LIMIT 50"

    cur.execute(sql, params)
    fine_rows = cur.fetchall()

    if restricted_self:
        cur.execute(
            "SELECT * FROM v_member_fine_summary WHERE member_id = %s",
            (user["member_id"],),
        )
    else:
        cur.execute(
            "SELECT * FROM v_member_fine_summary WHERE unpaid_amount > 0 ORDER BY unpaid_amount DESC LIMIT 15"
        )
    debt_summary = cur.fetchall()

    pay_sql = """
        SELECT p.payment_id, p.fine_id, l.member_id, pe.name AS member_name,
               p.payment_date, p.amount, p.method, p.status
        FROM payment p
        JOIN fine f              ON f.fine_id = p.fine_id
        JOIN loan l              ON l.loan_id = f.loan_id
        JOIN university_member m ON m.member_id = l.member_id
        JOIN person pe           ON pe.person_id = m.person_id
    """
    pay_params = []
    if restricted_self:
        pay_sql += " WHERE l.member_id = %s"
        pay_params.append(user["member_id"])
    pay_sql += " ORDER BY p.payment_id DESC LIMIT 20"
    cur.execute(pay_sql, pay_params)
    payment_rows = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "fines.html",
        fine_rows=fine_rows,
        debt_summary=debt_summary,
        payment_rows=payment_rows,
        status_filter=status_filter,
        restricted_self=restricted_self,
    )


# =====================================================================
# 4. TÀI NGUYÊN SỐ & KIỂM SOÁT TRUY CẬP (FR-08, FR-09, FR-10, BR08, BR09)
# =====================================================================
@app.route("/digital", methods=["GET", "POST"])
def digital():
    try:
        conn = get_db()
    except mysql.connector.Error as err:
        return render_template("error.html", error=str(err), config=DB_CONFIG), 500

    user = get_current_user(conn)
    cur = conn.cursor(dictionary=True)

    if request.method == "POST":
        action = request.form.get("action")

        if action == "access":
            # Nếu là Sinh viên / Giảng viên thì mặc định dùng chính member_id của phiên đăng nhập
            if has_role(user, ("Administrator", "Library staff")):
                member_id = request.form.get("member_id", "").strip()
            else:
                member_id = user["member_id"]

            digital_id = request.form.get("digital_id", "").strip()
            access_type = request.form.get("access_type", "VIEW").strip()
            try:
                access_id = next_id(cur, "digital_access", "access_id", "ACCLOG", 5)
                cur.execute(
                    """
                    INSERT INTO digital_access (access_id, member_id, digital_id, access_type)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (access_id, member_id, digital_id, access_type),
                )
                conn.commit()
                flash(
                    f"Truy cập hợp lệ ({access_id}): {member_id} đã {access_type} tài liệu {digital_id}.",
                    "success",
                )
            except mysql.connector.Error as err:
                conn.rollback()
                flash(f"MySQL chặn truy cập (BR08): {err.msg}", "danger")

        elif action == "add_digital":
            if not has_role(user, ("Administrator", "Library staff")):
                flash("Từ chối phân quyền (NFR-03): Chỉ thủ thư / quản trị viên được thêm tài nguyên số.", "danger")
            else:
                document_id = request.form.get("document_id", "").strip()
                file_format = request.form.get("file_format", "PDF").strip()
                size_val = request.form.get("size", "").strip()
                access_level = request.form.get("access_level", "OPEN").strip()
                license_id = request.form.get("license_id", "").strip() or None

                try:
                    dig_id = next_id(cur, "digital_resource", "digital_id", "DIG", 5)
                    cur.execute(
                        """
                        INSERT INTO digital_resource (
                            digital_id, document_id, file_format, `size`, access_level, license_id
                        )
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (
                            dig_id,
                            document_id,
                            file_format,
                            float(size_val) if size_val else None,
                            access_level,
                            license_id,
                        ),
                    )
                    conn.commit()
                    flash(f"Thêm tài nguyên số thành công: {dig_id}", "success")
                except (mysql.connector.Error, ValueError) as err:
                    conn.rollback()
                    flash(f"MySQL chặn thêm tài nguyên số (BR09): {getattr(err, 'msg', str(err))}", "danger")

        elif action == "update_digital":
            if not has_role(user, ("Administrator", "Library staff")):
                flash("Từ chối phân quyền (NFR-03).", "danger")
            else:
                digital_id = request.form.get("digital_id", "").strip()
                access_level = request.form.get("access_level", "OPEN").strip()
                license_id = request.form.get("license_id", "").strip() or None
                try:
                    cur.execute(
                        "UPDATE digital_resource SET access_level = %s, license_id = %s WHERE digital_id = %s",
                        (access_level, license_id, digital_id),
                    )
                    conn.commit()
                    flash(f"Đã cập nhật quyền tài nguyên số {digital_id} -> {access_level}.", "success")
                except mysql.connector.Error as err:
                    conn.rollback()
                    flash(f"MySQL chặn cập nhật (BR09): {err.msg}", "danger")

        cur.close()
        conn.close()
        return redirect(url_for("digital"))

    level_filter = request.args.get("level", "").strip()
    q_dig = request.args.get("q", "").strip()

    res_sql = """
        SELECT dr.digital_id, dr.document_id, d.title, dr.file_format,
               dr.`size`, dr.access_level, dr.license_id, oal.license_name
        FROM digital_resource dr
        JOIN document d ON d.document_id = dr.document_id
        LEFT JOIN open_access_license oal ON oal.license_id = dr.license_id
        WHERE 1=1
    """
    res_params = []
    if level_filter in ("OPEN", "RESTRICTED", "PRIVATE"):
        res_sql += " AND dr.access_level = %s"
        res_params.append(level_filter)
    if q_dig:
        like = f"%{q_dig}%"
        res_sql += " AND (dr.digital_id LIKE %s OR d.title LIKE %s OR dr.document_id LIKE %s)"
        res_params.extend([like, like, like])
    res_sql += " ORDER BY dr.digital_id LIMIT 40"

    cur.execute(res_sql, res_params)
    resources = cur.fetchall()

    restricted_self = not has_role(user, ("Administrator", "Library staff"))
    log_sql = """
        SELECT da.access_id, da.member_id, pe.name AS member_name,
               ua.permission_level, da.digital_id, dr.access_level,
               da.access_type, da.access_time
        FROM digital_access da
        JOIN university_member m  ON m.member_id = da.member_id
        JOIN person pe            ON pe.person_id = m.person_id
        LEFT JOIN user_account ua ON ua.member_id = m.member_id
        JOIN digital_resource dr  ON dr.digital_id = da.digital_id
    """
    log_params = []
    if restricted_self:
        log_sql += " WHERE da.member_id = %s"
        log_params.append(user["member_id"])
    log_sql += " ORDER BY da.access_time DESC LIMIT 20"

    cur.execute(log_sql, log_params)
    access_logs = cur.fetchall()

    cur.execute("SELECT license_id, license_name FROM open_access_license ORDER BY license_id")
    licenses = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "digital.html",
        resources=resources,
        access_logs=access_logs,
        licenses=licenses,
        level_filter=level_filter,
        q_dig=q_dig,
        restricted_self=restricted_self,
    )


# =====================================================================
# 5. THÀNH VIÊN, TÁC GIẢ & MÔ HÌNH EER CHỒNG CHÉO (BR14, FR-12, NFR-02/03)
# =====================================================================
@app.route("/people", methods=["GET", "POST"])
def people():
    try:
        conn = get_db()
    except mysql.connector.Error as err:
        return render_template("error.html", error=str(err), config=DB_CONFIG), 500

    user = get_current_user(conn)
    cur = conn.cursor(dictionary=True)

    if request.method == "POST":
        action = request.form.get("action")

        if action == "add_person":
            if not has_role(user, ("Administrator", "Library staff")):
                flash("Từ chối phân quyền (NFR-03): Chỉ thủ thư / quản trị viên được thêm cá nhân.", "danger")
            else:
                name = request.form.get("name", "").strip()
                birth = request.form.get("birth", "").strip() or None
                email = request.form.get("email", "").strip() or None
                phone = request.form.get("phone", "").strip() or None
                address = request.form.get("address", "").strip() or None
                try:
                    pid = next_id(cur, "person", "person_id", "PER", 4)
                    cur.execute(
                        """
                        INSERT INTO person (person_id, name, birth, email, phone, address)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (pid, name, birth, email, phone, address),
                    )
                    conn.commit()
                    flash(f"Thêm cá nhân thành công: {pid} ({name}).", "success")
                except mysql.connector.Error as err:
                    conn.rollback()
                    flash(f"MySQL chặn thêm cá nhân: {err.msg}", "danger")

        elif action == "add_author":
            if not has_role(user, ("Administrator", "Library staff", "Faculty")):
                flash("Từ chối phân quyền (NFR-03): Sinh viên không được tạo tác giả.", "danger")
            else:
                author_name = request.form.get("author_name", "").strip()
                person_id = request.form.get("person_id", "").strip() or None
                try:
                    aid = next_id(cur, "author", "author_id", "AUT", 4)
                    cur.execute(
                        "INSERT INTO author (author_id, person_id, author_name) VALUES (%s, %s, %s)",
                        (aid, person_id, author_name),
                    )
                    conn.commit()
                    flash(
                        f"Thêm tác giả thành công: {aid} - {author_name}"
                        + (f" (liên kết {person_id} - thực thể chồng chéo BR14)" if person_id else " (tác giả ngoài trường)"),
                        "success",
                    )
                except mysql.connector.Error as err:
                    conn.rollback()
                    flash(f"MySQL từ chối thêm tác giả: {err.msg}", "danger")

        elif action == "update_member_account":
            if not has_role(user, ("Administrator",)):
                flash("Từ chối phân quyền (NFR-03): Chỉ Quản trị viên (Administrator) được thay đổi trạng thái thành viên và cấp quyền tài khoản.", "danger")
            else:
                member_id = request.form.get("member_id", "").strip()
                member_status = request.form.get("member_status", "Active").strip()
                perm_level = request.form.get("permission_level", "").strip()
                acc_status = request.form.get("account_status", "").strip()
                try:
                    cur.execute(
                        "UPDATE university_member SET status = %s WHERE member_id = %s",
                        (member_status, member_id),
                    )
                    if perm_level and acc_status:
                        cur.execute(
                            """
                            UPDATE user_account
                            SET permission_level = %s, account_status = %s
                            WHERE member_id = %s
                            """,
                            (perm_level, acc_status, member_id),
                        )
                    conn.commit()
                    flash(
                        f"Đã cập nhật {member_id}: Thẻ={member_status}"
                        + (f", Tài khoản={acc_status}, Quyền số={perm_level}" if perm_level else ""),
                        "success",
                    )
                except mysql.connector.Error as err:
                    conn.rollback()
                    flash(f"Lỗi cập nhật tài khoản: {err.msg}", "danger")

        cur.close()
        conn.close()
        return redirect(url_for("people"))

    role_filter = request.args.get("role", "").strip()
    q_people = request.args.get("q", "").strip()

    # Thống kê phân cấp EER (Chuyên biệt hóa Disjoint & Chồng chéo Overlapping)
    cur.execute(
        """
        SELECT
            (SELECT COUNT(*) FROM person) AS total_person,
            (SELECT COUNT(*) FROM university_member) AS total_member,
            (SELECT COUNT(*) FROM student) AS total_student,
            (SELECT COUNT(*) FROM faculty_researcher) AS total_faculty,
            (SELECT COUNT(*) FROM library_staff) AS total_staff,
            (SELECT COUNT(*) FROM administrator) AS total_admin,
            (SELECT COUNT(*) FROM author) AS total_author,
            (SELECT COUNT(DISTINCT a.person_id)
               FROM author a
               JOIN university_member m ON m.person_id = a.person_id) AS overlapping_count,
            (SELECT COUNT(*) FROM author WHERE person_id IS NULL) AS external_author_count
        """
    )
    eer_stats = cur.fetchone()

    # Danh sách thành viên + vai trò + tài khoản + có phải tác giả không (BR14)
    mem_sql = """
        SELECT r.member_id, m.person_id, r.name, r.member_role, r.status,
               ua.username, ua.permission_level, ua.account_status,
               (SELECT COUNT(*) FROM author a WHERE a.person_id = m.person_id) AS is_author,
               (SELECT COUNT(*) FROM loan l WHERE l.member_id = r.member_id AND l.status IN ('ACTIVE','OVERDUE')) AS active_loans
        FROM v_member_role r
        JOIN university_member m  ON m.member_id = r.member_id
        LEFT JOIN user_account ua ON ua.member_id = r.member_id
        WHERE 1=1
    """
    mem_params = []
    if role_filter:
        mem_sql += " AND r.member_role = %s"
        mem_params.append(role_filter)
    if q_people:
        like = f"%{q_people}%"
        mem_sql += " AND (r.member_id LIKE %s OR r.name LIKE %s OR m.person_id LIKE %s OR ua.username LIKE %s)"
        mem_params.extend([like, like, like, like])
    mem_sql += " ORDER BY r.member_id LIMIT 40"

    cur.execute(mem_sql, mem_params)
    members = cur.fetchall()

    # Minh chứng cụ thể thực thể chồng chéo BR14: Vừa là thành viên trường vừa là tác giả có sách
    cur.execute(
        """
        SELECT p.person_id, p.name AS real_name, r.member_id, r.member_role,
               a.author_id, a.author_name,
               COUNT(da.document_id) AS authored_docs
        FROM person p
        JOIN university_member m ON m.person_id = p.person_id
        JOIN v_member_role r     ON r.member_id = m.member_id
        JOIN author a            ON a.person_id = p.person_id
        LEFT JOIN document_author da ON da.author_id = a.author_id
        GROUP BY p.person_id, p.name, r.member_id, r.member_role, a.author_id, a.author_name
        ORDER BY authored_docs DESC, p.person_id
        LIMIT 15
        """
    )
    overlapping_rows = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "people.html",
        eer_stats=eer_stats,
        members=members,
        overlapping_rows=overlapping_rows,
        role_filter=role_filter,
        q_people=q_people,
    )


# =====================================================================
# 6. BÁO CÁO & ĐẦY ĐỦ 15 TRUY VẤN PHỨC TẠP (Phase 3 - Q1 đến Q15)
# =====================================================================
COMPLEX_QUERIES = {
    "Q1": {
        "title": "Q1. Phiếu mượn đang hoạt động: người mượn, tài liệu, thủ thư xử lý",
        "tag": "JOIN 8 bảng",
        "sql": """SELECT l.loan_id, pe.name AS borrower, d.title,
       l.borrow_date, l.due_date, l.status, ps.name AS processed_by
FROM loan l
JOIN university_member m  ON m.member_id  = l.member_id
JOIN person pe            ON pe.person_id = m.person_id
JOIN physical_copy pc     ON pc.copy_id   = l.copy_id
JOIN document d           ON d.document_id = pc.document_id
JOIN library_staff s      ON s.member_id  = l.staff_id
JOIN university_member ms ON ms.member_id = s.member_id
JOIN person ps            ON ps.person_id = ms.person_id
WHERE l.status IN ('ACTIVE', 'OVERDUE')
ORDER BY l.due_date
LIMIT 50""",
    },
    "Q2": {
        "title": "Q2. Top 5 tài liệu được mượn nhiều nhất",
        "tag": "Aggregation + GROUP BY + LIMIT",
        "sql": """SELECT d.document_id, d.title, COUNT(l.loan_id) AS loan_count
FROM document d
JOIN physical_copy pc ON pc.document_id = d.document_id
JOIN loan l           ON l.copy_id = pc.copy_id
GROUP BY d.document_id, d.title
ORDER BY loan_count DESC, d.title
LIMIT 5""",
    },
    "Q3": {
        "title": "Q3. Tài liệu chưa từng được mượn lần nào",
        "tag": "Subquery NOT EXISTS",
        "sql": """SELECT d.document_id, d.title, d.`type`
FROM document d
WHERE NOT EXISTS (
    SELECT 1
    FROM physical_copy pc
    JOIN loan l ON l.copy_id = pc.copy_id
    WHERE pc.document_id = d.document_id
)
LIMIT 50""",
    },
    "Q4": {
        "title": "Q4. Thành viên mượn nhiều hơn mức trung bình",
        "tag": "Subquery vô hướng + HAVING",
        "sql": """SELECT m.member_id, pe.name, COUNT(l.loan_id) AS total_loans
FROM loan l
JOIN university_member m ON m.member_id = l.member_id
JOIN person pe           ON pe.person_id = m.person_id
GROUP BY m.member_id, pe.name
HAVING COUNT(l.loan_id) > (SELECT COUNT(*) / COUNT(DISTINCT member_id) FROM loan)
ORDER BY total_loans DESC, pe.name
LIMIT 50""",
    },
    "Q5": {
        "title": "Q5. Thống kê tiền phạt theo trạng thái",
        "tag": "Aggregation nhiều hàm",
        "sql": """SELECT f.status,
       COUNT(*)             AS fine_count,
       SUM(f.amount)        AS total_amount,
       ROUND(AVG(f.amount)) AS avg_amount,
       MAX(f.amount)        AS max_amount
FROM fine f
GROUP BY f.status
ORDER BY total_amount DESC""",
    },
    "Q6": {
        "title": "Q6. Thành viên đang nợ tiền phạt (Unpaid)",
        "tag": "JOIN + HAVING",
        "sql": """SELECT m.member_id, pe.name,
       COUNT(f.fine_id) AS unpaid_count,
       SUM(f.amount)    AS unpaid_total
FROM fine f
JOIN loan l              ON l.loan_id = f.loan_id
JOIN university_member m ON m.member_id = l.member_id
JOIN person pe           ON pe.person_id = m.person_id
WHERE f.status = 'Unpaid'
GROUP BY m.member_id, pe.name
HAVING SUM(f.amount) > 0
ORDER BY unpaid_total DESC
LIMIT 50""",
    },
    "Q7": {
        "title": "Q7. Lượt xem / tải theo mức truy cập của tài liệu số",
        "tag": "Aggregation có điều kiện",
        "sql": """SELECT dr.access_level,
       COUNT(da.access_id)              AS total_access,
       SUM(da.access_type = 'VIEW')     AS views,
       SUM(da.access_type = 'DOWNLOAD') AS downloads,
       COUNT(DISTINCT da.member_id)     AS distinct_users
FROM digital_resource dr
LEFT JOIN digital_access da ON da.digital_id = dr.digital_id
GROUP BY dr.access_level
ORDER BY total_access DESC""",
    },
    "Q8": {
        "title": "Q8. Tác giả có từ 2 tài liệu trở lên",
        "tag": "JOIN + GROUP_CONCAT + HAVING",
        "sql": """SELECT a.author_id, a.author_name,
       COUNT(da.document_id) AS doc_count,
       GROUP_CONCAT(d.title ORDER BY d.publication_year SEPARATOR '; ') AS titles
FROM author a
JOIN document_author da ON da.author_id = a.author_id
JOIN document d         ON d.document_id = da.document_id
GROUP BY a.author_id, a.author_name
HAVING COUNT(da.document_id) >= 2
ORDER BY doc_count DESC, a.author_name
LIMIT 50""",
    },
    "Q9": {
        "title": "Q9. Số tài liệu và số bản sao theo thể loại",
        "tag": "LEFT JOIN + COUNT DISTINCT",
        "sql": """SELECT c.cate_name,
       COUNT(DISTINCT dc.document_id) AS document_count,
       COUNT(DISTINCT pc.copy_id)     AS copy_count
FROM category c
LEFT JOIN document_category dc ON dc.category_id = c.category_id
LEFT JOIN physical_copy pc     ON pc.document_id = dc.document_id
GROUP BY c.category_id, c.cate_name
ORDER BY document_count DESC, c.cate_name""",
    },
    "Q10": {
        "title": "Q10. Xếp hạng thành viên theo lượt truy cập tài liệu số trong từng vai trò",
        "tag": "Window Function RANK() OVER",
        "sql": """SELECT r.member_role, r.name,
       COUNT(da.access_id) AS access_count,
       RANK() OVER (PARTITION BY r.member_role ORDER BY COUNT(da.access_id) DESC) AS rank_in_role
FROM v_member_role r
LEFT JOIN digital_access da ON da.member_id = r.member_id
GROUP BY r.member_role, r.member_id, r.name
ORDER BY r.member_role, rank_in_role, r.name
LIMIT 50""",
    },
    "Q11": {
        "title": "Q11. Tỷ lệ trả sách trễ hạn theo tháng",
        "tag": "Aggregation theo tháng",
        "sql": """SELECT DATE_FORMAT(l.return_date, '%Y-%m') AS return_month,
       COUNT(*) AS returned_loans,
       SUM(l.return_date > l.due_date) AS late_loans,
       ROUND(100 * SUM(l.return_date > l.due_date) / COUNT(*), 1) AS late_percent
FROM loan l
WHERE l.status = 'RETURNED'
GROUP BY DATE_FORMAT(l.return_date, '%Y-%m')
ORDER BY return_month""",
    },
    "Q12": {
        "title": "Q12. Số suất mượn còn lại của từng thành viên (BR01)",
        "tag": "Subquery trong FROM + CASE + EXISTS",
        "sql": """SELECT t.member_id, t.name, t.max_loans, t.current_loans,
       t.max_loans - t.current_loans AS remaining
FROM (
    SELECT m.member_id, pe.name,
           CASE WHEN EXISTS (SELECT 1 FROM student s WHERE s.member_id = m.member_id)
                THEN 5 ELSE 10 END AS max_loans,
           (SELECT COUNT(*) FROM loan l
             WHERE l.member_id = m.member_id
               AND l.status IN ('ACTIVE', 'OVERDUE')) AS current_loans
    FROM university_member m
    JOIN person pe ON pe.person_id = m.person_id
) t
ORDER BY remaining ASC, t.current_loans DESC, t.name
LIMIT 50""",
    },
    "Q13": {
        "title": "Q13. Tài liệu có bản sao nhưng không còn bản nào sẵn sàng cho mượn",
        "tag": "Correlated Subquery EXISTS / NOT EXISTS",
        "sql": """SELECT d.document_id, d.title,
       (SELECT COUNT(*) FROM physical_copy pc WHERE pc.document_id = d.document_id) AS total_copies
FROM document d
WHERE EXISTS (SELECT 1 FROM physical_copy pc WHERE pc.document_id = d.document_id)
  AND NOT EXISTS (SELECT 1 FROM physical_copy pc
                   WHERE pc.document_id = d.document_id AND pc.status = 'Available')
LIMIT 50""",
    },
    "Q14": {
        "title": "Q14. Top 5 thành viên có tổng tiền phạt cao nhất",
        "tag": "CTE (WITH)",
        "sql": """WITH member_fines AS (
    SELECT l.member_id,
           COUNT(*)      AS fine_count,
           SUM(f.amount) AS total_fine
    FROM fine f
    JOIN loan l ON l.loan_id = f.loan_id
    GROUP BY l.member_id
)
SELECT m.member_id, pe.name, mf.fine_count, mf.total_fine
FROM member_fines mf
JOIN university_member m ON m.member_id = mf.member_id
JOIN person pe           ON pe.person_id = m.person_id
ORDER BY mf.total_fine DESC, pe.name
LIMIT 5""",
    },
    "Q15": {
        "title": "Q15. Toàn bộ hoạt động (mượn sách + truy cập số) của một thành viên",
        "tag": "UNION ALL",
        "has_member_param": True,
        "sql": """SELECT 'Mượn sách' AS activity, l.borrow_date AS activity_date, d.title
FROM loan l
JOIN physical_copy pc ON pc.copy_id = l.copy_id
JOIN document d       ON d.document_id = pc.document_id
WHERE l.member_id = %s
UNION ALL
SELECT CONCAT('Truy cập số - ', da.access_type) AS activity,
       DATE(da.access_time) AS activity_date, d.title
FROM digital_access da
JOIN digital_resource dr ON dr.digital_id = da.digital_id
JOIN document d          ON d.document_id = dr.document_id
WHERE da.member_id = %s
ORDER BY activity_date""",
    },
}


@app.route("/reports")
def reports():
    try:
        conn = get_db()
    except mysql.connector.Error as err:
        return render_template("error.html", error=str(err), config=DB_CONFIG), 500

    get_current_user(conn)
    selected_q = request.args.get("q", "Q1").upper()
    if selected_q not in COMPLEX_QUERIES:
        selected_q = "Q1"
    q15_member = request.args.get("member_id", "MEM0084").strip() or "MEM0084"

    q_meta = COMPLEX_QUERIES[selected_q]
    cur = conn.cursor(dictionary=True)

    t0 = time.perf_counter()
    if q_meta.get("has_member_param"):
        cur.execute(q_meta["sql"], (q15_member, q15_member))
    else:
        cur.execute(q_meta["sql"])
    rows = cur.fetchall()
    exec_ms = round((time.perf_counter() - t0) * 1000, 2)
    columns = list(rows[0].keys()) if rows else []

    cur.close()
    conn.close()

    return render_template(
        "reports.html",
        queries=COMPLEX_QUERIES,
        selected_q=selected_q,
        q_meta=q_meta,
        q15_member=q15_member,
        columns=columns,
        rows=rows,
        exec_ms=exec_ms,
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
