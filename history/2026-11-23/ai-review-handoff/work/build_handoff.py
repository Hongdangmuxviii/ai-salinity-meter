from pathlib import Path
import html, shutil, json, hashlib, zipfile
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4, A3
from reportlab.lib.colors import HexColor, white
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'output'
FONT=r'C:\Windows\Fonts\malgun.ttf'; BOLD=r'C:\Windows\Fonts\malgunbd.ttf'
pdfmetrics.registerFont(TTFont('K',FONT));pdfmetrics.registerFont(TTFont('KB',BOLD))
SOURCE=Path(r'C:\Users\Yeon\OneDrive - 한국공학대학교\바탕 화면\새 폴더 (3)')
attachments=[
 ('R4P2_01_overview.png','KakaoTalk_20261120_165634599.png','전체 실배선과 부품 배치'),
 ('R4P2_02_power.png','KakaoTalk_20261120_165635775.png','배터리 충전 전원 배선'),
 ('R4P2_03_electrode_adc.png','KakaoTalk_20261120_165636460.png','전극 저항 ADC 배선'),
 ('R4P2_04_communication_controls.png','KakaoTalk_20261120_165637533.png','통신 온도 버튼 부저 배선'),
 ('R4P2_05_battery_divider_correction.png','KakaoTalk_20261120_165639168.png','배터리 감시선과 접지선 정정 상세'),
]
manifest=[]
for dest,orig,title in attachments:
 src=SOURCE/orig;dst=OUT/'diagrams'/dest;shutil.copy2(src,dst)
 with Image.open(src) as im:sz=im.size
 manifest.append({'file':'diagrams/'+dest,'original':orig,'title':title,'pixel_size':sz,'sha256':hashlib.sha256(src.read_bytes()).hexdigest()})

# All prose and tables are shared by PDF and AI-readable text.
pages=[]
def page(title):
 p={'title':title,'blocks':[]};pages.append(p);return p['blocks']
def P(b,s):b.append(('p',s))
def H(b,s):b.append(('h',s))
def T(b,head,rows,widths):b.append(('table',head,rows,widths))
def B(b,s):b.append(('bullet',s))

b=page('프로젝트 목표와 검토 목적')
P(b,'이 문서는 휴대용 AI 염도·부피 측정기 MVP를 다른 AI 또는 전자회로 검토자에게 설명하기 위한 인계 문서다. 기존 대화를 보지 않아도 목표, 보유 부품, 측정 방식, 최신 배선 의도와 미검증 항목을 파악하고 회로를 독립적으로 검토할 수 있게 작성했다.')
P(b,'검토 대상은 사용자가 2026년 11월 23일 제공한 R4-P2 그림 5장이다. 그림에 적힌 작업 지시는 기존 설계 자료이며, 이 문서가 회로의 정확성이나 통전 안전성을 승인했다는 뜻은 아니다. 그림에서 읽은 연결 의도와 실제로 시험한 상태를 구분한다.')
H(b,'잡고 있는 제품 컨셉')
P(b,'전극 2개로 액체의 전기적 응답을 얻고 온도센서로 측정 온도를 함께 기록한다. 기준액으로 보정한 뒤 염도에 대응시키고, 화면과 버튼이 있는 배터리 내장 휴대 장치로 구현하는 것이 기본 방향이다. 기존 3봉 헤드와 이미 구매한 모듈을 재사용한다.')
P(b,'카메라와 다중 구역 ToF 센서를 함께 쓰는 염도·부피 측정기라는 확장 컨셉도 유지한다. ToF는 용기 내부 거리·깊이와 부피 추정의 보조 정보를 얻는 용도다. 카메라는 영상 정보를 얻는 부품으로 확보했다. 음식·용기 인식이나 보정에 AI를 구체적으로 어떻게 쓸지, 모델과 학습 데이터, 최종 추론 위치는 아직 확정·검증된 것으로 보지 않는다.')
H(b,'지금의 제작과 개발 범위')
T(b,['구분','현재 기준'],[
 ['제작 방식','2.54mm 독립 패드 만능기판에 저항과 단자 등을 납땜하고 기존 완제품 모듈을 하네스로 연결한다.'],
 ['사용자 조작','OLED 128×32, 버튼 3개, 부저. 측정·모드·저장은 제안된 버튼 역할이며 통합 펌웨어는 별도 개발 대상이다.'],
 ['전원','구매한 DTP803040 1셀 배터리와 Pololu #2810을 사용하고 XIAO USB 충전 기능을 이용하는 제안이다.'],
 ['완료 범위','기초 전극·온도 시험 기록은 있다. 전체 R4-P2 조립, 배터리 충전, 모든 모듈의 동시 동작과 염도 정확도는 검증 완료가 아니다.'],
 ],[94,421])
