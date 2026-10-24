import argparse
import socket
import time

p = argparse.ArgumentParser()
p.add_argument("--ip", required=True, help="ESP32 IP")
args = p.parse_args()
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
print(f"Sending black/white test to {args.ip}:4210")
try:
    for i in range(40):
        frame = bytes([0xFF if i % 2 else 0x00]) * 1024
        sock.sendto(b"VID0" + frame, (args.ip, 4210))
        print("WHITE" if i % 2 else "BLACK")
        time.sleep(0.4)
finally:
    sock.close()
