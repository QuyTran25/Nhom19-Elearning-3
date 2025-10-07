# test_scenarios/load_test.py
"""
Load Test cho Chat Server Async
===============================

Tạo nhiều client đồng thời (ví dụ 50 client) để kiểm tra khả năng xử lý của server.
Kịch bản:
- Mỗi client kết nối tới server async (localhost:8888)
- Gửi một tin nhắn "Hello from Client X"
- Nhận phản hồi từ server
- Ghi nhận thời gian phản hồi trung bình

Cách chạy:
    python test_scenarios/load_test.py --clients 50 --host localhost --port 8888
"""

import asyncio
import time
import argparse
import json
import statistics

async def run_client(id, host, port, message, results):
    try:
        reader, writer = await asyncio.open_connection(host, port)
        start = time.perf_counter()

        # Gửi tin nhắn dạng JSON (tương thích server nhóm bạn)
        payload = json.dumps({"client_id": id, "message": message}) + "\n"
        writer.write(payload.encode())
        await writer.drain()

        # Nhận phản hồi đầu tiên
        data = await reader.readline()
        end = time.perf_counter()

        latency = end - start
        results.append(latency)
        print(f"[Client {id:02d}] Response after {latency:.4f}s: {data.decode().strip()}")

        writer.close()
        await writer.wait_closed()
    except Exception as e:
        print(f"[Client {id:02d}] Error: {e}")

async def main(num_clients, host, port):
    results = []
    tasks = []
    message = "Xin chào từ client!"

    start_time = time.perf_counter()
    for i in range(1, num_clients + 1):
        tasks.append(run_client(i, host, port, message, results))

    await asyncio.gather(*tasks)
    total_time = time.perf_counter() - start_time

    if results:
        avg = statistics.mean(results)
        print("\n===== KẾT QUẢ TỔNG HỢP =====")
        print(f"Số client: {num_clients}")
        print(f"Thời gian trung bình phản hồi: {avg:.4f}s")
        print(f"Tổng thời gian kiểm thử: {total_time:.2f}s")
        print("=============================")
    else:
        print("Không nhận được phản hồi nào từ server.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Async Chat Server Load Test")
    parser.add_argument("--clients", type=int, default=50, help="Số lượng client đồng thời")
    parser.add_argument("--host", type=str, default="localhost", help="Địa chỉ server")
    parser.add_argument("--port", type=int, default=8888, help="Cổng server")

    args = parser.parse_args()
    asyncio.run(main(args.clients, args.host, args.port))
