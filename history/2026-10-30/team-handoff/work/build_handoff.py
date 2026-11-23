"""Generate a Korean team review pack. Existing head CAD is copied, not redesigned.
The EC circuit is an unbuilt engineering proposal, not a validated salinity meter.
"""
from pathlib import Path
import json, math, re, hashlib, collections, struct, shutil, html
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.graphics.shapes import Drawing, Rect, Line, Circle, String, Polygon
from reportlab.graphics import renderPDF, renderSVG
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / 'package'
PDF = ROOT / 'output/pdf/스마트염도계_팀공유_설계검토본.pdf'
DATE = '2026-10-30'
pdfmetrics.registerFont(TTFont('Korean', r'C:\Windows\Fonts\malgun.ttf'))
pdfmetrics.registerFont(TTFont('KoreanBold', r'C:\Windows\Fonts\malgunbd.ttf'))
INK = '#163047'; MUTED = '#526678'; BLUE = '#2365A0'; TEAL = '#217D79'
LIGHT = '#EEF4F8'; GOLD = '#A57517'; ORANGE = '#B94E28'; RED = '#A92B35'
PAGE_W, PAGE_H = A4
LEFT = 38; RIGHT = PAGE_W-38; WIDTH = RIGHT-LEFT

SOURCES = [
 ('S1', 'Seeed XIAO ESP32-S3: 핀 배치·배터리 사용', 'https://wiki.seeedstudio.com/xiao_esp32s3_getting_started/'),
 ('S2', 'Seeed Sense: 카메라·SD 공유 핀', 'https://wiki.seeedstudio.com/xiao_esp32s3_pin_multiplexing/'),
 ('S3', 'DFRobot DFR0553: 단자·전원', 'https://wiki.dfrobot.com/dfr0553/'),
 ('S4', 'DFR0553 모듈 실제 회로: 입력 직렬 300Ω', 'https://dfimg.dfrobot.com/wiki/19356/DFR0553_gravity-ads1115-16-big-adc-module_schematics_V1.0.pdf'),
 ('S5', 'TI ADS1115: 입력 범위·860SPS·보호', 'https://www.ti.com/lit/ds/symlink/ads1115.pdf'),
 ('S6', 'SparkFun VL53L5CX: 전원·주소·풀업', 'https://learn.sparkfun.com/tutorials/qwiic-tof-imager---vl53l5cx-hookup-guide/all'),
 ('S7', 'ONE005 부저: 3.3~5V, HIGH 활성', 'https://m.one-stop.co.kr/goods/view_contents?no=17838&zoom=1'),
 ('S8', '구매 온도센서 제품·외형 치수', 'https://www.devicemart.co.kr/goods/view?no=15584272'),
 ('S9', '온도 프로브 판매처 치수 그림: Ø6×50mm', 'https://www.devicemart.co.kr/data/editor/temp_17309466766911.jpg'),
 ('S10', 'Analog Devices DS18B20: 3선 전원·1-Wire', 'https://www.analog.com/media/en/technical-documentation/data-sheets/ds18b20.pdf'),
 ('S11', 'P5/P6 O링 명목 치수', 'https://www.awimach.com/sealing/products/size/oring.php'),
 ('S12', 'Vishay BAT43: 소신호 쇼트키 다이오드', 'https://www.vishay.com/docs/85660/bat42.pdf'),
 ('S13', 'Vishay 1N5819: 정류용 부품 특성', 'https://www.vishay.com/docs/88525/1n5817.pdf'),
 ('S14', 'Pololu #2810 전원 스위치', 'https://www.pololu.com/product/2810'),
 ('S15', 'Espressif ESP32-S3 MCPWM', 'https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/peripherals/mcpwm.html'),
 ('S16', '상용 전도도 센서: 측정면 전체 침수·기포', 'https://atlas-scientific.com/files/EC_K_10_probe.pdf'),
]