P(b,'검토의 핵심은 “선을 그렸는가”와 “이 구조로 원하는 값을 신뢰성 있게 측정할 수 있는가”를 함께 확인하는 것이다. 전기적 결선, 측정 원리, 보정 가능성과 제작성을 각각 판정해 달라.')

b=page('보유한 핵심 모듈과 센서')
P(b,'아래는 사용자 구매·보유 언급, 기존 부품 기록과 실험 사용 내용을 종합한 목록이다. 구매 기록은 현재 재고 수량, 수령품의 세부 변형이나 정상 동작까지 보증하지 않는다. 가격은 이번 검토 범위에서 제외했다.')
T(b,['부품','모델과 규격','수량과 상태'],[
 ['메인보드와 카메라','Seeed XIAO ESP32-S3 Sense. 카메라는 기존 Sense 보드 결합을 유지. 정확한 카메라 센서 리비전은 실물 확인.','1개 보유·기초 시험 사용'],
 ['외부 ADC','DFRobot Gravity ADS1115 DFR0553. 4채널 16비트 모듈.','1개 보유·기초 시험 사용'],
 ['거리 센서','SparkFun SEN-19013 Qwiic Mini ToF Imager / ST VL53L5CX.','1개 구매·보유 기록'],
 ['화면','SSD1306 0.91인치 OLED, I2C, 128×32, 4핀.','1개 구매·보유 기록'],
 ['온도센서','EM Tech DS18B20 프로브형 / 상품 15584272. 금속관 Ø6×50mm, 4.7kΩ 풀업 내장형으로 확인한 제품.','1개 보유·헤드에 사용'],
 ['측정 전극','SUS316L 스테인리스 환봉 Ø5mm.','2개 사용·기존 헤드에 결착'],
 ['리튬폴리머 배터리','DTP803040, 1셀 3.7V 1000mAh. 기존 확정 상품 15337882. 단자 표기는 Molex 51021-0200 / 2핀 / 1.25mm.','1개 구매 완료를 사용자 확인'],
 ['전원 스위치','Pololu Mini MOSFET Slide Switch LV #2810. 충전기나 배터리 PCM 자체가 아님.','1개 구매·보유 기록'],
 ['부저','ONE005 회로내장형 액티브 부저 모듈. 3.3V 공급, S 제어 제안.','1개 구매·보유 기록'],
 ['버튼','VLT-TSW015 택트, 12×12×10mm, 순간 NO 접점.','6개 구매 기록 중 3개 사용'],
 ['기존 케이블','Qwiic PRT-17912, ADS1115 동봉 Gravity 케이블. 배터리 상대 커넥터 관련 구매 언급도 있음.','정확한 짝과 극성은 수령품 확인'],
 ],[91,300,124])
P(b,'과거 추천 목록에 있었던 다른 용량의 배터리나 별도 TP4056, 별도 카메라 모듈을 현재 보유품으로 섞지 않는다. 배터리 모델은 위 DTP803040을 기준으로 검토한다.')

b=page('수동 부품과 기존 헤드의 제약')
T(b,['부품','구매 기록','R4-P2 도면의 필요량과 확인점'],[
 ['1kΩ 1% 1/4W','10개','R1·R2·R12~R15 = 6개. 실제 남은 재고는 재확인.'],
 ['10kΩ 1% 1/4W','10개','R3~R11·R16·R17·R18 = 12개. 기록상 구매량보다 2개 많아 추가 구매·여유분 확인 필요.'],
 ['4.7kΩ 저항','10개','기존 온도센서 내장 풀업 전제에서는 추가 실장하지 않는 안.'],
 ['0.1µF 50V 세라믹','10개','C1~C4 = 4개. C1~C3는 모듈 전원, C4는 배터리 ADC 필터.'],
 ['1N5819','10개','보유 기록은 있으나 최신 배선의 실장 부품으로 그려져 있지 않음.'],
 ['BAT43','미보유로 사용자 확인','이전 제안에 등장했으나 이번 최신 그림의 필수 실장품으로 보지 않음.'],
 ['C5 100µF','보유 확인 안 됨','R4-P2에 추가된 전원 커패시터. 정격전압·극성·형상·재고 확인 필요.'],
 ['단자와 잠금 하네스','제작·조달 확정 안 됨','J4~J10 소켓·플러그, 헤드 5핀 잠금 연결, 당김 방지와 라벨은 업체 작업 범위로 제안됨.'],
 ],[102,95,318])
