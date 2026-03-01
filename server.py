import cv2
import socket
import pickle
import struct

# 웹캠 초기화
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)  # 해상도 설정
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# 소켓 연결 설정
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
host_ip = '192.168.0.6'  # PC의 IP 주소 입력
port = 8999  # 포트 번호, 맥북과 일치해야 함

client_socket.connect((host_ip, port))  # 맥북과 연결

# 이미지 데이터 전송 준비
while True:
    ret, frame = cap.read()
    if ret:
        data = pickle.dumps(frame)  # 프레임을 바이트로 직렬화
        message = struct.pack("Q", len(data)) + data
        client_socket.sendall(message)  # 데이터 전송

        # 'q' 누르면 종료
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
client_socket.close()