PINS = [
 ('3V3', '-', '공통 3.3V 전원', 'ADS VCC, OLED VCC, ToF 3V3, 온도 VDD, 부저 +'),
 ('GND', '-', '공통 기준선', '모듈 GND, 온도 GND, 버튼 반대편'),
 ('D0', 'GPIO1', '전극 구동 A', 'R1 1kΩ → E1; A2로 구동 전압 감시'),
 ('D1', 'GPIO2', '전극 구동 B', 'R2 1kΩ → E2; A3로 구동 전압 감시'),
 ('D2', 'GPIO3', '미사용', '스트래핑 핀: 이번 배선에서는 비워 둠'),
 ('D3', 'GPIO4', '온도 DATA', 'DS18B20 DATA. 내장 4.7kΩ 풀업 실물 확인'),
 ('D4', 'GPIO5', 'I2C SDA', 'ADS SDA/D, OLED SDA, ToF SDA를 병렬 연결'),
 ('D5', 'GPIO6', 'I2C SCL', 'ADS SCL/C, OLED SCL, ToF SCL을 병렬 연결'),
 ('D6', 'GPIO43', '버튼 1', '10kΩ 풀업 + 버튼 쪽 직렬 1kΩ; 누르면 LOW'),
 ('D7', 'GPIO44', '버튼 2', '10kΩ 풀업 + 버튼 쪽 직렬 1kΩ; 누르면 LOW'),
 ('D8', 'GPIO7', '버튼 3', 'SD SCK와 공유: SD 카드 제거·SD/SPI 비활성'),
 ('D9', 'GPIO8', '부저 제어', '직렬 1kΩ → ONE005 S; S에 10kΩ 풀다운'),
 ('D10', 'GPIO9', '미사용', 'SD MOSI와 공유; 이번에는 비워 둠'),
]
ADC = [
 ('A0 / S', 'E1', 'R3 10kΩ 경유', 'E1 금속봉 쪽 전압'),
 ('A1 / S', 'E2', 'R4 10kΩ 경유', 'E2 금속봉 쪽 전압'),
 ('A2 / S', 'D0 구동 노드', 'R5 10kΩ 경유', 'R1 앞 전압'),
 ('A3 / S', 'D1 구동 노드', 'R6 10kΩ 경유', 'R2 뒤 전압'),
]
PARTS_E = [
 ('메인보드·카메라', 'XIAO ESP32S3 Sense', '1', '구매 기록', '헤더 납땜 완료 여부는 실물 재확인'),
 ('ADC 모듈', 'DFRobot Gravity ADS1115 / DFR0553', '1', '구매 기록', 'ADDR=0x48; 색 대신 실크 S/+/- 확인'),
 ('화면', 'SSD1306 OLED, I2C, 128×32, 4핀', '1', '구매 기록', '3.3V 공급; 0x3C 또는 0x3D 스캔'),
 ('ToF 모듈', 'SparkFun SEN-19013 / VL53L5CX', '1', '구매 기록', '3.3V, 7비트 주소 0x29'),
 ('온도센서', 'EM Tech DS18B20 / 15584272', '1', '구매 기록', '금속관 Ø6×50mm; 4.7kΩ 내장형'),
 ('전극봉', 'SUS316L, Ø5mm', '2', '보유·결착 언급', '전체 길이 미확인; 위쪽 연결 구간 필요'),
 ('버튼', '12×12×10mm 택트, VLT-TSW015', '3 사용 / 6 구매', '구매 기록', '4다리 중 다른 접점군 하나씩 사용'),
 ('부저 모듈', 'ONE005 액티브, 3.3~5V', '1', '구매 기록', '3.3V로 사용; S=HIGH 활성'),
 ('저항 1kΩ', '1/4W, 1%', '6 실장 + 시험용', '10개 구매 기록', 'R1,R2,R12~R15; Rs는 실측'),
 ('저항 10kΩ', '1/4W, 1%', '10 실장', '10개 구매 기록', 'R3~R11,R16; 시험용 여유분 별도'),
 ('저항 4.7kΩ', '1/4W, 1%', '조건부', '10개 구매 기록', '내장 온도 풀업이 있으면 추가하지 않음'),
 ('커패시터', '0.1µF 세라믹, 50V', '3 사용', '10개 구매 기록', 'ADC/ToF/OLED 전원선 사이, 가까이'),
 ('입력 클램프', 'BAT43, 다리형 DO-35', '8', '이번 안의 추가 부품', 'D1~D8. 1N5819와 구분, 구매 전 규격 확인'),
 ('기존 다이오드', '1N5819', '0 실장 / 10 구매', '구매 기록', '정류용; 이번 정밀 ADC 입력에는 미사용'),
 ('Qwiic 케이블', 'PRT-17912', '1', '주문 언급', 'ToF 전용. Gravity 커넥터와 다름'),
 ('ADC I2C 케이블', 'Gravity 4핀 동봉 케이블', '1', '동봉 목록 확인', '도체 색 말고 VCC/GND/C/D 대조'),
 ('전원 스위치', 'Pololu Mini MOSFET LV #2810', '1', '구매 기록', '보유 목록에 포함. 충전 경로 적용은 보류'),
 ('리튬 배터리', '보호회로 있는 1셀 3.7V, 4.2V 충전형', '1 계획', '모델·보유 미확인', '충전 허용 전류·커넥터·실물 극성 확인 전 연결 금지'),
 ('배터리 커넥터', '배터리 실물과 맞는 짝 + 배선', '1세트 계획', '추가 커넥터 구매 언급', '51021-0200 언급만으로 핀 극성/납땜 상태 확정 불가'),
 ('시험 준비물', '브레드보드·점퍼·악어클립·멀티미터·USB 데이터선', '보유분', '구매/보유 언급', '최종 제품 BOM과 구분; 원가 합산하지 않음'),
]
PARTS_M = [
 ('전극봉용 O링', 'P5: 내경 4.8 × 굵기 1.9mm', '2', '실리콘 경도 50~60A 시험 조건; 실물 미검증'),
 ('온도센서용 O링', 'P6: 내경 5.8 × 굵기 1.9mm', '1', 'P5/P6는 크기 이름이며 식품 인증 아님'),
 ('평패킹', '실리콘 시트 1mm, 외곽 34×32mm', '1', '구멍 6mm×2 / 7mm×1. 도면 포함'),
 ('캡 결합 볼트', 'M3×25mm, 일반머리/렌치머리', '4', '길이는 머리 제외. 접시머리는 사용하지 않음'),
 ('봉 고정 나사', 'M3×12mm 나일론', '3', '기존과 같은 옆면 압착. 금속관 변형 주의'),
 ('육각너트', '일반 M3', '7', '결합용 4 + 봉 고정용 3; 보유분 재사용 가능'),
 ('전극 연결·인장 완화', '마른 구간 악어클립(시험) / 고정 단자(추후)', '2회로', '실제 단자 형태 미확정. 금속봉 직접 납땜 요구 아님'),
 ('배선 절연·고정', '절연 슬리브/수축튜브/케이블 고정', '필요량', '배터리/노출 도체 단락 방지; 식품 접촉부 사용 아님'),
 ('MVP 본체', 'PCB 지지·배터리 고정·광학창 구조', '미설계', '현재 헤드 모델에는 포함되지 않음'),
]
MODEL_INFO = [
 ('holder.stl', '상단 고정부', '1', '54×34×18', True),
 ('cap_core.stl', '중앙 캡', '1', '34×32×26.3', True),
 ('seal_retainer.stl', '아래 받침과 기둥', '1', '58×38×29.75', True),
 ('tip_alignment_jig.stl', '세 끝 높이 맞춤 받침', '1', '58×38×12', False),
 ('fit_coupon.stl', '봉 구멍 시험판', '먼저 1', '40×25×5', False),
]

def txt(d,x,y,s,size=25,color=INK,bold=False,anchor='start'):
    d.add(String(x,y,s,fontName='KoreanBold' if bold else 'Korean',fontSize=size,
                 fillColor=colors.HexColor(color),textAnchor=anchor))
def line(d,x1,y1,x2,y2,color=INK,width=3,dash=None):
    z=Line(x1,y1,x2,y2); z.strokeColor=colors.HexColor(color); z.strokeWidth=width
    if dash: z.strokeDashArray=dash
    d.add(z)
def box(d,x,y,w,h,title,sub='',fill=LIGHT,color=INK,fs=27):
    d.add(Rect(x,y,w,h,rx=12,ry=12,strokeColor=colors.HexColor(color),
               strokeWidth=2,fillColor=colors.HexColor(fill)))
    txt(d,x+w/2,y+h*.57,title,fs,color,True,'middle')
    if sub: txt(d,x+w/2,y+h*.25,sub,21,MUTED,False,'middle')
def dot(d,x,y,color=BLUE):
    d.add(Circle(x,y,5,fillColor=colors.HexColor(color),strokeColor=None))
def resistor_h(d,x1,x2,y,label):
    mid=(x1+x2)/2
    line(d,x1,y,mid-35,y); line(d,mid+35,y,x2,y)
    d.add(Rect(mid-35,y-14,70,28,strokeColor=colors.HexColor(INK),fillColor=colors.white,strokeWidth=3))
    txt(d,mid,y+32,label,22,INK,False,'middle')
def resistor_v(d,x,y1,y2,label):
    mid=(y1+y2)/2
    line(d,x,y1,x,mid+23); line(d,x,mid-23,x,y2)
    d.add(Rect(x-11,mid-23,22,46,strokeColor=colors.HexColor(INK),fillColor=colors.white,strokeWidth=2))
    txt(d,x+20,mid-6,label,21)
def ground(d,x,y):
    line(d,x,y,x,y-14); line(d,x-16,y-14,x+16,y-14,INK,2)
    line(d,x-10,y-22,x+10,y-22,INK,2); line(d,x-4,y-30,x+4,y-30,INK,2)
def arrow(d,x1,y1,x2,y2,color=TEAL):
    line(d,x1,y1,x2,y2,color,3)
    angle=math.atan2(y2-y1,x2-x1); l=12
    pts=[x2,y2,x2-l*math.cos(angle-.45),y2-l*math.sin(angle-.45),x2-l*math.cos(angle+.45),y2-l*math.sin(angle+.45)]
    d.add(Polygon(pts,fillColor=colors.HexColor(color),strokeColor=None))

