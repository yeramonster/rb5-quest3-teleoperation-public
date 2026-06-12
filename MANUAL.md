# MANUAL — 설치 및 실행 가이드

이 문서는 시스템을 직접 설치하고 실행하기 위한 매뉴얼입니다. 프로젝트 개요와 기술적 설명은 [README](README.md)를 참고하세요.

---

## 목차

1. [사전 요구사항](#1-사전-요구사항)
2. [네트워크 구성](#2-네트워크-구성)
3. [Linux PC 설정](#3-linux-pc-설정)
4. [Unity 설정](#4-unity-설정)
5. [실행 순서](#5-실행-순서)
6. [좌표 방향 튜닝](#6-좌표-방향-튜닝)
7. [자주 발생하는 문제](#7-자주-발생하는-문제)

---

## 1. 사전 요구사항

| 항목 | 내용 |
|------|------|
| Linux PC | Ubuntu 22.04, Python 3.10+ |
| Windows PC | Unity 2022.3 LTS, Meta XR SDK |
| 로봇 | RB5-850 (rbpodo 제어 가능 상태) |
| 디바이스 | Meta Quest 3 |
| 네트워크 | Quest-PC 동일 Wi-Fi, PC-로봇 유선 LAN |

---

## 2. 네트워크 구성

| 항목 | 값 | 비고 |
|------|-----|------|
| 로봇 IP | `<ROBOT_IP>` (예: `172.16.x.x`) | 유선 LAN |
| Linux PC IP | `<PC_IP>` (예: `192.168.x.x`) | Wi-Fi, Quest와 동일망 |
| UDP 포트 | `5159` | 손 위치 전송 |
| HTTP 포트 | `8080` | 카메라 영상 |

> Linux PC는 Wi-Fi(Quest용)와 유선 LAN(로봇용) 두 네트워크에 동시 연결되어 중계 역할을 합니다. IP는 환경에 맞게 수정하세요.

---

## 3. Linux PC 설정

### 3.1 패키지 설치

```bash
python3 -m venv venv
source venv/bin/activate
pip install rbpodo numpy flask opencv-python
```

### 3.2 방화벽 포트 개방

```bash
sudo ufw allow 5159/udp
sudo ufw allow 8080
```

### 3.3 연결 확인

```bash
ping <ROBOT_IP>       # 로봇 연결 확인
ls /dev/video*        # 웹캠 확인 (/dev/video0)
```

### 3.4 서버 설정값 수정

`python/teleop_udp.py` 상단의 설정을 환경에 맞게 조정합니다.

```python
ROBOT_IP = "<ROBOT_IP>"            # 로봇 유선 LAN IP로 변경
SIM_MODE = True                    # 첫 테스트는 True 권장, 실제 로봇 사용 시 False
HOME = [127.0, -684.0, 276.0]      # 로봇 시작 TCP 위치 (펜던트에서 확인)
SCALE = 500.0                      # 손 1m 이동 = 로봇 500mm 이동

# 작업공간 제한 (mm) — 안전을 위해 좁게 시작
X_MIN, X_MAX = -100.0, 400.0
Y_MIN, Y_MAX = -900.0, -400.0
Z_MIN, Z_MAX = 50.0, 500.0

MOVE_SPEED = 300.0
MOVE_ACC   = 500.0
```

> `HOME` 값은 로봇 펜던트에서 현재 TCP 위치를 읽어 입력하세요. 작업공간 제한은 처음엔 좁게 설정하고 점차 넓히는 것을 권장합니다.

---

## 4. Unity 설정

### 4.1 Player Settings

`Edit → Project Settings → Player → Android`

- **Other Settings → Allow downloads over HTTP**: `Always allowed`
- **Publishing Settings → Custom Main Manifest**: 체크

### 4.2 AndroidManifest.xml

`Assets/Plugins/Android/AndroidManifest.xml`의 `<application>` 태그에 추가:

```xml
<application ... android:usesCleartextTraffic="true">
```

### 4.3 스크립트 연결

**HandSender.cs**
1. 빈 GameObject 생성 → `HandSender` 스크립트 부착
2. Inspector 설정:
   - `Server IP`: Linux PC의 Wi-Fi IP
   - `Server Port`: `5159`
   - `Right Hand Anchor`: Hierarchy의 `RightHandAnchor` 드래그

**RobotCamera.cs**
1. `3D Object → Quad` 생성 (이름: `CameraScreen`)
2. Transform: Position `(0, 0, 2)`, Scale `(1.6, 0.9, 1)`
3. `RobotCamera` 스크립트 부착
4. Inspector 설정:
   - `Snapshot Url`: `http://<PC_IP>:8080/snapshot`
   - `Display Mesh`: 자동 연결됨 (비어 있어도 동작)

### 4.4 빌드

Quest를 USB로 연결 후 `File → Build Settings → Build And Run`

---

## 5. 실행 순서

### 5.1 Linux PC — 서버 2개 실행 (터미널 2개)

```bash
# 터미널 1 — 로봇 제어
cd ~/your-project-dir && source venv/bin/activate
python3 -u teleop_udp.py

# 터미널 2 — 카메라
cd ~/your-project-dir && source venv/bin/activate
python3 -u camera_server.py
```

### 5.2 카메라 동작 확인

Windows 브라우저에서 접속:
```
http://<PC_IP>:8080/stream
```
영상이 보이면 정상입니다.

### 5.3 Quest 실행

1. Quest 착용
2. 빌드된 앱 실행
3. XR 공간에 로봇 카메라 영상 확인
4. 손을 천천히 움직여 로봇 추종 확인

> ⚠️ **안전 주의**: 첫 실행 시 로봇 펜던트 속도를 30% 이하로 낮추고, 비상정지 버튼을 준비한 상태로 테스트하세요.

---

## 6. 좌표 방향 튜닝

로봇 좌표계는 모델·설치 방향마다 다릅니다. 펜던트에서 +X, +Y, +Z 방향을 확인한 뒤 `teleop_udp.py`의 `quest_to_robot()` 함수에서 부호를 조정합니다.

본 프로젝트 로봇 기준 (+X=왼쪽, +Y=뒤, +Z=위):

```python
rx = clamp(HOME[0] - dx, X_MIN, X_MAX)   # 좌우
ry = clamp(HOME[1] - dz, Y_MIN, Y_MAX)   # 앞뒤
rz = clamp(HOME[2] + dy, Z_MIN, Z_MAX)   # 위아래
```

특정 축이 반대로 움직이면 해당 줄의 부호(`+`/`-`)를 바꾸세요.

---

## 7. 자주 발생하는 문제

| 증상 | 확인 사항 |
|------|-----------|
| Python에서 "연결 대기중"만 뜸 | Unity Server Port가 5159인지, 같은 Wi-Fi인지 확인 |
| 카메라 사이트 안 열림 | Linux `ufw allow 8080`, Windows 방화벽 인바운드 허용 |
| Quest에서 노란 네모 | URP 셰이더 적용 후 재빌드 필요 |
| 로봇이 종료 시에만 움직임 | UDP 최신 패킷 처리 방식인지 확인 |
| 좌우 반대로 움직임 | 실행 중인 파일이 teleop_udp.py가 맞는지 확인 후 부호 조정 |

상세한 문제 해결 기록은 [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)를 참고하세요.

### 디버깅 — adb logcat

Quest 앱의 런타임 로그 확인:

```powershell
adb logcat -c            # 기존 로그 삭제
adb logcat -s Unity      # Unity 로그만 보기
```
