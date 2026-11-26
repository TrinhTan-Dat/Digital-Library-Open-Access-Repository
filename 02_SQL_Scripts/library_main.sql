-- =====================================================================
-- ĐỒ ÁN MÔN CƠ SỞ DỮ LIỆU (INT1313) - HỌC KỲ 1, 2026-2027
-- Chủ đề 8: Digital Library & Open-Access Repository
-- Nhóm: Sinh Viên PTIT (Lớp D24CQCN02-N) | GVHD: Lê Hà Thanh
-- Thành viên:
--   1. Trịnh Tấn Đạt     (N24DCCN105)
--   2. Hồ Hoài Sang      (N24DCCN159)
--   3. Nguyễn Quốc Thái  (N24DCCN164)
-- Hệ quản trị: MySQL 8.0+ (InnoDB, utf8mb4_unicode_ci)
-- Chuẩn viết mã: SQLStyle.guide / Google SQL Style Guide
-- ---------------------------------------------------------------------
--  Cấu trúc:
--    PHẦN 1. Tạo database
--    PHẦN 2. Tạo 20 bảng (kèm PK, FK, UNIQUE, CHECK)
--    PHẦN 3. Index hỗ trợ tìm kiếm (NFR-01)
--    PHẦN 4. Trigger cho các quy tắc nghiệp vụ không viết được bằng CHECK
--    PHẦN 5. Stored procedure
--    PHẦN 6. View
--    PHẦN 7. 15 truy vấn phức tạp (JOIN, subquery, aggregation, CTE, window)
--    PHẦN 8. Các câu lệnh kiểm thử ràng buộc (đang để dạng comment)
-- =====================================================================

-- =====================================================================
-- PHẦN 1. TẠO DATABASE
-- =====================================================================
SET NAMES utf8mb4;

CREATE DATABASE IF NOT EXISTS digital_library
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE digital_library;

-- Xóa bảng cũ (nếu chạy lại script). Chỉ ảnh hưởng database digital_library.
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS payment;
DROP TABLE IF EXISTS fine;
DROP TABLE IF EXISTS digital_access;
DROP TABLE IF EXISTS loan;
DROP TABLE IF EXISTS document_author;
DROP TABLE IF EXISTS document_category;
DROP TABLE IF EXISTS digital_resource;
DROP TABLE IF EXISTS physical_copy;
DROP TABLE IF EXISTS document;
DROP TABLE IF EXISTS open_access_license;
DROP TABLE IF EXISTS category;
DROP TABLE IF EXISTS publisher;
DROP TABLE IF EXISTS author;
DROP TABLE IF EXISTS user_account;
DROP TABLE IF EXISTS library_staff;
DROP TABLE IF EXISTS administrator;
DROP TABLE IF EXISTS faculty_researcher;
DROP TABLE IF EXISTS student;
DROP TABLE IF EXISTS university_member;
DROP TABLE IF EXISTS person;
SET FOREIGN_KEY_CHECKS = 1;

DROP VIEW IF EXISTS v_document_catalog;
DROP VIEW IF EXISTS v_overdue_loans;
DROP VIEW IF EXISTS v_member_role;
DROP VIEW IF EXISTS v_member_fine_summary;

DROP PROCEDURE IF EXISTS sp_return_loan;
DROP PROCEDURE IF EXISTS sp_mark_overdue_loans;
DROP EVENT IF EXISTS ev_mark_overdue_loans;

-- =====================================================================
-- PHẦN 2. TẠO BẢNG
-- --------------------------------------------------------------------
-- 2.1 NHÓM CON NGƯỜI & VAI TRÒ
-- ---------------------------------------------------------------------

-- Bảng 1: person
CREATE TABLE person (
    person_id   VARCHAR(10)  NOT NULL,
    name        VARCHAR(100) NOT NULL,
    birth       DATE         NULL,
    email       VARCHAR(100) NULL,
    phone       VARCHAR(20)  NULL,
    address     VARCHAR(255) NULL,
    CONSTRAINT pk_person PRIMARY KEY (person_id),
    CONSTRAINT uq_person_email UNIQUE (email),
    CONSTRAINT uq_person_phone UNIQUE (phone),
    CONSTRAINT ck_person_email CHECK (email IS NULL OR email LIKE '%_@_%._%'),
    CONSTRAINT ck_person_phone CHECK (phone IS NULL OR phone REGEXP '^[0-9]{10}$')
) ENGINE = InnoDB;

-- Bảng 2: university_member
CREATE TABLE university_member (
    member_id   VARCHAR(10) NOT NULL,
    person_id   VARCHAR(10) NOT NULL,
    join_date   DATE        NOT NULL DEFAULT (CURRENT_DATE),
    status      VARCHAR(20) NOT NULL DEFAULT 'Active',
    CONSTRAINT pk_university_member PRIMARY KEY (member_id),
    CONSTRAINT uq_member_person UNIQUE (person_id),
    CONSTRAINT fk_member_person FOREIGN KEY (person_id) REFERENCES person (person_id),
    CONSTRAINT ck_member_status CHECK (status IN ('Active', 'Inactive', 'Suspended', 'Graduated'))
) ENGINE = InnoDB;

-- Bảng 3: student
CREATE TABLE student (
    member_id       VARCHAR(10)  NOT NULL,
    student_code    VARCHAR(20)  NOT NULL,
    major           VARCHAR(100) NULL,
    enrollment_year INT          NOT NULL,
    CONSTRAINT pk_student PRIMARY KEY (member_id),
    CONSTRAINT uq_student_code UNIQUE (student_code),
    CONSTRAINT fk_student_member FOREIGN KEY (member_id)
        REFERENCES university_member (member_id) ON DELETE CASCADE
) ENGINE = InnoDB;

-- Bảng 4: faculty_researcher
CREATE TABLE faculty_researcher (
    member_id      VARCHAR(10)  NOT NULL,
    employee_code  VARCHAR(20)  NOT NULL,
    department     VARCHAR(100) NOT NULL,
    `rank`         VARCHAR(50)  NULL,
    research_field VARCHAR(100) NULL,
    CONSTRAINT pk_faculty_researcher PRIMARY KEY (member_id),
    CONSTRAINT uq_faculty_employee_code UNIQUE (employee_code),
    CONSTRAINT fk_faculty_member FOREIGN KEY (member_id)
        REFERENCES university_member (member_id) ON DELETE CASCADE
) ENGINE = InnoDB;

-- Bảng 6: administrator (tạo trước library_staff vì library_staff tham chiếu admin_code)
CREATE TABLE administrator (
    member_id  VARCHAR(10) NOT NULL,
    admin_code VARCHAR(20) NOT NULL,
    CONSTRAINT pk_administrator PRIMARY KEY (member_id),
    CONSTRAINT uq_administrator_code UNIQUE (admin_code),
    CONSTRAINT fk_administrator_member FOREIGN KEY (member_id)
        REFERENCES university_member (member_id) ON DELETE CASCADE
) ENGINE = InnoDB;