def system_diagram():
    d=Drawing(1200,740)
    txt(d,25,705,'시스템 배선 개요 / USB 전원 시험 구성',33,INK,True)
    box(d,25,470,300,185,'XIAO ESP32S3 Sense','카메라는 동봉 보드 연결 유지')
    box(d,25,355,300,75,'USB-C 5V 입력','배터리 미연결로 먼저 시험',fs=24)
    line(d,175,430,175,470,BLUE)
    txt(d,350,650,'모든 모듈 VCC → 3V3 / GND → 공통 GND',25,TEAL,True)
    # A bundled two-conductor bus, not a short between SDA and SCL.
    line(d,325,560,420,560,BLUE); line(d,420,560,420,295,BLUE)
    line(d,350,547,370,573,BLUE,2); line(d,370,547,390,573,BLUE,2)
    txt(d,340,596,'I2C 두 선',22,BLUE,True)
    txt(d,345,519,'D4=SDA',20,BLUE); txt(d,345,488,'D5=SCL',20,BLUE)
    for y,title,sub in [(535,'ADS1115 / DFR0553','VCC,GND,D=SDA,C=SCL / 0x48'),(415,'SSD1306 OLED','VCC,GND,SDA,SCL / 0x3C 또는 0x3D'),(295,'SEN-19013 ToF','Qwiic 3.3V,GND,SDA,SCL / 0x29')]:
        line(d,420,y+35,485,y+35,BLUE); dot(d,420,y+35)
        box(d,485,y,685,85,title,sub,fs=27)
    box(d,25,205,300,95,'전극봉 2개','D0/D1 → 1kΩ씩 → E1/E2',fs=25)
    box(d,25,70,300,90,'DS18B20','D3 DATA / VDD 3.3V / GND',fs=25)
    box(d,485,175,325,80,'버튼 3개','D6 / D7 / D8, 누르면 LOW',fs=25)
    box(d,845,175,325,80,'ONE005 부저','D9 → 1kΩ → S',fs=25)
    txt(d,485,115,'주의: SD 카드 제거. SD/SPI 초기화 금지.',25,RED,True)
    txt(d,485,72,'버튼 풀업·직렬저항·부저 풀다운은 별도 배선표 참조.',22)
    txt(d,25,20,'파란 버스는 두 도선의 묶음: SDA끼리, SCL끼리만 연결. SDA와 SCL을 서로 연결하지 않음.',22,MUTED)
    return d

def ec_diagram():
    d=Drawing(1200,760)
    txt(d,25,724,'전극 측정 시험 회로 / 검증 전 설계안',33,INK,True)
    txt(d,25,680,'D0/D1은 0~3.3V를 번갈아 출력. 음전압을 ADC에 넣지 않습니다.',25)
    y=535
    txt(d,40,y+45,'D0 / GPIO1',23,BLUE,True)
    txt(d,1150,y+45,'D1 / GPIO2',23,BLUE,True,'end')
    line(d,65,y,220,y); resistor_h(d,220,440,y,'R1 1kΩ')
    resistor_h(d,760,980,y,'R2 1kΩ'); line(d,980,y,1135,y)
    box(d,470,490,260,90,'E1  ← 液체 →  E2'.replace('液체','소금물'),'',fs=24)
    line(d,440,y,470,y); line(d,730,y,760,y)
    for x in [150,440,760,1050]: dot(d,x,y)
    for x,target,lab in [(150,190,'R5 10kΩ'),(440,450,'R3 10kΩ'),(760,740,'R4 10kΩ'),(1050,1000,'R6 10kΩ')]:
        resistor_v(d,x,y,335,lab)
        line(d,x,335,target,335,BLUE); line(d,target,335,target,295,BLUE)
    box(d,70,190,1055,105,'DFRobot ADS1115 / 공통 전원 3.3V','각 A0~A3의 S(신호) 핀에 연결. +는 전원, -는 GND',fs=29)
    for x,s in [(190,'A2: D0'),(450,'A0: E1'),(740,'A1: E2'),(1000,'A3: D1')]: txt(d,x+14,310,s,23,BLUE,True)
    # The GPIO pulldowns are separate branches, before current-limiting resistors.
    line(d,90,y,90,625); resistor_h(d,90,290,625,'R7 10kΩ')
    line(d,290,625,310,625); ground(d,310,625); dot(d,90,y)
    line(d,1110,y,1110,625); resistor_h(d,890,1110,625,'R8 10kΩ')
    line(d,870,625,890,625); ground(d,870,625); dot(d,1110,y)
    txt(d,28,142,'各 입력: 10kΩ 뒤 노드에 BAT43 상·하단 클램프 한 쌍 (총 8개)'.replace('各','각'),25,TEAL,True)
    txt(d,28,98,'윗 다이오드: 애노드=ADC 쪽 / 띠 있는 캐소드=3V3',24)
    txt(d,28,58,'아랫 다이오드: 애노드=GND / 띠 있는 캐소드=ADC 쪽',24)
    txt(d,28,16,'보유 1N5819는 이번 입력 클램프에 미사용. 별도 클램프 상세 그림과 보호 한계 참조.',22,RED)
    return d

def clamp_diagram():
    d=Drawing(1200,515)
    txt(d,25,480,'ADC 입력 보호 / A0~A3 각각 동일하게 1회씩',30,INK,True)
    line(d,90,245,180,245); resistor_h(d,180,410,245,'R3~R6 10kΩ')
    line(d,410,245,1020,245,BLUE); dot(d,650,245)
    txt(d,80,290,'측정 노드',24); txt(d,1050,235,'ADC S',25,BLUE,True)
    # Diode upper: A at node, K bar toward positive rail.
    line(d,650,245,650,333)
    d.add(Polygon([629,333,671,333,650,369],strokeColor=colors.HexColor(INK),fillColor=colors.white,strokeWidth=2))
    line(d,624,369,675,369,INK,4); line(d,650,369,650,420)
    line(d,570,420,730,420,TEAL); txt(d,760,410,'3V3 / 캐소드 띠 쪽',25,TEAL)
    txt(d,680,330,'BAT43',23)
    # Diode lower: A at ground, K toward node.
    line(d,650,245,650,192)
    line(d,624,192,675,192,INK,4)
    d.add(Polygon([629,156,671,156,650,192],strokeColor=colors.HexColor(INK),fillColor=colors.white,strokeWidth=2))
    line(d,650,156,650,108); ground(d,650,108)
    txt(d,680,145,'BAT43',23); txt(d,740,190,'캐소드 띠 쪽 = ADC 노드',24)
    txt(d,25,40,'같은 전원에서만 동작. 보호용 전류 제한이며 외부 전원·낙뢰·ESD 내성을 보증하지 않음.',23,RED)
    return d

def ui_diagram():
    d=Drawing(1200,470)
    txt(d,25,435,'버튼 1개 / 3회 반복',30,INK,True)
    txt(d,720,435,'부저 1개',30,INK,True)
    txt(d,50,280,'D6/7/8',24,BLUE,True)
    line(d,50,245,230,245,BLUE); dot(d,230,245)
    resistor_v(d,230,390,245,'10kΩ'); txt(d,200,400,'3V3',23,TEAL)
    resistor_h(d,230,440,245,'1kΩ')
    line(d,440,245,470,245); d.add(Circle(470,245,5,fillColor=colors.HexColor(INK)))
    line(d,470,257,525,300); d.add(Circle(535,245,5,fillColor=colors.HexColor(INK)))
    line(d,535,245,575,245); line(d,575,245,575,180); ground(d,575,180)
    txt(d,410,335,'누르면 연결',23)
    txt(d,30,105,'4핀 버튼: 같은 접점군은 평소에도 연결됨.',23)
    txt(d,30,65,'다른 접점군에서 한 다리씩 사용. 멀티미터로 확인.',22)
    txt(d,715,280,'D9',24,BLUE,True)
    resistor_h(d,750,970,245,'R15 1kΩ')
    line(d,970,245,1110,245,BLUE); dot(d,1000,245)
    txt(d,1125,235,'S',27,BLUE,True)
    resistor_v(d,1000,245,110,'R16 10kΩ'); ground(d,1000,110)
    txt(d,720,350,'ONE005: + → 3V3 / - → GND',24,TEAL)
    txt(d,720,45,'S=HIGH일 때 울림. 부저 전원을 GPIO에서 공급하지 않음.',21,RED)
    return d

