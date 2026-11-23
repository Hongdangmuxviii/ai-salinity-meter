# 스마트 염도계 팀 인계 패키지 R1

작성일: 2026-10-30. 검증 전 설계 자료이며 상용 염도계 회로·방수 성능 인증이 아닙니다.

## 먼저 열 파일

- 스마트염도계_팀공유_설계검토본.pdf: 회로, 목록, 조립도, 시험 절차를 모은 설명서.
- 02_circuits/system_wiring.svg: 전체 연결 개요.
- 02_circuits/electrode_test_circuit.svg: 두 전극 시험 회로.
- 02_circuits/adc_clamp.svg: ADC 입력 보호 다이오드 방향.
- 02_circuits/buttons_buzzer.svg: 버튼과 부저 상세.
- 02_circuits/wiring_and_limits.md: 팀원이 배선할 때 보는 표.
- 04_parts/parts_list.md: 구매 기록과 추가·미확정 부품을 구분한 목록.
- 03_assembly/mvp_layout_concept.svg: 본체 배치 개념. 출력 파일 아님.
- 03_assembly/exploded_preview.png: 현재 헤드의 분해 조립도.
- 03_assembly/assembly_steps_current.md: 너트 삽입 순서를 명확히 한 이번 인계용 조립 순서.

## 3D 출력 파일

01_models 안의 holder/cap_core/seal_retainer STL 각1개가 헤드 본체입니다.
tip_alignment_jig는 조립 중에만 쓰는 높이 맞춤 받침이며 fit_coupon은 먼저 출력할 구멍 시험판입니다.
세 본체와 받침은 한 판에 층별 출력할 수 있으나, 처음에는 구멍 시험부터 하세요.
SCAD는 수정 원본입니다. 기본 part="holder"라 한 부품만 보이며 part="assembly"는 조립 확인용입니다.
gasket_cut_template SVG/DXF는 1mm 실리콘 절단용입니다. 플라스틱으로 패킹을 출력하는 것이 아닙니다.

## 꼭 공유할 제한

1. 과거 회로 및 이번 회로는 실장·염수 성능 검증 전입니다. 원시 전압·온도부터 기록하세요.
2. 이번 GPIO 배치는 SD와 겹칩니다. SD 카드를 빼고 SD/SPI를 사용하지 않습니다.
3. BAT43 다리형 8개가 추가 제안 부품입니다. 보유1N5819를 검증 없이 대체하지 마세요.
4. 배터리 모델/극성/충전전류/커넥터가 미확정이므로 USB로 먼저 시험합니다.
5. 현재 헤드는 1mm 실리콘 시트 기준입니다. 실란트 대체안은 CAD/공정 검증에 반영되지 않았습니다.
6. 헤드 CAD는 기존 파일을 그대로 복사했습니다. 전체 케이스와 헤드-본체 결합부는 미설계입니다.
7. 실물 누수와 식품 접촉은 미검증입니다. 음식·뜨거운 국물·장시간 침수에 사용하지 않습니다.

구매 상태는 대화의 주문·보유 기록 기준이며 미확정 품목을 구매 완료로 처리하지 않았습니다.
manifest.json에는 파일 해시와 STL 기본 형상 재검사 결과가 들어 있습니다.