-- Bảng 5: library_staff
CREATE TABLE library_staff (
    member_id     VARCHAR(10)  NOT NULL,
    employee_code VARCHAR(20)  NOT NULL,
    `position`    VARCHAR(100) NOT NULL,
    work_shift    VARCHAR(50)  NULL,
    admin_code    VARCHAR(20)  NOT NULL,
    CONSTRAINT pk_library_staff PRIMARY KEY (member_id),
    CONSTRAINT uq_staff_employee_code UNIQUE (employee_code),
    CONSTRAINT fk_staff_member FOREIGN KEY (member_id)
        REFERENCES university_member (member_id) ON DELETE CASCADE,
    CONSTRAINT fk_staff_admin FOREIGN KEY (admin_code)
        REFERENCES administrator (admin_code)
) ENGINE = InnoDB;

-- Bảng 7: author
CREATE TABLE author (
    author_id   VARCHAR(10)  NOT NULL,
    person_id   VARCHAR(10)  NULL,
    author_name VARCHAR(100) NOT NULL,
    CONSTRAINT pk_author PRIMARY KEY (author_id),
    CONSTRAINT fk_author_person FOREIGN KEY (person_id) REFERENCES person (person_id)
) ENGINE = InnoDB;

-- ---------------------------------------------------------------------
-- 2.2 NHÓM TÀI LIỆU
-- ---------------------------------------------------------------------

-- Bảng 8: publisher
CREATE TABLE publisher (
    publisher_id VARCHAR(10)  NOT NULL,
    pub_name     VARCHAR(150) NOT NULL,
    address      VARCHAR(255) NULL,
    website      VARCHAR(100) NULL,
    CONSTRAINT pk_publisher PRIMARY KEY (publisher_id),
    CONSTRAINT uq_publisher_name UNIQUE (pub_name)
) ENGINE = InnoDB;

-- Bảng 9: category
CREATE TABLE category (
    category_id VARCHAR(10)  NOT NULL,
    cate_name   VARCHAR(100) NOT NULL,
    description VARCHAR(255) NULL,
    CONSTRAINT pk_category PRIMARY KEY (category_id),
    CONSTRAINT uq_category_name UNIQUE (cate_name)
) ENGINE = InnoDB;

-- Bảng 10: open_access_license
CREATE TABLE open_access_license (
    license_id   VARCHAR(10)  NOT NULL,
    license_name VARCHAR(100) NOT NULL,
    description  VARCHAR(255) NULL,
    CONSTRAINT pk_open_access_license PRIMARY KEY (license_id)
) ENGINE = InnoDB;

-- Bảng 11: document
CREATE TABLE document (
    document_id      VARCHAR(10)  NOT NULL,
    title            VARCHAR(200) NOT NULL,
    publication_year INT          NOT NULL,
    ISBN             VARCHAR(20)  NULL,
    description      VARCHAR(500) NULL,
    `language`       VARCHAR(50)  NOT NULL DEFAULT 'Vietnamese',
    `type`           VARCHAR(50)  NOT NULL,
    publisher_id     VARCHAR(10)  NULL,
    employee_code    VARCHAR(20)  NOT NULL,
    CONSTRAINT pk_document PRIMARY KEY (document_id),
    CONSTRAINT uq_document_isbn UNIQUE (ISBN),
    CONSTRAINT fk_document_publisher FOREIGN KEY (publisher_id)
        REFERENCES publisher (publisher_id),
    CONSTRAINT fk_document_staff FOREIGN KEY (employee_code)
        REFERENCES library_staff (employee_code),
    CONSTRAINT ck_document_type CHECK (`type` IN
        ('BOOK', 'JOURNAL', 'THESIS', 'PROJECT', 'RESEARCH_PAPER', 'OTHER')),
    CONSTRAINT ck_document_year CHECK (publication_year > 0)
) ENGINE = InnoDB;

-- Bảng 12: physical_copy
CREATE TABLE physical_copy (
    copy_id       VARCHAR(10)  NOT NULL,
    document_id   VARCHAR(10)  NOT NULL,
    status        VARCHAR(20)  NOT NULL DEFAULT 'Available',
    `condition`   VARCHAR(100) NULL,
    CONSTRAINT pk_physical_copy PRIMARY KEY (copy_id),
    CONSTRAINT fk_copy_document FOREIGN KEY (document_id) REFERENCES document (document_id),
    CONSTRAINT ck_copy_status CHECK (status IN
        ('Available', 'Borrowed', 'Lost', 'Damaged', 'Maintenance'))
) ENGINE = InnoDB;

-- Bảng 13: digital_resource
CREATE TABLE digital_resource (
    digital_id   VARCHAR(10) NOT NULL,
    document_id  VARCHAR(10) NOT NULL,
    file_format  VARCHAR(20) NOT NULL DEFAULT 'PDF',
    `size`       FLOAT       NULL,                         -- đơn vị MB
    upload_date  DATE        NOT NULL DEFAULT (CURRENT_DATE),
    access_level VARCHAR(20) NOT NULL,
    license_id   VARCHAR(10) NULL,
    CONSTRAINT pk_digital_resource PRIMARY KEY (digital_id),
    CONSTRAINT fk_digital_document FOREIGN KEY (document_id) REFERENCES document (document_id),
    CONSTRAINT fk_digital_license FOREIGN KEY (license_id) REFERENCES open_access_license (license_id),
    CONSTRAINT ck_digital_access_level CHECK (access_level IN ('OPEN', 'RESTRICTED', 'PRIVATE')),
    -- BR09: tài liệu OPEN bắt buộc có giấy phép open access
    CONSTRAINT ck_digital_open_license CHECK (access_level <> 'OPEN' OR license_id IS NOT NULL)
) ENGINE = InnoDB;

-- Bảng 14: document_category
CREATE TABLE document_category (
    document_id VARCHAR(10) NOT NULL,
    category_id VARCHAR(10) NOT NULL,
    CONSTRAINT pk_document_category PRIMARY KEY (document_id, category_id),
    CONSTRAINT fk_doccat_document FOREIGN KEY (document_id)
        REFERENCES document (document_id) ON DELETE CASCADE,
    CONSTRAINT fk_doccat_category FOREIGN KEY (category_id)
        REFERENCES category (category_id) ON DELETE CASCADE
) ENGINE = InnoDB;

