# AI 스마트 염도·부피 측정기

프로젝트의 코드, 원시 측정 기록, 보정표, 회로 자료, 3D 모델, 조립 의뢰 자료, 발표 자료와 사진을 보관하는 저장소입니다. 2026-11-24에 여러 작업 폴더의 관련 파일을 모았으며, 이전 버전도 보존했습니다.

## 현재 사용할 파일

| 항목 | 위치 |
|---|---|
| 기기에 올린 펌웨어 | [firmware/SalinityMeterCalibrated](firmware/SalinityMeterCalibrated) |
| 실제 저장된 보정표 | [CalibrationTable.h](firmware/SalinityMeterCalibrated/CalibrationTable.h) |
| 보정 모델과 기준값 | [calibration/current](calibration/current) |
| 보정 완료·확인 기록 | [보정표_저장완료_기록.txt](calibration/current/보정표_저장완료_기록.txt) |
| 해당 펌웨어 바이너리 | [firmware/releases/2026-11-24](firmware/releases/2026-11-24) |
| 최신으로 전달받은 회로 참고 이미지 R4-P2 | [hardware/original-R4-P2-images](hardware/original-R4-P2-images) |
| 헤드 CAD·STL 및 발표 자료 | [project-workspace/outputs](project-workspace/outputs) |
| 제작·측정 전체 이력 | [history](history) |
| 원본 위치·복사본 SHA-256·제외 내역 | [SOURCE_MANIFEST.json](SOURCE_MANIFEST.json) |

현재 프로그램은 `SALINITY_CAL_4P_V1`, 기기에서 읽어 확인한 보정표는 `REF_4P_20261124_V2`입니다. `history`의 이전 코드·설명·회로는 당시 자료이며, 현재 버전의 지시로 혼동하지 않아야 합니다.

## 확인된 상태

- XIAO ESP32-S3 Sense, ADS1115와 DS18B20을 사용합니다. 기존 헤드를 재사용하며, 실물 금속 봉의 돌출 길이는 약 10mm입니다.
- A0 측정 경로의 간헐적인 이상이 물 밖의 1kΩ 기준 부하에서도 관찰됐습니다. 물리적 원인을 확정·수리했다고 주장하지 않습니다. 현재 계산은 A0 값에 의존하지 않습니다.
- R1=R2=1kΩ인 설계에서 `C = 200 × (A1-A3)/(A2-A3)`로 전류 응답을 구합니다. A0 변환은 기존 샘플 시점을 유지하기 위해 남아 있지만 값은 계산에 사용하지 않습니다.
- `C`는 염도 %가 아닙니다. 세 획득의 중앙값을 구하고, 비교용 염도계의 0.5·0.6·1.1·2.0% 기준에 맞춘 단조 구간선형 표로 추정값을 만듭니다.
- 0.5·1.1%는 기존 원시 기록을 재계산한 기준입니다. 0.6·2.0%는 새 전류 응답으로 읽었고, 2.0% 상한점은 후속 확인값으로 한 번 조정했습니다.
- 최종 확인은 **같은 2.0% 기준액에서 2.01%**였습니다. 입력이 상한점보다 조금 높아 `ABOVE_REFERENCE_SPAN` 표시도 동반했습니다. 이는 동일 기준액의 반복 확인이며 독립적인 전체 구간 정확도 시험은 아닙니다.
- 온도 보상은 미적용입니다. 기준마다 기록 온도·시점이 다릅니다. 다른 온도·음식 성분·침수 조건에서의 정확도와 전체 OLED/ToF/버튼/배터리 통합 동작까지 검증한 것은 아닙니다.

## 하드웨어와 측정 연결

| XIAO/노드 | 연결 |
|---|---|
| D0 / GPIO1 | R1 1kΩ → 전극 E1 |
| D1 / GPIO2 | R2 1kΩ → 전극 E2 |
| E1 / E2 | 각각 R3 / R4 10kΩ → ADS A0:A / A1:A |
| D0 / D1 구동 노드 | 각각 R5 / R6 10kΩ → ADS A2:A / A3:A |
| D0 / D1 구동 노드 | 각각 R7 / R8 10kΩ → GND |
| D3 / GPIO4 | DS18B20 DATA, 노랑선 |
| D4 / GPIO5 | I2C SDA |
| D5 / GPIO6 | I2C SCL |
| 3V3 / GND | 센서 공통 전원·접지 |

ADS1115는 주소 `0x48`, 3.3V 전원, I2C 100kHz, `GAIN_ONE`, 860SPS를 사용합니다. DFR0553의 `A0:A`는 A0 행의 **A 신호 단자**이며, 같은 행의 `+/-` 전원 단자와 구별해야 합니다. DS18B20은 빨강=VDD, 검정=GND, 노랑=DATA입니다.

회로 이미지와 만능기판 의뢰서는 검토·제작 이력을 위한 자료입니다. R4-P2 전체 장치가 최종 조립·검증됐다는 의미는 아닙니다.

## 펌웨어 빌드와 명령

실제 사용한 환경:

- Arduino CLI 1.6.0
- ESP32 Arduino core 3.3.12
- Adafruit ADS1X15 2.6.2
- Adafruit BusIO 1.17.4
- OneWire 2.3.8
- DallasTemperature 4.0.5

해당 보드 패키지와 라이브러리가 설치된 환경에서:

```sh
arduino-cli compile --fqbn esp32:esp32:XIAO_ESP32S3:USBMode=hwcdc,CDCOnBoot=default firmware/SalinityMeterCalibrated
arduino-cli upload --fqbn esp32:esp32:XIAO_ESP32S3:USBMode=hwcdc,CDCOnBoot=default --port <PORT> firmware/SalinityMeterCalibrated
```

USB 시리얼은 115200 baud입니다.

| 명령 | 동작 |
|---|---|
| `m` | 세 획득의 중앙값으로 보정 염도 추정 출력 |
| `k` | 보정 전 전류 응답 한 획득 |
| `p` | 기기에 저장된 네 보정점 출력 |
| `t` | 온도만 읽기 |

`m`은 중간에 `CURRENT_RESULT` 세 줄을 내보낸 뒤 **`SALINITY_RESULT`**를 출력합니다. 첫 중간 결과에서 읽기를 끝내면 안 됩니다. 명령이 없거나 측정이 끝나면 구동 핀은 INPUT으로 해제합니다.

## 자료 구분

`history`는 원본을 바꾸지 않고 보존한 날짜별 아카이브입니다. 일부 제작 스크립트·설정에는 당시 PC의 절대 경로가 들어 있습니다. 현재 펌웨어는 위 독립된 폴더에서 빌드할 수 있지만, 과거 문서·이미지 생성 스크립트는 경로와 외부 실행환경을 조정해야 할 수 있습니다.

직접 만든 소스·모델·문서·측정 자료와 프로젝트별 빌드 산출물은 포함했습니다. `node_modules`, Arduino/ESP32 컴파일러 설치본, 라이브러리/오브젝트 캐시, 기존 `.git` 내부와 OS 임시 파일은 포함하지 않았습니다. 원래 전달된 초기 클립보드 도식 한 장은 현재 디스크에 없어 `unavailable_sources`에 기록했습니다.

관련 제조사 자료와 외부 라이브러리는 각 원저작자의 조건을 따릅니다. 이 저장소에 별도의 오픈소스 라이선스를 새로 부여하지 않았습니다.

복사본의 원본 일치 여부는 다음으로 확인할 수 있습니다:

```sh
python tools/verify_manifest.py
```
