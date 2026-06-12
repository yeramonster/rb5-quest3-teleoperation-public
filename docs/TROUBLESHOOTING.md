# Troubleshooting

개발 과정에서 마주친 문제들과 해결 방법을 정리했습니다. 비슷한 시스템을 만드는 분께 도움이 되길 바랍니다.

---

## 1. Unity: NativeWebSocket 네임스페이스 인식 실패

**증상**
```
error CS0246: The type or namespace name 'NativeWebSocket' could not be found
```
패키지를 설치하고 asmdef로 참조를 추가해도 해결되지 않음.

**해결**
NativeWebSocket 패키지를 포기하고 C# 내장 `System.Net.Sockets`를 사용. 외부 의존성을 없애 빌드 안정성도 확보.

---

## 2. Unity: OVRHand 컴포넌트 없음

**증상**
프로젝트가 Meta Interaction SDK 방식이라 `OVRHand` 컴포넌트를 직접 쓸 수 없었음.

**해결**
`OVRHand` 대신 `RightHandAnchor`의 Transform 위치를 직접 사용.

---

## 3. JSON 포맷 깨짐

**증상**
```json
{"position":{"x":0.0,"y":0.0,"z":F4}}
```
`z` 값이 `F4`로 깨져서 전송됨.

**원인**
C# 문자열 보간 `{pos.z:F4}` 처리 문제.

**해결**
```csharp
pos.z.ToString("F4")
```
명시적 변환 사용.

---

## 4. 로봇 명령 쌓임 [M561] (가장 큰 난관)

**증상**
```
[M561] 이전 동작이 종료되지 않은 시점에서 새로운 동작 명령이 수신되었습니다
```
손 데이터가 20Hz로 빠르게 들어오는데 `move_l`이 블로킹이라 명령이 쌓임. 프로그램을 종료하면 그제서야 로봇이 움직임.

**시도했으나 실패한 방법들**
- `task_stop` + `move_l` 반복 → 멈췄다 시작 반복으로 못 움직임
- `wait_for_move_finished` 추가 → 여전히 쌓임
- `eval` 스크립트 직접 전송 → 경고 그대로

**해결**
**WebSocket → UDP 전환.** UDP 소켓에서 수신 버퍼를 모두 비우고 **최신 패킷 1개만** 처리.

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

UDP는 신뢰성을 보장하지 않지만, 실시간 제어에서는 "최신 위치"만 중요하므로 오래된 패킷을 버리는 게 오히려 이상적.

---

## 5. 카메라: 텍스처 크기 불일치

**증상**
```
Graphics.CopyTexture called with mismatching texture data sizes
```
에러가 대량으로 발생.

**해결**
`Graphics.CopyTexture` 대신 `Texture2D.LoadImage()` 사용.

```csharp
_tex.LoadImage(req.downloadHandler.data);
```

---

## 6. 카메라: 회색/노란 화면 (셰이더 문제)

**증상 A** — Unity 에디터에서 Quad가 회색
URP `Lit` 셰이더 때문에 텍스처가 안 보임.

**증상 B** — Quest 빌드에서 노란 네모만 보이고 로그도 안 뜸

**원인** (logcat 분석으로 발견)
```
ArgumentNullException: shader
at RobotCamera.Start()
```
`Shader.Find("Unlit/Texture")`가 Quest 빌드에서 `null` 반환 → `Start()`가 중간에 죽어서 카메라 루프가 시작 안 됨.

**해결**
URP 셰이더 사용 + null 방어 코드 추가.

```csharp
Shader sh = Shader.Find("Universal Render Pipeline/Unlit");
if (sh == null) sh = Shader.Find("Unlit/Texture");
if (sh == null) sh = Shader.Find("Sprites/Default");
if (sh != null)
    displayMesh.material = new Material(sh);
```

---

## 7. HTTP 연결 차단 (Quest 빌드)

**증상**
```
InvalidOperationException: Insecure connection not allowed
```
에디터에선 카메라가 보이는데 Quest 빌드에서 `http://` 차단.

**해결**
1. `Player Settings → Allow downloads over HTTP → Always allowed`
2. `AndroidManifest.xml`의 `<application>`에 추가:
   ```xml
   android:usesCleartextTraffic="true"
   ```

---

## 8. 좌표 방향 반대

**증상**
손을 왼쪽으로 움직이면 로봇이 오른쪽으로 감.

**함정**
부호를 바꿔도 적용이 안 됐는데, 알고 보니 **실행 중인 파일이 아닌 다른 파일**(WebSocket 버전)을 수정하고 있었음.

**해결**
실제 동작 중인 `teleop_udp.py`에서 로봇 좌표계에 맞게 부호 조정.

```python
rx = clamp(HOME[0] - dx, X_MIN, X_MAX)
ry = clamp(HOME[1] - dz, Y_MIN, Y_MAX)
rz = clamp(HOME[2] + dy, Z_MIN, Z_MAX)
```

---

## 핵심 교훈

1. **외부 패키지보다 내장 기능** — NativeWebSocket 대신 C# 내장 소켓
2. **실시간 제어엔 UDP** — 명령 쌓임 문제의 결정적 해결책
3. **에디터 ≠ 빌드** — 셰이더 null처럼 빌드에서만 터지는 문제는 `adb logcat`으로 진단
4. **수정 중인 파일 확인** — 같은 기능의 파일이 여러 개면 실제 실행 파일을 확인할 것

### 디버깅 팁: adb logcat

Quest 앱의 런타임 로그 확인:

```powershell
adb logcat -c            # 기존 로그 삭제
adb logcat -s Unity      # Unity 로그만 보기
```
