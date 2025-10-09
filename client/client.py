# client.py
import socket
import threading

def receive_messages(sock):
    """Luồng riêng để nhận tin nhắn từ server."""
    while True:
        try:
            data = sock.recv(1024)
            if not data:
                print("❌ Server đóng kết nối.")
                break
            print("\n📩 Server:", data.decode())
        except ConnectionResetError:
            print("⚠️ Mất kết nối với server.")
            break
        except Exception as e:
            print("Lỗi:", e)
            break

def main():
    print("=== TCP Chat Client ===")
    host = input("Nhập IP server (mặc định 127.0.0.1): ") or "127.0.0.1"
    port = int(input("Nhập port server (mặc định 8888): ") or 8888)

    # Kết nối tới server
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((host, port))
        print(f"✅ Đã kết nối tới server {host}:{port}")
    except Exception as e:
        print("❌ Không thể kết nối:", e)
        return

    # Tạo luồng riêng để nhận tin nhắn
    threading.Thread(target=receive_messages, args=(sock,), daemon=True).start()

    # Gửi tin nhắn
    try:
        while True:
            msg = input("Bạn: ")
            if msg.lower() in {"exit", "quit"}:
                print("🔚 Đóng kết nối.")
                sock.close()
                break
            sock.sendall(msg.encode())
    except KeyboardInterrupt:
        print("\n🛑 Dừng client.")
        sock.close()

if __name__ == "__main__":
    main()