def mvp_diagram():
    d=Drawing(1200,850)
    txt(d,25,810,'전체 MVP 예상 배치 / 치수 미정·출력용 아님',32,INK,True)
    d.add(Rect(350,285,500,450,rx=24,ry=24,strokeColor=colors.HexColor(INK),strokeWidth=3,fillColor=colors.HexColor(LIGHT)))
    box(d,380,630,195,70,'카메라','기존 Sense 카메라',fill='#FFFFFF',fs=25)
    box(d,625,630,195,70,'ToF','광학창·시야 확보',fill='#FFFFFF',fs=25)
    box(d,390,490,420,95,'OLED 화면','0.91인치 / 전면',fill='#FFFFFF',fs=26)
    for x,s in [(450,'버튼1'),(600,'버튼2'),(750,'버튼3')]:
        d.add(Circle(x,420,34,strokeColor=colors.HexColor(TEAL),fillColor=colors.white,strokeWidth=2)); txt(d,x,414,s,20,anchor='middle')
    txt(d,600,330,'내부: XIAO · ADS · 부저 · 배터리',24,anchor='middle')
    line(d,600,285,600,245,TEAL,5)
    box(d,390,100,420,145,'현재 캡형 헤드 v2','58×38×47.75mm / 본체 결합부 미설계',fill='#DCEEEB',fs=27)
    for x in [490,600,710]: line(d,x,100,x,55,MUTED,14)
    line(d,335,125,865,125,BLUE,2,[8,5]); txt(d,910,112,'예시 수면',23,BLUE)
    txt(d,490,15,'전극',21,anchor='middle'); txt(d,600,15,'온도',21,anchor='middle'); txt(d,710,15,'전극',21,anchor='middle')
    txt(d,25,640,'마른 구역',27,TEAL,True)
    arrow(d,200,630,340,630)
    txt(d,25,200,'새 헤드 3부품',25,TEAL,True)
    arrow(d,220,185,375,185)
    txt(d,875,570,'본체 크기는 아직 미정',22,RED)
    txt(d,875,530,'기판·배터리 실측 후',22)
    txt(d,875,495,'외함과 지지대를 설계',22)
    txt(d,875,200,'세 금속 끝은',23)
    txt(d,875,165,'아래로 각각 10mm',23,TEAL,True)
    return d

def export_drawing(d,basename,folder):
    folder.mkdir(parents=True,exist_ok=True)
    svg=folder/(basename+'.svg')
    renderSVG.drawToFile(d,str(svg))
    # Keep standalone labels readable on teammates' machines without our font alias.
    svg.write_text(svg.read_text(encoding='utf-8').replace('font-family: KoreanBold','font-family: Malgun Gothic').replace('font-family: Korean','font-family: Malgun Gothic'),encoding='utf-8')
    temp=ROOT/'work'/(basename+'.pdf')
    cc=canvas.Canvas(str(temp),pagesize=(d.width,d.height))
    renderPDF.draw(d,cc,0,0); cc.save()
    return temp

STYLES = {
 'body': ParagraphStyle('body',fontName='Korean',fontSize=9.3,leading=15,textColor=colors.HexColor(INK),wordWrap='CJK',spaceAfter=7),
 'small': ParagraphStyle('small',fontName='Korean',fontSize=8,leading=12,textColor=colors.HexColor(MUTED),wordWrap='CJK'),
 'cell': ParagraphStyle('cell',fontName='Korean',fontSize=8.1,leading=12,wordWrap='CJK',textColor=colors.HexColor(INK)),
 'th': ParagraphStyle('th',fontName='KoreanBold',fontSize=8.3,leading=12,wordWrap='CJK',textColor=colors.white),
}

def para(c,text,x,y,w=WIDTH,kind='body'):
    p=Paragraph(text,STYLES[kind]); _,h=p.wrap(w,1000); p.drawOn(c,x,y-h); return y-h-5
def heading(c,title,y):
    c.setFont('KoreanBold',12); c.setFillColor(colors.HexColor(TEAL)); c.drawString(LEFT,y-14,title); return y-27
def table(c,headers,rows,widths,y,pad=7):
    data=[[Paragraph(html.escape(str(s)),STYLES['th']) for s in headers]]
    data += [[Paragraph(html.escape(str(s)),STYLES['cell']) for s in row] for row in rows]
    t=Table(data,colWidths=widths,hAlign='LEFT')
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.HexColor(INK)),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F2F6F9')]),
        ('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),
        ('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),pad),('BOTTOMPADDING',(0,0),(-1,-1),pad),
        ('LINEBELOW',(0,0),(-1,0),.6,colors.HexColor(INK)),
    ]))
    _,h=t.wrap(WIDTH,1000)
    if y-h<48: raise RuntimeError(f'Table overflow at y={y}, h={h}, {headers}')
    t.drawOn(c,LEFT,y-h); return y-h-13
def img(c,path,x,y,w,h):
    with Image.open(path) as im: iw,ih=im.size
    ratio=min(w/iw,h/ih); dw,dh=iw*ratio,ih*ratio
    c.drawImage(str(path),x+(w-dw)/2,y-dh,width=dw,height=dh,mask='auto')
    return y-dh
def drawing(c,d,y,w=WIDTH):
    s=w/d.width; c.saveState(); c.translate(LEFT,y-d.height*s); c.scale(s,s); renderPDF.draw(d,c,0,0); c.restoreState(); return y-d.height*s-12
def footer(c,n):
    c.setStrokeColor(colors.HexColor('#D3DEE6')); c.line(LEFT,37,RIGHT,37)
    c.setFont('Korean',7); c.setFillColor(colors.HexColor(MUTED))
    c.drawString(LEFT,23,'AI 스마트 염도계 | 팀 검토용 R1 | 실물 검증 전 | '+DATE)
    c.drawRightString(RIGHT,23,str(n))
def start(c,n,title,kicker='TEAM ENGINEERING HANDOFF / R1'):
    if n>1: c.showPage()
    c.setFillColor(colors.HexColor(TEAL)); c.setFont('KoreanBold',8); c.drawString(LEFT,PAGE_H-37,kicker)
    c.setFillColor(colors.HexColor(INK)); c.setFont('KoreanBold',21); c.drawString(LEFT,PAGE_H-72,title)
    footer(c,n); return PAGE_H-94
def callout(c,text,y):
    p=Paragraph(text,STYLES['body']); _,h=p.wrap(WIDTH-22,1000)
    c.setFillColor(colors.HexColor('#FFF1E8')); c.roundRect(LEFT,y-h-18,WIDTH,h+18,5,stroke=0,fill=1)
    p.drawOn(c,LEFT+11,y-h-8); return y-h-30

