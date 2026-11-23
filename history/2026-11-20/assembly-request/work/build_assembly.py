from pathlib import Path
import csv, json, html, shutil, hashlib, collections
from reportlab.graphics.shapes import Drawing, Line, Rect, Circle, String
from reportlab.graphics import renderPDF, renderSVG
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor, white
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A3, landscape

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'output'
pdfmetrics.registerFont(TTFont('K',r'C:\Windows\Fonts\malgun.ttf'))
pdfmetrics.registerFont(TTFont('KB',r'C:\Windows\Fonts\malgunbd.ttf'))
W,H=1600,1100; INK='#172C3E'; BLUE='#165E9A'; GRAY='#526471'; LIGHT='#F3F6F8'; TEAL='#076D70'
N=collections.OrderedDict()
def net(name,*pins): N.setdefault(name,[]).extend(pins)

# This dictionary is the authoritative electrical pin-to-net definition.
net('BATT_RAW','B1.+','J1.B+','U2.VIN')
net('VBAT_SW','U2.VOUT','U1.BAT+','TP1.PAD')
net('+3V3','U1.3V3','U3.VCC','U4.VCC','U5.3V3','U6.VDD','J3.1','U7.+',
    'R9.1','R10.1','R11.1','C1.1','C2.1','C3.1','TP2.PAD')
net('GND','B1.-','J1.B-','U2.GND','U1.GND','U1.BAT-','U3.GND','U4.GND','U5.GND',
    'U6.GND','J3.3','U7.-','R7.2','R8.2','R16.2','SW1.B','SW2.B','SW3.B',
    'C1.2','C2.2','C3.2','TP0.PAD')
net('DRIVE_A','U1.D0','R1.1','R5.1','R7.1','TP3.PAD')
net('DRIVE_B','U1.D1','R2.1','R6.1','R8.1','TP4.PAD')
net('E1','R1.2','R3.1','J2.1','E1.DRY','TP5.PAD')
net('E2','R2.2','R4.1','J2.2','E2.DRY','TP6.PAD')
for k in range(4):net(f'ADC{k}',f'R{[3,4,5,6][k]}.2',f'U3.A{k}:A')
net('TEMP_DQ','U1.D3','J3.2','U6.DQ','TP7.PAD')
net('I2C_SDA','U1.D4','U3.D','U4.SDA','U5.SDA')
net('I2C_SCL','U1.D5','U3.C','U4.SCL','U5.SCL')
for k in range(1,4):
 net(f'KEY{k}',f'U1.D{5+k}',f'R{8+k}.2',f'R{11+k}.1')
 net(f'KEY{k}_CONTACT',f'R{11+k}.2',f'SW{k}.A')
net('BUZZ_CTRL','U1.D9','R15.1'); net('BUZZ_S','R15.2','R16.1','U7.S')
NC=['U1.D2','U1.D10','U1.5V','U2.ON','U2.SW_EXT','U5.INT','U5.LP','U5.RST']
pins={}
for n,pp in N.items():
 for p in pp:
  assert p not in pins, f'Duplicate assignment {p}'
  pins[p]=n
for k in range(1,17):
 assert f'R{k}.1' in pins and f'R{k}.2' in pins
 assert pins[f'R{k}.1']!=pins[f'R{k}.2']
for p in NC:assert p not in pins
assert pins['R5.1']=='DRIVE_A' and pins['R3.1']=='E1'
assert pins['U1.BAT+']=='VBAT_SW' and pins['U1.3V3']=='+3V3'

def writecsv(name,head,rows):
 with (OUT/name).open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.writer(f);w.writerow(head);w.writerows(rows)
writecsv('netlist.csv',['NET','REF.PIN'],[(n,p) for n,pp in N.items() for p in pp])
writecsv('wire_connections.csv',['연결망','시작 단자','연결 단자','의미'],[(n,pp[0],p,'동일 NET의 모든 단자는 전기적으로 연결') for n,pp in N.items() for p in pp[1:]])
(OUT/'electrical_definition.json').write_text(json.dumps({'revision':'ASM-R3','nets':N,'no_external_connection':NC},ensure_ascii=False,indent=2),encoding='utf-8')

