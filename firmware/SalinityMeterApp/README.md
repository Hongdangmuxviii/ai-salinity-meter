# SalinityMeterApp — 통합 펌웨어 R8.0 (R7 배선 그대로)

R7.1 측정 펌웨어(`SalinityMeterCalibrated`)의 염도 측정을 그대로 옮기고, 아래 기능을 붙였습니다. 흐름은 특허명세서 P2026-070의 S100~S700을 따릅니다.

- OLED(SSD1306 128×32) 화면, 버튼 3개, 부저
- ToF(VL53L5CX 8×8) 수면 거리 측정과 국물 부피 계산
- 카메라(XIAO ESP32-S3 Sense) 촬영
- 측정값과 사진을 BLE로 휴대폰에 전송

> **상태 (2026-11-24): 컴파일 통과, 실물 검증 전.** 아래 5절 환경에서 `--warnings all`로 빌드했고 이 스케치 코드에서는 경고가 없습니다. 플래시 759,698 B(22%), 전역 RAM 48,588 B(14%) (`broth` 명령 추가 후)입니다. 기기에 올려서 동작을 확인하는 것은 아직 하지 않았으므로 [검증 체크리스트](#6-검증-체크리스트)를 2번부터 진행해야 합니다.

## 1. 휴대폰 연동 방식 후보

| 후보 | 장점 | 단점 | 판단 |
|---|---|---|---|
| **BLE GATT (채택)** | 공유기 불필요, 저전력, iOS·Android 모두 지원. 특허 도 1의 "MCU 및 BLE 보드"와 일치 | 처리량이 낮음. VGA JPEG(약 30KB)는 약 1~3초 걸림 | **MVP 기본값.** 값·명령·사진을 모두 처리 |
| Wi-Fi SoftAP (기기가 AP) + HTTP/WebSocket | 빠름(사진 즉시 전송). 브라우저만으로도 시험 가능 | 연결 중 휴대폰 인터넷이 끊기고, 매번 Wi-Fi를 전환해야 함. 전력 소모 큼 | 사진·스트리밍이 많아지면 BLE 위에 추가 |
| Wi-Fi STA (집 공유기) + mDNS | 빠르고 휴대폰 인터넷도 유지 | 최초 Wi-Fi 설정(프로비저닝)이 필요. 같은 네트워크에서만 동작 | 가정 고정 설치형에 적합 |
| BLE + Wi-Fi 하이브리드 | 평소에는 BLE, 사진만 Wi-Fi로 고속 전송 | 구현·앱 복잡도가 가장 높음 | 2차 개선 후보 |
| 클라우드(MQTT/Firebase) | 원격 조회, 이력 동기화 | 서버·인터넷이 필수이고 지연이 있음 | 앱이 BLE로 받은 뒤 업로드하는 편이 단순함 |

BLE를 고른 이유는 세 가지입니다. 특허 구성과 같고, 주방에서 공유기 없이 바로 연결되며, 앱이 없어도 **nRF Connect / Serial Bluetooth Terminal 같은 범용 BLE 터미널 앱으로 지금 바로 시험**할 수 있습니다. 텍스트 채널은 Nordic UART Service 표준 UUID를 씁니다.

## 2. 버튼과 화면

KEY2(모드)를 짧게 누르면 화면이 **SALT → SCAN → TARGET → GUIDE → LINK** 순서로 바뀝니다. 화면 위쪽 오른쪽에는 마지막 온도와 블루투스 상태(`BT*`=휴대폰 연결됨)가 표시됩니다.

| 화면 | KEY1 측정 (짧게) | KEY3 저장 (짧게) | KEY3 길게 |
|---|---|---|---|
| SALT (S100/S300) | 염도 측정(약 4초) | 결과를 기기 이력에 저장 | 이력 전체를 휴대폰으로 전송 |
| SCAN (S200/S400) | ToF + 사진 촬영 후 전송 | ToF만 측정 | **빈 그릇 기준거리(Dfloor) 저장** |
| TARGET (S500) | 목표 +0.1%p | 목표 −0.1%p | — |
| GUIDE (S600/S700) | **투입 완료 → 재측정** | 결과 저장 | — |
| LINK | 휴대폰에 현재 상태 재전송 | 이력 전송 | — |

- KEY1을 길게 누르면 어느 화면에서든 염도를 측정합니다.
- KEY2를 길게 누르면 화면이 꺼집니다. 2분 동안 조작이 없어도 꺼지고, 꺼진 상태에서 처음 누르는 버튼은 화면만 켭니다.
- 부저: 클릭(누름), 짧게 2번(완료), 길게(오류), 3번 후 길게(목표 도달), 2번 중간 길이(경고: 범위 밖·불안정·반복 초과).
- GUIDE 화면 표시 예시
  - `+1.4g` / `SALT 0.62>0.80%`: 소금 1.4g 추가
  - `+180mL` / `WATER`: 물 180mL 추가
  - `ON TARGET`: 목표 도달
  - 부피를 모를 때는 `+3.0g/L`처럼 1L 기준 양을 표시

### 간 맞추기 순서 (특허 S100~S700)
1. 빈 그릇을 놓고 SCAN 화면에서 KEY3를 길게 눌러 바닥까지의 거리를 저장합니다. 그릇 치수는 휴대폰에서 `bowl` 명령으로 한 번 설정합니다.
2. 국을 담고 SCAN에서 KEY1을 누르면 수면 높이로 부피를 계산하고 사진을 전송합니다.
3. SALT에서 KEY1을 눌러 염도를 측정합니다.
4. TARGET에서 목표 염도를 맞춥니다.
5. GUIDE 화면에서 투입량을 확인합니다.
6. 소금이나 물을 넣고 저은 뒤 GUIDE에서 KEY1을 누르면 다시 스캔·측정합니다. ±0.05%p 안에 들어오면 `ON TARGET`이 뜹니다. 3회를 넘기면 "수동 조정 또는 보정 권장"을 표시합니다.

### 계산식
- 부피:
  - 원형(테이퍼) 용기는 원뿔대 공식, 사각 용기는 가로×세로×H로 계산합니다. 수면 높이는 `H = Dfloor − Dsurface`입니다.
  - `Dsurface`는 8×8 깊이맵 중앙 4×4 영역 유효값의 중앙값입니다. 유효값이 4개 미만이면 전체 유효 영역을 씁니다.
  - 건더기 보정은 `Vbroth = Vtotal × (1 − α·γ)`입니다. α(건더기 면적비)는 휴대폰 앱이 사진을 분석해 `solids` 명령으로 보내줍니다. 기본값 α=0은 보정 없음입니다.
- 수학식 1: `Wsalt[g] = (Starget − Scurrent) × Vbroth[L] × K`, K=10
- 수학식 2: `Vwater = Vbroth × (Scurrent / Starget − 1)`

## 3. 측정 동작 — R7.1 대비 바뀐 것과 유지한 것

**유지한 것**
- 펄스 타이밍, ADS 채널 순서, 검증 한계값, 3회 중앙값, 보정표 `REF_4P_20261124_V2`
- 시리얼 명령 `m`/`k`/`t`/`p`와 출력 줄(`PHASE`, `CURRENT_RESULT`, `SALINITY_RESULT`, `TEMP`, `CAL_*`)

**측정 중 조건을 보정 당시와 맞추기 위한 처리**
- I2C를 **보정 당시와 같은 100kHz·타임아웃 5ms**로 바꾼 뒤 측정하고, 끝나면 400kHz로 되돌립니다. 응답값이 시간에 따라 변하기 때문입니다.
- 측정 중에는 카메라 전원(XCLK)을 끄고, ToF는 대기 상태로 둡니다. 부저는 소리를 멈추고, OLED·BLE 통신도 하지 않습니다.

**새로 추가한 보정 (기본값은 모두 꺼짐)**
- 온도보정: `S = S_T / (1 + β(T − 20℃))`.
  - 기준온도를 25℃가 아닌 20℃로 둔 이유: 현재 보정표가 19~22℃에서 온도보정 없이 만들어졌기 때문입니다.
  - β는 이 프로브로 실측한 뒤 `tcomp`로 켭니다.
- 셀상수 1점 보정: 농도를 아는 기준용액에 담그고 `cellcal 1.0`을 보내면 배율을 계산해 저장합니다(0.7~1.3 범위만 허용).
- 드리프트 경고: 3회 측정 인덱스의 편차가 0.8을 넘으면 `unstable`로 표시합니다. 보정 데이터의 편차(0.06~0.39)를 보고 잡은 **임시값**입니다.

> 보정표는 OLED·ToF·BLE가 없는 상태로 만들어졌습니다. 통합 펌웨어에서는 0.6%·2.0% 기준액으로 **재확인이 필요**합니다.

## 4. BLE 프로토콜

- 광고 이름: `SaltMeter-XXXX`
- MTU: 517까지 요청합니다. 실제 값은 휴대폰이 정합니다.

| 서비스 / 특성 | UUID | 방향 | 내용 |
|---|---|---|---|
| NUS 서비스 | `6E400001-B5A3-F393-E0A9-E50E24DCCA9E` | | |
| RX | `6E400002-…` | 휴대폰→기기 (Write) | 텍스트 명령. 한 줄에 명령 하나 |
| TX | `6E400003-…` | 기기→휴대폰 (Notify) | JSON 한 줄 + `\n`. MTU보다 길면 나뉘어 오므로 `\n`까지 이어 붙여야 함 |
| 이미지 서비스 | `5A17A000-6D2B-4E8C-9C3B-7E3F0A1C0001` | | |
| IMG | `5A17A001-…` | 기기→휴대폰 (Notify) | `[u16 imageId LE][u16 chunkIndex LE][JPEG 조각]` |

휴대폰이 TX 알림을 구독하면 기기가 `hello`, `settings`, 최근 결과를 자동으로 보냅니다.

### 기기 → 휴대폰 이벤트 (`type`)
| type | 주요 필드 |
|---|---|
| `hello` | fw, name, cal, 센서별 감지 여부(adc/tempSensor/oled/tof/camera), records |
| `salinity` | seq, pct(보고값), tablePct, index, tempC, span(`IN/BELOW/ABOVE_REFERENCE_SPAN`, `OUTSIDE_MODEL_DOMAIN`), trials[3], unstable, epoch |
| `tof` | surfaceMm, floorMm, fillMm, totalMl, solidsMl, brothMl, validZones, grid[64] (−1=무효) |
| `guide` | targetPct, currentPct, kind(`ADD_SALT/ADD_WATER/ON_TARGET/NO_DATA`), amount, unit, perLiter, brothMl, brothSource(`app`/`device`/`none`), stepRatio, round, reached, advise |
| `image_begin` / `image_end` | id, bytes, crc32(zlib), width, height, chunkBytes, chunks / sent, complete |
| `record`, `history_end` | 저장된 이력 |
| `settings`, `raw`, `temp`, `ack`, `error`(op, code, msg) | |

**사진 수신 방법**: `image_begin`을 받은 뒤 IMG 조각을 `chunkIndex × chunkBytes` 위치에 채웁니다. 빠진 조각은 `img <id> 3 17 42`로 다시 요청합니다(최신 사진만, 한 번에 10개까지). 마지막에 CRC32로 확인합니다.

### 휴대폰 → 기기 명령
```
measure | m            염도 측정 (k=원시 응답, t=온도, p=보정표)
scan [qvga|vga|svga|xga]   ToF + 사진    tof    ToF만    photo [size]   사진만
img <id> [chunk...]    사진 조각 재전송
target <pct>           목표 염도 (0.3~3.0)      guide   현재 가이드 다시 받기
recheck                투입 완료 → 재측정 (S700)
floor | floor <mm> | floor clear     빈 그릇 기준거리
bowl round <위지름> <바닥지름> <깊이>  |  bowl rect <가로> <세로> <깊이>   (mm)
solids <alpha> [gamma] 앱의 건더기 분석 결과 반영
tcomp <beta>           온도보정 계수 (0=끔)       cellcal <pct> | cellcal reset
saltk <K>              수학식1 계수 (기본 10)
broth <mL> [비율] | broth clear   앱이 계산한 국물량(카메라·ToF·역산 융합)과 1차 투입 비율. 30분간 기기 계산 대신 사용
save | history | history clear | time <unix초> | settings | status | beep | factory
```
USB 시리얼(115200)에서도 같은 명령을 쓸 수 있습니다. 시리얼에는 이벤트가 `EVT {json}` 형식으로 찍히고, USB로 요청한 사진은 `IMG_B64` 줄로 덤프됩니다. [tools/serial_client.py](../../tools/serial_client.py)를 쓰면 앱 없이도 사진을 jpg로 저장하고 CRC를 확인할 수 있습니다.

## 5. 빌드

R7.1 환경(Arduino CLI 1.6.0, ESP32 core 3.3.12, ADS1X15 2.6.2, BusIO 1.17.4, OneWire 2.3.8, DallasTemperature 4.0.5)에 아래를 추가합니다.

| 라이브러리 | 용도 |
|---|---|
| NimBLE-Arduino 2.5.2 | BLE |
| Adafruit SSD1306 2.5.17 + Adafruit GFX Library 2.0.0 | OLED |
| SparkFun VL53L5CX Arduino Library 1.0.3 | ToF |
| esp32-camera | 코어에 포함되어 있어 별도 설치 불필요 |

카메라 때문에 **PSRAM=OPI를 반드시 켜야** 합니다(R7.1과 다른 부분). 저장소 루트에서 실행합니다:
```sh
arduino-cli compile --fqbn esp32:esp32:XIAO_ESP32S3:USBMode=hwcdc,CDCOnBoot=default,PSRAM=opi firmware/SalinityMeterApp
arduino-cli upload  --fqbn esp32:esp32:XIAO_ESP32S3:USBMode=hwcdc,CDCOnBoot=default,PSRAM=opi --port <PORT> firmware/SalinityMeterApp
```
이 PC에서는 C: 공간이 부족해 빌드 환경 전체를 `E:\arduino`에 설치했습니다. 실행 파일, 코어, 라이브러리, 다운로드 캐시, 빌드 출력이 모두 여기에 있고 설정 파일은 `E:\arduino\arduino-cli.yaml`입니다:
```powershell
$env:TEMP='E:\arduino\tmp'; $env:TMP='E:\arduino\tmp'
E:\arduino\bin\arduino-cli.exe --config-file E:\arduino\arduino-cli.yaml compile --fqbn "esp32:esp32:XIAO_ESP32S3:USBMode=hwcdc,CDCOnBoot=default,PSRAM=opi" --build-path E:\arduino\build\SalinityMeterApp firmware/SalinityMeterApp
```
업로드할 때는 `compile`을 `upload --port COMx`로 바꿉니다.

Arduino IDE에서는 보드 XIAO_ESP32S3를 고르고 USB Mode=Hardware CDC and JTAG, USB CDC On Boot=Enabled, **PSRAM=OPI PSRAM**으로 설정합니다.

## 6. 검증 체크리스트

### 부분 조립 상태에서 먼저 할 수 있는 시험
부품이 빠져 있어도 펌웨어는 멈추지 않습니다. 없는 부품은 부팅 줄(`READY ... adc=0 oled=0 tof=0 …`)과 `hello` 이벤트에 0/false로 표시되고, 그 기능을 요청하면 `error` 이벤트만 나옵니다. 버튼은 내부 풀업을 켜 두었기 때문에 버튼 배선이 없어도 저절로 눌리지 않습니다.

| 단계 | 필요한 것 | 확인 내용 |
|---|---|---|
| A. XIAO 단독 | XIAO ESP32-S3 Sense(카메라 포함) + USB | 부팅 줄에 `camera=1 psram=1` 표시. `python tools/serial_client.py COMx "photo qvga"`로 jpg 저장과 CRC 일치 확인. 휴대폰 nRF Connect에서 `SaltMeter-XXXX`에 연결 → TX 구독 → RX에 `status`를 써서 `hello` JSON 수신 |
| B. 기존 브레드보드 + 헤드 | R7.1 보정 때와 같은 배선(D0/D1 구동, ADS1115 0x48, DS18B20 D3, I2C D4/D5) | **측정 동등성**: 같은 기준액에서 R7.1 펌웨어로 `m`을 여러 번, R8.0으로 `m`을 여러 번 측정해 `SALINITY_RESULT`의 index가 같은 범위인지 비교합니다. BLE `measure` → `salinity`/`guide` 수신, `target 1.0` → 가이드 계산 확인 |
| C. 부품이 도착하는 대로 | OLED → ToF → 버튼·부저 순서로 하나씩 연결 | 아래 2~8번 |

B 단계는 펌웨어 교체가 측정값을 바꾸지 않는지 확인하는 가장 중요한 시험입니다. R7.1 펌웨어는 원래 저장소의 `firmware/releases/R7.1-2026-11-24`에 있습니다.

### 전체 조립 후
1. ~~컴파일~~ 통과. 남은 경고는 OneWire 2.3.8의 `#undef` 경고 2건뿐이며 R7.1 빌드 기록과 같습니다. 실행 중 확인할 것: 코어 3.3.12에서 Wire(I2C0)와 카메라 SCCB(I2C1)가 함께 동작하는지.
2. **부팅**: `READY ... adc=1 temp=1 oled=1 tof=1 camera=1 psram=1`이 나오는지 확인합니다. ToF 펌웨어 업로드 때문에 부팅에 약 3초 걸립니다.
3. **측정 동등성**: 같은 기준액에서 R7.1과 R8.0의 `m` 결과(index)를 비교합니다. USB를 연결한 상태와 배터리만 쓰는 상태 모두에서 확인합니다. USB가 없을 때 `Serial.printf`가 지연되는지 확인하는 단계입니다.
4. **버튼**: KEY1(GPIO43)은 부팅 중 UART0 TX로 쓰입니다. 부팅 뒤 짧게·길게 누름이 정상인지 확인합니다.
5. **부저**: 평상시 무음, 패턴별 소리를 확인합니다.
6. **ToF**: 빈 그릇 기준거리 저장 → 물을 정해진 양(예: 300mL)만큼 부으며 `tof`의 brothMl을 확인합니다. 물 표면의 적외선 반사 때문에 유효 영역 수가 줄어드는지 봅니다.
7. **사진**: USB `scan`으로 jpg와 CRC를 확인합니다. BLE에서는 nRF Connect로 IMG 알림을 받아 봅니다.
8. **BLE**: nRF Connect에서 TX를 구독하고 RX에 `measure`를 써서 `salinity`·`guide` JSON을 받는지 확인합니다.

## 7. 파일
| 파일 | 내용 |
|---|---|
| `SalinityMeterApp.ino` | 상태, 명령 처리, 버튼 동작, 화면 구성, 부팅 |
| `SalinityProbe.*` | R7.1 측정 코드 이식(측정에 영향을 주는 부분은 원본 그대로) |
| `SaltModel.*` | 부피·투입량·온도/셀 보정 계산식 |
| `TofSensor.*`, `CameraCapture.*` | 센서 |
| `Display.*`, `Buttons.*`, `Buzzer.*` | 사용자 인터페이스 |
| `BleLink.*` | BLE |
| `Storage.*` | NVS 설정과 이력(30건) |
| `Config.h`, `JsonLine.h` | 핀·상수, JSON 생성 |
| `CalibrationTable.h` | R7.1에서 그대로 복사 |