-- Bảng 15: document_author (BR12, BR13)
CREATE TABLE document_author (
    document_id  VARCHAR(10) NOT NULL,
    author_id    VARCHAR(10) NOT NULL,
    author_order INT         NOT NULL,
    CONSTRAINT pk_document_author PRIMARY KEY (document_id, author_id),
    CONSTRAINT uq_document_author_order UNIQUE (document_id, author_order),
    CONSTRAINT fk_docauth_document FOREIGN KEY (document_id)
        REFERENCES document (document_id) ON DELETE CASCADE,
    CONSTRAINT fk_docauth_author FOREIGN KEY (author_id)
        REFERENCES author (author_id) ON DELETE CASCADE,
    CONSTRAINT ck_docauth_order CHECK (author_order > 0)
) ENGINE = InnoDB;

-- ---------------------------------------------------------------------
-- 2.3 NHÓM HOẠT ĐỘNG & TÀI CHÍNH
-- ---------------------------------------------------------------------

-- Bảng 16: loan
-- active_copy_id: cột sinh tự động, chỉ có giá trị khi phiếu đang hoạt động.
-- UNIQUE trên cột này đảm bảo BR03/BR15 (mỗi bản sao tối đa 1 phiếu mượn đang hoạt động).
CREATE TABLE loan (
    loan_id        VARCHAR(10) NOT NULL,
    member_id      VARCHAR(10) NOT NULL,
    copy_id        VARCHAR(10) NOT NULL,
    staff_id       VARCHAR(10) NOT NULL,
    borrow_date    DATE        NOT NULL DEFAULT (CURRENT_DATE),
    due_date       DATE        NOT NULL,
    return_date    DATE        NULL,
    status         VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    active_copy_id VARCHAR(10) GENERATED ALWAYS AS
        (IF(status IN ('ACTIVE', 'OVERDUE'), copy_id, NULL)) STORED,
    CONSTRAINT pk_loan PRIMARY KEY (loan_id),
    CONSTRAINT uq_loan_active_copy UNIQUE (active_copy_id),
    CONSTRAINT fk_loan_member FOREIGN KEY (member_id) REFERENCES university_member (member_id),
    CONSTRAINT fk_loan_copy FOREIGN KEY (copy_id) REFERENCES physical_copy (copy_id),
    CONSTRAINT fk_loan_staff FOREIGN KEY (staff_id) REFERENCES library_staff (member_id),
    CONSTRAINT ck_loan_status CHECK (status IN ('ACTIVE', 'RETURNED', 'OVERDUE', 'LOST')),
    -- BR05: ngày đến hạn phải sau ngày mượn
    CONSTRAINT ck_loan_due_after_borrow CHECK (due_date > borrow_date),
    -- BR04: ngày trả không được trước ngày mượn
    CONSTRAINT ck_loan_return_after_borrow CHECK (return_date IS NULL OR return_date >= borrow_date),
    -- Đã trả thì phải có ngày trả
    CONSTRAINT ck_loan_returned_has_date CHECK (status <> 'RETURNED' OR return_date IS NOT NULL)
) ENGINE = InnoDB;

-- Bảng 17: digital_access
CREATE TABLE digital_access (
    access_id   VARCHAR(15) NOT NULL,
    member_id   VARCHAR(10) NOT NULL,
    digital_id  VARCHAR(10) NOT NULL,
    access_time DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    access_type VARCHAR(20) NOT NULL,
    CONSTRAINT pk_digital_access PRIMARY KEY (access_id),
    CONSTRAINT fk_access_member FOREIGN KEY (member_id) REFERENCES university_member (member_id),
    CONSTRAINT fk_access_digital FOREIGN KEY (digital_id) REFERENCES digital_resource (digital_id),
    CONSTRAINT ck_access_type CHECK (access_type IN ('VIEW', 'DOWNLOAD'))
) ENGINE = InnoDB;

-- Bảng 18: fine
CREATE TABLE fine (
    fine_id     VARCHAR(10)   NOT NULL,
    loan_id     VARCHAR(10)   NOT NULL,
    amount      DECIMAL(10,2) NOT NULL,
    reason      VARCHAR(255)  NOT NULL,
    issued_date DATE          NOT NULL DEFAULT (CURRENT_DATE),
    status      VARCHAR(20)   NOT NULL DEFAULT 'Unpaid',
    CONSTRAINT pk_fine PRIMARY KEY (fine_id),
    CONSTRAINT uq_fine_loan UNIQUE (loan_id),
    CONSTRAINT fk_fine_loan FOREIGN KEY (loan_id) REFERENCES loan (loan_id),
    CONSTRAINT ck_fine_amount CHECK (amount > 0),
    CONSTRAINT ck_fine_status CHECK (status IN ('Unpaid', 'Paid', 'Waived'))
) ENGINE = InnoDB;

-- Bảng 19: payment (BR11, BR16)
CREATE TABLE payment (
    payment_id   VARCHAR(10)   NOT NULL,
    fine_id      VARCHAR(10)   NOT NULL,
    payment_date DATE          NOT NULL DEFAULT (CURRENT_DATE),
    amount       DECIMAL(10,2) NOT NULL,
    method       VARCHAR(50)   NOT NULL,
    status       VARCHAR(20)   NOT NULL DEFAULT 'COMPLETED',
    CONSTRAINT pk_payment PRIMARY KEY (payment_id),
    CONSTRAINT uq_payment_fine UNIQUE (fine_id),
    CONSTRAINT fk_payment_fine FOREIGN KEY (fine_id) REFERENCES fine (fine_id),
    CONSTRAINT ck_payment_amount CHECK (amount > 0),
    CONSTRAINT ck_payment_status CHECK (status IN ('PENDING', 'COMPLETED'))
) ENGINE = InnoDB;

-- ---------------------------------------------------------------------
-- 2.4 NHÓM TÀI KHOẢN
-- ---------------------------------------------------------------------

-- Bảng 20: user_account
CREATE TABLE user_account (
    account_id       VARCHAR(10)  NOT NULL,
    member_id        VARCHAR(10)  NOT NULL,
    username         VARCHAR(100) NOT NULL,
    password_hash    VARCHAR(255) NOT NULL,
    permission_level VARCHAR(20)  NOT NULL DEFAULT 'Open',
    account_status   VARCHAR(20)  NOT NULL DEFAULT 'Active',
    create_at        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_user_account PRIMARY KEY (account_id),
    CONSTRAINT uq_account_member UNIQUE (member_id),
    CONSTRAINT uq_account_username UNIQUE (username),
    CONSTRAINT fk_account_member FOREIGN KEY (member_id)
        REFERENCES university_member (member_id) ON DELETE CASCADE,
    CONSTRAINT ck_account_permission CHECK (permission_level IN ('Open', 'Restricted', 'Private')),
    CONSTRAINT ck_account_status CHECK (account_status IN ('Active', 'Revoked'))
) ENGINE = InnoDB;