def make_pdf(ds):
    PDF.parent.mkdir(parents=True,exist_ok=True)
    c=canvas.Canvas(str(PDF),pagesize=A4)
    c.setTitle('AI 스마트 염도계 - 팀공유 설계검토본 R1')
    c.setAuthor('AI 창업 프로젝트 / 설계 검토 자료')
    y=start(c,1,'스마트 염도계 팀 공유 패키지')
    y=para(c,'현재 보유 부품과 캡형 헤드 v2를 기준으로 한 <b>배선 제안·부품 목록·3D 파일·예상 조립도</b>입니다. 상용 설계의 검증 결과가 아니라, 팀원이 제작과 시험을 이어갈 수 있도록 만든 인계 자료입니다.',LEFT,y)
    y=callout(c,'<b>중요:</b> 과거 전극 회로와 이번 회로 모두 실물 검증 전입니다. SUS316L 2전극 + ADS1115 시험 회로에서 얻는 값은 전극 계면·분극 영향을 포함한 원시 데이터입니다. 바로 염도(%)로 표시하거나 정확도를 보장하지 않습니다.',y)
    y=img(c,PKG/'03_assembly/assembly_preview.png',LEFT,y,WIDTH*.52,250)
    # compact summary alongside cover render
    y2=PAGE_H-294
    y2=para(c,'<b>기구 기준</b><br/>헤드 외형 58×38×47.75mm<br/>전극 Ø5mm 두 개<br/>온도 프로브 Ø6×50mm<br/>세 끝 돌출 길이 각각 10mm<br/>옆면 나사·너트 고정 유지',LEFT+WIDTH*.55,y2,WIDTH*.45)
    y2=para(c,'<b>회로 기준</b><br/>공통 3.3V / USB로 먼저 시험<br/>OLED·ADS·ToF는 I2C 공유<br/>버튼 3개 + 액티브 부저<br/>이번 핀 배치에서는 SD 미사용',LEFT+WIDTH*.55,y2-7,WIDTH*.45)
    y=min(y,y2)-18
    y=heading(c,'구분해서 전달할 내용',y)
    y=table(c,['상태','포함 내용'],[
        ('현재 파일','v2 헤드 원본과 STL 5개, 패킹 절단 도면. 기존 파일은 변경하지 않았습니다.'),
        ('새로 작성한 제안','전극 측정 시험회로, 정확한 핀 배선표, 예상 전체 배치. 실장·동작 확인 전입니다.'),
        ('확정되지 않은 것','배터리 실물·충전 경로, 본체 케이스, 전극 접점의 최종 단자, 방수·식품 적합성·염도 정확도.'),
    ],[85,WIDTH-85],y)
    para(c,'읽는 순서: 2~4쪽 회로 → 5~6쪽 부품·모델 → 7~9쪽 조립·예상 배치 → 10쪽 시험 → 11쪽 출처. 가격은 영수증·배송비가 확정되지 않아 새 총액을 만들지 않았습니다.',LEFT,y,kind='small')

    y=start(c,2,'01. 전체 회로와 핀 배치')
    y=drawing(c,ds['system'],y)
    y=table(c,['보드 표기','ESP32 핀','역할'],[(r[0],r[1],r[2]) for r in PINS], [65,85,WIDTH-150],y,pad=5)
    para(c,'[S1,S2] D번호와 GPIO 번호는 다릅니다. 예: D4는 GPIO4가 아니라 GPIO5입니다. D6/D7은 UART와 겹치므로 시리얼 로그는 USB CDC를 사용합니다. D8/D9는 SD와 겹쳐 SD 카드 제거·SD/SPI 미초기화가 전제입니다.',LEFT,y,kind='small')

    y=start(c,3,'02. 두 전극의 교번 구동 회로')
    y=drawing(c,ds['ec'],y)
    y=table(c,['ADC 단자','측정할 곳','외부 직렬저항','읽는 값'],ADC,[70,110,105,WIDTH-285],y)
    y=para(c,'<b>교번:</b> 반주기 A는 D0=HIGH/D1=LOW, B는 D0=LOW/D1=HIGH입니다. 각 입력의 대지 전압은 0~3.3V 안에 두고, E1-E2의 차이만 부호가 바뀝니다. 한 전극을 음전압 전원에 연결하는 방식이 아닙니다.',LEFT,y)
    y=para(c,'<b>전류 제한:</b> R1과 R2는 각각 1kΩ 1%입니다. 물 대신 두 봉을 단락해도 명목 최대 전류는 3.3V÷2kΩ=1.65mA입니다. GPIO 앞에 저항을 생략하면 안 됩니다. R7/R8은 각각 D0/D1에서 GND로 연결하는 10kΩ 풀다운입니다.',LEFT,y)
    y=para(c,'<b>전원:</b> DFR0553 VCC는 3.3V, GND는 공통 GND, ADDR는 0x48로 둡니다. A0~A3의 S만 측정 노드에 연결합니다. 3핀 묶음의 +나 -에 봉을 연결하지 마세요. 모듈 내부에 채널별 300Ω이 있으나 외부 10kΩ은 그대로 사용합니다. [S3,S4]',LEFT,y)
    para(c,'R1/R2 및 직렬저항은 독자 제안값입니다. 이 문서는 KiCad PCB 설계·펌웨어·상용 EC 아날로그 프런트엔드를 제공한다는 뜻이 아닙니다.',LEFT,y,kind='small')

    y=start(c,4,'03. 입력 보호와 주변장치 배선')
    y=drawing(c,ds['clamp'],y)
    y=para(c,'<b>BAT43 × 8개 추가:</b> 4개 ADC 입력마다 상·하단 다이오드 한 쌍을 외부 10kΩ 뒤에 둡니다. 윗 다이오드의 띠는 3V3, 아랫 다이오드의 띠는 ADC 쪽입니다. 케이블 연결은 전원을 끈 상태에서 합니다. [S5,S12]',LEFT,y)
    y=para(c,'<b>보호 한계:</b> ADC 권장 입력은 GND~VDD입니다. 클램프의 실제 순방향 전압·누설전류·배선 인덕턴스 때문에 입력 한계가 자동 보장되는 것은 아닙니다. 같은 전원의 수동 셀 시험에만 쓰고, 외부 전압이 있는 액체·히터·금속 전원 용기는 금지합니다. 전원 OFF 중 입력 인가도 금지합니다. 제조사 최대 정격을 정상 동작 범위로 삼지 않습니다.',LEFT,y)
    y=para(c,'보유 1N5819는 정류용이며, 이번 ADC 클램프에 무조건 대체하지 않습니다. BAT43도 누설전류가 0이 아니므로 저항 시험으로 오차를 확인해야 합니다. 과거 다이오드 제안이 정밀 측정용으로 검증된 것은 아닙니다. [S12,S13]',LEFT,y)
    y=drawing(c,ds['ui'],y)
    para(c,'버튼 풀업 R9/R10/R11=10kΩ, 버튼 직렬 R12/R13/R14=1kΩ. 부저 R15=1kΩ, R16=10kΩ 풀다운. DS18B20는 VDD/DATA/GND 3선으로 연결하며, DATA는 D3. 내장 4.7kΩ이 확인되면 외부 풀업을 중복 설치하지 않습니다. 전선 색만으로 단자를 단정하지 마세요. [S7,S10]',LEFT,y,kind='small')

    y=start(c,5,'04. 부품 목록 - 전자부품')
    y=para(c,'“구매 기록”은 사용자가 보낸 주문 내역·보유 언급을 뜻하며 수령품 검수 완료라는 뜻은 아닙니다. 구매 수량과 이번 실장 수량을 구분했습니다. 미확정 품목을 구매 완료로 처리하지 않았습니다.',LEFT,y)
    rows=[(a,b,c_,d) for a,b,c_,d,e in PARTS_E]
    y=table(c,['부품','모델 / 규격','사용 / 구매 수량','기록 상태'],rows,[83,205,92,WIDTH-380],y)
    para(c,'정확한 모듈 단자·역할은 별도 parts_list.md와 배선표에 있습니다. 이번 회로에 필요한 저항은 1kΩ 6개, 10kΩ 10개이며, 시험용 1kΩ·4.7kΩ·10kΩ 각 1개를 별도로 준비하면 좋습니다. BAT43 8개는 기존 구매 목록에 없던 추가품입니다.',LEFT,y,kind='small')

    y=start(c,6,'05. 헤드 부품과 3D 출력 파일')
    y=table(c,['조립품','규격','수량'],[(a,b,q) for a,b,q,n in PARTS_M[:6]],[110,WIDTH-155,45],y)
    y=para(c,'O링은 P5 내경4.8×굵기1.9mm 두 개, P6 내경5.8×굵기1.9mm 한 개입니다. 실리콘 경도 50~60A는 초기 시험 조건일 뿐 실물 검증·식품 인증이 아닙니다. 일반 M3 너트 7개를 씁니다. [S11]',LEFT,y)
    y=table(c,['파일','용도','수량','외형 mm','제품에 남음'],[(a,b,q,z,'예' if stay else '아니요') for a,b,q,z,stay in MODEL_INFO],[125,125,45,135,WIDTH-430],y)
    y=heading(c,'출력과 파일 사용',y)
    y=para(c,'STL은 mm 단위입니다. holder/cap_core/seal_retainer 3개를 한 판에 서로 떨어뜨려 놓고 층별 출력할 수 있습니다. 정렬 받침도 같은 판에 넣을 수 있습니다. 단, 먼저 fit_coupon으로 실제 봉 끼움을 확인해야 재출력 위험을 줄일 수 있습니다.',LEFT,y)
    y=para(c,'기본 후보 설정: PETG, 0.4mm 노즐, 0.2mm 층, 벽 5줄, 밀봉 부품 내부채움 100%. 이것만으로 수밀성을 보장하지 않습니다. cap_core는 넓은 면이 바닥이고 작은 원형 돌출부가 위인 출력 방향입니다. 자동 방향 변경은 하지 마세요.',LEFT,y)
    y=para(c,'원본 SCAD는 part="holder"가 기본이라 한 부품만 보입니다. part="assembly" 또는 "exploded" 후 F5는 확인용입니다. 이 전체 조립 화면은 통째로 출력하지 않습니다. 패킹 SVG/DXF는 실리콘 절단용이며 플라스틱 패킹 출력용이 아닙니다.',LEFT,y)
    para(c,'기존 용기 테두리 프레임(v1)은 이번 패키지에 포함하지 않았습니다. 새 헤드와 바로 호환된다고 보장하지 않으며, 현재 작업 대상은 캡형 헤드 v2입니다.',LEFT,y,kind='small')

    y=start(c,7,'06. 예상 헤드 조립도')
    y=para(c,'아래는 현재 CAD의 분해도입니다. 위부터 고정부 → 실리콘 평패킹 → 중앙 캡 → O링 3개가 들어가는 아래 받침 순서입니다. 바깥 기둥의 너트 4개와 위에서 넣는 M3×25 볼트로 결합합니다.',LEFT,y)
    y=img(c,PKG/'03_assembly/exploded_preview.png',LEFT,y,WIDTH,430)-12
    y=table(c,['그림의 위치','부품 / 역할'],[
        ('맨 위 파란 블록','holder: 봉을 옆면 나일론 나사로 누르는 고정부'),
        ('노란 얇은 판','1mm 실리콘 시트에서 자르는 평패킹. 접합면용 보조 씰'),
        ('가운데 청록 블록','cap_core: 봉 위쪽을 감싸고 아래 돌출부로 O링을 누름'),
        ('아래 파란 받침·주황 링','seal_retainer와 O링 3개. 봉 둘레 누수를 막는 시험 구조'),
    ],[115,WIDTH-115],y)
    para(c,'원본 기구 파일은 1mm 시트를 0.75mm로 누르는 형상을 유지합니다. 시트 대신 실란트를 바르는 방법은 대안 논의만 있었으며, 이번 CAD에 검증된 대체 공정으로 반영하지 않았습니다. 봉에 홈을 파지 않습니다.',LEFT,y,kind='small')

    y=start(c,8,'07. 조립 순서와 끝 높이 맞춤')
    y=para(c,'① 무전원 상태에서 구멍·나사 맞춤 확인 → ② 아래 홈에 P5/P5/P6 O링, 기둥 위 육각 홈에 M3 너트 4개 삽입 → ③ 캡 돌출부를 아래로 향해 올림 → ④ 평패킹·상단 고정부를 올리고 볼트를 느슨하게 체결합니다.',LEFT,y)
    y=para(c,'⑤ 금속봉·온도 프로브를 통과시킴 → ⑥ 정렬 받침 위에 헤드를 놓고 세 끝을 받침 바닥에 닿게 맞춤 → ⑦ 옆면 나일론 나사로 가볍게 고정 → ⑧ 바깥 볼트 네 개를 대각선 순서로 조금씩 조임 → ⑨ 받침 제거·실측 확인 순서입니다.',LEFT,y)
    y=img(c,PKG/'03_assembly/front_alignment.png',LEFT,y,WIDTH*.52,300)
    yj=PAGE_H-242
    yj=img(c,PKG/'03_assembly/tip_alignment_jig_preview.png',LEFT+WIDTH*.54,yj,WIDTH*.46,165)-10
    yj=para(c,'정렬 받침의 네 기둥에 헤드 바닥을 올립니다. 세 끝을 바닥판 위에 닿게 하면 10mm가 됩니다. 측정할 때는 받침을 빼세요.',LEFT+WIDTH*.54,yj,WIDTH*.46)
    y=min(y,yj)-15
    y=heading(c,'온도 프로브 길이와 고정 위치',y)
    y=para(c,'구매 제품의 금속관 명목 치수는 Ø6×50mm입니다. 끝을z=-10mm에 두면 금속관 위끝z=40mm, 고정부 밑면z=29.75mm입니다. 금속관 삽입은10.25mm, 나사 중심z=36.75mm는 접합보다3.25mm 아래입니다. 케이블 접합·수축튜브의 실제 위치와 굵기도 확인하세요. 지름6.5mm 구멍에 접합부가 걸리면 억지로 밀지 말고 수정해야 합니다. [S8,S9]',LEFT,y)
    y=para(c,'기존 헤드 아래로 나왔던 55mm를 새 헤드에서도 유지하지 않습니다. 새 고정부 밑면부터 아래 끝까지는 39.75mm입니다. 남는 전극 길이는 위쪽으로 보내며, 실제 전체 길이는 아직 미확인입니다. 미리보기의 긴 봉은 예시입니다.',LEFT,y)
    para(c,'온도관은 전극 회로와 연결하지 않습니다. 나사를 과하게 조여 관을 찌그러뜨리지 마세요. 위쪽 전기 접점은 마른 구역에 두고, 케이블 당김이 봉 높이를 바꾸지 않게 고정해야 합니다.',LEFT,y,kind='small')

    y=start(c,9,'08. 전체 MVP 예상 조립 배치')
    y=para(c,'이 그림은 현재 부품으로 구성할 때의 배치 개념입니다. 본체 케이스·배터리 지지대·헤드 결합부는 아직 치수 설계가 없으므로, 이 그림을 조립 가능성이 검증된 완성품이나 출력 모델로 사용하지 마세요.',LEFT,y)
    y=drawing(c,ds['mvp'],y)
    y=heading(c,'본체를 설계하기 전 확정할 것',y)
    y=para(c,'기판·케이블 높이, 배터리 크기, USB 공간, 광학 시야, 버튼 이동량, 전극 접점과 배선 고정을 실측해야 합니다. 카메라 제어 버스와 외부 I2C의 컨트롤러 배정·전력 여유도 통합 시험에서 확인합니다. ToF·카메라·OLED·부저·배터리는 물 밖에 둡니다.',LEFT,y)
    y=callout(c,'<b>배터리 연결은 보류:</b> 1셀 3.7V/4.2V 충전형 보호 배터리의 정확한 모델·충전 허용 전류·커넥터 극성을 확인한 뒤 BAT+/BAT-에 연결합니다. 생배터리를 3V3 또는 5V 핀에 넣지 마세요. 이번 문서에 배터리 커넥터 핀 번호를 임의로 지정하지 않았습니다.',y)
    para(c,'XIAO의 USB 충전 기능은 보드 리비전과 배터리 사양을 대조해야 합니다. 보유 #2810은 충전기가 아니며, 충전선 중간에 넣었을 때 역방향 충전과 OFF 동작은 확인하지 않았습니다. USB가 꽂혀 있으면 배터리 스위치 OFF만으로 전체 전원이 꺼진다고 가정하지 않습니다. [S1,S14]',LEFT,y,kind='small')

    y=start(c,10,'09. 펌웨어 요구사항과 검증 순서')
    y=table(c,['단계','팀원이 확인할 내용 / 다음 단계 조건'],[
      ('1. 무전원','핀 헤더·납땜·극성 확인. 전원선 단락 검사. 4핀 버튼의 접점군과 실제 1kΩ 두 개의 저항값 기록.'),
      ('2. USB + I2C','전극·배터리 미연결로 시작. 3.3V 확인 후 모듈을 하나씩 연결. ADS 0x48, ToF 0x29, OLED 0x3C/0x3D 확인. SDA/SCL 풀업 전압과 병렬 풀업 확인.'),
      ('3. 구동 파형','카메라/Wi-Fi/부저는 일단 OFF. MCPWM 등 하드웨어 타이머로 50Hz 상보 파형을 생성하고 오실로스코프/로직 분석기로 확인. 시작·종료·오류 때 두 핀 LOW.'),
      ('4. ADC + 저항','PGA ±4.096V, 860SPS, 단일 변환으로 채널별 읽기. 한 반주기 10ms 안의 같은 위상에서 A0~A3를 완료. I2C 지연으로 반주기를 넘으면 그 샘플 폐기.'),
      ('5. 건식 기준','물 대신 1kΩ,4.7kΩ,10kΩ 저항을 E1-E2 사이에 각각 연결해 계산값 확인. 목표는 초기 오차 5% 이내(우리 시험 기준, 검증 성능 아님). 정·역 차이도 기록.'),
      ('6. 기구 누수','전자부품 없이 상온 물로 시험. 끝 기준 15/20/25mm 잠김 후 분해하여 O링 위쪽 젖음 검사. 시험 시간·반복 횟수 기록. 통과 전 전기 측정 금지.'),
      ('7. 액체 비교','누수 통과 후만 동일 온도·용기·위치에서 반복. 깊이·기포·전극 표면·시간 경과·온도관 영향 기록. 건식 저항 통과가 액체 전도도 정확도를 보장하지 않음.'),
      ('8. MVP 이관','헤드·재질·회로·주파수·샘플 시점이 확정된 뒤 표준액/기준계로 교정. 최종 본체 조립 후 다시 확인. 범위 부적합 시 전용 EC 프런트엔드 재검토.'),
    ],[73,WIDTH-73],y)
    y=para(c,'<b>데이터 계산(저항성 부하의 단순 모델):</b><br/>Vcell = A0-A1, Vdrive = A2-A3<br/>I ≈ (Vdrive-Vcell) ÷ (R1+R2), Rapp = Vcell ÷ I<br/>단, I가 분해능·잡음에 비해 작거나 채널이 포화되면 무효로 처리합니다. 3.3V를 상수로 빼지 말고 구동 노드 실측값을 사용하세요. ADC 입력 부하·누설·순차 샘플링과 전극 계면은 이 모델에 포함되지 않습니다.',LEFT,y)
    y=para(c,'ADS1115의 860SPS는 4채널 동시 샘플링 속도가 아닙니다. 4변환만 이론상 약 4.65ms이며 I2C·전환 지연이 더해집니다. 1kHz 교번 신호를 그대로 정밀 추적하는 용도로는 부족합니다. 50Hz는 시험 시작안이지 SUS316L에 최적인 EC 주파수가 아닙니다. [S5,S15]',LEFT,y)
    para(c,'로그 권장: 시간, 위상, 샘플 시점, A0~A3 원시값/전압, R1/R2 실측값, Rapp, 온도, 잠김 깊이, 시료/헤드 버전. 출력은 원시값·온도 중심으로 하고 염도%는 교정 전 표시하지 않습니다. 자동 제한 시간·통신 오류 정지·watchdog를 구현하고, 무인/장시간 침수는 하지 마세요.',LEFT,y,kind='small')

    y=start(c,11,'10. 출처·한계·인계 체크리스트')
    y=para(c,'확인일 '+DATE+'. 공개 자료는 해당 제품의 명목 사양을 확인하는 근거이며, 구매한 실물의 진위·리비전·정확도·식품 안전을 확인한 시험 성적서가 아닙니다. 독자적인 저항값·핀 할당·형상·시험 기준은 위 자료를 바탕으로 작성한 제안입니다.',LEFT,y)
    for sid,title,url in SOURCES:
        y=para(c,f'<b>{sid}.</b> {html.escape(title)}<br/><link href="{html.escape(url,quote=True)}" color="#2365A0">{html.escape(url)}</link>',LEFT,y,kind='small')-3
    y=heading(c,'팀 인계 전 체크',y)
    y=para(c,'□ 추가 BAT43·O링·평패킹·나사 보유 확인　□ 헤더 납땜 확인<br/>□ 배터리 모델/극성/충전 조건 확정 전 미연결　□ SD 미사용 조건 공유<br/>□ 누수·저항·위상/ADC 시험 기록　□ 식품 접촉과 뜨거운 국물 사용 금지',LEFT,y)
    para(c,'식품용 O링이나 실란트 하나를 사용했다고 FDM 헤드 전체가 식품용이 되지 않습니다. 시험 물은 먹지 마세요. 보정값은 형상 변경 후 그대로 승계하지 않으며, 최종 동일 조립 상태로 재검증합니다. 이 패키지에는 실행 검증된 펌웨어, PCB 제조 파일, 전체 외함 STL은 없습니다.',LEFT,y,kind='small')
    c.save()
    return PDF

