import socket
import subprocess
import re

def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('0.0.0.0', 8998))
    server_socket.listen(1)
    print("클라이언트와의 연결 대기중...")

    try:
        while True:
            client_socket, addr = server_socket.accept()
            print(f"connected by {addr}")

            try:
                while True:
                    data = client_socket.recv(1024)
                    if not data:
                        break
                    message = data.decode()
                    message = re.sub(r'[^\d]', '', message)
                    print(message)
                    message = int(message)

                    # 특정 메시지 수신 시 server.py 스크립트 실행
                    if message == 1:
                        print("Executing server.py...")
                        subprocess.run(['python3', '/home/krh/yolo/yolov8_live/server.py'])
                    else:
                        print(f"Message does not match: '{message}'")
                        
            finally:
                client_socket.close()

    finally:
        server_socket.close()

if __name__ == "__main__":
    start_server()