-- =====================================================================
-- PHẦN 3. INDEX HỖ TRỢ TÌM KIẾM (FR-11, NFR-01)
-- =====================================================================
CREATE INDEX idx_document_title  ON document (title);
CREATE INDEX idx_document_year   ON document (publication_year);
CREATE INDEX idx_author_name     ON author (author_name);
CREATE INDEX idx_loan_member_status ON loan (member_id, status);
CREATE INDEX idx_loan_status_due ON loan (status, due_date);
CREATE INDEX idx_access_time     ON digital_access (access_time);
CREATE INDEX idx_copy_doc_status ON physical_copy (document_id, status);
CREATE INDEX idx_digital_doc     ON digital_resource (document_id);

-- =====================================================================
-- PHẦN 4. TRIGGER CHO CÁC QUY TẮC NGHIỆP VỤ
-- Trong Workbench, DELIMITER $$ được dùng để chứa dấu ; bên trong thân trigger.
-- =====================================================================
-- Ghi chú về biến @loading_data:
--   File library_data.sql bật @loading_data = 1 (chỉ trong phiên đang chạy) khi nạp dữ liệu
--   lịch sử, để 5 trigger bên dưới (mượn sách, thanh toán, truy cập tài liệu số) không chặn
--   dữ liệu cũ, ví dụ phiếu đang mượn của thành viên đã bị Suspended hoặc lượt truy cập của
--   tài khoản hiện đã Revoked. Nạp xong file đó đặt lại về 0. Ứng dụng thật không được bật biến này.
DELIMITER $$

-- ---------- Kiểm tra ngày/năm không vượt quá hiện tại ----------
-- (CHECK của MySQL không cho dùng CURDATE()/NOW() nên dùng trigger)

CREATE TRIGGER trg_person_bi BEFORE INSERT ON person
FOR EACH ROW
BEGIN
    IF NEW.birth IS NOT NULL AND NEW.birth > CURDATE() THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'person.birth không được lớn hơn ngày hiện tại';
    END IF;
END$$

CREATE TRIGGER trg_person_bu BEFORE UPDATE ON person
FOR EACH ROW
BEGIN
    IF NEW.birth IS NOT NULL AND NEW.birth > CURDATE() THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'person.birth không được lớn hơn ngày hiện tại';
    END IF;
END$$

CREATE TRIGGER trg_document_bi BEFORE INSERT ON document
FOR EACH ROW
BEGIN
    IF NEW.publication_year > YEAR(CURDATE()) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Năm xuất bản không được lớn hơn năm hiện tại';
    END IF;
END$$

CREATE TRIGGER trg_document_bu BEFORE UPDATE ON document
FOR EACH ROW
BEGIN
    IF NEW.publication_year > YEAR(CURDATE()) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Năm xuất bản không được lớn hơn năm hiện tại';
    END IF;
END$$

CREATE TRIGGER trg_user_account_bi BEFORE INSERT ON user_account
FOR EACH ROW
BEGIN
    IF NEW.create_at > NOW() THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Ngày tạo tài khoản không được sau thời điểm hiện tại';
    END IF;
END$$

CREATE TRIGGER trg_user_account_bu BEFORE UPDATE ON user_account
FOR EACH ROW
BEGIN
    IF NEW.create_at > NOW() THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Ngày tạo tài khoản không được sau thời điểm hiện tại';
    END IF;
END$$

-- ---------- LOAN: BR01, BR02, BR03, BR06, BR07, thành viên Suspended ----------
CREATE TRIGGER trg_loan_bi BEFORE INSERT ON loan
FOR EACH ROW
BEGIN
    DECLARE v_member_status VARCHAR(20);
    DECLARE v_copy_status   VARCHAR(20);
    DECLARE v_overdue       INT DEFAULT 0;
    DECLARE v_active        INT DEFAULT 0;
    DECLARE v_limit         INT DEFAULT 10;

    -- Chỉ kiểm tra khi tạo phiếu mượn mới đang hoạt động
    IF NEW.status = 'ACTIVE' AND IFNULL(@loading_data, 0) = 0 THEN

        -- Thành viên bị Suspended không được mượn
        SELECT MAX(status) INTO v_member_status
        FROM university_member WHERE member_id = NEW.member_id;
        IF v_member_status = 'Suspended' THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'Thành viên đang bị đình chỉ (Suspended), không được mượn tài liệu';
        END IF;

        -- BR06, BR07: chỉ bản sao Available mới được mượn
        SELECT MAX(status) INTO v_copy_status
        FROM physical_copy WHERE copy_id = NEW.copy_id;
        IF v_copy_status IS NOT NULL AND v_copy_status <> 'Available' THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'Bản sao không ở trạng thái Available nên không thể mượn (BR06, BR07)';
        END IF;

        -- BR02: không được mượn khi đang có tài liệu quá hạn
        SELECT COUNT(*) INTO v_overdue
        FROM loan
        WHERE member_id = NEW.member_id
          AND (status = 'OVERDUE' OR (status = 'ACTIVE' AND due_date < CURDATE()));
        IF v_overdue > 0 THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'Thành viên đang có tài liệu quá hạn, không được mượn thêm (BR02)';
        END IF;

        -- BR01: sinh viên tối đa 5, các đối tượng còn lại tối đa 10
        IF EXISTS (SELECT 1 FROM student WHERE member_id = NEW.member_id) THEN
            SET v_limit = 5;
        END IF;

        SELECT COUNT(*) INTO v_active
        FROM loan
        WHERE member_id = NEW.member_id
          AND status IN ('ACTIVE', 'OVERDUE');
        IF v_active >= v_limit THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'Đã đạt giới hạn số tài liệu được mượn cùng lúc (BR01)';
        END IF;
    END IF;
END$$

-- Sau khi tạo phiếu mượn: chuyển bản sao sang Borrowed
CREATE TRIGGER trg_loan_ai AFTER INSERT ON loan
FOR EACH ROW
BEGIN
    IF NEW.status = 'ACTIVE' AND IFNULL(@loading_data, 0) = 0 THEN
        UPDATE physical_copy SET status = 'Borrowed' WHERE copy_id = NEW.copy_id;
    END IF;
END$$

