# Hệ thống quản lý thư viện số và kho truy cập mở PTIT

**Digital Library \& Open-Access Repository — Chủ đề 8**

\[!\[Môn học](https://img.shields.io/badge/M%C3%B4n%20h%E1%BB%8Dc-INT1313-blue)]()
\[!\[Database](https://img.shields.io/badge/Database-MySQL%208.0%2B-orange)]()
\[!\[Backend](https://img.shields.io/badge/Backend-Python%20Flask-black)]()

## 1\. Thông tin dự án

|Thuộc tính|Nội dung|
|-|-|
|Tên đề tài|Hệ thống quản lý thư viện số và quyền truy cập tài liệu số cho các trường đại học|
|Chủ đề|Chủ đề 8: Digital Library \& Open-Access Repository|
|Môn học|Cơ sở dữ liệu (INT1313)|
|Học kỳ / năm học|Học kỳ 1 — 2026–2027|
|Nhóm thực hiện|Sinh Viên PTIT|
|Lớp|D24CQCN02-N|
|Giảng viên hướng dẫn|Lê Hà Thanh|
|Hệ quản trị CSDL|MySQL 8.0+|
|Ứng dụng|Python Flask, MySQL Connector/Python, HTML/Jinja2|
|Repository|https://github.com/TrinhTan-Dat/Digital-Library-Open-Access-Repository|

## 2\. Thành viên nhóm

Thông tin thành viên được ghi theo hồ sơ sinh viên PTIT HCM:

|STT|Họ và tên|Mã sinh viên|Email sinh viên|
|-:|-|-|-|
|1|Trịnh Tấn Đạt|N24DCCN105|n24dccn105@student.ptithcm.edu.vn|
|2|Hồ Hoài Sang|N24DCCN159|n24dccn159@student.ptithcm.edu.vn|
|3|Nguyễn Quốc Thái|N24DCCN164|n24dccn164@student.ptithcm.edu.vn|

**Lớp:** D24CQCN02-N

## 3\. Giới thiệu

Dự án xây dựng hệ thống quản lý tập trung tài liệu vật lý và tài liệu số trong môi trường đại học. Hệ thống hỗ trợ quản lý hồ sơ thành viên, danh mục tài liệu, bản sao vật lý, tác giả, nhà xuất bản, mượn/trả, tiền phạt, thanh toán và quyền truy cập tài nguyên số.

Đồ án triển khai theo 4 giai đoạn trong 12 tuần, bao gồm phân tích yêu cầu, thiết kế EER và lược đồ quan hệ, chuẩn hóa dữ liệu, cài đặt cơ sở dữ liệu, xây dựng truy vấn SQL, tích hợp ứng dụng web và kiểm thử.

## 4\. Chức năng chính

* Quản lý tài liệu, thông tin xuất bản và danh mục thể loại.
* Quản lý bản sao vật lý và trạng thái bản sao.
* Quản lý nhiều tác giả cho một tài liệu và thứ tự tác giả.
* Quản lý hồ sơ thành viên và các vai trò: sinh viên, giảng viên/nhà nghiên cứu, nhân viên thư viện, quản trị viên.
* Lập phiếu mượn, trả tài liệu, xử lý quá hạn và báo mất.
* Tính tiền phạt, quản lý biên lai và ghi nhận thanh toán.
* Quản lý tài nguyên số, giấy phép truy cập mở và mức truy cập Open/Restricted/Private.
* Ghi nhật ký lượt xem/tải tài liệu số.
* Tra cứu tài liệu theo nhiều tiêu chí.
* Cung cấp trang chạy 15 truy vấn SQL phục vụ báo cáo và vấn đáp.

## 5\. Công nghệ và tiêu chuẩn

* **Database:** MySQL 8.0+ (InnoDB, `utf8mb4\_unicode\_ci`).
* **Backend:** Python 3.10+ và Flask.
* **Kết nối CSDL:** `mysql-connector-python`.
* **Frontend:** HTML, Jinja2 templates.
* **Công cụ:** MySQL Workbench, Git, GitHub.
* **Mô hình hóa:** EER (Elmasri), lược đồ IE Crow’s Foot.
* **Tài liệu:** SRS theo ISO/IEC/IEEE 29148; từ điển dữ liệu theo ISO/IEC 11179.
* **SQL style:** SQLStyle.guide / Google SQL Style Guide.

## 6\. Yêu cầu môi trường

Trước khi cài đặt, cần có:

* MySQL Server 8.0 trở lên đang chạy.
* Python 3.10 trở lên.
* MySQL Workbench (khuyến nghị) hoặc MySQL CLI.
* Git (nếu clone repository).

## 7\. Cài đặt cơ sở dữ liệu

### Bước 1: Tạo schema và các đối tượng SQL

Mở MySQL Workbench, kết nối đến MySQL Server và chạy toàn bộ file:
02\_SQL\_Scripts/library\_main.sql

File này tạo database `digital\_library`, các bảng, ràng buộc, chỉ mục, triggers, stored procedures, views và các truy vấn.

### Bước 2: Nạp dữ liệu mẫu

Sau khi chạy thành công `library\_main.sql`, chạy tiếp:
02\_SQL\_Scripts/library\_data.sql

Kiểm tra database `digital\_library` và các bảng đã có dữ liệu.

## 8\. Cấu hình và chạy ứng dụng web

### Bước 1: Cấu hình kết nối MySQL

Mở file `03\_Web\_Application/app.py`, tìm biến `DB\_CONFIG` và cập nhật thông tin kết nối MySQL trên máy:

```python
DB\_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "YOUR\_MYSQL\_PASSWORD",
    "database": "digital\_library",
    "charset": "utf8mb4",
}
```

Thay `YOUR\_MYSQL\_PASSWORD` bằng mật khẩu MySQL của bạn. Không đưa mật khẩu thật hoặc thông tin bí mật vào repository công khai.

### Bước 2: Cài đặt thư viện Python

Mở Terminal/PowerShell tại thư mục `03\_Web\_Application` và chạy:

```bash
python -m pip install -r requirements.txt
```

### Bước 3: Khởi chạy ứng dụng

```bash
python app.py
```

Mở trình duyệt tại:

[http://127.0.0.1:5000](http://127.0.0.1:5000)

Ứng dụng yêu cầu kết nối đến MySQL và database `digital\_library` đã được tạo, nạp dữ liệu.

## 9\. Kiểm thử

Tại thư mục `03\_Web\_Application`, chạy:

```bash
python test\_live\_db.py
```

Bộ kiểm thử được xây dựng cho kiểm thử tích hợp với MySQL thật, gồm **39 test cases**. Kết quả dự kiến theo báo cáo dự án là **39 PASS | 0 FAIL**.