H(b,'기존 헤드는 재사용한다')
P(b,'현재 캡형 헤드는 전극 2개와 온도센서 1개를 고정한 3봉 구조다. 아래 플라스틱 면에서 세 금속 끝이 각각 10mm만 나온다. 예전 40mm 또는 55mm 돌출 헤드를 기준으로 설명하거나 전체 봉을 새로 길게 노출시키면 안 된다.')
T(b,['항목','현재 설계·사용 기준'],[
 ['헤드 외형','기존 CAD의 하부 프레임 58×38mm. 바닥부터 상단까지 약 47.75mm.'],
 ['세 봉 배치','두 전극 중심 간격 20mm. 온도센서는 전극 열에서 뒤쪽으로 떨어진 배치. 정확한 형상은 기존 CAD 기준.'],
 ['기구 부품','M3×25 체결 볼트, M3×12 나일론 고정 나사, M3 너트, P5/P6 O링과 실리콘 패킹 관련 보유·설계 기록. 수량·재질은 실물 대조.'],
 ['측정 조건','침수 길이·온도·용기·위치·물양·기포·측정 시간을 통제해야 한다. 거치대의 8mm 잠김은 시험용 제안값이지 검증된 최적값은 아님.'],
 ],[95,420])
P(b,'멀티미터, USB 데이터 케이블, 빵판, 점퍼선, 악어클립과 나사 등의 보유 언급이 있다. 이들은 시험 도구 또는 조립 자재이며 최종 모듈 목록과 구분한다.')

b=page('최신 도면의 MCU 핀과 측정 회로')
P(b,'이하 연결표는 첨부 R4-P2의 논리 연결을 읽어 정리한 검토용 전사다. 새로 검증한 CAD 네트리스트가 아니다. 칩의 숫자 핀 번호 대신 XIAO의 D번호와 ESP32 GPIO 번호를 구분해서 확인한다.')
T(b,['XIAO 핀','GPIO','도면상 연결 의도'],[
 ['D0','1','전극 구동 A. R1·R5·R7의 공통 노드.'],['D1','2','전극 구동 B. R2·R6·R8의 공통 노드.'],
 ['D2','3','미사용. 기존안의 스트래핑 핀 고려를 유지.'],['D3','4','온도 DATA. J3.2와 센서 노랑선.'],
 ['D4','5','ADC·OLED·ToF 공통 I2C SDA.'],['D5','6','ADC·OLED·ToF 공통 I2C SCL.'],
 ['D6','43','측정 버튼 입력. R9 풀업과 R12 직렬.'],['D7','44','모드 버튼 입력. R10 풀업과 R13 직렬.'],
 ['D8','7','저장 버튼 입력. R11 풀업과 R14 직렬.'],['D9','8','R15를 거친 부저 S 제어.'],
 ['D10','9','R17·R18 분압과 C4 필터의 배터리 전압 감시.'],['3V3 / GND','-','주변장치 공통 3.3V와 GND. 5V 핀은 주변 센서 전원으로 쓰지 않는 안.'],
 ],[100,47,368])
H(b,'전극과 ADC 입력의 대응')
T(b,['부품','양 끝 연결'],[
 ['R1 1kΩ','D0 구동 노드 ↔ E1'],['R2 1kΩ','D1 구동 노드 ↔ E2'],
 ['R3 / R4 각 10kΩ','E1 → R3 → ADS A0:A / E2 → R4 → ADS A1:A'],
 ['R5 / R6 각 10kΩ','D0의 R1 앞 노드 → R5 → ADS A2:A / D1의 R2 앞 노드 → R6 → ADS A3:A'],
 ['R7 / R8 각 10kΩ','각 D0·D1 구동 노드 → GND 풀다운'],
 ],[125,390])
P(b,'DFR0553의 A0:A는 A0 행에 있는 A 신호 접점이라는 뜻이다. 같은 행의 +는 전원, -는 GND이며 전극 신호와 구분한다. 모듈의 D는 SDA, C는 SCL이다. 외부 I2C는 ADS=0x48, OLED=0x3C 또는 0x3D 실측, ToF=0x29를 전제로 제안됐다. [S1~S4]')