-- Sau khi cập nhật phiếu mượn: trả sách -> bản sao Available và tự tạo tiền phạt (BR10, FR-05, FR-06)
-- Mức phạt: 5.000 VNĐ cho mỗi ngày trễ (có thể chỉnh số này).
CREATE TRIGGER trg_loan_au AFTER UPDATE ON loan
FOR EACH ROW
BEGIN
    DECLARE v_next INT DEFAULT 1;

    IF OLD.status IN ('ACTIVE', 'OVERDUE') AND NEW.status = 'RETURNED' THEN

        UPDATE physical_copy SET status = 'Available'
        WHERE copy_id = NEW.copy_id AND status = 'Borrowed';

        IF NEW.return_date > NEW.due_date
           AND NOT EXISTS (SELECT 1 FROM fine WHERE loan_id = NEW.loan_id) THEN

            -- Mã tiền phạt có dạng FIN0001, FIN0002, ... (theo dữ liệu trong file Excel)
            SELECT IFNULL(MAX(CAST(SUBSTRING(fine_id, 4) AS UNSIGNED)), 0) + 1
            INTO v_next FROM fine;

            INSERT INTO fine (fine_id, loan_id, amount, reason, issued_date, status)
            VALUES (CONCAT('FIN', LPAD(v_next, 4, '0')),
                    NEW.loan_id,
                    DATEDIFF(NEW.return_date, NEW.due_date) * 5000,
                    'Trả tài liệu quá hạn',
                    CURDATE(),
                    'Unpaid');
        END IF;

    ELSEIF OLD.status IN ('ACTIVE', 'OVERDUE') AND NEW.status = 'LOST' THEN
        UPDATE physical_copy SET status = 'Lost' WHERE copy_id = NEW.copy_id;
    END IF;
END$$

-- ---------- PAYMENT: BR11, BR16 ----------
CREATE TRIGGER trg_payment_bi BEFORE INSERT ON payment
FOR EACH ROW
BEGIN
    DECLARE v_fine_amount DECIMAL(10,2);
    DECLARE v_fine_status VARCHAR(20);

    SELECT MAX(amount), MAX(status) INTO v_fine_amount, v_fine_status
    FROM fine WHERE fine_id = NEW.fine_id;

    IF IFNULL(@loading_data, 0) = 0 AND v_fine_status IS NOT NULL AND v_fine_status <> 'Unpaid' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Khoản phạt này không ở trạng thái Unpaid nên không thể thanh toán';
    END IF;

    IF IFNULL(@loading_data, 0) = 0 AND v_fine_amount IS NOT NULL AND NEW.amount > v_fine_amount THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Số tiền thanh toán vượt quá tiền phạt (BR11)';
    END IF;

    IF IFNULL(@loading_data, 0) = 0 AND v_fine_amount IS NOT NULL AND NEW.amount < v_fine_amount THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Tiền phạt phải được thanh toán dứt điểm một lần (BR16)';
    END IF;
END$$

CREATE TRIGGER trg_payment_bu BEFORE UPDATE ON payment
FOR EACH ROW
BEGIN
    DECLARE v_fine_amount DECIMAL(10,2);

    SELECT MAX(amount) INTO v_fine_amount FROM fine WHERE fine_id = NEW.fine_id;

    IF v_fine_amount IS NOT NULL AND NEW.amount <> v_fine_amount THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Số tiền thanh toán phải bằng đúng số tiền phạt (BR11, BR16)';
    END IF;
END$$

-- Thanh toán xong (COMPLETED) thì khoản phạt chuyển sang Paid
CREATE TRIGGER trg_payment_ai AFTER INSERT ON payment
FOR EACH ROW
BEGIN
    IF NEW.status = 'COMPLETED' AND IFNULL(@loading_data, 0) = 0 THEN
        UPDATE fine SET status = 'Paid' WHERE fine_id = NEW.fine_id;
    END IF;
END$$

CREATE TRIGGER trg_payment_au AFTER UPDATE ON payment
FOR EACH ROW
BEGIN
    IF NEW.status = 'COMPLETED' AND OLD.status <> 'COMPLETED' THEN
        UPDATE fine SET status = 'Paid' WHERE fine_id = NEW.fine_id;
    END IF;
END$$

-- ---------- DIGITAL_ACCESS: BR08 (kiểm tra quyền truy cập) ----------
-- Open < Restricted < Private; tài khoản phải Active và đủ cấp để mở tài liệu.
CREATE TRIGGER trg_digital_access_bi BEFORE INSERT ON digital_access
FOR EACH ROW
BEGIN
    DECLARE v_perm INT;
    DECLARE v_need INT;

    SELECT MAX(CASE permission_level
                   WHEN 'Open'       THEN 1
                   WHEN 'Restricted' THEN 2
                   WHEN 'Private'    THEN 3
               END)
    INTO v_perm
    FROM user_account
    WHERE member_id = NEW.member_id AND account_status = 'Active';

    SELECT MAX(CASE access_level
                   WHEN 'OPEN'       THEN 1
                   WHEN 'RESTRICTED' THEN 2
                   WHEN 'PRIVATE'    THEN 3
               END)
    INTO v_need
    FROM digital_resource
    WHERE digital_id = NEW.digital_id;

    IF IFNULL(@loading_data, 0) = 0 AND v_perm IS NULL THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Thành viên không có tài khoản đang hoạt động (BR08)';
    END IF;

    IF IFNULL(@loading_data, 0) = 0 AND v_need IS NOT NULL AND v_perm < v_need THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Cấp quyền của tài khoản không đủ để truy cập tài liệu số này (BR08)';
    END IF;
END$$

DELIMITER ;

-- =====================================================================
-- PHẦN 5. STORED PROCEDURE
-- =====================================================================
DELIMITER $$

-- Trả tài liệu: cập nhật status và return_date trong cùng một câu UPDATE
-- (để thỏa CHECK ck_loan_returned_has_date). Trigger sẽ tự cập nhật bản sao
-- và tạo tiền phạt nếu trả trễ.
-- Dùng: CALL sp_return_loan('LOA00002', NULL);   -- NULL = lấy ngày hôm nay
CREATE PROCEDURE sp_return_loan(IN p_loan_id VARCHAR(10), IN p_return_date DATE)
BEGIN
    UPDATE loan
    SET status = 'RETURNED',
        return_date = COALESCE(p_return_date, CURDATE())
    WHERE loan_id = p_loan_id
      AND status IN ('ACTIVE', 'OVERDUE');

    IF ROW_COUNT() = 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Không tìm thấy phiếu mượn đang hoạt động với mã này';
    END IF;
END$$

-- Đánh dấu OVERDUE cho các phiếu ACTIVE đã quá hạn
CREATE PROCEDURE sp_mark_overdue_loans()
BEGIN
    UPDATE loan
    SET status = 'OVERDUE'
    WHERE status = 'ACTIVE' AND due_date < CURDATE();
END$$

DELIMITER ;

-- (Tùy chọn) Chạy tự động mỗi ngày. Cần bật event scheduler:
--   SET GLOBAL event_scheduler = ON;
-- CREATE EVENT ev_mark_overdue_loans
--     ON SCHEDULE EVERY 1 DAY
--     STARTS (CURRENT_DATE + INTERVAL 1 DAY)
--     DO CALL sp_mark_overdue_loans();

-- =====================================================================
-- PHẦN 6. VIEW (Phase 3 - Triggers/Views)
-- =====================================================================

