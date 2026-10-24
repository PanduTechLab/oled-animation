import argparse
import socket
import time
import cv2
import numpy as np
from PIL import Image, ImageOps

WIDTH, HEIGHT = 128, 64
PORT = 4210


def encode_frame(bgr, mode="dither", fit="crop", threshold=128):
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    if fit == "crop":
        ratio = WIDTH / HEIGHT
        if w / h > ratio:
            new_w = max(1, round(h * ratio))
            x = (w - new_w) // 2
            gray = gray[:, x:x + new_w]
        else:
            new_h = max(1, round(w / ratio))
            y = (h - new_h) // 2
            gray = gray[y:y + new_h, :]
        image = Image.fromarray(gray).resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    else:
        image = ImageOps.contain(Image.fromarray(gray), (WIDTH, HEIGHT), Image.Resampling.LANCZOS)
        canvas = Image.new("L", (WIDTH, HEIGHT), 0)
        canvas.paste(image, ((WIDTH - image.width) // 2, (HEIGHT - image.height) // 2))
        image = canvas

    image = ImageOps.autocontrast(image)

    if mode == "dither":
        pixels = np.asarray(
            image.convert("1", dither=Image.Dither.FLOYDSTEINBERG), dtype=np.uint8
        )
    else:
        gray_arr = np.asarray(image, dtype=np.uint8)
        pixels = (gray_arr > threshold).astype(np.uint8)

    # SSD1306 page format: each byte represents eight VERTICAL pixels.
    packed = np.packbits(pixels.reshape(8, 8, WIDTH).transpose(0, 2, 1), axis=2, bitorder="little")
    return packed.tobytes()


def main():
    p = argparse.ArgumentParser(description="Stream an MP4 to an ESP32 SSD1306 OLED")
    p.add_argument("video", help="MP4/AVI file path")
    p.add_argument("--ip", required=True, help="ESP32 IP shown in Arduino Serial Monitor")
    p.add_argument("--fps", type=float, default=12)
    p.add_argument("--mode", choices=["dither", "threshold"], default="dither")
    p.add_argument("--fit", choices=["crop", "letterbox"], default="crop")
    p.add_argument("--threshold", type=int, default=128, help="0-255, used with --mode threshold")
    args = p.parse_args()

    if args.fps <= 0:
        p.error("--fps must be greater than zero")
    if not 0 <= args.threshold <= 255:
        p.error("--threshold must be between 0 and 255")

    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        raise SystemExit(f"Cannot open video: {args.video}")

    source_fps = cap.get(cv2.CAP_PROP_FPS)
    if source_fps <= 0 or not np.isfinite(source_fps):
        source_fps = 30.0

    print(f"Source: {source_fps:.2f} FPS | Output: {args.fps:.2f} FPS")
    print(f"Sending to {args.ip}:{PORT} | Ctrl+C to stop")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    source_index = 0
    sent = 0
    started = time.perf_counter()

    try:
        while True:
            ok, frame = cap.read()  # sequential decode, no expensive repeated seeking
            if not ok:
                break

            timestamp = source_index / source_fps
            source_index += 1

            # Only output frames at requested timestamps; drop extras.
            if timestamp + 1e-8 < sent / args.fps:
                continue

            target = started + sent / args.fps
            delay = target - time.perf_counter()
            if delay > 0:
                time.sleep(delay)

            payload = b"VID0" + encode_frame(frame, args.mode, args.fit, args.threshold)
            sock.sendto(payload, (args.ip, PORT))
            sent += 1

            if sent % 30 == 0:
                print(f"Sent {sent} frames")
    except KeyboardInterrupt:
        print("Stopped")
    finally:
        cap.release()
        sock.close()
        print(f"Finished. Sent {sent} frames. UDP send does not confirm delivery.")


if __name__ == "__main__":
    main()
