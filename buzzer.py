import socket
import json
import RPi.GPIO as GPIO
import time
import threading

def setup_buzzer(pin):
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(pin, GPIO.OUT)
    return GPIO.PWM(pin, 440)  # "라" 음계에 해당하는 주파수인 440Hz 설정

def play_tone(pwm, event):
    """ PWM을 시작하여 부저를 계속 울리게 합니다. """
    pwm.start(50)  # 듀티 사이클 50%로 PWM 시작
    event.wait()  # 이벤트가 설정될 때까지 대기
    pwm.stop()  # PWM 정지

def stop_buzzer(event):
    event.set()  # 이벤트를 설정하여 play_tone 루프를 중지시킵니다.

def main():
    buzzer_pin = 18
    pwm_buzzer = setup_buzzer(buzzer_pin)
    play_event = threading.Event()

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    host_ip = '192.168.0.20'
    port = 8995
    server_socket.bind((host_ip, port))
    server_socket.listen(5)
    print("Listening for buzzer control commands on {}:{}".format(host_ip, port))

    try:
        while True:
            print("Waiting for a connection...")
            client_socket, addr = server_socket.accept()
            print("Connected to:", addr)

            full_data = ''
            try:
                while True:
                    data = client_socket.recv(1024)
                    if not data:
                        break
                    full_data += data.decode('utf-8')
                    try:
                        command = json.loads(full_data)
                        print("Command parsed:", command)
                        if command.get('command') == 'start_buzzer':
                            print("Executing command: Start Buzzer")
                            play_event.clear()  # 이벤트 상태 초기화
                            threading.Thread(target=play_tone, args=(pwm_buzzer, play_event)).start()
                        elif command.get('command') == 'stop_buzzer':
                            print("Executing command: Stop Buzzer")
                            stop_buzzer(play_event)  # 부저 소리 중지
                        full_data = ''  # 데이터 리셋
                    except json.JSONDecodeError as e:
                        print("JSON decoding failed:", e)
                        full_data = ''  # 에러 발생시 리셋
            finally:
                client_socket.close()
                print("Client connection closed.")
    finally:
        GPIO.cleanup()
        server_socket.close()
        print("Server socket closed.")

if __name__ == "__main__":
    main()