-- 6.1 Danh mục tài liệu: tác giả, thể loại, số bản sao, số bản sao còn sẵn
CREATE OR REPLACE VIEW v_document_catalog AS
SELECT d.document_id,
       d.title,
       d.publication_year,
       d.`type`,
       d.ISBN,
       p.pub_name,
       (SELECT GROUP_CONCAT(a.author_name ORDER BY da.author_order SEPARATOR ', ')
          FROM document_author da
          JOIN author a ON a.author_id = da.author_id
         WHERE da.document_id = d.document_id) AS authors,
       (SELECT GROUP_CONCAT(c.cate_name ORDER BY c.cate_name SEPARATOR ', ')
          FROM document_category dc
          JOIN category c ON c.category_id = dc.category_id
         WHERE dc.document_id = d.document_id) AS categories,
       (SELECT COUNT(*) FROM physical_copy pc
         WHERE pc.document_id = d.document_id) AS total_copies,
       (SELECT COUNT(*) FROM physical_copy pc
         WHERE pc.document_id = d.document_id AND pc.status = 'Available') AS available_copies,
       (SELECT COUNT(*) FROM digital_resource dr
         WHERE dr.document_id = d.document_id) AS digital_versions
FROM document d
    LEFT JOIN publisher p ON p.publisher_id = d.publisher_id;

-- 6.2 Phiếu mượn quá hạn kèm số ngày trễ
CREATE OR REPLACE VIEW v_overdue_loans AS
SELECT l.loan_id,
       l.member_id,
       pe.name AS member_name,
       d.title,
       l.copy_id,
       l.borrow_date,
       l.due_date,
       DATEDIFF(CURDATE(), l.due_date) AS days_overdue
FROM loan l
    JOIN university_member m ON m.member_id = l.member_id
    JOIN person pe           ON pe.person_id = m.person_id
    JOIN physical_copy pc    ON pc.copy_id = l.copy_id
    JOIN document d          ON d.document_id = pc.document_id
WHERE l.status = 'OVERDUE'
   OR (l.status = 'ACTIVE' AND l.due_date < CURDATE());

-- 6.3 Vai trò của từng thành viên
CREATE OR REPLACE VIEW v_member_role AS
SELECT m.member_id,
       pe.name,
       m.status,
       CASE
           WHEN EXISTS (SELECT 1 FROM administrator a      WHERE a.member_id = m.member_id) THEN 'Administrator'
           WHEN EXISTS (SELECT 1 FROM library_staff s      WHERE s.member_id = m.member_id) THEN 'Library staff'
           WHEN EXISTS (SELECT 1 FROM faculty_researcher f WHERE f.member_id = m.member_id) THEN 'Faculty'
           WHEN EXISTS (SELECT 1 FROM student st           WHERE st.member_id = m.member_id) THEN 'Student'
           ELSE 'Member'
       END AS member_role
FROM university_member m
    JOIN person pe ON pe.person_id = m.person_id;

-- 6.4 Tổng hợp tiền phạt theo thành viên
CREATE OR REPLACE VIEW v_member_fine_summary AS
SELECT m.member_id,
       pe.name,
       COUNT(f.fine_id) AS fine_count,
       COALESCE(SUM(CASE WHEN f.status = 'Unpaid' THEN f.amount END), 0) AS unpaid_amount,
       COALESCE(SUM(CASE WHEN f.status = 'Paid'   THEN f.amount END), 0) AS paid_amount,
       COALESCE(SUM(CASE WHEN f.status = 'Waived' THEN f.amount END), 0) AS waived_amount
FROM university_member m
    JOIN person pe      ON pe.person_id = m.person_id
    LEFT JOIN loan l    ON l.member_id = m.member_id
    LEFT JOIN fine f    ON f.loan_id = l.loan_id
GROUP BY m.member_id, pe.name;

-- =====================================================================
-- PHẦN 7. 15 TRUY VẤN PHỨC TẠP (Phase 3 - complex queries)
-- Mỗi truy vấn ghi rõ kỹ thuật sử dụng. Chạy từng câu bằng cách bôi đen
-- câu cần chạy rồi bấm tia sét có con trỏ (Execute Current Statement).
-- =====================================================================

-- Q1. [JOIN 8 bảng] Phiếu mượn đang hoạt động: người mượn, tài liệu, thủ thư xử lý
SELECT l.loan_id,
       pe.name  AS borrower,
       d.title,
       l.borrow_date,
       l.due_date,
       l.status,
       ps.name  AS processed_by
FROM loan l
    JOIN university_member m  ON m.member_id  = l.member_id
    JOIN person pe            ON pe.person_id = m.person_id
    JOIN physical_copy pc     ON pc.copy_id   = l.copy_id
    JOIN document d           ON d.document_id = pc.document_id
    JOIN library_staff s      ON s.member_id  = l.staff_id
    JOIN university_member ms ON ms.member_id = s.member_id
    JOIN person ps            ON ps.person_id = ms.person_id
WHERE l.status IN ('ACTIVE', 'OVERDUE')
ORDER BY l.due_date;

-- Q2. [Aggregation + GROUP BY + LIMIT] Top 5 tài liệu được mượn nhiều nhất
SELECT d.document_id,
       d.title,
       COUNT(l.loan_id) AS loan_count
FROM document d
    JOIN physical_copy pc ON pc.document_id = d.document_id
    JOIN loan l           ON l.copy_id = pc.copy_id
GROUP BY d.document_id, d.title
ORDER BY loan_count DESC, d.title
LIMIT 5;

-- Q3. [Subquery NOT EXISTS] Tài liệu chưa từng được mượn lần nào
SELECT d.document_id, d.title, d.`type`
FROM document d
WHERE NOT EXISTS (
    SELECT 1
    FROM physical_copy pc
    JOIN loan l ON l.copy_id = pc.copy_id
    WHERE pc.document_id = d.document_id
);

-- Q4. [Subquery vô hướng + HAVING] Thành viên mượn nhiều hơn mức trung bình
SELECT m.member_id,
       pe.name,
       COUNT(l.loan_id) AS total_loans
FROM loan l
    JOIN university_member m ON m.member_id = l.member_id
    JOIN person pe           ON pe.person_id = m.person_id
GROUP BY m.member_id, pe.name
HAVING COUNT(l.loan_id) > (SELECT COUNT(*) / COUNT(DISTINCT member_id) FROM loan)
ORDER BY total_loans DESC, pe.name;

-- Q5. [Aggregation nhiều hàm] Thống kê tiền phạt theo trạng thái
SELECT f.status,
       COUNT(*)              AS fine_count,
       SUM(f.amount)         AS total_amount,
       ROUND(AVG(f.amount))  AS avg_amount,
       MAX(f.amount)         AS max_amount
FROM fine f
GROUP BY f.status
ORDER BY total_amount DESC;

-- Q6. [JOIN + HAVING] Thành viên đang nợ tiền phạt (Unpaid)
SELECT m.member_id,
       pe.name,
       COUNT(f.fine_id) AS unpaid_count,
       SUM(f.amount)    AS unpaid_total