b=page('접속부와 그림의 연결 번호')
P(b,'R4-P2의 J번호는 이전 ASM-R3와 다르다. 다음 표는 최신 이미지 기준으로 읽은 기판측 논리 순서다. 실제 모듈의 물리 핀 좌우 순서와 같다고 단정하지 말고, 하네스 반대편은 실크와 맞춰야 한다.')
T(b,['접속부','도면의 핀 순서 또는 기능'],[
 ['P_B1 / P_SW / P_BAT','P_B1 1=배터리+ 2=GND. P_SW 1=VIN 쪽 2=VOUT 쪽 3=GND. P_BAT 1=XIAO BAT+ 쪽 2=BAT-·GND.'],
 ['J2 / J3','J2 1=E1, 2=E2. J3 1=센서 빨강 3V3, 2=노랑 DATA, 3=검정 GND.'],
 ['헤드 잠금 연결','전극 2선+온도센서 3선의 5핀 잠금 커넥터 쌍을 제작하는 의도. 결합 5핀의 최종 번호순은 이미지에 명시되지 않아 별도 확정 필요.'],
 ['J4 / J5 / J6','각 4핀. 1=3V3, 2=GND, 3=SDA, 4=SCL. 각각 ADC 전원·통신 / OLED / ToF.'],
 ['J7','ADC 센스 4핀. 1=A0(R3 뒤), 2=A1(R4 뒤), 3=A2(R5 뒤), 4=A3(R6 뒤).'],
 ['J8','버튼 4핀. 1=측정 버튼 접점선, 2=모드 접점선, 3=저장 접점선, 4=공통 GND.'],
 ['J9','부저 3핀. 1=3V3, 2=GND, 3=S(R15 뒤·R16 풀다운 노드).'],
 ['J10','BOOT·RESET 4핀. 1=BOOT, 2=GND, 3=RESET/EN, 4=GND. 실제 취출 접점과 케이블 방식 검토 필요.'],
 ],[106,409])
H(b,'그림의 같은 번호끼리 연결하는 규칙')
netnames={1:'D0 구동 A',2:'D1 구동 B',3:'온도 DATA',4:'I2C SDA',5:'I2C SCL',6:'D6 측정 버튼 입력',7:'공통 GND',8:'공통 3V3',9:'D10 분압 감시 노드',10:'D9 부저 제어 전단',11:'D8 저장 버튼 입력',12:'D7 모드 버튼 입력',13:'스위치 VOUT / XIAO BAT+',14:'배터리+ / 스위치 VIN',15:'ADS A0 신호',16:'ADS A1 신호',17:'ADS A2 신호',18:'ADS A3 신호',19:'측정 버튼 접점선',20:'모드 버튼 접점선',21:'저장 버튼 접점선',22:'부저 S 노드',23:'전극 E1',24:'전극 E2',25:'BOOT 취출선',26:'RESET 취출선'}
T(b,['번호','연결망','번호','연결망'],[[str(i),netnames[i],str(i+13),netnames[i+13]] for i in range(1,14)],[33,224,33,225])
P(b,'만능기판은 독립 패드이며 빵판처럼 행 전체가 연결되지 않는다. 부품면을 본 그림이므로 납땜면에서는 좌우가 반대다. 중간 구멍을 선이 지나간다고 접속하라는 뜻이 아니다. 교차부의 곡선 다리·끊김·접속점 표현이 실제 배선과 맞는지도 검토 대상이다.')

b=page('측정 원리와 실제 시험 범위')
H(b,'기존 시험 펌웨어의 동작')
P(b,'동봉 HeadWaterTest.ino는 기존 D0/D1 전극·D3 온도 시험 소스다. D0/D1에 서로 반대 극성의 0~3.3V 펄스를 번갈아 주고, 정지 시 두 핀을 입력으로 돌린다. 약 20ms 펄스와 5쌍 평균을 사용하며 ADS1115는 GAIN_ONE, 860SPS, 외부 I2C는 100kHz다. A0~A3는 순차 변환한다. 회로 설계가 확정된 정밀 교류 전도도 계측기는 아니다.')
P(b,'전극 사이 차전압은 |A0-A1|, 실제 구동 차전압은 |A2-A3|로 보고 RAW = 100 × (1 - |A0-A1| / |A2-A3|)를 0~100으로 제한한다. 이 값은 전체 구동 전압 중 직렬 저항에 걸리는 비율을 표현한 무차원 응답이다. 실제 염도 %가 아니다.')
H(b,'대화 기록에 남아 있는 관찰값')
T(b,['시험 상태','기록된 관찰값','해석 한계'],[
 ['전극 대신 1kΩ 시험 저항','RAW 약 66.77','직렬 1kΩ 두 개를 포함한 단순 모델의 약 66.7과 가까운 기능 확인.'],
 ['서로 닿지 않는 공기 중 헤드','RAW 약 0.01~0.02','개방 상태의 원시 응답 기록.'],
 ['수돗물 시험','RAW 약 55.40~55.43, 온도 약 22.88~22.94°C','NaCl 농도를 아는 기준액이 아니므로 염도 정확도 자료가 아님.'],
 ['극성별 응답','정·역방향 약 52.6 / 58.2의 차이 기록','전극 분극·구동·센스 시점·접촉 상태의 영향을 별도로 검토해야 함.'],
 ],[107,190,218])
