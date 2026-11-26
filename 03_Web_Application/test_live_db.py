"""
Bộ kiểm thử tự động End-to-End cho CSDL digital_library & Ứng dụng Flask (INT1313)
Cách chạy: python test_live_db.py
An toàn: Mọi phép thử thêm/sửa dữ liệu đều được ROLLBACK hoặc dọn sạch sau khi test xong.
"""
import time
import mysql.connector
from app import DB_CONFIG, COMPLEX_QUERIES, app as flask_app


def run_tests():
    passed = 0
    failed = 0

    def ok(name, detail=""):
        nonlocal passed
        passed += 1
        print(f"  [PASS] {name}" + (f" -> {detail}" if detail else ""))

    def fail(name, detail=""):
        nonlocal failed
        failed += 1
        print(f"  [FAIL] {name}" + (f" -> {detail}" if detail else ""))

    print("=== 1. KIỂM TRA KẾT NỐI & CẤU TRÚC 20 BẢNG / 4 VIEWS ===")
    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor(dictionary=True)

    cur.execute("SHOW FULL TABLES WHERE Table_type = 'BASE TABLE'")
    tables = [list(r.values())[0] for r in cur.fetchall()]
    if len(tables) == 20:
        ok("Đủ 20 bảng cơ sở dữ liệu", ", ".join(tables[:5]) + "...")
    else:
        fail("Số lượng bảng không khớp", f"Tìm thấy {len(tables)} bảng (cần 20)")

    cur.execute("SHOW FULL TABLES WHERE Table_type = 'VIEW'")
    views = [list(r.values())[0] for r in cur.fetchall()]
    if len(views) >= 4:
        ok("Đủ 4 Views nghiệp vụ", ", ".join(views))
    else:
        fail("Thiếu View", f"Tìm thấy {views}")

    print("\n=== 2. KIỂM TRA HIỆU NĂNG TÌM KIẾM TỐI ƯU (NFR-01 < 200ms) ===")
    t0 = time.perf_counter()
    cur.execute(
        """
        SELECT d.document_id FROM document d
        WHERE d.title LIKE %s
        ORDER BY d.document_id ASC LIMIT 50
        """,
        ("%dữ liệu%",),
    )
    ids = [r["document_id"] for r in cur.fetchall()]
    if ids:
        ph = ", ".join(["%s"] * len(ids))
        cur.execute(f"SELECT * FROM v_document_catalog WHERE document_id IN ({ph})", ids)
        _ = cur.fetchall()
    ms = round((time.perf_counter() - t0) * 1000, 2)
    if ms < 200:
        ok("Truy vấn tìm kiếm NFR-01 đạt < 200ms", f"{ms} ms ({len(ids)} dòng)")
    else:
        fail("Truy vấn vượt 200ms", f"{ms} ms")

    print("\n=== 3. KIỂM TRA TOÀN BỘ 15 TRUY VẤN PHỨC TẠP (Q1 - Q15) ===")
    for qid, meta in COMPLEX_QUERIES.items():
        try:
            t0 = time.perf_counter()
            if meta.get("has_member_param"):
                cur.execute(meta["sql"], ("MEM0084", "MEM0084"))
            else:
                cur.execute(meta["sql"])
            rows = cur.fetchall()
            dt = round((time.perf_counter() - t0) * 1000, 2)
            ok(f"{qid} ({meta['tag']})", f"{len(rows)} dòng trong {dt} ms")
        except mysql.connector.Error as err:
            fail(f"{qid} bị lỗi SQL", err.msg)

    print("\n=== 4. KIỂM TRA CÁC TRIGGER & RÀNG BUỘC NGHIỆP VỤ (BR01 - BR16) ===")
    must_fail_cases = [
        (
            "BR02: Thành viên quá hạn MEM0006 không được mượn thêm",
            "INSERT INTO loan (loan_id, member_id, copy_id, staff_id, due_date) "
            "VALUES ('LOA99001', 'MEM0006', 'COP00001', 'MEM0362', CURDATE() + INTERVAL 14 DAY)",
        ),
        (
            "Suspended: Thành viên MEM0069 bị đình chỉ không được mượn",
            "INSERT INTO loan (loan_id, member_id, copy_id, staff_id, due_date) "
            "VALUES ('LOA99002', 'MEM0069', 'COP00001', 'MEM0362', CURDATE() + INTERVAL 14 DAY)",
        ),
        (
            "BR06/07: Bản sao Lost (COP00030) không được mượn",
            "INSERT INTO loan (loan_id, member_id, copy_id, staff_id, due_date) "
            "VALUES ('LOA99003', 'MEM0004', 'COP00030', 'MEM0362', CURDATE() + INTERVAL 14 DAY)",
        ),
        (
            "BR03/15: Bản sao đang mượn (COP00002) không được mượn trùng",
            "INSERT INTO loan (loan_id, member_id, copy_id, staff_id, due_date) "
            "VALUES ('LOA99004', 'MEM0004', 'COP00002', 'MEM0362', CURDATE() + INTERVAL 14 DAY)",
        ),
        (
            "BR05: Ngày đến hạn <= ngày mượn bị chặn",
            "INSERT INTO loan (loan_id, member_id, copy_id, staff_id, borrow_date, due_date) "
            "VALUES ('LOA99005', 'MEM0004', 'COP00001', 'MEM0362', CURDATE(), CURDATE())",
        ),
        (
            "BR09: Tài liệu số OPEN không có giấy phép bị chặn",
            "INSERT INTO digital_resource (digital_id, document_id, access_level, license_id) "
            "VALUES ('DIG99001', 'DOC00001', 'OPEN', NULL)",
        ),
        (
            "BR13: Trùng thứ tự tác giả author_order = 1 bị chặn",
            "INSERT INTO document_author (document_id, author_id, author_order) "
            "VALUES ('DOC00001', 'AUT0001', 1)",
        ),
        (
            "BR08: Tài khoản Open (MEM0002) mở tài liệu PRIVATE (DIG00005) bị chặn",
            "INSERT INTO digital_access (access_id, member_id, digital_id, access_type) "
            "VALUES ('ACCLOG99001', 'MEM0002', 'DIG00005', 'VIEW')",
        ),
        (
            "BR08: Tài khoản Revoked (MEM0008) không được truy cập tài liệu số",
            "INSERT INTO digital_access (access_id, member_id, digital_id, access_type) "
            "VALUES ('ACCLOG99002', 'MEM0008', 'DIG00002', 'VIEW')",
        ),
        (
            "BR11: Thanh toán vượt tiền phạt (FIN0002) bị chặn",
            "INSERT INTO payment (payment_id, fine_id, amount, method) "
            "VALUES ('PAY99001', 'FIN0002', 999999.00, 'Tiền mặt')",
        ),
        (
            "BR16: Thanh toán thiếu tiền phạt (FIN0002) bị chặn",
            "INSERT INTO payment (payment_id, fine_id, amount, method) "
            "VALUES ('PAY99002', 'FIN0002', 1000.00, 'Tiền mặt')",
        ),
        (
            "Trigger ngày sinh ở tương lai bị chặn",
            "INSERT INTO person (person_id, name, birth) "
            "VALUES ('PER99001', 'Test Future', CURDATE() + INTERVAL 5 DAY)",
        ),
    ]

    for label, sql in must_fail_cases:
        try:
            cur.execute(sql)
            conn.rollback()
            fail(label, "KHÔNG bị chặn như kỳ vọng!")
        except mysql.connector.Error as err:
            conn.rollback()
            ok(label, f"Đã chặn đúng ({err.msg})")

    cur.close()
    conn.close()

    print("\n=== 5. KIỂM TRA HTTP ROUTES CỦA FLASK (200 OK & PHÂN QUYỀN NFR-03) ===")
    client = flask_app.test_client()
    for path in ["/", "/document/DOC00001", "/loans", "/fines", "/digital", "/people", "/reports?q=Q1", "/login"]:
        resp = client.get(path)
        if resp.status_code == 200:
            ok(f"GET {path}", "HTTP 200 OK")
        else:
            fail(f"GET {path}", f"HTTP {resp.status_code}")

    # Kiểm tra phân quyền Sinh viên không được phép thêm bản sao
    client.get("/switch_role/Student", follow_redirects=True)
    resp = client.post("/", data={"action": "add_copy", "document_id": "DOC00001", "quantity": "1"}, follow_redirects=True)
    if "Từ chối phân quyền (NFR-03)".encode("utf-8") in resp.data:
        ok("NFR-03: Chặn Sinh viên nhập kho bản sao ở tầng backend")
    else:
        fail("NFR-03: Không thấy thông báo chặn phân quyền Sinh viên")

    print(f"\n====================================================")
    print(f"KẾT QUẢ TỔNG HỢP: {passed} PASS | {failed} FAIL")
    print(f"====================================================")


if __name__ == "__main__":
    run_tests()
