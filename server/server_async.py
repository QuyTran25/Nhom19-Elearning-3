"""
Chat Server Bất Đồng Bộ sử dụng asyncio
========================================

Server này được tối ưu hóa bằng cách sử dụng asyncio để xử lý nhiều client đồng thời
mà không cần sử dụng đa luồng. Điều này giúp:
- Giảm độ trễ phản hồi
- Tận dụng CPU hiệu quả hơn
- Xử lý hàng nghìn kết nối đồng thời
- Quản lý tài nguyên tốt hơn

Tác giả: Nhóm 19 - E-Learning 3
"""

import asyncio
import logging
import json
import time
from datetime import datetime
from typing import Dict, Set
import signal
import sys

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('server_async.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AsyncChatServer:
    """
    Chat Server bất đồng bộ sử dụng asyncio
    
    Tính năng:
    - Xử lý nhiều client đồng thời
    - Broadcast tin nhắn đến tất cả client
    - Quản lý danh sách client online
    - Ghi log hoạt động
    - Xử lý graceful shutdown
    """
    
    def __init__(self, host='localhost', port=8888):
        self.host = host
        self.port = port
        self.clients: Dict[asyncio.StreamWriter, Dict] = {}  # Lưu trữ thông tin client
        self.client_counter = 0
        self.start_time = time.time()
        self.message_count = 0
        self.server = None
        
    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """
        Xử lý kết nối từ một client cụ thể
        
        Args:
            reader: Stream để đọc dữ liệu từ client
            writer: Stream để gửi dữ liệu đến client
        """
        # Lấy thông tin địa chỉ client
        client_addr = writer.get_extra_info('peername')
        self.client_counter += 1
        client_id = f"Client_{self.client_counter}"
        
        # Lưu trữ thông tin client
        client_info = {
            'id': client_id,
            'address': client_addr,
            'connected_at': datetime.now(),
            'message_count': 0
        }
        self.clients[writer] = client_info
        
        logger.info(f" {client_id} kết nối từ {client_addr}")
        
        try:
            # Gửi thông báo chào mừng
            welcome_msg = {
                'type': 'welcome',
                'message': f'Chào mừng {client_id}! Bạn đã kết nối đến Chat Server Async.',
                'client_id': client_id,
                'server_info': {
                    'total_clients': len(self.clients),
                    'server_uptime': time.time() - self.start_time
                }
            }
            await self.send_message(writer, welcome_msg)
            
            # Thông báo cho tất cả client khác về client mới
            join_notification = {
                'type': 'user_joined',
                'message': f'{client_id} đã tham gia phòng chat',
                'client_id': client_id,
                'timestamp': datetime.now().isoformat()
            }
            await self.broadcast_message(join_notification, exclude=writer)
            
            # Xử lý tin nhắn từ client
            while True:
                try:
                    # Đọc dữ liệu với timeout để tránh blocking vô hạn
                    data = await asyncio.wait_for(
                        reader.read(4096), 
                        timeout=300  # 5 phút timeout
                    )
                    
                    if not data:
                        break
                        
                    # Giải mã và xử lý tin nhắn
                    message = data.decode('utf-8').strip()
                    if not message:
                        continue
                        
                    await self.process_message(writer, message, client_info)
                    
                except asyncio.TimeoutError:
                    logger.warning(f" {client_id} timeout - không có hoạt động trong 5 phút")
                    break
                except Exception as e:
                    logger.error(f" Lỗi xử lý tin nhắn từ {client_id}: {e}")
                    break
                    
        except Exception as e:
            logger.error(f" Lỗi xử lý client {client_id}: {e}")
        finally:
            await self.disconnect_client(writer, client_info)
    
    async def process_message(self, writer: asyncio.StreamWriter, message: str, client_info: Dict):
        """
        Xử lý tin nhắn từ client
        
        Args:
            writer: Stream writer của client
            message: Nội dung tin nhắn
            client_info: Thông tin client
        """
        client_id = client_info['id']
        client_info['message_count'] += 1
        self.message_count += 1
        
        # Thêm độ trễ giả lập để test hiệu suất (có thể điều chỉnh)
        await asyncio.sleep(0.01)  # 10ms delay để mô phỏng xử lý
        
        # Tạo response message
        response = {
            'type': 'chat_message',
            'sender': client_id,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'message_id': self.message_count
        }
        
        logger.info(f" {client_id}: {message}")
        
        # Broadcast tin nhắn đến tất cả client (bao gồm cả người gửi)
        await self.broadcast_message(response)
        
        # Gửi confirmation về cho người gửi
        confirmation = {
            'type': 'message_sent',
            'message': 'Tin nhắn đã được gửi thành công',
            'message_id': self.message_count
        }
        await self.send_message(writer, confirmation)
    
    async def send_message(self, writer: asyncio.StreamWriter, message: Dict):
        """
        Gửi tin nhắn đến một client cụ thể
        
        Args:
            writer: Stream writer của client
            message: Nội dung tin nhắn (dict)
        """
        try:
            # Chuyển đổi message thành JSON và gửi
            json_message = json.dumps(message, ensure_ascii=False) + '\n'
            writer.write(json_message.encode('utf-8'))
            await writer.drain()
        except Exception as e:
            logger.error(f" Lỗi gửi tin nhắn: {e}")
    
    async def broadcast_message(self, message: Dict, exclude: asyncio.StreamWriter = None):
        """
        Broadcast tin nhắn đến tất cả client đang kết nối
        
        Args:
            message: Nội dung tin nhắn
            exclude: Client không gửi đến (optional)
        """
        if not self.clients:
            return
            
        # Tạo danh sách tasks để gửi tin nhắn đồng thời
        tasks = []
        disconnected_clients = []
        
        for writer, client_info in self.clients.items():
            if writer != exclude:
                try:
                    task = asyncio.create_task(self.send_message(writer, message))
                    tasks.append(task)
                except Exception as e:
                    logger.error(f" Lỗi tạo task gửi tin nhắn cho {client_info['id']}: {e}")
                    disconnected_clients.append(writer)
        
        # Thực hiện tất cả tasks đồng thời
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # Xóa các client đã ngắt kết nối
        for writer in disconnected_clients:
            if writer in self.clients:
                del self.clients[writer]
    
    async def disconnect_client(self, writer: asyncio.StreamWriter, client_info: Dict):
        """
        Xử lý ngắt kết nối client
        
        Args:
            writer: Stream writer của client
            client_info: Thông tin client
        """
        client_id = client_info['id']
        
        try:
            # Xóa client khỏi danh sách
            if writer in self.clients:
                del self.clients[writer]
            
            # Đóng kết nối
            writer.close()
            await writer.wait_closed()
            
            # Thông báo cho các client khác
            leave_notification = {
                'type': 'user_left',
                'message': f'{client_id} đã rời phòng chat',
                'client_id': client_id,
                'timestamp': datetime.now().isoformat()
            }
            await self.broadcast_message(leave_notification)
            
            # Tính toán thống kê
            duration = datetime.now() - client_info['connected_at']
            logger.info(f" {client_id} đã ngắt kết nối. "
                       f"Thời gian online: {duration.total_seconds():.2f}s, "
                       f"Tin nhắn gửi: {client_info['message_count']}")
                       
        except Exception as e:
            logger.error(f" Lỗi ngắt kết nối {client_id}: {e}")
    
    async def start_server(self):
        """
        Khởi động server
        """
        try:
            # Tạo server sử dụng asyncio.start_server
            self.server = await asyncio.start_server(
                self.handle_client,
                self.host,
                self.port
            )
            
            addr = self.server.sockets[0].getsockname()
            logger.info(f" Chat Server Async đã khởi động tại {addr[0]}:{addr[1]}")
            logger.info(f" Server sẵn sàng xử lý nhiều client đồng thời!")
            
            # Chạy server vô hạn
            async with self.server:
                await self.server.serve_forever()
                
        except Exception as e:
            logger.error(f" Lỗi khởi động server: {e}")
            raise
    
    async def shutdown(self):
        """
        Tắt server một cách graceful
        """
        logger.info(" Đang tắt server...")
        
        # Thông báo cho tất cả client
        shutdown_msg = {
            'type': 'server_shutdown',
            'message': 'Server đang tắt. Cảm ơn bạn đã sử dụng dịch vụ!',
            'timestamp': datetime.now().isoformat()
        }
        await self.broadcast_message(shutdown_msg)
        
        # Đóng tất cả kết nối client
        for writer in list(self.clients.keys()):
            try:
                writer.close()
                await writer.wait_closed()
            except Exception as e:
                logger.error(f" Lỗi đóng kết nối client: {e}")
        
        # Đóng server
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        # In thống kê cuối
        uptime = time.time() - self.start_time
        logger.info(f" Thống kê server:")
        logger.info(f"   - Thời gian hoạt động: {uptime:.2f}s")
        logger.info(f"   - Tổng số tin nhắn: {self.message_count}")
        logger.info(f"   - Tổng số client đã kết nối: {self.client_counter}")
        logger.info(" Server đã tắt thành công!")

async def main():
    """
    Hàm chính để chạy server
    """
    server = AsyncChatServer()
    
    # Xử lý tín hiệu để tắt server gracefully
    def signal_handler():
        logger.info(" Nhận tín hiệu tắt server...")
        asyncio.create_task(server.shutdown())
    
    # Đăng ký signal handlers (chỉ hoạt động trên Unix/Linux)
    try:
        loop = asyncio.get_running_loop()
        for sig in [signal.SIGINT, signal.SIGTERM]:
            loop.add_signal_handler(sig, signal_handler)
    except NotImplementedError:
        # Windows không hỗ trợ signal handlers trong asyncio
        logger.info(" Signal handlers không được hỗ trợ trên Windows")
    
    try:
        await server.start_server()
    except KeyboardInterrupt:
        logger.info(" Nhận Ctrl+C, đang tắt server...")
        await server.shutdown()
    except Exception as e:
        logger.error(f" Lỗi server: {e}")
        await server.shutdown()

if __name__ == "__main__":
    """
    Entry point của ứng dụng
    
    Cách chạy:
    python server_async.py
    
    Hoặc để chỉ định host/port:
    python server_async.py --host 0.0.0.0 --port 9999
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Chat Server Bất Đồng Bộ')
    parser.add_argument('--host', default='localhost', help='Địa chỉ IP server (default: localhost)')
    parser.add_argument('--port', type=int, default=8888, help='Port server (default: 8888)')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Mức độ log (default: INFO)')
    
    args = parser.parse_args()
    
    # Cấu hình log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    print("=" * 60)
    print(" CHAT SERVER BẤT ĐỒNG BỘ - NHÓM 19")
    print("=" * 60)
    print(f" Host: {args.host}")
    print(f" Port: {args.port}")
    print(f"Log Level: {args.log_level}")
    print("=" * 60)
    print(" Nhấn Ctrl+C để tắt server")
    print("=" * 60)
    
    try:
        # Chạy server
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n Cảm ơn bạn đã sử dụng Chat Server Async!")
    except Exception as e:
        print(f" Lỗi nghiêm trọng: {e}")
        sys.exit(1)