from pathlib import Path
import math, shutil, json, csv, html
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor, white
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output'; PDF=OUT/'pdf'/'스마트염도계_배터리내장_설계안_R2.pdf'
pdfmetrics.registerFont(TTFont('K',r'C:\Windows\Fonts\malgun.ttf'))
pdfmetrics.registerFont(TTFont('KB',r'C:\Windows\Fonts\malgunbd.ttf'))
W,H=1200,820
INK='#183348'; TEAL='#087F85'; BLUE='#2166AA'; GRAY='#5B6F7E'; LIGHT='#EEF4F7'; ORANGE='#A45520'
C=canvas.Canvas(str(PDF),pagesize=(W,H))
C.setTitle('스마트 염도계 배터리 내장 MVP 설계안 R2')
C.setAuthor('AI 창업프로젝트')

def text(x,y,s,size=19,color=INK,bold=False,anchor='left'):
 C.setFillColor(HexColor(color)); C.setFont('KB' if bold else 'K',size)
 {'left':C.drawString,'center':C.drawCentredString,'right':C.drawRightString}[anchor](x,H-y,s)
def line(x,y,xx,yy,color=INK,width=2,dash=None):
 C.setStrokeColor(HexColor(color));C.setLineWidth(width);C.setDash(dash or [])
 C.line(x,H-y,xx,H-yy);C.setDash([])
def rect(x,y,w,h,fill=LIGHT,stroke=INK,r=8):
 C.setStrokeColor(HexColor(stroke));C.setFillColor(HexColor(fill));C.setLineWidth(1.5)
 C.roundRect(x,H-y-h,w,h,r,stroke=1,fill=1)
def dot(x,y,col=BLUE):
 C.setFillColor(HexColor(col)); C.circle(x,H-y,4,stroke=0,fill=1)
def arrow(x,y,xx,yy,col=BLUE):
 line(x,y,xx,yy,col,2.2);a=math.atan2(yy-y,xx-x)
 for d in [-.45,.45]:line(xx,yy,xx-12*math.cos(a+d),yy-12*math.sin(a+d),col,2.2)
def block(x,y,w,h,title,sub=None):
 rect(x,y,w,h);text(x+14,y+29,title,21,bold=True)
 if sub:
  for i,s in enumerate(sub):text(x+14,y+58+i*25,s,16,GRAY)
def para(x,y,w,s,size=17,color=INK):
 p=Paragraph(s,ParagraphStyle('p',fontName='K',fontSize=size,leading=size*1.55,textColor=HexColor(color),wordWrap='CJK'))
 _,h=p.wrap(w,1000);p.drawOn(C,x,H-y-h);return y+h
def ground(x,y):
 line(x,y,x,y+12);line(x-15,y+12,x+15,y+12);line(x-10,y+19,x+10,y+19);line(x-4,y+26,x+4,y+26)
def rh(x,xx,y,label):
 m=(x+xx)/2;line(x,y,m-28,y);rect(m-28,y-10,56,20,'#FFFFFF',r=0);line(m+28,y,xx,y)
 text(m,y-23,label,17,anchor='center')
def rv(x,y,yy,label,left=False):
 m=(y+yy)/2;line(x,y,x,m-22);rect(x-10,m-22,20,44,'#FFFFFF',r=0);line(x,m+22,x,yy)
 text(x-19 if left else x+19,m+5,label,16,anchor='right' if left else 'left')
def note(x,y,w,title,s):
 rect(x,y,w,90,'#F0F7F7',TEAL);text(x+14,y+27,title,18,TEAL,True);para(x+14,y+38,w-28,s,15)
def start(n,title,sub):
 if n>1:C.showPage()
 text(35,35,'AI SALINITY PROJECT  /  BATTERY MVP  /  R2',13,TEAL,True)
 text(35,78,title,30,bold=True);text(35,110,sub,16,GRAY)
 line(35,775,1165,775,'#CEDAE1',1)
 text(35,798,'2026-11-20  |  모듈 연결 설계안 · 외형 예상도  |  통합 동작·교정·방수 검증 전',12,GRAY)
 text(1165,798,f'{n} / 6',13,GRAY,anchor='right')
