"""
Phân tích và So sánh Hiệu suất Server Blocking vs Async
======================================================

Mô tả:
- Tự động chạy test với cả 2 loại server (blocking và async)
- Đo thời gian phản hồi, tốc độ xử lý với nhiều mức độ tải khác nhau
- Vẽ biểu đồ so sánh trực quan bằng matplotlib
- Tạo báo cáo phân tích chi tiết

Tác giả: Nhóm 19 - E-Learning 3
"""

import asyncio
import subprocess
import time
import statistics
import matplotlib.pyplot as plt
import json
import os
import sys
import threading
import socket
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Tuple
import numpy as np
import pandas as pd
from datetime import datetime

class PerformanceAnalyzer:
    """
    Lớp phân tích hiệu suất cho server blocking và async
    """
    
    def __init__(self):
        self.results = {
            'blocking': {},
            'async': {}
        }
        self.test_scenarios = [1, 3, 5, 8, 10, 15, 20]  # Số lượng client phù hợp cho blocking server
        self.server_processes = {}
        
    def setup_directories(self):
        """Tạo thư mục lưu kết quả nếu chưa có"""
        os.makedirs('analysis/results', exist_ok=True)
        os.makedirs('analysis/plots', exist_ok=True)
        
    def start_server(self, server_type: str, port: int = 8888) -> subprocess.Popen:
        """
        Khởi động server (blocking hoặc async)
        
        Args:
            server_type: 'blocking' hoặc 'async'  
            port: cổng server
            
        Returns:
            Process object của server
        """
        if server_type == 'blocking':
            cmd = [sys.executable, 'server/server_blocking.py']
        else:
            cmd = [sys.executable, 'server/server_async.py']
            
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Đợi server khởi động
            time.sleep(2)
            return process
            
        except Exception as e:
            print(f"Lỗi khởi động server {server_type}: {e}")
            return None
    
    def stop_server(self, process: subprocess.Popen):
        """Dừng server process"""
        if process:
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                
    def test_blocking_server(self, num_clients: int, host: str = '127.0.0.1', port: int = 8888) -> Dict:
        """
        Test hiệu suất server blocking với số lượng client nhất định
        
        Args:
            num_clients: Số lượng client đồng thời
            host: Địa chỉ server
            port: Cổng server
            
        Returns:
            Dict chứa kết quả test
        """
        results = {
            'response_times': [],
            'successful_connections': 0,
            'failed_connections': 0,
            'total_time': 0
        }
        
        def client_task(client_id):
            """Task cho mỗi client blocking"""
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(10)  # Timeout 10 giây
                
                start_time = time.perf_counter()
                sock.connect((host, port))
                
                # Gửi tin nhắn
                message = f"Hello from blocking client {client_id}"
                sock.sendall(message.encode())
                
                # Nhận phản hồi
                response = sock.recv(1024)
                end_time = time.perf_counter()
                
                response_time = end_time - start_time
                results['response_times'].append(response_time)
                results['successful_connections'] += 1
                
                sock.close()
                return response_time
                
            except Exception as e:
                results['failed_connections'] += 1
                print(f"Blocking Client {client_id} lỗi: {e}")
                return None
        
        # Chạy test tuần tự vì server blocking chỉ xử lý 1 client/lần
        start_total = time.perf_counter()
        
        # Chạy từng client một (phù hợp với server blocking gốc)
        for i in range(num_clients):
            client_task(i)
            time.sleep(0.1)  # Nghỉ ngắn giữa các client
                
        results['total_time'] = time.perf_counter() - start_total
        
        return results
    
    async def test_async_server(self, num_clients: int, host: str = '127.0.0.1', port: int = 8888) -> Dict:
        """
        Test hiệu suất server async với số lượng client nhất định
        
        Args:
            num_clients: Số lượng client đồng thời
            host: Địa chỉ server  
            port: Cổng server
            
        Returns:
            Dict chứa kết quả test
        """
        results = {
            'response_times': [],
            'successful_connections': 0,
            'failed_connections': 0,
            'total_time': 0
        }
        
        async def client_task(client_id):
            """Task cho mỗi async client"""
            try:
                reader, writer = await asyncio.open_connection(host, port)
                
                start_time = time.perf_counter()
                
                # Gửi tin nhắn text format (theo server async gốc)
                message = f"Hello from async client {client_id}\n"
                
                writer.write(message.encode())
                await writer.drain()
                
                # Nhận phản hồi
                response = await reader.readline()
                end_time = time.perf_counter()
                
                response_time = end_time - start_time
                results['response_times'].append(response_time)
                results['successful_connections'] += 1
                
                writer.close()
                await writer.wait_closed()
                
                return response_time
                
            except Exception as e:
                results['failed_connections'] += 1
                print(f"Async Client {client_id} lỗi: {e}")
                return None
        
        # Chạy tất cả client đồng thời
        start_total = time.perf_counter()
        
        tasks = [client_task(i) for i in range(num_clients)]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        results['total_time'] = time.perf_counter() - start_total
        
        return results
    
    def run_performance_tests(self):
        """
        Chạy toàn bộ test cases cho cả 2 server
        """
        print("Bắt đầu phân tích hiệu suất Server Blocking vs Async")
        print("=" * 60)
        
        self.setup_directories()
        
        # Test từng loại server (yêu cầu start manual)
        for server_type in ['blocking', 'async']:
            print(f"\nTesting {server_type.upper()} Server...")
            print(f"VUI LÒNG KHỞI ĐỘNG {server_type.upper()} SERVER TRƯỚC KHI TIẾP TỤC!")
            print(f"Chạy lệnh: python server/server_{server_type}.py")
            
            input("Nhấn Enter khi server đã sẵn sàng...")
            
            try:
                # Test với các kịch bản khác nhau
                for num_clients in self.test_scenarios:
                    print(f"   Testing với {num_clients} clients...")
                    
                    if server_type == 'blocking':
                        result = self.test_blocking_server(num_clients)
                    else:
                        result = asyncio.run(self.test_async_server(num_clients))
                    
                    self.results[server_type][num_clients] = result
                    
                    # In kết quả ngay lập tức
                    if result['response_times']:
                        avg_time = statistics.mean(result['response_times'])
                        print(f"      OK - Avg Response: {avg_time:.4f}s | Success: {result['successful_connections']} | Failed: {result['failed_connections']}")
                    else:
                        print(f"      LỖII: Không có kết nối thành công nào")
                    
                    time.sleep(1)  # Nghỉ giữa các test
                    
            finally:
                print(f"   Hoàn thành test {server_type} server")
                print(f"   Bạn có thể dừng server {server_type} bằng Ctrl+C")
                input("Nhấn Enter để tiếp tục test server tiếp theo...")
                time.sleep(1)  # Nghỉ ngắn
    
    def analyze_results(self) -> Dict:
        """
        Phân tích và tính toán các chỉ số từ kết quả test
        
        Returns:
            Dict chứa phân tích chi tiết
        """
        analysis = {
            'summary': {},
            'detailed_metrics': {},
            'recommendations': []
        }
        
        for server_type in ['blocking', 'async']:
            metrics = {
                'avg_response_times': [],
                'max_response_times': [],
                'min_response_times': [],
                'success_rates': [],
                'throughput': []  # requests per second
            }
            
            for num_clients, result in self.results[server_type].items():
                if result['response_times']:
                    # Tính các chỉ số thống kê
                    response_times = result['response_times']
                    metrics['avg_response_times'].append(statistics.mean(response_times))
                    metrics['max_response_times'].append(max(response_times))
                    metrics['min_response_times'].append(min(response_times))
                    
                    # Tỷ lệ thành công
                    total_attempts = result['successful_connections'] + result['failed_connections']
                    success_rate = result['successful_connections'] / total_attempts if total_attempts > 0 else 0
                    metrics['success_rates'].append(success_rate)
                    
                    # Throughput (requests/second)
                    throughput = result['successful_connections'] / result['total_time'] if result['total_time'] > 0 else 0
                    metrics['throughput'].append(throughput)
                else:
                    # Trường hợp không có kết quả
                    metrics['avg_response_times'].append(float('inf'))
                    metrics['max_response_times'].append(float('inf'))
                    metrics['min_response_times'].append(float('inf'))
                    metrics['success_rates'].append(0)
                    metrics['throughput'].append(0)
            
            analysis['detailed_metrics'][server_type] = metrics
        
        # Tóm tắt so sánh
        analysis['summary'] = self._create_summary_comparison()
        
        # Đề xuất
        analysis['recommendations'] = self._generate_recommendations()
        
        return analysis
    
    def _create_summary_comparison(self) -> Dict:
        """Tạo bảng tóm tắt so sánh"""
        summary = {}
        
        for scenario_idx, num_clients in enumerate(self.test_scenarios):
            blocking_result = self.results.get('blocking', {}).get(num_clients, {})
            async_result = self.results.get('async', {}).get(num_clients, {})
            
            # Tính toán chỉ số cho từng scenario
            blocking_avg = statistics.mean(blocking_result.get('response_times', [float('inf')])) if blocking_result.get('response_times') else float('inf')
            async_avg = statistics.mean(async_result.get('response_times', [float('inf')])) if async_result.get('response_times') else float('inf')
            
            # So sánh hiệu suất  
            improvement = ((blocking_avg - async_avg) / blocking_avg * 100) if blocking_avg != float('inf') and async_avg != float('inf') else 0
            
            summary[num_clients] = {
                'blocking_avg_response': blocking_avg,
                'async_avg_response': async_avg,
                'performance_improvement': improvement,
                'blocking_success_rate': blocking_result.get('successful_connections', 0) / (blocking_result.get('successful_connections', 0) + blocking_result.get('failed_connections', 1)),
                'async_success_rate': async_result.get('successful_connections', 0) / (async_result.get('successful_connections', 0) + async_result.get('failed_connections', 1))
            }
            
        return summary
        
    def _generate_recommendations(self) -> List[str]:
        """Tạo các đề xuất dựa trên kết quả phân tích"""
        recommendations = []
        
        # Phân tích xu hướng hiệu suất
        async_avg_times = []
        blocking_avg_times = []
        
        for num_clients in self.test_scenarios:
            async_result = self.results.get('async', {}).get(num_clients, {})
            blocking_result = self.results.get('blocking', {}).get(num_clients, {})
            
            if async_result.get('response_times'):
                async_avg_times.append(statistics.mean(async_result['response_times']))
            if blocking_result.get('response_times'):
                blocking_avg_times.append(statistics.mean(blocking_result['response_times']))
        
        # Đề xuất dựa trên phân tích
        if len(async_avg_times) > 0 and len(blocking_avg_times) > 0:
            avg_async = statistics.mean(async_avg_times)
            avg_blocking = statistics.mean(blocking_avg_times)
            
            if avg_async < avg_blocking:
                improvement = ((avg_blocking - avg_async) / avg_blocking) * 100
                recommendations.append(f"Server Async nhanh hơn Server Blocking trung bình {improvement:.1f}%")
                recommendations.append("Nên sử dụng Server Async cho ứng dụng production")
            else:
                recommendations.append("Server Blocking có hiệu suất tương đương hoặc tốt hơn trong test case này")
        
        recommendations.extend([
            "Server Async thích hợp cho ứng dụng có nhiều I/O operations",
            "Server Blocking đơn giản hơn để debug và maintain",
            "Với số lượng client lớn (>50), async có lợi thế rõ rệt",
            "Cần xem xét memory usage khi scale up"
        ])
        
        return recommendations
    
    def create_visualizations(self, analysis: Dict):
        """
        Tạo các biểu đồ so sánh hiệu suất
        
        Args:
            analysis: Kết quả phân tích từ analyze_results()
        """
        # Thiết lập style cho matplotlib
        plt.style.use('default')
        plt.rcParams['font.size'] = 10
        plt.rcParams['figure.figsize'] = (12, 8)
        
        # Chuẩn bị dữ liệu cho biểu đồ
        clients = self.test_scenarios
        
        blocking_avg = []
        async_avg = []
        blocking_throughput = []
        async_throughput = []
        
        for num_clients in clients:
            # Average response time
            blocking_result = self.results.get('blocking', {}).get(num_clients, {})
            async_result = self.results.get('async', {}).get(num_clients, {})
            
            if blocking_result.get('response_times'):
                blocking_avg.append(statistics.mean(blocking_result['response_times']))
                blocking_throughput.append(blocking_result['successful_connections'] / blocking_result['total_time'])
            else:
                blocking_avg.append(0)
                blocking_throughput.append(0)
                
            if async_result.get('response_times'):
                async_avg.append(statistics.mean(async_result['response_times']))
                async_throughput.append(async_result['successful_connections'] / async_result['total_time'])
            else:
                async_avg.append(0)
                async_throughput.append(0)
        
        # Tạo figure với subplots
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('So sánh Hiệu suất Server Blocking vs Async', fontsize=16, fontweight='bold')
        
        # 1. Biểu đồ thời gian phản hồi trung bình
        ax1.plot(clients, blocking_avg, 'ro-', label='Blocking Server', linewidth=2, markersize=6)
        ax1.plot(clients, async_avg, 'bo-', label='Async Server', linewidth=2, markersize=6)
        ax1.set_xlabel('Số lượng Client đồng thời')
        ax1.set_ylabel('Thời gian phản hồi trung bình (s)')
        ax1.set_title('Thời gian Phản hồi Trung bình')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        ax1.set_yscale('log')  # Log scale để dễ nhìn
        
        # 2. Biểu đồ throughput
        ax2.bar([x - 0.2 for x in clients], blocking_throughput, width=0.4, label='Blocking Server', color='red', alpha=0.7)
        ax2.bar([x + 0.2 for x in clients], async_throughput, width=0.4, label='Async Server', color='blue', alpha=0.7)
        ax2.set_xlabel('Số lượng Client đồng thời')
        ax2.set_ylabel('Throughput (requests/s)')
        ax2.set_title('Throughput Comparison')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # 3. Biểu đồ tỷ lệ thành công
        blocking_success = []
        async_success = []
        
        for num_clients in clients:
            blocking_result = self.results.get('blocking', {}).get(num_clients, {})
            async_result = self.results.get('async', {}).get(num_clients, {})
            
            blocking_total = blocking_result.get('successful_connections', 0) + blocking_result.get('failed_connections', 0)
            async_total = async_result.get('successful_connections', 0) + async_result.get('failed_connections', 0)
            
            blocking_success.append(blocking_result.get('successful_connections', 0) / blocking_total * 100 if blocking_total > 0 else 0)
            async_success.append(async_result.get('successful_connections', 0) / async_total * 100 if async_total > 0 else 0)
        
        ax3.plot(clients, blocking_success, 'ro-', label='Blocking Server', linewidth=2, markersize=6)
        ax3.plot(clients, async_success, 'bo-', label='Async Server', linewidth=2, markersize=6)
        ax3.set_xlabel('Số lượng Client đồng thời')
        ax3.set_ylabel('Tỷ lệ thành công (%)')
        ax3.set_title('Tỷ lệ Kết nối Thành công')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        ax3.set_ylim(0, 105)
        
        # 4. Box plot so sánh phân phối thời gian phản hồi
        all_blocking_times = []
        all_async_times = []
        
        for num_clients in clients:
            blocking_result = self.results.get('blocking', {}).get(num_clients, {})
            async_result = self.results.get('async', {}).get(num_clients, {})
            
            all_blocking_times.extend(blocking_result.get('response_times', []))
            all_async_times.extend(async_result.get('response_times', []))
        
        if all_blocking_times and all_async_times:
            ax4.boxplot([all_blocking_times, all_async_times], labels=['Blocking', 'Async'])
            ax4.set_ylabel('Thời gian phản hồi (s)')
            ax4.set_title('Phân phối Thời gian Phản hồi')
            ax4.grid(True, alpha=0.3)
        else:
            ax4.text(0.5, 0.5, 'Không đủ dữ liệu\ncho box plot', ha='center', va='center', transform=ax4.transAxes)
            ax4.set_title('Phân phối Thời gian Phản hồi')
        
        plt.tight_layout()
        
        # Lưu biểu đồ
        plt.savefig('analysis/plots/performance_comparison.png', dpi=300, bbox_inches='tight')
        plt.savefig('analysis/plots/performance_comparison.pdf', bbox_inches='tight')
        print("Đã lưu biểu đồ tại: analysis/plots/performance_comparison.png")
        
        # Hiển thị biểu đồ
        plt.show()
    
    def generate_report(self, analysis: Dict):
        """
        Tạo báo cáo chi tiết dạng text và JSON
        
        Args:
            analysis: Kết quả phân tích từ analyze_results()
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Báo cáo text
        report_text = f"""