P(b,'위 숫자는 이전 대화의 시험 보고를 인계한 것이며 독립 성적서나 전체 원시 로그를 새로 확인한 결과가 아니다. 부품의 재현성·정확도 허용오차를 보증하는 근거로 사용하지 말아 달라.')
H(b,'정규화와 교정에서 아직 필요한 일')
P(b,'같은 헤드 형상, 같은 유효 침수 길이와 용기 조건에서 농도가 알려진 여러 기준액을 온도별·반복 측정해야 한다. 그 자료로 변환표나 회귀식을 만들고, 학습·보정에 쓰지 않은 시료로 오차를 확인한다. 임의의 최솟값·최댓값을 0~100으로 바꾸거나 전극 재질 정보를 입력하는 것만으로 농도 교정이 끝나지 않는다.')
P(b,'NaCl 용액에서 얻은 변환식은 다른 이온과 고형물·유지방 등이 있는 모든 음식에 그대로 적용된다고 보장할 수 없다. ToF만으로 모든 용기의 부피를 바로 알 수 있는 것도 아니다. 카메라·ToF·염도 추정의 결합 방법과 성능 목표는 별도 검증 항목이다.')
P(b,'기존 소스는 OLED·ToF·버튼·부저·D10 배터리 감시·BOOT/RESET 외부 조작을 통합하지 않았다. 파일 상단의 B10/B22/C14/C18 같은 주석은 과거 빵판 좌표이며 R4-P2 만능기판 좌표로 사용하지 않는다.')

b=page('배터리 감시와 최신 변경점')
H(b,'전원과 충전의 제안된 연결')
P(b,'배터리+ → Pololu #2810 VIN → VOUT → XIAO BAT+. 배터리-, 스위치 GND, XIAO BAT-와 주변 모듈 GND는 공통이다. 스위치 ON에서 XIAO USB-C를 연결해 충전하는 안이다. XIAO 내장 충전 기능과 Pololu의 ON 상태 양방향 통전에 근거한 제안이며 전체 장치의 충전 검증 기록은 없다. OFF 충전이나 USB 연결 상태의 완전 차단을 보장하는 구성으로 간주하지 않는다. [S1, S5, S6]')
H(b,'R17과 R18 및 C4')
P(b,'최신 전체 도면에서는 13번인 VOUT/XIAO BAT+ 쪽 → R17 10kΩ → 9번 감시 노드 → R18 10kΩ → 7번 GND로 읽힌다. 9번에는 D10, TP8과 C4 0.1µF 한쪽이 연결되고 C4 반대쪽은 GND다. 마지막 정정 그림도 9번과 7번을 전선으로 직접 연결하지 말라는 의도를 보여 준다. 상세 그림의 “배터리 쪽” 표현과 전체 도면의 취출점을 함께 대조해야 한다.')
P(b,'이상적 분압 계산은 V_D10 = V_취출점 / 2 이므로 4.2V에서 약 2.1V다. 분압 전류는 약 0.21mA, 등가 저항 5kΩ와 0.1µF의 시정수는 약 0.5ms다. 계산상 값이며 ADC 감쇠·보정, GPIO 입력 설정, 전원 꺼짐 시 역급전과 실제 측정 오차는 별도 확인 대상이다. 전압만으로 정확한 배터리 잔량 %를 보장하지 않는다.')
H(b,'C5와 BOOT 및 RESET')
P(b,'C5는 도면상 +3V3와 GND 사이의 100µF 전원 커패시터다. 극성, 정격전압, 실제 부피, 충전·기동 돌입전류와 레귤레이터 안정성을 검토해야 한다. BOOT와 RESET/EN은 XIAO 일반 D핀 대신 기존 접점에서 취출하는 것으로 그려져 있다. 실제 보드 리비전에서 어느 패드인지, 접지 쪽을 잘못 취출하지 않는지, 외부 케이블의 잡음 영향을 확인해야 한다.')
T(b,['항목','이전 ASM-R3','이번 R4-P2'],[
 ['D10','미사용','배터리 감시 입력'],['외부 저항','1kΩ 6개 + 10kΩ 10개','1kΩ 6개 + 10kΩ 12개'],
 ['외부 커패시터','0.1µF 3개','0.1µF 4개 + 100µF 1개'],['접속부','단자 위주의 회로 연결표','J4~J10 소켓, BOOT/RESET, 5핀 헤드 하네스와 기판 배치 추가'],
 ],[91,177,247])
P(b,'이전 외함 제안 64×44×108mm는 이 만능기판의 확정 외함이 아니다. 최신 기판 그림은 50.80×91.44mm, 19열×35행, 피치 2.54mm로 표기돼 있다. 모듈·소켓·선 굽힘·배터리·헤드 결합부까지 포함해 다시 맞춰야 한다.')