BOM=[
 ['U1','1','XIAO ESP32-S3 Sense','기존 보드와 카메라','사용자 제공','SD 카드 제거'],
 ['U2','1','Pololu Mini MOSFET Slide Switch LV #2810','구매품','사용자 제공','ON/SW_EXT 외부 미연결'],
 ['U3','1','DFRobot Gravity ADS1115 DFR0553','3.3V, ADDR=0x48','사용자 제공','모듈 단자 A/+/- 구분'],
 ['U4','1','SSD1306 OLED','I2C 128×32, 4핀','사용자 제공','3.3V, 주소 실측 기록'],
 ['U5','1','SparkFun SEN-19013','VL53L5CX Mini / Qwiic','사용자 제공','0x29, 기존 케이블 재사용'],
 ['U6','1','EM Tech DS18B20','15584272, Ø6×50, 풀업 내장형','기존 헤드 재사용','VDD 빨강 / DQ 노랑 / GND 검정'],
 ['U7','1','ONE005 액티브 부저 모듈','3.3V 공급 / S 제어','사용자 제공','완제품 모듈, GPIO 전원 공급 금지'],
 ['B1','1','DTP803040','1셀 3.7V, 1000mAh, 4.2V 충전형','사용자 제공','보호회로·허용전류·극성 수령 검수'],
 ['E1,E2','2','SUS316L 전극','Ø5mm, 기존 헤드 결착 상태','기존 헤드 재사용','팁 돌출 10mm 유지'],
 ['SW1~SW3','3','VLT-TSW015 택트','12×12×10mm, 순간 NO 접점','사용자 제공','서로 다른 접점군 한 다리씩'],
 ['R1,R2,R12~R15','6','1kΩ 저항','1%, 1/4W, 다리형','보유품 사용','R1/R2 실측값 별도 기록'],
 ['R3~R11,R16','10','10kΩ 저항','1%, 1/4W, 다리형','보유품 사용','회로도 R번호대로 표기'],
 ['C1~C3','3','0.1µF 세라믹','보유 50V 제품 사용 가능','보유품 사용','각 모듈 전원 가까이'],
 ['J1','1쌍','배터리 상대 커넥터·전선','기존 51021-0200 2핀 1.25mm에 결합','실물 짝 확인','극성 확인, 배터리 선 절단 금지'],
 ['J2','1','2P 나사 단자대','5.08mm 피치, 기판용','업체 준비','1=E1 / 2=E2'],
 ['J3','1','3P 나사 단자대','5.08mm 피치, 기판용','업체 준비','1=VDD / 2=DQ / 3=GND'],
 ['PCB-A','1','배선 조립 기판','2.54mm 만능기판 또는 별도 캐리어','업체 준비','모듈 크기 실측 후 외형 제안'],
 ['WIRE / FIX','1식','절연 전선·고정·수축튜브','전원 AWG24 / 신호 AWG26 권장','업체 준비','기존 모듈 케이블 우선 재사용'],
]
writecsv('BOM.csv',['REF','수량','품명','규격','조달','조립 주의'],BOM)

# Schematic graphics: actual terminal stubs, reference designators and global nets.
S=[]; d=None
def txt(x,y,s,size=19,bold=False,col=INK,anchor='start'):
 d.add(String(x,H-y,s,fontName='KB' if bold else 'K',fontSize=size,fillColor=HexColor(col),textAnchor=anchor))
def ln(x,y,xx,yy,col=INK,w=1.8,dash=None):
 v=Line(x,H-y,xx,H-yy,strokeColor=HexColor(col),strokeWidth=w)
 if dash:v.strokeDashArray=dash
 d.add(v)
def box(x,y,w,h,fill='#FFFFFF',stroke=INK):d.add(Rect(x,H-y-h,w,h,fillColor=HexColor(fill),strokeColor=HexColor(stroke),strokeWidth=1.7))
def dot(x,y):d.add(Circle(x,H-y,4,fillColor=HexColor(INK),strokeColor=None))
def circle(x,y,r=5):d.add(Circle(x,H-y,r,fillColor=white,strokeColor=HexColor(INK),strokeWidth=1.5))
def gnd(x,y):
 ln(x,y,x,y+12);ln(x-15,y+12,x+15,y+12);ln(x-10,y+19,x+10,y+19);ln(x-4,y+26,x+4,y+26)