=================================================================
        BÁO CÁO PHÂN TÍCH HIỆU SUẤT SERVER BLOCKING vs ASYNC
=================================================================
Thời gian: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Tác giả: Nhóm 19 - E-Learning 3

1. TỔNG QUAN TEST
-----------------
Số kịch bản test: {len(self.test_scenarios)}
Số client test: {', '.join(map(str, self.test_scenarios))}

2. KẾT QUẢ CHI TIẾT
------------------
"""
        
        # Thêm chi tiết cho từng kịch bản
        for num_clients in self.test_scenarios:
            summary = analysis['summary'].get(num_clients, {})
            
            report_text += f"""
Kịch bản {num_clients} clients:
  • Blocking Server:
    - Thời gian phản hồi TB: {summary.get('blocking_avg_response', 'N/A'):.4f}s
    - Tỷ lệ thành công: {summary.get('blocking_success_rate', 0)*100:.1f}%
  • Async Server:
    - Thời gian phản hồi TB: {summary.get('async_avg_response', 'N/A'):.4f}s
    - Tỷ lệ thành công: {summary.get('async_success_rate', 0)*100:.1f}%
  • Cải thiện hiệu suất: {summary.get('performance_improvement', 0):.1f}%
"""
        
        report_text += f"""
3. KHUYẾN NGHỊ
--------------
"""
        
        for rec in analysis['recommendations']:
            report_text += f"  {rec}\n"
            
        report_text += f"""