b=page('다른 AI에 요청할 독립 검토')
P(b,'검토자는 아래 항목을 확인하고, 이전 AI의 판단이나 첨부 그림의 “수정 완료” 표기를 승인 근거로 사용하지 말아 달라. 불확실한 항목은 실물·자료가 필요한 이유와 필요한 확인 방법을 적어 달라.')
checks=[
 ('결선과 그림 표현','R4-P2 전체·부분 그림·마지막 정정 상세의 같은 번호가 같은 망인지 확인. 특히 9번 분압 노드와 7번 GND 단락, R1 앞·뒤 센스 위치, 교차선과 독립 패드의 접속 오류를 확인.'),
 ('GPIO와 ADC 전압','XIAO D번호와 GPIO 대응, D10 ADC 입력 범위·감쇠, ADS1115 각 핀의 GND 기준 입력 범위와 전원 꺼짐 상태를 검토. PGA의 ±측정범위 설정을 외부 음전압 허용으로 해석하지 말 것.'),
 ('전극 구동과 측정 품질','GPIO 직접 구동과 양쪽 1kΩ의 타당성, 전극 분극·부식·DC 성분, 순차 샘플링과 정착 시간, 10kΩ 입력 직렬 저항 및 모듈 내부 회로의 측정 오차를 검토.'),
 ('전원과 충전','배터리 PCM·전류 허용치, XIAO 충전 조건, 스위치 역방향 통전·USB 우회 동작, 모든 모듈의 피크 전류·발열·3.3V 전압 강하와 C5 영향을 검토.'),
 ('배터리 감시와 종료','취출점이 RAW 배터리인지 스위치 뒤 BAT+인지 확정. R17/R18/C4의 ADC 구동 적합성, 충전 중 표시 의미, 전원이 꺼졌을 때 역급전 가능성을 검토.'),
 ('I2C와 소프트웨어 충돌','ADS·OLED·ToF 주소, 모듈 내장 풀업의 합성값, ToF 초기화와 메모리, 온도센서 내장 풀업, D8/D9/D10과 SD 공유를 검토. SD 미사용 조건을 확인.'),
 ('BOOT와 RESET','GPIO0/BOOT 및 EN/RESET 실제 취출 패드, 버튼 접점군, 케이블 길이·노이즈, 외함을 연 뒤 수리·업로드할 수 있는지 검토.'),
 ('제작성과 조립 의뢰','기판 치수·소켓 방향·뒤집힌 납땜면·하네스 길이·역삽입 방지·절연·인장 완화·검사점 접근성을 검토. 작업자가 추측해야 하는 미정 항목을 명시.'),
 ('보유품과 추가 자재','10kΩ 12개 필요와 구매 기록 10개의 차이, C5와 잠금 커넥터의 미확인 보유 상태를 대조. 꼭 필요한 변경과 선택 개선을 나눌 것.'),
 ('제품 컨셉과 보정 가능성','고정 침수 깊이와 금속 온도관 영향, 표준액 교정과 음식 매트릭스 한계, 카메라·ToF의 부피·AI 역할이 현재 부품 구성으로 검증 가능한지 평가.'),
]
for title,detail in checks:B(b,title+' - '+detail)
H(b,'받고 싶은 검토 결과 형식')
P(b,'① 회로 검토 판정과 검토 가능한 범위 ② 통전 전에 수정해야 할 문제 ③ 측정 정확도·재현성 문제 ④ 제작·소프트웨어 문제 ⑤ 수정이 필요한 정확한 핀과 연결망 ⑥ 추가 부품의 규격·수량·이유 ⑦ 단계별 통전·충전·기능 검사. 각 지적에 도면 위치, 제조사 근거, 확정 사실인지 추론인지와 우선순위를 적어 달라.')