def label(x,y,n,anchor='start'):txt(x,y-7,n,18,True,BLUE,anchor)
def rh(x,xx,y,ref,val):
 m=(x+xx)/2;ln(x,y,m-30,y);box(m-30,y-10,60,20);ln(m+30,y,xx,y)
 txt(m,y-40,ref,18,True,anchor='middle');txt(m,y-18,val,17,anchor='middle')
def rv(x,y,yy,ref,val,left=False):
 m=(y+yy)/2;ln(x,y,x,m-25);box(x-10,m-25,20,50);ln(x,m+25,x,yy)
 xx=x-20 if left else x+20;a='end' if left else 'start'
 txt(xx,m-5,ref,18,True,anchor=a);txt(xx,m+20,val,17,anchor=a)
def tp(x,y,ref):ln(x,y,x,y-23);circle(x,y-28,5);txt(x+11,y-28,ref,15,col=GRAY)
def nc(x,y):ln(x-5,y-5,x+5,y+5);ln(x-5,y+5,x+5,y-5)
def pin(x,y,name,netname,side='left',length=150):
 if side=='left':
  ln(x-length,y,x,y);txt(x+10,y+6,name,18);label(x-length,y,netname)
 else:
  ln(x,y,x+length,y);txt(x-10,y+6,name,18,anchor='end');label(x+length,y,netname,'end')
def lines(x,y,ss,size=18,dy=30,col=INK):
 for i,s in enumerate(ss):txt(x,y+i*dy,s,size,col=col)
def header(n,title,scope):
 global d;d=Drawing(W,H);S.append(d)
 box(20,20,W-40,H-40);txt(45,56,'ASM-R3  /  조립업체 전달용  /  MODULE-LEVEL SCHEMATIC',17,True,TEAL)
 txt(45,99,title,30,True);txt(45,133,scope,18,col=GRAY)
 ln(20,1020,1580,1020);ln(1100,1020,1100,1080);ln(1430,1020,1430,1080)
 txt(40,1046,'스마트 염도계 · 보유 모듈 배선 조립 / 2026-11-20',17,True)
 txt(40,1072,'같은 NET 이름은 모두 연결. ● 접속 / 교차선에 점이 없으면 비접속 / × 외부 배선 없음.',15,col=GRAY)
 txt(1120,1046,'기존 헤드 재사용 / 배터리 내장',16);txt(1120,1072,'기판 조립·통합 검수 기준',16)
 txt(1505,1057,f'{n} / 6',20,True,anchor='middle')

header(1,'S01  전원 · 메인보드 · OLED · ToF','모듈 단자의 실제 실크 이름을 사용합니다. 모듈을 칩으로 대체하지 않습니다. U3/U6/U7은 다음 시트에서 연결합니다.')
# Battery and mating connector. J1 numbers deliberately not made up.
txt(65,193,'B1  DTP803040',23,True);txt(65,225,'3.7V / 1000mAh / 1S',18)
ln(95,265,95,290);ln(65,290,125,290,w=3);ln(78,301,112,301,w=3);ln(95,301,95,337)
ln(95,265,205,265);ln(95,337,205,337);circle(210,265);circle(210,337)
txt(235,269,'J1.B+  →  BATT_RAW',18,True,BLUE);txt(235,341,'J1.B-  →  GND',18,True,BLUE)
txt(65,389,'J1 = 기존 배터리와 맞는 상대 커넥터.',17)
txt(65,418,'B+/B-는 논리 표기. 실물 핀 번호를 추정하지 말 것.',16)
txt(65,447,'멀티미터로 실제 극성 확인 후 전선에 + / - 라벨.',16)
box(180,510,360,220,LIGHT);txt(360,544,'U2  Pololu #2810 LV',23,True,anchor='middle')
pin(180,587,'VIN','BATT_RAW',length=120);pin(540,587,'VOUT','VBAT_SW',side='right',length=140)
tp(630,587,'TP1')
pin(180,642,'GND','GND',length=120);ln(540,650,580,650);nc(580,650);txt(530,656,'ON',18,anchor='end')
tp(120,642,'TP0')
ln(540,700,580,700);nc(580,700);txt(530,706,'SW_EXT',18,anchor='end')
lines(65,790,['U2 내장 슬라이드 스위치로 배터리 경로 개폐.',
 '충전은 스위치 ON + XIAO USB-C 연결.',
 'USB 연결 중에는 OFF라도 보드가 켜질 수 있음.',
 '측정 시 USB 분리. 별도 충전 모듈은 실장하지 않음.',
 '배터리 +를 3V3 또는 5V 핀에 연결하지 않음.'],17,34)