def pic(path,x,y,w,h):
 with Image.open(path) as im:iw,ih=im.size
 s=min(w/iw,h/ih);dw,dh=iw*s,ih*s
 C.drawImage(str(path),x+(w-dw)/2,H-y-dh,width=dw,height=dh)
def table(x,y,widths,headers,rows,size=15):
 styles=[ParagraphStyle('th',fontName='KB',fontSize=size,leading=size*1.4,textColor=white,wordWrap='CJK'),ParagraphStyle('tc',fontName='K',fontSize=size,leading=size*1.4,textColor=HexColor(INK),wordWrap='CJK')]
 data=[[Paragraph(html.escape(str(v)),styles[0]) for v in headers]]+[[Paragraph(html.escape(str(v)),styles[1]) for v in row] for row in rows]
 t=Table(data,colWidths=widths)
 t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),HexColor(INK)),('ROWBACKGROUNDS',(0,1),(-1,-1),[white,HexColor(LIGHT)]),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),9),('RIGHTPADDING',(0,0),(-1,-1),9),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
 _,h=t.wrap(sum(widths),1000);assert y+h<764,(y,h);t.drawOn(C,x,H-y-h);return y+h

# 1. Actual CAD views, with current short-tip head.
start(1,'기존 헤드 + 배터리 내장 본체','기존 세 봉과 헤드 재사용 · OLED 128×32 · 버튼 3개 · 구매한 DTP803040 배터리')
pic(ROOT/'work'/'assembled.png',30,128,430,600)
pic(ROOT/'work'/'cutaway.png',465,128,430,600)
text(245,747,'전면 예상도',18,TEAL,True,anchor='center');text(680,747,'뒷덮개를 연 내부 배치',18,TEAL,True,anchor='center')
text(905,159,'설계 기준',21,TEAL,True)
for y,title,body in [
 (185,'본체 약 64×44×108mm','기존 헤드 포함 전체 높이 약 166mm. 치수는 공간 배치 제안값입니다.'),
 (300,'배터리 3.7V · 1,000mAh','DTP803040 재사용. 중앙 뒤쪽에 독립 수납하고 기판과 절연합니다.'),
 (415,'기존 헤드 58×38mm','세 금속 끝의 돌출 길이 10mm 유지. 옆 고정 나사 접근 공간을 남깁니다.'),
 (530,'버튼 기능 제안','왼쪽 측정 / 가운데 모드 / 오른쪽 저장. 측정값은 내부 플래시에 저장합니다.'),
 (645,'카메라 · ToF 유지','전면 위쪽에 각각 개구부 배치. 실제 창 크기와 광학 시야는 실물 확인 후 확정합니다.')]:
 text(905,y,title,17,bold=True);para(905,y+13,255,body,15)

# 2. Power: deliberate, constrained charging-through-switch behavior.
start(2,'전원 회로 · USB 충전','배터리 → 보유 Pololu #2810 → XIAO BAT+  /  주변 모듈은 XIAO 3V3 사용')
block(40,230,230,135,'B1  DTP803040',['1셀 3.7V / 1,000mAh','충전 종지 4.2V 규격','커넥터 극성 실측 후 연결'])
block(380,230,260,135,'U2  Pololu #2810',['VIN                  VOUT','ON 핀은 연결하지 않음','내장 슬라이드 스위치 사용'])
block(760,230,390,135,'U1  XIAO ESP32-S3 Sense',['BAT+ / BAT- 전용 패드','내장 USB 충전·3.3V 전원 회로','BAT+에 연결. 3V3/5V 핀에 배터리 금지'])
line(270,260,380,260,BLUE);text(323,247,'B+',16,BLUE,True,anchor='center')
line(640,260,760,260,BLUE);text(700,247,'BAT+',16,BLUE,True,anchor='center')
for x in [300,675,1120]:
 if x==300:line(270,330,x,330)
 elif x==675:line(640,330,x,330)
 else:line(1120,365,1120,385)
 ground(x,330 if x!=1120 else 385)
