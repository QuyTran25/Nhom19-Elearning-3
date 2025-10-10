# Hướng dẫn Phân tích Hiệu suất Server
## Nhóm 19 - E-Learning 3

## Cách chạy ĐÚNG:

mở 3 terminal mới 
1. dán : python analysis\compare_performance.py
2. dán : python server\server_blocking.py
3. dán : python server\server_async.py
cụ thể : đợi server chạy ổn định như mô tả ở dưới

1. Chạy script phân tích trong Terminal 1
2. Khi được yêu cầu, khởi động BLOCKING SERVER trong Terminal 2:
   → python server\\server_blocking.py
   → Đợi thông báo "Server Blocking đang chạy..."
   → Quay lại Terminal 1 nhấn Enter

3. Script sẽ test blocking server với các kịch bản
4. Sau khi xong, dừng blocking server (Ctrl+C trong Terminal 2)

5. Khi được yêu cầu, khởi động ASYNC SERVER trong Terminal 3:
   → python server\\server_async.py  
   → Đợi server chạy ổn định
   → Quay lại Terminal 1 nhấn Enter

6. Script sẽ test async server và tạo báo cáo