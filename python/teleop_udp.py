import socket
import json
import time
import numpy as np
import rbpodo as rb

# ── 설정 (환경에 맞게 수정하세요) ────────────────
LOCAL_IP   = "0.0.0.0"
LOCAL_PORT = 5159
ROBOT_IP   = "192.168.x.x"   # 로봇 유선 LAN IP로 변경
SIM_MODE   = True             # 첫 실행 시 True 권장, 실제 로봇 사용 시 False

SCALE = 500.0  # 손 1m 이동 = 로봇 500mm 이동

# 로봇 홈 TCP 위치 (펜던트에서 확인)
HOME    = [127.0, -684.0, 276.0]
HOME_RX, HOME_RY, HOME_RZ = 179.0, 1.0, -178.0

# 작업공간 제한 (mm)
X_MIN, X_MAX = -100.0,  400.0
Y_MIN, Y_MAX = -900.0, -400.0
Z_MIN, Z_MAX =   50.0,  500.0

MOVE_SPEED = 300.0
MOVE_ACC   = 500.0
# ──────────────────────────────────────────────

robot  = None
rc     = None
origin = None


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def quest_to_robot(qx, qy, qz):
    global origin
    if origin is None:
        origin = [qx, qy, qz]
        print(f"[CALIB] 기준점 설정: {origin}")

    dx = (qx - origin[0]) * SCALE
    dy = (qy - origin[1]) * SCALE
    dz = (qz - origin[2]) * SCALE

    # 로봇 좌표계 매핑 (+X=왼쪽, +Y=뒤, +Z=위)
    rx = clamp(HOME[0] - dx, X_MIN, X_MAX)  # 좌우
    ry = clamp(HOME[1] - dz, Y_MIN, Y_MAX)  # 앞뒤
    rz = clamp(HOME[2] + dy, Z_MIN, Z_MAX)  # 위아래

    return np.array([rx, ry, rz, HOME_RX, HOME_RY, HOME_RZ])


def robot_connect():
    global robot, rc
    print(f"[ROBOT] 연결 중: {ROBOT_IP}")
    robot = rb.Cobot(ROBOT_IP)
    rc    = rb.ResponseCollector()

    if SIM_MODE:
        robot.set_operation_mode(rc, rb.OperationMode.Simulation)
        print("[ROBOT] 시뮬레이션 모드")
    else:
        robot.set_operation_mode(rc, rb.OperationMode.Real)
        print("[ROBOT] 실제 로봇 모드 ⚠")

    robot.set_speed_bar(rc, 0.3)
    robot.flush(rc)
    print("[ROBOT] 연결 완료 ✓")


def main():
    robot_connect()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((LOCAL_IP, LOCAL_PORT))
    sock.setblocking(False)
    print(f"\nUDP 수신 대기: {LOCAL_IP}:{LOCAL_PORT}")
    print("Quest 연결 대기 중...\n")

    while True:
        # 버퍼 비우기: 최신 패킷만 남기기
        latest = None
        while True:
            try:
                data, addr = sock.recvfrom(1024)
                latest = data
            except BlockingIOError:
                break

        if latest:
            try:
                msg = json.loads(latest.decode("utf-8"))
                pos = msg.get("position", {})
                qx  = float(pos["x"])
                qy  = float(pos["y"])
                qz  = float(pos["z"])

                target = quest_to_robot(qx, qy, qz)
                print(f"[HAND] Quest({qx:.3f},{qy:.3f},{qz:.3f}) → "
                      f"Robot({target[0]:.1f},{target[1]:.1f},{target[2]:.1f}) mm")

                robot.move_l(rc, target, MOVE_SPEED, MOVE_ACC)
                if robot.wait_for_move_started(rc, 0.5).type() == rb.ReturnType.Success:
                    robot.wait_for_move_finished(rc)

            except (json.JSONDecodeError, KeyError, ValueError) as e:
                print(f"[PARSE ERROR] {e}")

        time.sleep(0.01)  # 100Hz


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n종료")
        if robot:
            robot.task_stop(rc)