text(290,390,'B- / GND',15,GRAY);text(655,390,'GND',15,GRAY)
block(800,138,285,62,'USB-C  5V / 데이터')
arrow(940,200,940,230,TEAL)
arrow(745,211,287,211,TEAL);text(515,190,'충전 방향  ←  스위치 ON일 때',17,TEAL,True,anchor='center')
line(945,365,945,442,TEAL);line(120,442,1080,442,TEAL);dot(945,442,TEAL)
text(600,427,'공통 +3V3 전원망',18,TEAL,True,anchor='center')
names=[('ADS1115','VCC / +'),('OLED','VCC'),('ToF','3V3'),('DS18B20','빨강 / VDD'),('ONE005','+ / VCC')]
for i,(a,b) in enumerate(names):
 x=40+i*228;line(x+95,442,x+95,476,TEAL);block(x,476,206,82,a,[b]);line(x+102,558,x+102,569);ground(x+102,569)
text(42,632,'GND 기호는 모두 같은 선입니다. 센서·버튼·배터리·스위치의 GND를 공통 연결합니다.',16,GRAY)
table(40,652,[220,910],['상태','이 설계의 동작'],[
 ('배터리 사용 / 충전','휴대 측정은 USB 분리 + 스위치 ON. 충전은 스위치 ON + USB 연결. 충전 중 측정은 중지합니다.'),
 ('스위치 OFF','USB를 뺀 상태에서 배터리 동작이 꺼집니다. USB가 연결돼 있으면 보드는 켜질 수 있고, OFF 상태 충전은 보장하지 않습니다.')],14)

# 3. Analog measurement is an actual resistor / node schematic.
start(3,'전극 측정 회로 · 기존 배선 유지','E1·E2는 금속 전극 2개. 온도센서는 별도 1-Wire 회로입니다. 같은 이름의 노드는 같은 선입니다.')
y=307
text(45,205,'D0 / GPIO1',22,BLUE,True);text(1150,205,'D1 / GPIO2',22,BLUE,True,anchor='right')
line(75,y,230,y);rh(230,430,y,'R1  1kΩ');line(430,y,480,y)
rect(480,257,235,100,'#EAF4F2',TEAL);text(597,289,'E1  |  시료  |  E2',21,TEAL,True,anchor='center');text(597,328,'두 금속봉 사이',17,GRAY,anchor='center')
line(715,y,770,y);rh(770,970,y,'R2  1kΩ');line(970,y,1130,y)
for x in [145,455,743,1055]:dot(x,y)
# Pulldowns, before series drive resistors.
line(95,y,95,245);rh(95,300,245,'R7  10kΩ');ground(300,245);dot(95,y)
line(1105,y,1105,245);rh(900,1105,245,'R8  10kΩ');ground(900,245);dot(1105,y)
for x,dest,lab,ch in [(145,145,'R5  10kΩ','A2 ← D0'),(455,435,'R3  10kΩ','A0 ← E1'),(743,745,'R4  10kΩ','A1 ← E2'),(1055,1035,'R6  10kΩ','A3 ← D1')]:
 rv(x,307,460,lab);line(x,460,dest,460,BLUE);line(dest,460,dest,500,BLUE);text(dest,485,ch,18,BLUE,True,anchor='center')
block(60,500,1080,90,'U3  DFRobot Gravity ADS1115 / DFR0553',['각 A0~A3 채널의 A(신호) 핀만 위 회로에 연결. 전원 3.3V / GND, I2C 주소 0x48'])
note(40,620,550,'단자 방향','기판 글자를 기준으로 A=신호, +=3V3, -=GND입니다. 예전 그림의 핀 좌우 순서를 따라 연결하지 않습니다.')
note(610,620,550,'구동 방식','D0/D1 극성을 번갈아 구동하고 정지 때는 입력 상태로 둡니다. 입력 전압은 ADS 전원 범위 안에서만 사용합니다.')
text(42,742,'이번 기본 회로는 보유 저항을 사용합니다. BAT43을 필수 추가 부품으로 넣지 않았으며 외부 정전기·오접속 보호는 미검증입니다.',15,ORANGE)