4. KẾT LUẬN
-----------
Dựa trên kết quả test, server async thường có hiệu suất tốt hơn
khi số lượng client đồng thời tăng cao. Server blocking phù hợp
cho các ứng dụng đơn giản với ít client concurrent.

=================================================================
"""
        
        # Lưu báo cáo
        with open(f'analysis/results/performance_report_{timestamp}.txt', 'w', encoding='utf-8') as f:
            f.write(report_text)
            
        # Lưu dữ liệu raw dạng JSON
        with open(f'analysis/results/raw_data_{timestamp}.json', 'w', encoding='utf-8') as f:
            json.dump({
                'test_results': self.results,
                'analysis': analysis,
                'timestamp': timestamp
            }, f, indent=2, ensure_ascii=False)
        
        print("Đã tạo báo cáo chi tiết:")
        print(f"   - Text: analysis/results/performance_report_{timestamp}.txt")
        print(f"   - JSON: analysis/results/raw_data_{timestamp}.json")
        
        # In báo cáo ra console
        print(report_text)
    
    def run_complete_analysis(self):
        """
        Chạy toàn bộ quy trình phân tích
        """
        print("Khởi động phân tích hiệu suất toàn diện...")
        
        # 1. Chạy performance tests
        self.run_performance_tests()
        
        # 2. Phân tích kết quả  
        print("\nĐang phân tích kết quả...")
        analysis = self.analyze_results()
        
        # 3. Tạo biểu đồ
        print("\nĐang tạo biểu đồ...")
        self.create_visualizations(analysis)
        
        # 4. Tạo báo cáo
        print("\nĐang tạo báo cáo...")
        self.generate_report(analysis)
        
        print("\nHoàn thành phân tích hiệu suất!")
        print("Kết quả được lưu trong thư mục analysis/")


def main():
    """Hàm chính để chạy phân tích"""
    print("Chương trình Phân tích Hiệu suất Server")
    print("   Blocking vs Async Performance Analyzer")
    print("   Nhóm 19 - E-Learning 3")
    print("=" * 50)
    
    try:
        analyzer = PerformanceAnalyzer()
        analyzer.run_complete_analysis()
        
    except KeyboardInterrupt:
        print("\nNgười dùng hủy chương trình")
    except Exception as e:
        print(f"\nLỗi trong quá trình phân tích: {e}")
        import traceback
        traceback.print_exc()
    
    input("\nNhấn Enter để thoát...")


if __name__ == "__main__":
    main()