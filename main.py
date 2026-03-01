import cv2
import argparse
import socket
import pickle
import struct
import time
from ultralytics import YOLO
import supervision as sv
import numpy as np
import base64
import json

def parse_arguments():
    parser = argparse.ArgumentParser(description="YOLOv8 live")
    parser.add_argument("--webcam-resolution", default=[1280, 720], nargs=2, type=int)
    args = parser.parse_args()
    return args

def send_data(data, ip, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((ip, port))
        sock.sendall(json.dumps(data).encode('utf-8'))
        print("데이터 전송 완료.")

def send_buzzer_signal(ip, port, command):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:     
            sock.connect((ip, port))
            sock.sendall(json.dumps(command).encode('utf-8'))
            print("부저 신호 전송 완료.")
        except Exception as e:
            print(f"부저 신호 전송 실패: {e}")

def apply_mosaic_to_face(frame, factor=45):
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)
    for (x, y, w, h) in faces:
        # 얼굴 영역이 너무 작아서 모자이크 처리가 불가능한 경우를 대비
        if w < factor or h < factor:
            continue  # 너무 작은 영역은 모자이크 처리를 하지 않음
        face_roi = frame[y:y+h, x:x+w]
        face_roi = cv2.resize(face_roi, (w // factor, h // factor))
        face_roi = cv2.resize(face_roi, (w, h), interpolation=cv2.INTER_AREA)
        frame[y:y+h, x:x+w] = face_roi
    return frame


def main():
    args = parse_arguments()
    model = YOLO("helmet_final.pt")
    box_annotator = sv.BoxAnnotator(thickness=2, text_thickness=2, text_scale=1)
    zone_polygon = (np.array([[0, 0], [0.5, 0], [0.5, 1], [0, 1]]) * np.array(args.webcam_resolution)).astype(int)
    zone = sv.PolygonZone(polygon=zone_polygon, frame_resolution_wh=tuple(args.webcam_resolution))
    zone_annotator = sv.PolygonZoneAnnotator(zone=zone, color=sv.Color.red(), thickness=2, text_thickness=4, text_scale=2)

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    host_ip = '192.168.0.6' # PC의 IP 주소
    port = 8999
    server_socket.bind((host_ip, port))
    server_socket.listen(5)
    print("Listening at:", host_ip, "on port", port)
    client_socket, addr = server_socket.accept()
    print('Connected by:', addr)

    data = b""
    payload_size = struct.calcsize("Q")
    helmet_absence_start = None
    start_time = time.time()
    image_captured = False

    try:
        while True:
            while len(data) < payload_size:
                packet = client_socket.recv(4 * 1024)
                if not packet: break
                data += packet
            packed_msg_size = data[:payload_size]
            data = data[payload_size:]
            msg_size = struct.unpack("Q", packed_msg_size)[0]

            while len(data) < msg_size:
                data += client_socket.recv(4 * 1024)
            frame_data = data[:msg_size]
            data = data[msg_size:]

            frame = pickle.loads(frame_data)
            result = model(frame, agnostic_nms=True)[0]
            detections = sv.Detections.from_yolov8(result)

            # Draw bounding boxes and labels on the original frame
            original_frame = box_annotator.annotate(scene=frame.copy(), detections=detections)
            cv2.imshow('YOLOv8 Detection', original_frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

            # Apply mosaic to faces on a copy for transmission
            frame_with_mosaic = apply_mosaic_to_face(frame.copy(), factor=45)

            helmet_present = any(det[1] > 0.1 for det in detections)
            if not helmet_present:
                if helmet_absence_start is None:
                    helmet_absence_start = time.time()
                elif time.time() - helmet_absence_start >= 3:
                    send_buzzer_signal('192.168.0.8', 8995, {'command': 'start_buzzer'})
                    helmet_absence_start = None
            else:
                if helmet_absence_start is not None:
                    send_buzzer_signal('192.168.0.8', 8995, {'command': 'stop_buzzer'})
                    helmet_absence_start = None

            # Send mosaic-applied data if the condition is met
            if time.time() - start_time > 5 and not image_captured:
                image_captured = True
                _, img_encoded = cv2.imencode('.jpg', frame_with_mosaic)
                img_base64 = base64.b64encode(img_encoded).decode('utf-8')
                confidence = max([conf for _, conf, _, _ in detections], default=0)
                result_data = {'image': img_base64, 'confidence': float(confidence)}
                send_data(result_data, '192.168.0.7', 8997) # 안드로이드폰 ip주소

    finally:
        cv2.destroyAllWindows()
        client_socket.close()
        server_socket.close()

if __name__ == "__main__":
    main()