# 4. I2C and temperature plus controls, independent and fully net-labeled.
start(4,'화면 · 온도 · 버튼 · 부저 연결','모든 +3V3와 GND는 2쪽의 공통 전원망에 연결합니다. 모듈 단자의 실제 글자를 확인합니다.')
text(40,152,'I2C 버스 · 3개 모듈 병렬',22,TEAL,True)
text(42,191,'D4 / GPIO5 = SDA',17,BLUE,True);text(42,223,'D5 / GPIO6 = SCL',17,BLUE,True)
for y,lab in [(260,'SDA'),(300,'SCL')]:
 line(60,y,1105,y,BLUE);text(1120,y+5,lab,16,BLUE,True)
mods=[(120,'ADS1115  0x48','D=SDA  /  C=SCL'),(460,'OLED  0x3C / 0x3D','SDA  /  SCL'),(800,'VL53L5CX  0x29','Qwiic SDA  /  SCL')]
for x,a,b in mods:
 line(x+60,260,x+60,334,BLUE);dot(x+60,260)
 line(x+245,300,x+245,334,BLUE);dot(x+245,300)
 block(x,334,310,80,a,[b+'  ·  3V3/GND'])
text(42,448,'추가 I2C 풀업은 우선 실장하지 않습니다. 모듈 내장 풀업 합성값과 버스 동작을 통합 시 확인합니다.',15,GRAY)
text(40,488,'온도센서 · 구매한 EM Tech DS18B20',21,TEAL,True)
for y,color,s in [(526,'#B03735','빨강  →  +3V3'),(556,INK,'검정  →  GND'),(586,'#9B7B05','노랑  →  D3 / GPIO4')]:text(45,y,s,18,color,True)
para(45,605,390,'구매 제품은 4.7kΩ 풀업 내장형으로 확인한 제품입니다. 같은 풀업 저항을 추가하지 않습니다.',16)
text(470,488,'버튼 1회로 × 3개',21,TEAL,True)
text(485,552,'D6 / D7 / D8',16,BLUE,True);line(490,570,645,570,BLUE);dot(645,570)
rv(645,515,570,'10kΩ');text(645,510,'3V3',14,TEAL,anchor='center')
rh(645,825,570,'1kΩ');line(825,570,850,570);dot(850,570,INK);line(850,562,891,537);dot(900,570,INK);line(900,570,930,570);ground(930,570)
text(476,631,'R9/R10/R11 = 풀업 10kΩ',15);text(476,657,'R12/R13/R14 = 직렬 1kΩ',15)
text(476,685,'스위치 반대 접점군을 사용. 누르면 LOW.',15,GRAY)
text(970,488,'부저 ONE005',19,TEAL,True)
text(970,527,'D9 / GPIO8',16,BLUE,True)
rh(970,1155,570,'R15 1kΩ');text(1150,608,'S 핀',16,BLUE,True,anchor='right')
line(1115,570,1115,623);dot(1115,570);rv(1115,623,692,'R16',left=True);ground(1115,692)
text(973,742,'R16 = 10kΩ  /  +=3V3, -=GND',13,GRAY)

# 5. Authoritative mapping / counted BOM.
start(5,'최종 연결표 · 보유 부품 기준','회로도와 아래 표의 핀 이름이 일치합니다. 현재 실험 회로에 표시장치와 조작부를 추가하는 구성입니다.')
pins=[('D0 / 1','R1 → E1 / A2 감시'),('D1 / 2','R2 → E2 / A3 감시'),('D2 / 3','비움 · 스트래핑 핀'),('D3 / 4','온도 노랑 DATA'),('D4 / 5','I2C SDA 공통'),('D5 / 6','I2C SCL 공통'),('D6 / 43','버튼 1 · 측정'),('D7 / 44','버튼 2 · 모드'),('D8 / 7','버튼 3 · 저장'),('D9 / 8','ONE005 S · R15 경유'),('D10 / 9','비움'),('BAT+ / BAT-','2쪽의 스위치 / 공통 GND')]
table(40,140,[135,395],['XIAO D번호 / GPIO','연결 대상'],pins,15)
parts=[('기존 센서부','XIAO Sense, DFR0553, DS18B20, SUS316L 전극 2개'),('조작·광학','OLED 128×32, 버튼 3개, ONE005, SEN-19013 ToF'),('배터리·스위치','DTP803040 3.7V 1,000mAh, Pololu #2810'),('배터리 연결선','51021-0200에 맞물리는 상대편 + 전선. 극성 실측'),('1kΩ  6개','R1,R2,R12,R13,R14,R15'),('10kΩ  10개','R3~R11, R16'),('0.1µF  3개','ADC / OLED / ToF 각각 VCC-GND 가까이'),('실장·고정','만능기판 또는 새 PCB, 절연재, 배선 고정, 본체 나사')]
table(605,140,[165,390],['부품','사용 기준'],parts,15)
text(610,490,'전원 바이패스 · 각 모듈 바로 옆',18,TEAL,True)
for i,x in enumerate([652,835,1018]):
 text(x,520,'+3V3',14,TEAL,anchor='center');line(x,526,x,541,TEAL)
 line(x-14,541,x+14,541);line(x-14,549,x+14,549);line(x,549,x,558);ground(x,558)
 text(x+23,548,f'C{i+1}',14,bold=True);text(x+23,570,'0.1µF',13,GRAY)
