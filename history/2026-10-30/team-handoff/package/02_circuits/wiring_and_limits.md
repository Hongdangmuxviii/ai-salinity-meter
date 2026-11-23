# 배선표 - 검증 전 회로 제안 R1

USB 전원, 공통 3.3V, SD 미사용 구성입니다. 문서 PDF를 함께 읽으세요.

| XIAO 핀 | GPIO | 기능 | 연결 |
| --- | --- | --- | --- |
| 3V3 | - | 공통 3.3V 전원 | ADS VCC, OLED VCC, ToF 3V3, 온도 VDD, 부저 + |
| GND | - | 공통 기준선 | 모듈 GND, 온도 GND, 버튼 반대편 |
| D0 | GPIO1 | 전극 구동 A | R1 1kΩ → E1; A2로 구동 전압 감시 |
| D1 | GPIO2 | 전극 구동 B | R2 1kΩ → E2; A3로 구동 전압 감시 |
| D2 | GPIO3 | 미사용 | 스트래핑 핀: 이번 배선에서는 비워 둠 |
| D3 | GPIO4 | 온도 DATA | DS18B20 DATA. 내장 4.7kΩ 풀업 실물 확인 |
| D4 | GPIO5 | I2C SDA | ADS SDA/D, OLED SDA, ToF SDA를 병렬 연결 |
| D5 | GPIO6 | I2C SCL | ADS SCL/C, OLED SCL, ToF SCL을 병렬 연결 |
| D6 | GPIO43 | 버튼 1 | 10kΩ 풀업 + 버튼 쪽 직렬 1kΩ; 누르면 LOW |
| D7 | GPIO44 | 버튼 2 | 10kΩ 풀업 + 버튼 쪽 직렬 1kΩ; 누르면 LOW |
| D8 | GPIO7 | 버튼 3 | SD SCK와 공유: SD 카드 제거·SD/SPI 비활성 |
| D9 | GPIO8 | 부저 제어 | 직렬 1kΩ → ONE005 S; S에 10kΩ 풀다운 |
| D10 | GPIO9 | 미사용 | SD MOSI와 공유; 이번에는 비워 둠 |

## ADC 입력

| 단자 | 노드 | 외부 저항 | 의미 |
| --- | --- | --- | --- |
| A0 / S | E1 | R3 10kΩ 경유 | E1 금속봉 쪽 전압 |
| A1 / S | E2 | R4 10kΩ 경유 | E2 금속봉 쪽 전압 |
| A2 / S | D0 구동 노드 | R5 10kΩ 경유 | R1 앞 전압 |
| A3 / S | D1 구동 노드 | R6 10kΩ 경유 | R2 뒤 전압 |

각 ADC S 입력에 BAT43 클램프 2개(총8개): 위쪽 A=ADC/K=3V3, 아래쪽 A=GND/K=ADC. K는 띠 있는 쪽. 모듈 내부 300Ω과 별개로 외부10kΩ을 사용합니다.

R1/R2=1kΩ 전극 전류 제한. R3~R6=10kΩ ADC 직렬. R7/R8=10kΩ D0/D1 풀다운. R9~R11=10kΩ 버튼 풀업. R12~R14=1kΩ 버튼 직렬. R15=1kΩ 부저 S 직렬. R16=10kΩ 부저 S 풀다운.

DS18B20의 VDD/DATA/GND는 실물 표기와 대조하세요. 온도관은 E1/E2나 GND에 추가로 연결하지 않습니다. 내장4.7kΩ 풀업이 있으면 별도 풀업을 중복 설치하지 않습니다.

3.3V 모듈 VCC-GND 사이에 0.1µF 세라믹 각1개를 ADC/ToF/OLED 가까이에 놓습니다. 커넥터 색상은 보증되지 않으므로 실크와 도통으로 확인합니다.

## 구동·샘플링

50Hz/50% 상보 파형은 하드웨어 타이머로 생성하고 실제 파형을 확인합니다. 한 반주기10ms 안에서 같은 위상의4채널 단일변환을 완료하고 경계를 넘는 샘플은 폐기합니다. PGA±4.096V/860SPS는 시작 설정이며4채널 동시 측정이 아닙니다. 시작·종료·오류 때두핀LOW. 펌웨어는 이 패키지에 포함되지 않았습니다.

Vcell=A0-A1; Vdrive=A2-A3; I≈(Vdrive-Vcell)/(R1+R2); Rapp=Vcell/I. 저항성부하 가정이며 액체의 순수저항·염도%를 보장하지 않습니다.

## 전원 보류

배터리 모델·극성·충전허용전류가 미확정입니다. USB로 먼저 시험하고 배터리는 연결하지 않습니다. #2810을 충전선에 넣는 방식은 검증 전입니다. 생배터리를3V3/5V핀에 연결하지마세요.

## 출처

- S1: [Seeed XIAO ESP32-S3: 핀 배치·배터리 사용](https://wiki.seeedstudio.com/xiao_esp32s3_getting_started/)
- S2: [Seeed Sense: 카메라·SD 공유 핀](https://wiki.seeedstudio.com/xiao_esp32s3_pin_multiplexing/)
- S3: [DFRobot DFR0553: 단자·전원](https://wiki.dfrobot.com/dfr0553/)
- S4: [DFR0553 모듈 실제 회로: 입력 직렬 300Ω](https://dfimg.dfrobot.com/wiki/19356/DFR0553_gravity-ads1115-16-big-adc-module_schematics_V1.0.pdf)
- S5: [TI ADS1115: 입력 범위·860SPS·보호](https://www.ti.com/lit/ds/symlink/ads1115.pdf)
- S6: [SparkFun VL53L5CX: 전원·주소·풀업](https://learn.sparkfun.com/tutorials/qwiic-tof-imager---vl53l5cx-hookup-guide/all)
- S7: [ONE005 부저: 3.3~5V, HIGH 활성](https://m.one-stop.co.kr/goods/view_contents?no=17838&zoom=1)
- S8: [구매 온도센서 제품·외형 치수](https://www.devicemart.co.kr/goods/view?no=15584272)
- S9: [온도 프로브 판매처 치수 그림: Ø6×50mm](https://www.devicemart.co.kr/data/editor/temp_17309466766911.jpg)
- S10: [Analog Devices DS18B20: 3선 전원·1-Wire](https://www.analog.com/media/en/technical-documentation/data-sheets/ds18b20.pdf)
- S11: [P5/P6 O링 명목 치수](https://www.awimach.com/sealing/products/size/oring.php)
- S12: [Vishay BAT43: 소신호 쇼트키 다이오드](https://www.vishay.com/docs/85660/bat42.pdf)
- S13: [Vishay 1N5819: 정류용 부품 특성](https://www.vishay.com/docs/88525/1n5817.pdf)
- S14: [Pololu #2810 전원 스위치](https://www.pololu.com/product/2810)
- S15: [Espressif ESP32-S3 MCPWM](https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/peripherals/mcpwm.html)
- S16: [상용 전도도 센서: 측정면 전체 침수·기포](https://atlas-scientific.com/files/EC_K_10_probe.pdf)