# Complete main board symbol, pin labels on each stub.
box(825,195,290,760,LIGHT);txt(970,231,'U1  XIAO',25,True,anchor='middle');txt(970,260,'ESP32-S3 Sense',21,True,anchor='middle')
u1=[('D0 / GPIO1','DRIVE_A'),('D1 / GPIO2','DRIVE_B'),('D2 / GPIO3',None),('D3 / GPIO4','TEMP_DQ'),('D4 / GPIO5','I2C_SDA'),('D5 / GPIO6','I2C_SCL'),('D6 / GPIO43','KEY1'),('D7 / GPIO44','KEY2'),('D8 / GPIO7','KEY3'),('D9 / GPIO8','BUZZ_CTRL'),('D10 / GPIO9',None)]
for i,(p,n) in enumerate(u1):
 y=312+i*48
 if n:pin(825,y,p,n,length=140)
 else:ln(790,y,825,y);txt(835,y+6,p,18);nc(790,y)
for y,p,n in [(838,'BAT+','VBAT_SW'),(875,'BAT-','GND'),(912,'GND','GND')]:pin(825,y,p,n,length=140)
pin(1115,315,'3V3','+3V3',side='right',length=105);tp(1170,315,'TP2')
ln(1115,365,1150,365);nc(1150,365);txt(1105,371,'5V',18,anchor='end')
txt(970,840,'USB-C',22,True,anchor='middle');txt(970,874,'5V 입력 / 충전 / 업로드',15,anchor='middle');txt(970,915,'카메라 기존 결합 유지',15,anchor='middle')
for y,ref,model in [(200,'U4','SSD1306 128×32'),(565,'U5','VL53L5CX MINI')]:
 box(1350,y,200,265,LIGHT);txt(1450,y+33,ref,23,True,anchor='middle');txt(1450,y+62,model,16,True,anchor='middle')
 for yy,p,n in [(y+105,'VCC' if ref=='U4' else '3V3','+3V3'),(y+148,'GND','GND'),(y+191,'SDA','I2C_SDA'),(y+234,'SCL','I2C_SCL')]:pin(1350,yy,p,n,length=120)
txt(1225,498,'OLED 주소는 0x3C / 0x3D 중 실측 기록.',15)
txt(1225,530,'커넥터 좌우 순서는 실물 실크 기준.',15)
lines(1215,872,['U5 7-bit I2C 주소 0x29.', 'INT / LP / RST 외부 미연결.', 'Qwiic PRT-17912 케이블 재사용.', 'I2C 추가 풀업은 실장하지 않음.'],16,30)

