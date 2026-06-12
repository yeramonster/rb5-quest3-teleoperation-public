# RB5-850 × Meta Quest 3 — XR 핸드트래킹 텔레오퍼레이션

> Meta Quest 3 XR 장비의 핸드트래킹 데이터로 RB5-850 6축 한팔로봇을 실시간 원격제어하는 텔레오퍼레이션 시스템
>
> *Real-time teleoperation of a Rainbow Robotics RB5-850 6-DOF arm using Meta Quest 3 XR hand-tracking*

Meta Quest 3를 착용한 사용자가 손을 움직이면, 그 핸드트래킹 데이터가 RB5-850 한팔로봇에 실시간 전달되어 로봇 팔이 손동작을 그대로 따라옵니다. 동시에 로봇에 장착된 카메라 영상을 XR 공간에서 보면서 작업하므로, 별도의 조작 장치 없이 손동작만으로 로봇을 원격 제어할 수 있습니다.

<!-- 데모 GIF를 여기에 넣으세요. 포트폴리오에서 가장 중요한 부분입니다. -->
<!-- ![demo](docs/images/demo.gif) -->
**▶ 데모 영상:**

---

## 핵심 요약

| | |
|---|---|
| **무엇을** | XR 핸드 트래킹 기반 로봇 원격 제어 시스템 |
| **어떻게** | Quest 손 좌표 → UDP → 좌표 변환 → 로봇 모션 명령 |
| **사용 기술** | Unity, C#, Python, rbpodo, OpenCV, Flask, UDP/HTTP |
| **결과** | 손 움직임 실시간 추종 + XR 로봇 시점 영상 구현 완료 |

---

## 시스템 아키텍처

<img width="700" alt="architecture png" src="https://github.com/user-attachments/assets/fa77c94b-ea33-435b-9fb8-e0d00053f028" />

세 개의 노드로 구성됩니다. Quest와 연동된 Unity(Windows)가 손 위치를 보내고 로봇 영상을 받으며, Linux PC가 좌표 변환과 로봇 제어를 중계하고, RB5-850이 실제 동작을 수행합니다.

- **제어 신호**: Quest 손 위치 → Unity → UDP(5159) → Linux PC → rbpodo → 로봇
- **영상**: 로봇 카메라 → Flask HTTP(8080) → Unity → XR 화면

---

## 동작 흐름

<img width="700" alt="flow png" src="https://github.com/user-attachments/assets/9c4c1170-60ef-4ff8-b6e2-a7d7a0a95528" />

핸드 트래킹 데이터가 20Hz로 들어오면, 수신 버퍼에서 **최신 패킷 1개만** 골라 로봇 좌표로 변환하고, 작업공간 범위로 제한한 뒤 로봇에 전달합니다. 이 루프가 실시간으로 반복됩니다.

---

## 기술적 도전과 해결

이 프로젝트에서 가장 의미 있었던 문제 해결 과정입니다.

<img width="700" alt="challenges png" src="https://github.com/user-attachments/assets/fa351dbc-a38a-4b20-865e-23b3348f42a5" />

### 1. 실시간 제어 시 명령이 쌓이는 문제 (가장 큰 난관)

**문제** — 손 데이터가 20Hz로 빠르게 들어오는데, 로봇 제어 함수(`move_l`)가 목표 도달까지 대기하는 블로킹 방식이라 명령이 큐에 계속 쌓였습니다. 로봇이 동작 중엔 멈춰 있다가 프로그램을 종료해야 그제서야 움직이는 현상이 발생했습니다. (펜던트 [M561] 경고)

**시도** — `task_stop` 반복, `wait_for_move_finished` 추가, `eval` 직접 전송 등을 시도했으나 모두 실패.

**해결** — 통신을 **WebSocket에서 UDP로 전환**하고, 수신 버퍼를 비운 뒤 **가장 최신 패킷 하나만** 처리하도록 구현했습니다. UDP는 신뢰성을 보장하지 않지만, 실시간 제어에서는 "가장 최근의 손 위치"만 유효하므로 오래된 패킷을 버리는 것이 오히려 이상적인 동작입니다.

```python
# 버퍼 비우기: 최신 패킷만 남기기
latest = None
while True:
    try:
        data, addr = sock.recvfrom(1024)
        latest = data
    except BlockingIOError:
        break
```

### 2. Quest 빌드에서만 발생한 셰이더 오류

**문제** — Unity 에디터에선 카메라 영상이 정상인데, Quest로 빌드하면 노란 네모만 보이고 로그도 안 떴습니다.

**진단** — `adb logcat`으로 런타임 로그를 분석해 원인을 찾았습니다.
```
ArgumentNullException: shader → RobotCamera.Start()
```
`Shader.Find("Unlit/Texture")`가 빌드 환경에서 `null`을 반환해, `Start()`가 중간에 종료되어 카메라 루프가 시작되지 못한 것이었습니다.

**해결** — URP 셰이더를 우선 사용하고, 실패 시 단계적으로 대체하는 **null 방어 코드**를 추가했습니다.
```csharp
Shader sh = Shader.Find("Universal Render Pipeline/Unlit");
if (sh == null) sh = Shader.Find("Unlit/Texture");
if (sh == null) sh = Shader.Find("Sprites/Default");
```

### 3. 그 외 해결한 문제들

- **Unity 패키지 의존성** — NativeWebSocket 인식 실패 → C# 내장 소켓으로 대체
- **HTTP 차단** — Android cleartext 정책 → Manifest에 `usesCleartextTraffic` 추가
- **좌표 방향 정합** — 로봇 좌표계(+X=왼쪽, +Y=뒤, +Z=위)를 펜던트로 확인 후 축 매핑

전체 시행착오 기록은 [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)에 정리했습니다.

---

## 배운 점

- **실시간 제어에는 UDP가 적합** — "최신 상태만 유효"한 제어 특성과 UDP의 비신뢰성이 오히려 부합한다는 것을 체득
- **에디터 ≠ 빌드 환경** — 빌드에서만 터지는 문제는 `adb logcat` 같은 디바이스 로그로 진단해야 함
- **외부 패키지보다 내장 기능** — 의존성을 줄이는 것이 빌드 안정성에 유리

---

## 기술 스택

`Unity 2022.3` · `C#` · `Python` · `rbpodo` · `OpenCV` · `Flask` · `Meta XR SDK` · `UDP` · `HTTP/MJPEG`

---

## 프로젝트 구조

```
.
├── README.md                # 프로젝트 개요 (현재 문서)
├── MANUAL.md                # 설치 및 실행 매뉴얼
├── python/
│   ├── teleop_udp.py        # 손 위치 수신 → 로봇 제어
│   └── camera_server.py     # 웹캠 HTTP 스트리밍
├── unity/
│   ├── HandSender.cs        # Quest 손 위치 UDP 전송
│   └── RobotCamera.cs       # 로봇 카메라 영상 XR 표시
└── docs/
    ├── TROUBLESHOOTING.md   # 시행착오 상세 기록
    └── images/              # 다이어그램, 데모
```

**설치하고 직접 실행하려면 → [MANUAL.md](MANUAL.md)**

---

## 향후 개선 방향

- 양손 트래킹 및 그리퍼 제어 추가
- 손 회전(자세) 정보를 로봇 TCP 자세에 반영
- 네트워크 지연 보상 및 안전 정지 로직 고도화