note(605,620,550,'SD 카드는 사용하지 않습니다','D8/D9가 Sense의 SD 신호와 겹칩니다. SD 카드를 빼고 SD/SPI 초기화를 하지 않는 소프트웨어 구성이 전제입니다.')
text(43,733,'카메라는 기존 Sense 전용 커넥터로 유지합니다. ToF 케이블 PRT-17912는 배터리 커넥터로 사용하지 않습니다.',15,GRAY)

# 6. Calibration boundaries, buildability, accessible references.
start(6,'측정값 정규화 · 제작 확정 조건','회로와 외형은 지금 정리할 수 있습니다. 염도 표시 계수는 기준 시료와의 비교 결과로 정합니다.')
steps=[('1  조건 고정','현재 헤드 · 잠기는 길이 · 컵과 위치 · 물양 · 구동 주기를 고정합니다. 세 봉의 끝 10mm 전체가 잠길 필요보다 같은 유효 침수 길이를 재현하는 것이 중요합니다.'),('2  기준값과 짝짓기','알려진 농도의 기준액 여러 개에서 온도와 원시값을 반복 기록합니다. 0%, 낮음, 중간, 높음 등 실제 사용할 범위를 포함하고 농도 단위를 고정합니다.'),('3  변환식 만들기','표준액으로 변환표 또는 회귀식을 맞추고 온도 영향을 확인합니다. 고정된 2%/°C 계수를 모든 음식에 일괄 적용하지 않습니다.'),('4  별도 시료로 검증','변환식에 쓰지 않은 시료와 재측정으로 오차·반복성을 확인합니다. NaCl 용액 보정만으로 모든 음식의 실제 소금 농도를 보장할 수는 없습니다.')]
y=146
for title,body in steps:
 text(40,y,title,20,TEAL,True);y=para(40,y+12,540,body,16)+30
text(40,650,'화면 예시의 RAW 55.4는 염도 55.4%가 아닙니다.',17,ORANGE,True)
para(40,665,545,'교정 전에는 RAW와 온도를 표시하고, 검증한 후 선택한 단위의 염도로 전환합니다. 임의의 최대·최소로 0~100만 만드는 것은 농도 교정이 아닙니다.',15)
text(620,153,'외함 제작 전에 확정할 것',21,TEAL,True)
para(620,170,535,'본체 크기는 64×44×108mm를 제안했습니다. 배터리 공간은 약 34×46×12mm를 배정하되 실제 보호회로·선·커넥터를 포함한 외형을 재서 조정해야 합니다. 배터리를 나사로 누르지 않습니다.',16)
para(620,275,535,'기존 헤드는 그대로 두고 위쪽 마른 구역에 본체를 체결합니다. 도면의 바닥 관통선·결합부는 개념 배치이며, 조립 나사·누수 차단·인장 완화 구조를 확정한 출력용 STL은 아닙니다.',16)
para(620,380,535,'구매 배터리의 보호회로와 허용 방전전류, 전체 모듈의 순간 소비전류·발열·3.3V 전압을 통합 시험에서 대조합니다. 사용시간은 현재 측정 자료로 확정하지 않습니다.',16)
text(620,490,'확인 근거와 제조사 문서',19,TEAL,True)
sources=[('Seeed · 전원 / BAT 패드 / USB 충전','https://wiki.seeedstudio.com/xiao_esp32s3_getting_started/'),('Pololu · ON 상태 양방향 통전 확인','https://forum.pololu.com/t/soft-switch-2810-with-battery/18180/4'),('DFRobot · ADC 단자와 전원','https://wiki.dfrobot.com/dfr0553/'),('배터리 · 기존에 확정한 상품 15337882','https://www.devicemart.co.kr/goods/view?no=15337882'),('온도센서 · 기존에 확인한 제품 시트','https://www.devicemart.co.kr/goods/view?no=15584272')]
yy=521
for title,url in sources:
 text(620,yy,title,14,BLUE);C.linkURL(url,(620,H-yy-5,1155,H-yy+17),relative=0);yy+=34