b=page('근거와 첨부 자료의 사용 방법')
P(b,'자료 기준일은 2026년 11월 23일이다. R4-P2 이미지 5장은 사용자가 이번 요청에 직접 첨부한 원본을 변경하지 않고 복사했다. 아래 번호 순서로 보면 전체 배치, 전원, 전극, 통신과 조작부, 분압 정정 내용을 따라갈 수 있다.')
for i,(dest,orig,title) in enumerate(attachments,1):B(b,f'그림 {i} {title} / diagrams/{dest} / 원본 {orig}')
P(b,'과거 부품·헤드 자료와 구매 대화는 보유품과 기존 형상·개발 이력을 설명하는 데 사용했다. 회로 연결은 최신 첨부를 우선하며, 과거 ASM-R3의 J번호·D10 미사용·저항 16개 구성을 최신 상태에 그대로 적용하지 않았다. 동봉 펌웨어는 과거 기초 시험 기준을 확인하기 위한 참고 소스다.')
H(b,'제조사 확인 자료')
sources=[
 ('S1','Seeed XIAO ESP32-S3 전원과 배터리','https://wiki.seeedstudio.com/xiao_esp32s3_getting_started/'),
 ('S2','Seeed 핀 다중화와 Sense SD 공유','https://wiki.seeedstudio.com/xiao_esp32s3_pin_multiplexing/'),
 ('S3','DFRobot DFR0553 전원과 단자','https://wiki.dfrobot.com/dfr0553/'),
 ('S4','SparkFun VL53L5CX 사용 문서','https://learn.sparkfun.com/tutorials/qwiic-tof-imager---vl53l5cx-hookup-guide/all'),
 ('S5','Pololu #2810 제품 문서','https://www.pololu.com/product/2810'),
 ('S6','Pololu 기술지원의 ON 상태 양방향 통전 설명','https://forum.pololu.com/t/soft-switch-2810-with-battery/18180/4'),
 ('S7','TI ADS1115 데이터시트','https://www.ti.com/lit/ds/symlink/ads1115.pdf'),
 ('S8','Analog Devices DS18B20 데이터시트','https://www.analog.com/media/en/technical-documentation/data-sheets/ds18b20.pdf'),
 ('S9','구매 온도센서 상품 15584272','https://www.devicemart.co.kr/goods/view?no=15584272'),
 ('S10','구매 배터리 기존 확정 상품 15337882','https://www.devicemart.co.kr/goods/view?no=15337882'),
]
for key,title,url in sources:P(b,f'[{key}] {title}<br/><link href="{url}" color="#1F567B">{url}</link>')
P(b,'제조사 자료는 검토자가 수령품 리비전과 대조할 출처다. 일부 판매·SparkFun 페이지는 이번 조회에서 본문을 다시 확보하지 못해 과거 모델 확인 기록과 링크만 보존했다. 방수·식품 접촉 적합성·온도 응답·염도 정확도·부피 정확도·AI 성능은 이 자료로 인증되지 않는다. 전자부품이 수돗물에 잠깐 닿았던 이력이 있어 통합 전 외관·절연·기능 재검수가 필요하다.')

# Create an upload-friendly plain-text version without relying on pictures for core pin data.
def plain(s):
 import re
 return html.unescape(re.sub(r'<[^>]+>',' ',s)).strip()
txt=['휴대용 AI 염도 부피 측정기 프로젝트 인계와 회로 검토 요청','기준일 2026-11-23 / 검토 대상 R4-P2 / 다른 AI에게 이 텍스트와 그림 5장을 함께 제공하세요.','']
for i,pg in enumerate(pages,1):
 txt+=['',f'{i}. {pg["title"]}','']
 for block in pg['blocks']:
  if block[0]=='table':
   txt.append(' | '.join(block[1]));txt+=[' | '.join(map(str,row)) for row in block[2]];txt.append('')
  else:txt.extend([('- ' if block[0]=='bullet' else '')+plain(block[1]),''])
(OUT/'다른AI_프로젝트설명과_회로검토요청.txt').write_text('\n'.join(txt),encoding='utf-8-sig')

# Typeset a self-contained review document, followed by unedited source diagrams.
PW,PH=A4; LEFT=40; RIGHT=PW-40; WIDTH=RIGHT-LEFT
INK='#172B3A'; GRAY='#5F6B74'
styles={
 'p':ParagraphStyle('body',fontName='K',fontSize=9.5,leading=14.5,textColor=HexColor(INK),wordWrap='CJK',spaceAfter=8),
 'bullet':ParagraphStyle('bullet',fontName='K',fontSize=9.3,leading=14,textColor=HexColor(INK),wordWrap='CJK',leftIndent=9,firstLineIndent=-9,spaceAfter=7),
 'h':ParagraphStyle('head',fontName='KB',fontSize=11,leading=16,textColor=HexColor('#000000'),spaceBefore=7,spaceAfter=7),
 'cell':ParagraphStyle('cell',fontName='K',fontSize=8.8,leading=12.6,textColor=HexColor(INK),wordWrap='CJK'),
 'th':ParagraphStyle('th',fontName='KB',fontSize=8.8,leading=12.6,textColor=white,wordWrap='CJK')}
pdf=OUT/'pdf'/'AI검토용_프로젝트목표_보유부품_R4P2_인계문서.pdf'
c=canvas.Canvas(str(pdf),pagesize=A4);c.setTitle('AI 검토용 프로젝트 목표 보유 부품과 R4P2 회로 인계');c.setAuthor('AI 창업프로젝트')
layout=[]
def footer(n,w=PW,h=PH):
 c.setStrokeColor(HexColor('#D9D9D9'));c.line(36,34,w-36,34)
 c.setFillColor(HexColor(GRAY));c.setFont('K',7.5);c.drawString(36,22,'2026-11-23  |  AI 독립 검토용  |  최신 첨부 R4-P2 기준')
 c.drawRightString(w-36,22,str(n))