def md_table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(str(c).replace('|','/') for c in row)+' |' for row in rows])

def write_sidecars():
    parts='# 부품 목록 - 팀 검토용 R1\n\n'+DATE+' 기준. 구매 기록은 수령·검수 완료를 뜻하지 않습니다. 가격 총액은 재계산하지 않았습니다.\n\n## 전자부품\n\n'
    parts+=md_table(['부품','규격','수량','보유 기록','주의'],PARTS_E)
    parts+='\n\n## 기구·조립품\n\n'+md_table(['부품','규격','수량','주의'],PARTS_M)
    parts+='\n\n## 출력물\n\n'+md_table(['파일','용도','수량','외형 mm','제품에 남음'],[(a,b,q,z,'예' if s else '아니요') for a,b,q,z,s in MODEL_INFO])
    parts+='\n\n이번 안 추가품: BAT43 다리형 8개. O링/패킹/나사/배터리의 실제 구매 여부는 아직 확인되지 않았습니다. 보유품과 대조 후 주문하세요.\n'
    (PKG/'04_parts/parts_list.md').write_text(parts,encoding='utf-8')
    wiring='# 배선표 - 검증 전 회로 제안 R1\n\nUSB 전원, 공통 3.3V, SD 미사용 구성입니다. 문서 PDF를 함께 읽으세요.\n\n'
    wiring+=md_table(['XIAO 핀','GPIO','기능','연결'],PINS)
    wiring+='\n\n## ADC 입력\n\n'+md_table(['단자','노드','외부 저항','의미'],ADC)
    wiring+='\n\n각 ADC S 입력에 BAT43 클램프 2개(총8개): 위쪽 A=ADC/K=3V3, 아래쪽 A=GND/K=ADC. K는 띠 있는 쪽. 모듈 내부 300Ω과 별개로 외부10kΩ을 사용합니다.\n'
    wiring+='\nR1/R2=1kΩ 전극 전류 제한. R3~R6=10kΩ ADC 직렬. R7/R8=10kΩ D0/D1 풀다운. R9~R11=10kΩ 버튼 풀업. R12~R14=1kΩ 버튼 직렬. R15=1kΩ 부저 S 직렬. R16=10kΩ 부저 S 풀다운.\n'
    wiring+='\nDS18B20의 VDD/DATA/GND는 실물 표기와 대조하세요. 온도관은 E1/E2나 GND에 추가로 연결하지 않습니다. 내장4.7kΩ 풀업이 있으면 별도 풀업을 중복 설치하지 않습니다.\n'
    wiring+='\n3.3V 모듈 VCC-GND 사이에 0.1µF 세라믹 각1개를 ADC/ToF/OLED 가까이에 놓습니다. 커넥터 색상은 보증되지 않으므로 실크와 도통으로 확인합니다.\n'
    wiring+='\n## 구동·샘플링\n\n50Hz/50% 상보 파형은 하드웨어 타이머로 생성하고 실제 파형을 확인합니다. 한 반주기10ms 안에서 같은 위상의4채널 단일변환을 완료하고 경계를 넘는 샘플은 폐기합니다. PGA±4.096V/860SPS는 시작 설정이며4채널 동시 측정이 아닙니다. 시작·종료·오류 때두핀LOW. 펌웨어는 이 패키지에 포함되지 않았습니다.\n'
    wiring+='\nVcell=A0-A1; Vdrive=A2-A3; I≈(Vdrive-Vcell)/(R1+R2); Rapp=Vcell/I. 저항성부하 가정이며 액체의 순수저항·염도%를 보장하지 않습니다.\n'
    wiring+='\n## 전원 보류\n\n배터리 모델·극성·충전허용전류가 미확정입니다. USB로 먼저 시험하고 배터리는 연결하지 않습니다. #2810을 충전선에 넣는 방식은 검증 전입니다. 생배터리를3V3/5V핀에 연결하지마세요.\n'
    wiring+='\n## 출처\n\n'+'\n'.join(f'- {i}: [{t}]({u})' for i,t,u in SOURCES)+'\n'
    (PKG/'02_circuits/wiring_and_limits.md').write_text(wiring,encoding='utf-8')
    readme='''# 스마트 염도계 팀 인계 패키지 R1

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
'''
    (PKG/'README_먼저읽기.md').write_text(readme,encoding='utf-8')
    assembly='''# 이번 인계용 조립 순서

기존 기구 형상은 바꾸지 않았습니다. 이 순서는 부품을 덮기 전에 너트를 넣어야 하는 점을 명확히 한 설명입니다. CAD가 실제로 밀봉된다는 시험 결과는 아닙니다.

1. 전원을 모두 분리합니다. 봉과 온도센서의 실제 지름, 금속관 길이, 수축튜브/케이블 접합부가 고정부의 6.5mm 구멍을 통과하는지 먼저 확인합니다. 억지로 누르지 마세요.
2. seal_retainer의 아래 O링 자리에 P5 두 개와 P6 한 개를 넣습니다.
3. 같은 부품의 네 기둥 맨 위 육각 홈에 M3 너트 네 개를 먼저 넣습니다. 상단 고정부를 덮기 전에 넣어야 합니다.
4. cap_core의 작은 원형 돌출부 세 개가 아래를 향하게 넣습니다.
5. 중앙 캡 위에 도면대로 자른 1mm 실리콘 평패킹을 놓습니다.
6. holder를 올리고 M3×25mm 볼트 네 개를 위에서 넣어 조금만 체결합니다.
7. holder의 봉 고정용 너트 슬롯 세 곳에 나머지 M3 너트를 넣고 M3×12mm 나일론 나사 세 개를 옆에서 조금만 끼웁니다.
8. 두 전극과 온도센서를 통과시킵니다. O링을 찢거나 온도관을 찌그러뜨릴 정도로 힘을 주지 않습니다.
9. tip_alignment_jig를 책상에 놓고 네 기둥 위에 헤드의 바닥을 얹습니다. 세 금속 끝을 받침 바닥 위에 닿게 맞추고 옆면 나일론 나사로 가볍게 고정합니다.
10. 바깥 결합 볼트 네 개를 대각선으로 조금씩 조입니다. 기둥 정지면이 닿은 뒤 과하게 조이지 마세요. 봉 높이가 변하지 않았는지 확인합니다.
11. 정렬 받침을 빼고 세 끝이 아래 플라스틱 면에서 각각10mm 나오는지 확인합니다. 전극 연결부는 위쪽 마른 구간에 둡니다.
12. 전자부품 없이 상온 물로 누수 시험을 하고, 꺼내 닦은 뒤 분해하여 O링 위쪽에 물이 들어갔는지 확인합니다. 이 단계를 통과하기 전 전극 구동을 하지 않습니다.

O링: P5 내경4.8×굵기1.9mm ×2 / P6 내경5.8×굵기1.9mm ×1.
평패킹: 외곽34×32mm, 두께1mm, 구멍6mm 두 개·7mm 한 개. 01_models의 SVG/DXF는 이 재료 절단용입니다.
실란트 대체는 논의만 있었고 이 패키지는 원래의 평패킹 기준입니다.
'''
    (PKG/'03_assembly/assembly_steps_current.md').write_text(assembly,encoding='utf-8')