FROM fine f
    JOIN loan l              ON l.loan_id = f.loan_id
    JOIN university_member m ON m.member_id = l.member_id
    JOIN person pe           ON pe.person_id = m.person_id
WHERE f.status = 'Unpaid'
GROUP BY m.member_id, pe.name
HAVING SUM(f.amount) > 0
ORDER BY unpaid_total DESC;

-- Q7. [Aggregation có điều kiện] Lượt xem/tải theo mức truy cập của tài liệu số
SELECT dr.access_level,
       COUNT(da.access_id)                 AS total_access,
       SUM(da.access_type = 'VIEW')        AS views,
       SUM(da.access_type = 'DOWNLOAD')    AS downloads,
       COUNT(DISTINCT da.member_id)        AS distinct_users
FROM digital_resource dr
    LEFT JOIN digital_access da ON da.digital_id = dr.digital_id
GROUP BY dr.access_level
ORDER BY total_access DESC;

-- Q8. [JOIN + GROUP_CONCAT + HAVING] Tác giả có từ 2 tài liệu trở lên
SELECT a.author_id,
       a.author_name,
       COUNT(da.document_id) AS doc_count,
       GROUP_CONCAT(d.title ORDER BY d.publication_year SEPARATOR '; ') AS titles
FROM author a
    JOIN document_author da ON da.author_id = a.author_id
    JOIN document d         ON d.document_id = da.document_id
GROUP BY a.author_id, a.author_name
HAVING COUNT(da.document_id) >= 2
ORDER BY doc_count DESC, a.author_name;

-- Q9. [LEFT JOIN + COUNT DISTINCT] Số tài liệu và số bản sao theo thể loại
SELECT c.cate_name,
       COUNT(DISTINCT dc.document_id) AS document_count,
       COUNT(DISTINCT pc.copy_id)     AS copy_count
FROM category c
    LEFT JOIN document_category dc ON dc.category_id = c.category_id
    LEFT JOIN physical_copy pc     ON pc.document_id = dc.document_id
GROUP BY c.category_id, c.cate_name
ORDER BY document_count DESC, c.cate_name;

-- Q10. [Window function RANK] Xếp hạng thành viên theo số lượt truy cập tài liệu số trong từng vai trò
SELECT r.member_role,
       r.name,
       COUNT(da.access_id) AS access_count,
       RANK() OVER (PARTITION BY r.member_role ORDER BY COUNT(da.access_id) DESC) AS rank_in_role
FROM v_member_role r
    LEFT JOIN digital_access da ON da.member_id = r.member_id
GROUP BY r.member_role, r.member_id, r.name
ORDER BY r.member_role, rank_in_role, r.name;

-- Q11. [Aggregation theo tháng] Tỷ lệ trả trễ theo tháng
SELECT DATE_FORMAT(l.return_date, '%Y-%m')               AS return_month,
       COUNT(*)                                          AS returned_loans,
       SUM(l.return_date > l.due_date)                   AS late_loans,
       ROUND(100 * SUM(l.return_date > l.due_date) / COUNT(*), 1) AS late_percent
FROM loan l
WHERE l.status = 'RETURNED'
GROUP BY DATE_FORMAT(l.return_date, '%Y-%m')
ORDER BY return_month;

-- Q12. [Subquery trong FROM + CASE + EXISTS] Số suất mượn còn lại của từng thành viên (BR01)
SELECT t.member_id,
       t.name,
       t.max_loans,
       t.current_loans,
       t.max_loans - t.current_loans AS remaining
FROM (
    SELECT m.member_id,
           pe.name,
           CASE WHEN EXISTS (SELECT 1 FROM student s WHERE s.member_id = m.member_id)
                THEN 5 ELSE 10 END AS max_loans,
           (SELECT COUNT(*) FROM loan l
             WHERE l.member_id = m.member_id
               AND l.status IN ('ACTIVE', 'OVERDUE')) AS current_loans
    FROM university_member m
    JOIN person pe ON pe.person_id = m.person_id
) t
ORDER BY remaining, t.name;

-- Q13. [Subquery tương quan EXISTS / NOT EXISTS] Tài liệu có bản sao nhưng không còn bản nào sẵn sàng cho mượn
SELECT d.document_id,
       d.title,
       (SELECT COUNT(*) FROM physical_copy pc WHERE pc.document_id = d.document_id) AS total_copies
FROM document d
WHERE EXISTS (SELECT 1 FROM physical_copy pc WHERE pc.document_id = d.document_id)
  AND NOT EXISTS (SELECT 1 FROM physical_copy pc
                   WHERE pc.document_id = d.document_id AND pc.status = 'Available');

-- Q14. [CTE WITH] Top 5 thành viên có tổng tiền phạt cao nhất
WITH member_fines AS (
    SELECT l.member_id,
           COUNT(*)      AS fine_count,
           SUM(f.amount) AS total_fine
    FROM fine f
    JOIN loan l ON l.loan_id = f.loan_id
    GROUP BY l.member_id
)
SELECT pe.name,
       mf.fine_count,
       mf.total_fine
FROM member_fines mf
    JOIN university_member m ON m.member_id = mf.member_id
    JOIN person pe           ON pe.person_id = m.person_id
ORDER BY mf.total_fine DESC, pe.name
LIMIT 5;

-- Q15. [UNION ALL] Toàn bộ hoạt động (mượn sách + truy cập tài liệu số) của thành viên MEM0084
SELECT 'Mượn sách' AS activity,
       l.borrow_date AS activity_date,
       d.title
FROM loan l
    JOIN physical_copy pc ON pc.copy_id = l.copy_id
    JOIN document d       ON d.document_id = pc.document_id
WHERE l.member_id = 'MEM0084'
UNION ALL
SELECT CONCAT('Truy cập số - ', da.access_type) AS activity,
       DATE(da.access_time) AS activity_date,
       d.title
FROM digital_access da
    JOIN digital_resource dr ON dr.digital_id = da.digital_id
    JOIN document d          ON d.document_id = dr.document_id
WHERE da.member_id = 'MEM0084'
ORDER BY activity_date;

-- Truy vấn đơn giản trên các view (để minh họa View)
-- SELECT * FROM v_document_catalog;
-- SELECT * FROM v_overdue_loans;
-- SELECT * FROM v_member_fine_summary WHERE unpaid_amount > 0;

-- =====================================================================
-- PHẦN 8. CÂU LỆNH KIỂM THỬ RÀNG BUỘC
-- Bỏ dấu -- ở từng câu để thử (bôi đen rồi nhấn Ctrl+/ để bỏ comment),
-- sau đó chạy riêng câu đó bằng Ctrl+Enter. Các câu "PHẢI LỖI" dùng để chứng
-- minh ràng buộc nghiệp vụ hoạt động: dòng đỏ trong ô Output là kết quả ĐÚNG.
-- Các mã bên dưới (thành viên, bản sao, tiền phạt...) là mã thật trong file Excel.
-- =====================================================================

