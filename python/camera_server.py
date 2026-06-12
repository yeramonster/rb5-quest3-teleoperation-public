import cv2
import threading
from flask import Flask, Response

CAMERA_INDEX = 0
WIDTH        = 1280
HEIGHT       = 720
FPS          = 30
PORT         = 8080
JPEG_QUALITY = 80

app    = Flask(__name__)
_frame = None
_lock  = threading.Lock()


def capture_loop():
    global _frame
    cap = cv2.VideoCapture(CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)
    cap.set(cv2.CAP_PROP_FPS,          FPS)

    if not cap.isOpened():
        raise RuntimeError(f"카메라 {CAMERA_INDEX} 열기 실패")

    print(f"카메라 시작: {WIDTH}x{HEIGHT}@{FPS}fps")
    while True:
        ret, frame = cap.read()
        if not ret:
            continue
        with _lock:
            _frame = frame


@app.route("/snapshot")
def snapshot():
    with _lock:
        frame = _frame
    if frame is None:
        return "No frame", 503
    _, buf = cv2.imencode(".jpg", frame,
                          [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    return Response(buf.tobytes(), mimetype="image/jpeg")


@app.route("/stream")
def stream():
    def gen():
        while True:
            with _lock:
                frame = _frame
            if frame is None:
                continue
            _, buf = cv2.imencode(".jpg", frame,
                                  [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
                   + buf.tobytes() + b"\r\n")
    return Response(gen(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")


if __name__ == "__main__":
    t = threading.Thread(target=capture_loop, daemon=True)
    t.start()
    print(f"카메라 서버: http://<PC_IP>:{PORT}/snapshot")
    print(f"스트림 확인: http://<PC_IP>:{PORT}/stream")
    app.run(host="0.0.0.0", port=PORT, threaded=True)