header(2,'S02  전극 구동 · ADC · 헤드 연결','R1~R8을 빠짐없이 실장합니다. U3는 DFR0553 완제품 모듈입니다. A0~A3의 A(신호) 접점만 센스선에 연결합니다.')
yy=335;label(65,yy,'DRIVE_A');ln(65,yy,260,yy);rh(260,460,yy,'R1','1kΩ / 1%');ln(460,yy,560,yy)
ln(1020,yy,1140,yy);rh(1140,1340,yy,'R2','1kΩ / 1%');ln(1340,yy,1530,yy);label(1530,yy,'DRIVE_B','end')
for x in [170,510,1080,1430]:dot(x,yy)
ln(115,yy,115,235);rh(115,350,235,'R7','10kΩ');gnd(350,235);dot(115,yy)
ln(1480,yy,1480,235);rh(1250,1480,235,'R8','10kΩ');gnd(1250,235);dot(1480,yy)
tp(170,yy,'TP3');tp(1430,yy,'TP4');tp(510,yy,'TP5');tp(1080,yy,'TP6')
# Head connector terminals on the actual E1/E2 nodes.
ln(560,yy,560,260);circle(560,255);txt(583,278,'J2.1 / E1',18,True,BLUE)
ln(1020,yy,1020,260);circle(1020,255);txt(997,278,'J2.2 / E2',18,True,BLUE,anchor='end')
ln(560,250,640,250,dash=[7,4]);ln(640,250,640,204,dash=[7,4]);ln(1020,250,945,250,dash=[7,4]);ln(945,250,945,204,dash=[7,4])
ln(640,196,640,235,w=5);ln(945,196,945,235,w=5)
ln(650,216,935,216,col=GRAY,dash=[5,5]);txt(792,191,'기존 금속 전극 E1 / 시료 / E2',17,anchor='middle')
txt(790,380,'J2: 2P / 5.08mm 나사 단자대',17,anchor='middle')
txt(790,410,'기존 전극의 마른 연결부에 접속',17,anchor='middle')
for x,ref,n in [(170,'R5','ADC2'),(510,'R3','ADC0'),(1080,'R4','ADC1'),(1430,'R6','ADC3')]:
 rv(x,335,520,ref,'10kΩ',left=x>1000);label(x,552,n,'middle');ln(x,520,x,578)
box(65,578,1465,250,LIGHT);txt(790,621,'U3  DFRobot Gravity ADS1115 / DFR0553  (ADDR = 0x48)',24,True,anchor='middle')
for x,p in [(170,'A2 : A'),(510,'A0 : A'),(1080,'A1 : A'),(1430,'A3 : A')]:txt(x,660,p,21,True,anchor='middle')
for x,name,n in [(195,'VCC / +','+3V3'),(555,'GND / -','GND'),(985,'D / SDA','I2C_SDA'),(1365,'C / SCL','I2C_SCL')]:
 txt(x,767,name,19,True,anchor='middle');ln(x,828,x,866);label(x,895,n,'middle')
txt(72,936,'센스 저항 4개는 ADC 입력 직렬 저항입니다. R5/R6은 1kΩ 앞의 DRIVE 노드, R3/R4는 1kΩ 뒤 전극 노드에 연결.',17)
txt(72,971,'A0~A3 행의 + / - 접점에는 전극선을 연결하지 않음. 미사용 행의 + / -에는 추가 배선 없음. BAT43 / 1N5819 미실장.',17)

header(3,'S03  버튼 3개 · 온도센서 · 부저 · 전원 바이패스','NO 순간 스위치를 사용합니다. 모든 GND는 S01과 공통입니다. 제어신호는 같은 이름으로 U1에 연결합니다.')
for i in range(3):
 y=300+i*200;label(65,y,f'KEY{i+1}');ln(65,y,280,y);dot(230,y)
 label(230,y-112,'+3V3','middle');rv(230,y-100,y,f'R{9+i}','10kΩ')
 rh(280,490,y,f'R{12+i}','1kΩ');ln(490,y,585,y)
 dot(490,y);ln(490,y,490,y+52);ln(490,y+52,700,y+52);label(500,y+52,f'KEY{i+1}_CONTACT')
 circle(590,y);ln(590,y-8,645,y-46);circle(655,y);ln(660,y,705,y);gnd(705,y)
 txt(620,y-68,f'SW{i+1}',19,True,anchor='middle');txt(730,y+6,['측정','모드','저장'][i],18)
 txt(600,y+27,'A',15);txt(665,y+27,'B',15)
txt(55,873,'SW1~3 접점 A/B는 서로 다른 접점군입니다.',17)
txt(55,904,'4개 다리 중 같은 접점군끼리는 내부에서 항상 연결됩니다.',17)
txt(55,935,'다른 접점군에서 한 다리씩 사용. 접점군은 도통 검사로 식별.',17)
# Temperature connector / corresponding sensor lead colors.
box(1190,190,340,220,LIGHT);txt(1360,224,'U6  DS18B20',23,True,anchor='middle')
for y,term,pinname,n,color in [(270,'J3.1','VDD / 빨강','+3V3',INK),(320,'J3.2','DQ / 노랑','TEMP_DQ',INK),(370,'J3.3','GND / 검정','GND',INK)]:
 pin(1190,y,pinname,n,length=180);circle(1075,y);txt(1075,y+27,term,15,anchor='middle')