-- 8.1 Xem dữ liệu
-- SELECT status, COUNT(*) FROM loan GROUP BY status;                 -- ACTIVE 270, OVERDUE 130, RETURNED 1050, LOST 50
-- SELECT status, COUNT(*) FROM physical_copy GROUP BY status;        -- Available 2374, Borrowed 400, Lost 50
-- SELECT * FROM v_overdue_loans ORDER BY days_overdue DESC;

-- 8.2 Tìm kiếm tài liệu theo tiêu đề / tác giả / thể loại (FR-11)
-- SELECT d.document_id, d.title, d.publication_year,
--        GROUP_CONCAT(a.author_name ORDER BY da.author_order SEPARATOR ', ') AS authors
-- FROM document d
-- JOIN document_author da ON da.document_id = d.document_id
-- JOIN author a ON a.author_id = da.author_id
-- WHERE d.title LIKE '%dữ liệu%'
-- GROUP BY d.document_id, d.title, d.publication_year
-- LIMIT 20;

-- 8.3 Các câu PHẢI LỖI
-- BR02: MEM0006 (Active) đang có phiếu OVERDUE nên không được mượn thêm
-- INSERT INTO loan (loan_id, member_id, copy_id, staff_id, due_date)
-- VALUES ('LOA90001', 'MEM0006', 'COP00001', 'MEM0362', CURDATE() + INTERVAL 14 DAY);

-- Thành viên Suspended (MEM0069) không được mượn
-- INSERT INTO loan (loan_id, member_id, copy_id, staff_id, due_date)
-- VALUES ('LOA90002', 'MEM0069', 'COP00001', 'MEM0362', CURDATE() + INTERVAL 14 DAY);

-- BR06/BR07: COP00030 đang ở trạng thái Lost nên không thể mượn
-- INSERT INTO loan (loan_id, member_id, copy_id, staff_id, due_date)
-- VALUES ('LOA90003', 'MEM0004', 'COP00030', 'MEM0362', CURDATE() + INTERVAL 14 DAY);

-- BR03/BR15: COP00002 đang được người khác mượn (Borrowed)
-- INSERT INTO loan (loan_id, member_id, copy_id, staff_id, due_date)
-- VALUES ('LOA90004', 'MEM0004', 'COP00002', 'MEM0362', CURDATE() + INTERVAL 14 DAY);

-- BR05: ngày đến hạn không sau ngày mượn (lỗi 3819 - CHECK)
-- INSERT INTO loan (loan_id, member_id, copy_id, staff_id, borrow_date, due_date)
-- VALUES ('LOA90005', 'MEM0004', 'COP00001', 'MEM0362', CURDATE(), CURDATE());

-- BR09: tài liệu số OPEN nhưng không có giấy phép (lỗi 3819 - CHECK)
-- INSERT INTO digital_resource (digital_id, document_id, access_level, license_id)
-- VALUES ('DIG90001', 'DOC00001', 'OPEN', NULL);

-- BR13: trùng thứ tự tác giả 1 trong cùng tài liệu DOC00001 (lỗi 1062 - UNIQUE)
-- INSERT INTO document_author (document_id, author_id, author_order)
-- VALUES ('DOC00001', 'AUT0001', 1);

-- BR08: MEM0002 (quyền Open) truy cập tài liệu PRIVATE DIG00005
-- INSERT INTO digital_access (access_id, member_id, digital_id, access_type)
-- VALUES ('ACCLOG90001', 'MEM0002', 'DIG00005', 'VIEW');

-- BR08: MEM0008 có tài khoản đã bị Revoked nên không được truy cập
-- INSERT INTO digital_access (access_id, member_id, digital_id, access_type)
-- VALUES ('ACCLOG90002', 'MEM0008', 'DIG00002', 'VIEW');

-- BR11: thanh toán vượt tiền phạt (FIN0002 đang Unpaid, tiền phạt 61.402,70)
-- INSERT INTO payment (payment_id, fine_id, amount, method)
-- VALUES ('PAY90001', 'FIN0002', 71402.70, 'Tiền mặt');

-- BR16: phải thanh toán dứt điểm một lần, không được trả thiếu
-- INSERT INTO payment (payment_id, fine_id, amount, method)
-- VALUES ('PAY90002', 'FIN0002', 30701.35, 'Tiền mặt');

-- BR16: FIN0001 đã Paid, không thanh toán lần hai được
-- INSERT INTO payment (payment_id, fine_id, amount, method)
-- VALUES ('PAY90003', 'FIN0001', 57018.65, 'Tiền mặt');

-- Ngày sinh ở tương lai
-- INSERT INTO person (person_id, name, birth)
-- VALUES ('PER90001', 'Test', CURDATE() + INTERVAL 1 DAY);

-- 8.4 BR01: giới hạn mượn của sinh viên (tối đa 5 phiếu đang hoạt động)
-- MEM0084 là sinh viên đang có 4 phiếu. Câu 1 THÀNH CÔNG (phiếu thứ 5, làm thay đổi dữ liệu),
-- câu 2 PHẢI LỖI (phiếu thứ 6). Chạy xong có thể chạy lại lần lượt library_main.sql rồi library_data.sql để khôi phục dữ liệu.
-- INSERT INTO loan (loan_id, member_id, copy_id, staff_id, due_date)
-- VALUES ('LOA90006', 'MEM0084', 'COP00004', 'MEM0362', CURDATE() + INTERVAL 14 DAY);
-- INSERT INTO loan (loan_id, member_id, copy_id, staff_id, due_date)
-- VALUES ('LOA90007', 'MEM0084', 'COP00005', 'MEM0362', CURDATE() + INTERVAL 14 DAY);

-- 8.5 Kiểm thử BR04 (ngày trả < ngày mượn) và BR10 (trả trễ -> trigger tự tạo tiền phạt)
-- Phiếu LOA00023 đang ACTIVE (mượn 2026-11-16, hạn 2026-11-30), chưa có biên lai phạt.
-- Câu 1 (BR04 - PHẢI LỖI 3819): trả trước ngày mượn:
-- CALL sp_return_loan('LOA00023', '2026-11-01');
-- Câu 2 (BR10 - THÀNH CÔNG, làm thay đổi dữ liệu): giả lập trả trễ 5 ngày vào '2026-12-05'
-- -> Trigger trg_loan_au tự đổi bản sao về Available và tự sinh biên lai phạt FIN0363 (25.000 VNĐ):
-- CALL sp_return_loan('LOA00023', '2026-12-05');
-- SELECT * FROM fine WHERE loan_id = 'LOA00023';