def mesh_check(path):
    raw=path.read_bytes()
    if raw[:5].lower()==b'solid':
        verts=[tuple(map(float,m)) for m in re.findall(rb'vertex\s+([-+\d.eE]+)\s+([-+\d.eE]+)\s+([-+\d.eE]+)',raw)]
    else:
        n=struct.unpack_from('<I',raw,80)[0]; verts=[]
        assert len(raw)==84+50*n
        for i in range(n):
            f=struct.unpack_from('<12fH',raw,84+50*i); verts.extend([f[3:6],f[6:9],f[9:12]])
    assert len(verts)%3==0 and verts
    verts=[tuple(round(v,5) for v in p) for p in verts]
    edges=collections.Counter(); vol=0
    for a,b,c_ in zip(verts[0::3],verts[1::3],verts[2::3]):
        assert len({a,b,c_})==3
        for u,v in [(a,b),(b,c_),(c_,a)]: edges[tuple(sorted((u,v)))]+=1
        vol+=(a[0]*(b[1]*c_[2]-b[2]*c_[1])+a[1]*(b[2]*c_[0]-b[0]*c_[2])+a[2]*(b[0]*c_[1]-b[1]*c_[0]))/6
    bad=sum(v!=2 for v in edges.values())
    assert bad==0,(path.name,bad)
    lo=[min(v[i] for v in verts) for i in range(3)]; hi=[max(v[i] for v in verts) for i in range(3)]
    return {'triangles':len(verts)//3,'edge_manifold':bad==0,'dimensions_mm':[round(hi[i]-lo[i],3) for i in range(3)],'signed_volume_mm3':round(vol,2)}

def manifest():
    files=[]
    for p in sorted(PKG.rglob('*')):
        if p.is_file() and p.name!='manifest.json':
            r={'path':str(p.relative_to(PKG)).replace('\\','/'),'size':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
            if p.suffix=='.stl': r['mesh_check']=mesh_check(p)
            files.append(r)
    (PKG/'manifest.json').write_text(json.dumps({'date':DATE,'revision':'R1','cad':'unchanged copy of capped head v2','electrical_status':'unbuilt review proposal; not validated','files':files},ensure_ascii=False,indent=2),encoding='utf-8')
    print('Manifest:',len(files),'files; all 5 STL edge-manifold checks passed',flush=True)

def main():
    ds={'system':system_diagram(),'ec':ec_diagram(),'clamp':clamp_diagram(),'ui':ui_diagram(),'mvp':mvp_diagram()}
    for key,name in [('system','system_wiring'),('ec','electrode_test_circuit'),('clamp','adc_clamp'),('ui','buttons_buzzer')]: export_drawing(ds[key],name,PKG/'02_circuits')
    export_drawing(ds['mvp'],'mvp_layout_concept',PKG/'03_assembly')
    write_sidecars()
    pdf=make_pdf(ds)
    shutil.copy2(pdf,PKG/pdf.name)
    manifest()
    print(pdf,flush=True)

if __name__=='__main__': main()