txt(960,448,'J3 3P 단자대 순서  1=빨강 / 2=노랑 / 3=검정',17)
txt(960,479,'이 제품은 4.7kΩ 풀업 내장형. 외부 풀업 추가 없음.',17)
tp(1010,320,'TP7')
# Active buzzer module, true S node pull down.
box(1270,570,260,230,LIGHT);txt(1400,603,'U7  ONE005',23,True,anchor='middle')
pin(1270,647,'+ / VCC','+3V3',length=180);pin(1270,752,'- / GND','GND',length=50)
label(840,700,'BUZZ_CTRL');ln(840,700,960,700);rh(960,1140,700,'R15','1kΩ');ln(1140,700,1270,700);txt(1280,706,'S',18);dot(1150,700);label(1250,700,'BUZZ_S','end')
rv(1150,700,855,'R16','10kΩ');gnd(1150,855)
txt(960,925,'C1 / C2 / C3 각각 0.1µF, U3 / U4 / U5 전원 바로 옆.',17)
for i,x in enumerate([970,1180,1390]):
 label(x,953,'+3V3','middle');ln(x,953,x,966)
 ln(x-13,966,x+13,966);ln(x-13,974,x+13,974);ln(x,974,x,984);gnd(x,984)
 txt(x+25,966,f'C{i+1}',16,True);txt(x+25,991,'0.1µF',15)

# Full connection and acceptance specification. Text sheets are also vector PDF pages.
header(4,'A01  접속부 · 전원 분배 · 검사점','작업자는 netlist.csv로 회로망 전체를 확인하고 wire_connections.csv로 각 연결을 대조합니다. 핀 좌우 순서를 사진으로 추측하지 않습니다.')

def paragraph(x,y,w,s,size=18):
 p=Paragraph(s,ParagraphStyle('para',fontName='K',fontSize=size,leading=size*1.55,textColor=HexColor(INK),wordWrap='CJK'))
 _,h=p.wrap(w,2000);d.add(p.asDrawing()) if False else None
 # Paragraph drawing is added to each finished page separately, preserving CJK.
 paragraphs.setdefault(len(S),[]).append((p,x,y,w,h));return y+h
paragraphs={}
def tbl(x,y,widths,headers,rows,size=16):
 sty=ParagraphStyle('cell',fontName='K',fontSize=size,leading=size*1.4,textColor=HexColor(INK),wordWrap='CJK')
 th=ParagraphStyle('th',parent=sty,fontName='KB',textColor=white)
 data=[[Paragraph(html.escape(str(v)),th) for v in headers]]+[[Paragraph(html.escape(str(v)),sty) for v in row] for row in rows]
 t=Table(data,colWidths=widths)
 t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),HexColor(INK)),('ROWBACKGROUNDS',(0,1),(-1,-1),[white,HexColor(LIGHT)]),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),10),('RIGHTPADDING',(0,0),(-1,-1),10),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8)]))
 _,h=t.wrap(sum(widths),2000);assert y+h<1008,(len(S),y,h)
 tables.setdefault(len(S),[]).append((t,x,y,h));return y+h
tables={}
tbl(45,175,[130,250,490,640],['접속부','단자','연결','실물 작업 지시'],[
 ['J1','B+ / B-','B+→U2.VIN / B-→GND','기존 배터리 단자에 맞는 짝. B+/B-는 도면 논리명이며 제조사 cavity 번호가 아님. 실측 후 라벨.'],
 ['J2','1 / 2','1=E1 / 2=E2','2P 5.08mm 단자대. 기존 전극 마른 부분으로 각각 연결. 스테인리스 봉 직접 납땜을 전제하지 않음.'],
 ['J3','1 / 2 / 3','1=+3V3 / 2=TEMP_DQ / 3=GND','3P 5.08mm 단자대. 빨강/노랑/검정. U6 케이블 검정 피복은 센서 외피이며 전극 아님.'],
 ['U3 I2C','+ / - / D / C','+3V3 / GND / I2C_SDA / I2C_SCL','동봉 Gravity 케이블 또는 해당 핀 사용. A0~A3 센스선은 별도 4가닥.'],
 ['U3 센스','A0:A~A3:A','ADC0 / ADC1 / ADC2 / ADC3','각 채널 A 접점에 연결. 채널 + 또는 - 접점에 꽂지 않음.'],
 ['U4 OLED','VCC / GND / SDA / SCL','+3V3 / GND / I2C_SDA / I2C_SCL','제품 인쇄를 대조해 하네스 제작. 모듈마다 4핀 배열이 다를 수 있음.'],
 ['U5 ToF','3V3 / GND / SDA / SCL','+3V3 / GND / I2C_SDA / I2C_SCL','PRT-17912 / Qwiic 재사용. INT/LP/RST는 외부 배선 없음.'],
 ['U7 부저','+ / - / S','+3V3 / GND / BUZZ_S','완제품 부저 모듈의 신호핀. 전원은 GPIO에 연결하지 않음.'],
 ['SW1~3','A / B 접점군','KEYn_CONTACT / GND','각기 다른 접점군에서 한 다리씩 사용. 나머지 두 다리는 외부 배선 불필요.'],
 ],16)
