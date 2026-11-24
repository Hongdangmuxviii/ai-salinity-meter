AI 염도계 펌웨어 R7.1 / 실제 빌드 완료 / 2026-11-24
배선은 R7(99패드/71개 전선) 그대로 사용합니다.
수정: setup 첫 부분 pinMode(D9, OUTPUT); 다음 digitalWrite(D9, LOW);. 부팅 순간 부저음 허용, 정상 실행에서는 LOW 무음 지령. 측정식·보정표·USB m/k/t/p 명령은 유지. 배터리잔량표시 없음, SD미사용, Sense무개조.

사용 파일
- SalinityMeterCalibrated 폴더: 수정 소스와 기존 CalibrationTable.h
- SalinityMeterCalibrated.ino.bin: 앱 바이너리, 주소0x10000
- SalinityMeterCalibrated.ino.merged.bin: Arduino CLI가 생성한8MB 통합 이미지, 주소0x0
- build-info.json: 실제 버전·옵션·해시·빌드결과
- compile.log / image-info.txt: 빌드 및 이미지 검증 기록

조립 담당자가 업로드할 때
1. XIAO ESP32-S3 Sense 내장USB-C를 데이터 케이블로 연결. 장치 포트를 확인합니다.
2. 소스 폴더를 Arduino IDE로 열고 ESP32코어3.3.12/보드XIAO_ESP32S3를 선택합니다. USB Mode=Hardware CDC and JTAG, USB CDC On Boot=Enabled. 나머지는 보드 기본설정(8MB Flash)입니다. 라이브러리 버전은build-info.json과 같습니다.
3. CLI 사용 시 저장소 루트에서:
   arduino-cli compile --fqbn esp32:esp32:XIAO_ESP32S3:USBMode=hwcdc,CDCOnBoot=default firmware/SalinityMeterCalibrated
   arduino-cli upload --fqbn esp32:esp32:XIAO_ESP32S3:USBMode=hwcdc,CDCOnBoot=default --port <실제포트> firmware/SalinityMeterCalibrated
   ESP32용 업로더에서 통합이미지를 사용하는 경우에는 merged.bin을0x0에 씁니다. 앱bin을0x0에 쓰지 않습니다. 파일해시는build-info.json으로 확인합니다.
4. 115200bps 시리얼에서READY 확인, p로보정표확인, k/m/t로기존측정명령확인. 부팅순간소리는허용하며정상실행에서부저LOW무음확인. 외함닫고USB삽입/데이터/업로드/ON충전은기존실물검사표대로검사합니다.

이 환경에서는XIAO USB장치가연결되지않아기기업로드·통전·부저·충전검사는미실시입니다. 빌드성공을실물검사합격으로표시하지않습니다. OneWire2.3.8의기존#undef경고2건은로그에남겼고라이브러리는임의수정하지않았습니다.