para(620,706,535,'진행 상태는 기초 전극·온도 시험 완료, 전체 통합과 농도 교정은 미완료입니다. 사용자가 요청한 “시험 완료를 가정한 설계”로 작성했습니다.',14,GRAY)
C.save()

# A machine-readable wiring list remains usable alongside diagrams.
with (OUT/'pin_connections.csv').open('w',encoding='utf-8-sig',newline='') as f:
 wr=csv.writer(f);wr.writerow(['XIAO D / GPIO','연결 대상']);wr.writerows(pins)
(OUT/'설계상태.md').write_text('''# 배터리 내장 MVP 설계안 R2

구매 배터리는 DTP803040, 1셀 3.7V 1,000mAh이다. 기존에 확정한 상품은 디바이스마트 15337882이며 커넥터 표기는 Molex 51021-0200 2핀 1.25mm였다. 구매 완료는 2026-11-20 사용자 확인을 반영한다. 보호회로와 허용 전류는 통합 전 실물·시트로 대조한다.

## 회로 동작

- 배터리 + → Pololu #2810 VIN → VOUT → XIAO BAT+.
- 배터리 - / Pololu GND / XIAO BAT- / 주변 기기 GND는 공통.
- USB 충전은 스위치 ON에서 사용한다. USB가 연결되면 스위치 OFF라도 보드는 켜질 수 있다.
- 배터리를 XIAO 3V3 또는 5V 핀에 연결하지 않는다.
- 측정할 때 USB를 분리한다. 충전 중 측정을 멈춘다.
- ADC, OLED, ToF, 온도센서, 부저는 공통 3.3V에서 공급한다.
- 부품 전원마다 0.1uF 커패시터를 ADC/OLED/ToF 가까이 실장한다.
- SD 카드는 사용하지 않으며 SD/SPI 초기화를 하지 않는다.
- BAT43은 이번 기본 설계의 필수 구매품이 아니다. 보호 내성은 별도 검증 대상이다.

## 외형

본체 64×44×108mm, 헤드 포함 높이 약 166mm는 공간 배치 제안값이다. 기존 헤드 모델을 변경하지 않았으며 세 팁은 아래로 10mm만 나온다. 배터리는 기판과 분리해 고정한다. CAD와 그림은 외형 개념이며 최종 체결부와 나사·공차·방수 구조까지 확정한 생산용 설계는 아니다. 실제 OLED, 배터리, 커넥터와 전선 굽힘을 포함해 실측해야 한다.

## 값 처리

RAW 0~100은 염도 %가 아니다. 농도가 알려진 여러 표준액의 온도·RAW 자료로 변환표/회귀식을 정하고 별도 시료로 검증한다. 전극의 분극과 비선형성 때문에 단순 저항식만으로 실제 소금 농도를 확정하지 않는다. 음식의 다른 이온도 측정에 영향을 준다.

## 버튼 제안

측정 / 모드 / 저장. 저장은 내부 플래시를 사용한다. 이 문서 작성 중 기기에 코드를 업로드하거나 전원을 인가하지 않았다.
''',encoding='utf-8')
print(json.dumps({'pdf':str(PDF),'pages':6,'size':PDF.stat().st_size},ensure_ascii=False))