tbl(45,805,[160,595,160,595],['검사점','연결망','검사점','연결망'],[
 ['TP0','GND / 계측기 기준','TP1','VBAT_SW / 스위치 뒤 배터리 전압'],
 ['TP2','+3V3','TP3 / TP4','DRIVE_A / DRIVE_B'],
 ['TP5 / TP6','E1 / E2 전극 노드','TP7','TEMP_DQ / 온도 데이터']
],16)

header(5,'A02  BOM · 조립 작업 지시','R번호와 J번호는 이 문서 ASM-R3가 기준입니다. 이전 개념도 R2 및 예전 BAT43 추가안으로 혼합 조립하지 않습니다.')
tbl(45,171,[190,65,550,335,370],['REF','수량','품명 / 규격','조달','작업 핵심'],[[r[0],r[1],r[2]+' / '+r[3],r[4],r[5]] for r in BOM],14)

header(6,'A03  조립 범위 · 통전 검사 · 납품 기준','견적과 제작 지시에 사용할 문서입니다. 현재 수량 1대 기준. 배선은 지정됐으며 기판 배치와 외함 체결부는 업체 실측 설계 범위입니다.')
txt(45,183,'조립 작업 범위',23,True,TEAL)
paragraph(45,202,710,'보유 모듈 U1~U7, 배터리 B1, 버튼 SW1~3, 기존 3봉 헤드를 받아 모듈 간 배선과 R1~R16, C1~C3을 캐리어 기판에 조립합니다. J1~J3을 마킹하고 모듈·배터리·배선이 움직이지 않도록 고정합니다. 느슨한 점퍼선 접촉만으로 납품하지 않습니다.',18)
paragraph(45,358,710,'신호선 AWG26, 전원선 AWG24를 권장합니다. 기판 간 신호선은 가급적 100mm 이내로 하고 늘어나면 I2C·온도 통신을 다시 확인합니다. 전극 센스선을 부저와 카메라 전원선에서 떨어뜨리고, 젖는 구역에는 기판·나사 단자·배터리 연결부를 두지 않습니다.',18)
paragraph(45,514,710,'J2 출력부터 기존 봉의 마른 연결부까지는 기존 접속부를 재사용하거나 업체가 고정 클램프를 제안합니다. 봉 직접 납땜이나 팁 길이·간격 변경은 작업 범위에 넣지 않습니다. 본체 3D 출력물 체결과 방수 구조는 회로 조립 견적과 구분해 산정합니다.',18)
txt(45,698,'소프트웨어와 납품물',23,True,TEAL)
paragraph(45,717,710,'동봉 HeadWaterTest는 전극·온도 확인용 기존 소스입니다. OLED·ToF·버튼·부저까지 통합한 완성 펌웨어는 아닙니다. 업체는 별도 점검 코드로 각 모듈을 확인하고, 최종 통합 펌웨어·염도 교정은 별도 항목으로 견적에 표시합니다. SD/SPI를 초기화하지 않고 SD 카드는 제거합니다.',18)
paragraph(45,891,710,'납품은 조립물, 배선 양면 사진, 실제 연결표, 시험 결과표, 변경 부품 명세와 업체 제작 시험 코드로 구성합니다. 소스 없는 완성 기판만 납품하지 않습니다.',17)
txt(830,183,'통전 전과 후의 검사 순서',23,True,TEAL)
tests=[
 ['1','무전원','B1과 USB를 분리. netlist 대조, 전원 역극성/납땜 브리지 검사. R1/R2는 실장 전 실측해 기록.'],
 ['2','USB만 연결','B1 분리 상태에서 USB로 기동. TP2와 모듈 전원 실측. +3V3 목표 3.2~3.4V, 지속 단락·발열·재부팅 없음.'],
 ['3','통신·조작','U3=0x48, OLED=0x3C/0x3D, ToF=0x29 주소와 실제 읽기 확인. 온도 유효값, 버튼 3개 LOW 전환, 부저 ON/OFF 검사.'],
 ['4','전극 기능','J2.1-J2.2에 1kΩ 시험 저항. 양극성 구동과 RAW 약 66.7 확인(초기 기능 허용 60~73). 물성/염도 정확도 기준은 아님.'],
 ['5','배터리 구동','B1 보호회로·허용전류·짝 단자 극성 확인 후 연결. USB 분리 + U2 ON에서 구동. 실제 피크 전류를 배터리 허용값과 대조.'],
 ['6','충전·종료','스위치 ON에서 USB 충전 확인. 배터리 규격의 4.2V 충전 종지를 대조. U2 OFF+USB 분리 시 동작 정지. OFF 충전 요구는 별도 회로 변경.']]
