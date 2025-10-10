# Server kiểu blocking (trước tối ưu)
import socket

HOST = "127.0.0.1"   # Địa chỉ localhost
PORT = 8888          # Cổng server lắng nghe

#Xử lý gửi/nhận dữ liệu từ một client duy nhất
def handle_client(conn, addr):
    print(f"[+] Client kết nối từ {addr}")
    try:
        while True:
            data = conn.recv(1024).decode("utf-8") #server đợi dữ liệu từ client
            if not data:
                print(f"[-] Client {addr} đã ngắt kết nối")
                break
            print(f"[{addr}] Gửi: {data}")
            reply = f"Server nhận: {data}"
            conn.sendall(reply.encode("utf-8")) #gửi phản hồi lại client
    except ConnectionResetError:
        print(f"[!] Mất kết nối với {addr}")
    finally:
        conn.close()

def start_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f"Server Blocking đang chạy tại {HOST}: {PORT}")
        print("Đang chờ client kết nối...\n")

        while True:
            conn, addr = s.accept()  # CHẶN: chỉ xử lý 1 client tại 1 thời điểm
            handle_client(conn, addr)

if __name__ == "__main__":
    start_server()