for n,pg in enumerate(pages,1):
 if n>1:c.showPage()
 c.setPageSize(A4);c.setFillColor(HexColor('#000000'));c.setFont('K',8);c.drawString(LEFT,PH-36,'휴대용 AI 염도 부피 측정기 인계 문서')
 c.setFont('KB',19);c.drawString(LEFT,PH-72,pg['title'])
 if n==1:
  c.setFont('K',8.6);c.drawString(LEFT,PH-93,'다른 AI에게 목표와 부품을 설명하고 회로를 검토받기 위한 자료')
  y=PH-111
 else:y=PH-92
 for block in pg['blocks']:
  if block[0]=='table':
   _,head,rows,widths=block
   data=[[Paragraph(html.escape(v),styles['th']) for v in head]]+[[Paragraph(html.escape(str(v)),styles['cell']) for v in row] for row in rows]
   table=Table(data,colWidths=widths)
   table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),HexColor('#243B4B')),('ROWBACKGROUNDS',(0,1),(-1,-1),[white,HexColor('#F3F6F8')]),('GRID',(0,0),(-1,-1),.4,HexColor('#D9D9D9')),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
   _,hh=table.wrap(WIDTH,1000);assert y-hh>43,(n,'table',y,hh);table.drawOn(c,LEFT,y-hh);y-=hh+9
  else:
   kind,s=block;ss=('• '+s) if kind=='bullet' else s
   p=Paragraph(ss,styles[kind]);_,hh=p.wrap(WIDTH,1000)
   extra=styles[kind].spaceBefore if kind=='h' else 0
   assert y-hh-extra>43,(n,kind,y,hh,plain(s)[:40]);p.drawOn(c,LEFT,y-hh-extra);y-=hh+extra+styles[kind].spaceAfter
 footer(n);layout.append({'page':n,'lowest_y':y,'title':pg['title']})

for j,(dest,orig,title) in enumerate(attachments,1):
 c.showPage();aw,ah=A3;c.setPageSize(A3)
 c.setFillColor(HexColor('#000000'));c.setFont('KB',17);c.drawString(36,ah-37,f'원본 그림 {j}  {title}')
 c.setFont('K',9);c.drawString(36,ah-56,'사용자 첨부 R4-P2 원본 보존본  |  세부 글자는 확대하거나 ZIP의 PNG 원본으로 확인')
 ip=OUT/'diagrams'/dest
 with Image.open(ip) as im:iw,ih=im.size
 scale=min((aw-72)/iw,(ah-112)/ih);dw,dh=iw*scale,ih*scale
 c.drawImage(str(ip),(aw-dw)/2,54+(ah-112-dh)/2,width=dw,height=dh)
 footer(len(pages)+j,aw,ah)
c.save()

# Reference code is deliberately labelled baseline, never the new integrated firmware.
base=OUT/'baseline_firmware';firm=Path(r'C:\Users\Yeon\Documents\Codex\2026-11-14\head-test\HeadWaterTest\HeadWaterTest.ino')
shutil.copy2(firm,base/'HeadWaterTest.ino')
(base/'소스의범위.txt').write_text('기존 전극과 온도 시험 소스입니다. R4-P2 전체의 통합 펌웨어가 아닙니다. OLED, ToF, 버튼, 부저, D10 배터리 감시, BOOT/RESET 외부 연결을 검증하지 않습니다. 상단 주석의 빵판 좌표를 만능기판 좌표로 해석하지 마세요.\n',encoding='utf-8-sig')
(OUT/'원본자료목록.json').write_text(json.dumps({'date':'2026-11-23','diagrams_revision':'R4-P2','images':manifest,'baseline_firmware_sha256':hashlib.sha256(firm.read_bytes()).hexdigest()},ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'먼저읽기.txt').write_text('다른 AI에게 PDF 한 개를 올리면 본문과 회로 그림 5장을 함께 볼 수 있습니다. 텍스트 입력을 선호하는 AI에는 다른AI_프로젝트설명과_회로검토요청.txt를 복사하고 diagrams 폴더의 원본 PNG 5장을 함께 첨부하세요. baseline_firmware는 기존 기초 시험 참고 소스이며 최신 통합 완성 코드가 아닙니다. 이전 ASM-R3보다 최신인 이번 R4-P2의 연결을 우선 검토하세요.\n',encoding='utf-8-sig')
(ROOT/'work'/'layout.json').write_text(json.dumps(layout,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'pdf':str(pdf),'main_pages':len(pages),'total_pages':len(pages)+len(attachments),'text_characters':len('\n'.join(txt)),'layout':layout},ensure_ascii=False))