tbl(830,206,[45,125,515],['순서','조건','확인 및 기록'],tests,16)
paragraph(830,810,685,'동작 검증 전 대량 제작을 진행하지 않습니다. 배터리 허용 전류가 부족하거나 모듈 전압이 무너지면 실측 결과를 바탕으로 발주자에게 변경안을 제출합니다. 이 문서는 모듈 조립 기준이며, 커스텀 PCB 제작에는 별도 PCB 배치·배선·제조 데이터가 필요합니다.',16)
txt(830,968,'제조사 문서와 변경 이력은 동봉 README_업체전달.md 참조.',15,col=GRAY)

# Export editable schematic sheets, plus complete A3 PDF with true vector symbols.
pdf=OUT/'pdf'/'조립의뢰용_실배선회로도_ASM-R3.pdf'
page=landscape(A3);c=canvas.Canvas(str(pdf),pagesize=page)
c.setTitle('조립의뢰용 실배선 회로도 ASM-R3');c.setAuthor('AI 창업프로젝트')
scale=min(page[0]/W,page[1]/H)
for i,dd in enumerate(S,1):
 if i>1:c.showPage()
 c.saveState();c.translate((page[0]-W*scale)/2,(page[1]-H*scale)/2);c.scale(scale,scale);renderPDF.draw(dd,c,0,0)
 for p,x,y,w,h in paragraphs.get(i,[]):p.drawOn(c,x,H-y-h)
 for t,x,y,h in tables.get(i,[]):t.drawOn(c,x,H-y-h)
 c.restoreState()
 if i<=3:
  svg=OUT/'editable_schematics'/f'S0{i}_ASM-R3.svg';renderSVG.drawToFile(dd,str(svg))
  svg.write_text(svg.read_text(encoding='utf-8').replace('font-family: KB','font-family: Malgun Gothic').replace('font-family: K','font-family: Malgun Gothic'),encoding='utf-8')
c.save()
src=Path(r'C:\Users\Yeon\Documents\Codex\2026-11-14\head-test\HeadWaterTest\HeadWaterTest.ino')
shutil.copy2(src,OUT/'test_firmware'/'HeadWaterTest.ino')
readme='''# 조립업체 전달 사항 / ASM-R3 / 2026-11-20

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
'''
(OUT/'README_업체전달.md').write_text(readme,encoding='utf-8')
validation={'pages':len(S),'nets':len(N),'connected_pin_endpoints':len(pins),'external_resistors':16,'external_capacitors':3,'duplicate_pin_assignments':0,'firmware_sha256':hashlib.sha256(src.read_bytes()).hexdigest()}
(ROOT/'work'/'definition_checks.json').write_text(json.dumps(validation,indent=2),encoding='utf-8')
print(json.dumps(validation))
