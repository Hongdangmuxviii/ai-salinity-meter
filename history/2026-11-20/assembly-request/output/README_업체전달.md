# 조립업체 전달 사항 / ASM-R3 / 2026-11-20

보유 모듈을 사용해 스마트 염도계 시제품 1대를 배선 조립하는 의뢰 자료입니다. PDF S01~S03은 실제 외부 연결 회로이며 A01~A03은 연결표, BOM, 검수 기준입니다. netlist.csv가 핀-전기망 정의이고 wire_connections.csv는 그 연결 확인표입니다. 실물의 모듈 핀 순서를 임의로 정한 배치도가 아닙니다.

## 견적 요청 범위

사용자가 제공하는 모듈·기존 헤드를 재사용하고 저항 16개와 커패시터 3개를 캐리어 기판에 조립해주세요. 배터리는 DTP803040 3.7V 1000mAh입니다. 모듈 연결 하네스, J1 상대 커넥터 극성 확인, J2/J3 단자대, 배선 절연·고정, 통전 검사와 실제 회로 기록을 포함해주세요. 조립 작업, 소모 자재, 별도 PCB 설계가 필요한 경우 그 비용, 외함 체결, 통합 펌웨어 비용을 구분해 견적해주세요.

## 전기적 조건

- 배터리 + → U2 VIN, U2 VOUT → XIAO BAT+. 음극과 모든 GND 공통.
- U2의 ON과 SW_EXT는 외부 배선 없음. 내장 스위치로 조작.
- USB 충전은 스위치 ON에서 진행. OFF 충전/USB 연결 상태 완전 전원 차단은 이 회로의 요구 기능이 아님.
- 주변 모듈은 모두 XIAO 3V3 공급. 5V 핀은 미사용.
- XIAO D번호와 ESP32 GPIO 번호를 혼동하지 말 것.
- D0=GPIO1, D1=GPIO2, D3=GPIO4, D4=GPIO5, D5=GPIO6, D6=GPIO43, D7=GPIO44, D8=GPIO7, D9=GPIO8.
- SD 카드와 SD/SPI 기능은 사용하지 않음. 카메라 기존 전용 결합 유지.
- J1 B+/B-는 논리 이름이며 실제 커넥터 cavity 번호를 의미하지 않음. 실제 극성 확인 후 +선과 -선을 라벨링.
- J2 1/2, J3 1/2/3은 업체가 조립 기판에 부여할 순서다. 위에서 본 임의의 왼쪽/오른쪽이 아니라 단자 라벨로 납품.
- U3의 아날로그 입력 표기 A0:A는 A0 행의 A 신호 접점이라는 뜻. +/−는 입력 신호가 아님. U3 완제품 내부 회로를 개조하지 않음.
- U6은 기존에 확인한 4.7kΩ 풀업 내장형. 같은 외부 풀업 추가 없음.
- R1/R2는 각 1kΩ 전류 제한, R3~R6은 ADC 입력 직렬 10kΩ, R7/R8은 구동 10kΩ 풀다운.
- R9~R11은 버튼 10kΩ 풀업, R12~R14는 버튼 1kΩ 직렬, R15는 부저 S 직렬 1kΩ, R16은 S 풀다운 10kΩ.
- C1=ADC, C2=OLED, C3=ToF의 0.1µF VCC-GND 바이패스. 모듈에 가깝게 실장.
- BAT43, 1N5819, 외부 4.7kΩ는 이번 버전에 미실장. 외부 전원 오접속/ESD 보호가 추가 검증된 회로라는 뜻은 아님.

## 시험 소스 범위

test_firmware/HeadWaterTest.ino는 기존 전극·온도 시험 소스이며 완성 제품 UI 펌웨어가 아닙니다. Arduino의 해당 스케치 폴더 이름을 HeadWaterTest로 맞춰 사용합니다. OneWire, DallasTemperature, Adafruit ADS1X15/BusIO 라이브러리를 사용합니다. XIAO ESP32S3, USBMode=hwcdc, CDCOnBoot=default 기준이며 'cdc' 옵션은 해당 설치 버전에서 USB CDC 비활성 값이므로 혼동하지 마세요.

시리얼 115200에서 t=온도, m=온도+전극 양극성 시험입니다. I2C 100kHz, ADS1115 860SPS, GAIN_ONE. D0/D1 각각 약 20ms 펄스, 정지 시 입력. 완성 펌웨어도 이 전기 조건을 유지하고 OLED/ToF/버튼/부저 제어를 추가합니다. RAW 66.7은 염도 66.7%가 아닙니다. 보드 조립 검수와 염도 교정·인증은 구분합니다.

## 조립 확정 전에 대조할 실물 항목

배터리 PCM과 허용 방전전류/충전전류, 배터리 단자 실제 극성, OLED 커넥터 순서와 I2C 주소, 버튼 두 접점군, 모듈 전체의 순간 전류와 3.3V 안정성을 확인해주세요. 구매 기록만으로 위 항목이 통합 검증됐다고 간주하지 않습니다. 기존 외함 예상 크기 64×44×108mm는 기판 외형 강제 조건이 아닙니다. 케이스까지 함께 조립한다면 실제 부품 배치를 놓고 기판 외형과 커넥터 공간을 먼저 제안해주세요.

## 제조사 근거

- XIAO 전원/BAT/핀: https://wiki.seeedstudio.com/xiao_esp32s3_getting_started/
- XIAO Sense SD 공유 핀: https://wiki.seeedstudio.com/xiao_esp32s3_pin_multiplexing/
- Pololu #2810: https://www.pololu.com/product/2810
- 스위치 ON 시 양방향 통전: https://forum.pololu.com/t/soft-switch-2810-with-battery/18180/4
- DFR0553 단자: https://wiki.dfrobot.com/dfr0553/
- SparkFun SEN-19013 회로: https://cdn.sparkfun.com/assets/7/b/6/0/9/19013-Qwiic-ToF-Imager_-VL53L5CX-Mini_Schematic.pdf
- 온도센서 상품: https://www.devicemart.co.kr/goods/view?no=15584272
- 배터리 기존 확정 상품: https://www.devicemart.co.kr/goods/view?no=15337882
- ONE005 제조사: https://m.one-stop.co.kr/goods/view_contents?no=17838&zoom=1

ASM-R3는 이전 R2 외형 검토 자료를 대체하는 조립 의뢰용 전기 문서입니다. 위 기준을 변경하면 실제 수정 회로도와 BOM을 함께 납품해주세요.
