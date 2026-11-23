from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

root=Path(__file__).resolve().parent
im=Image.new('RGB',(1600,950),'#f7f9fc')
d=ImageDraw.Draw(im)
def f(n): return ImageFont.truetype('C:/Windows/Fonts/malgun.ttf',n)
def t(x,y,s,n=28,c='#192b42'): d.multiline_text((x,y),s,font=f(n),fill=c,spacing=12)

t(60,30,'확인용 연결: 헤드 대신 1kΩ 저항 1개',43)
t(60,100,'빵판의 핀과 저항은 그대로 두고, 헤드에 물린 악어클립 두 개만 옮깁니다.',28)
d.rounded_rectangle((60,175,1540,590),radius=22,fill='white',outline='#a2b1c4',width=3)
d.rounded_rectangle((110,225,480,505),radius=18,fill='#e6eef8')
t(140,250,'기존 빵판 회로',33)
t(140,325,'R1·R2 및 A0~A3\n연결은 그대로 유지',27)
d.line([(480,300),(610,300),(610,385),(665,385)],fill='#315c8b',width=10)
d.line([(480,450),(1390,450),(1390,385),(1325,385)],fill='#91632f',width=10)
t(525,210,'기존 헤드 전극선 2개',26)

# Existing crocodile clips grip one resistor lead each.
d.rounded_rectangle((665,350,805,420),radius=10,fill='#33485c')
d.polygon([(805,350),(838,373),(805,385)],fill='#9ca8b3')
d.polygon([(805,420),(838,397),(805,385)],fill='#9ca8b3')
d.rounded_rectangle((1185,350,1325,420),radius=10,fill='#33485c')
d.polygon([(1185,350),(1152,373),(1185,385)],fill='#9ca8b3')
d.polygon([(1185,420),(1152,397),(1185,385)],fill='#9ca8b3')
d.line([(830,385),(920,385)],fill='#7f8b96',width=7)
d.line([(1070,385),(1160,385)],fill='#7f8b96',width=7)
d.rounded_rectangle((920,346,1070,424),radius=22,fill='#a6d1dc',outline='#426e7c',width=3)
t(951,358,'1kΩ',32)
t(677,285,'악어클립 ①',25)
t(1181,285,'악어클립 ②',25)
t(725,480,'저항의 양다리를 하나씩 물리세요.\n두 클립의 금속 부분은 서로 떨어뜨립니다.',25)

d.rounded_rectangle((60,620,1540,885),radius=18,fill='#e6eef8')
t(90,645,'① USB 분리',30)
t(90,700,'② 헤드 금속 전극에서 악어클립 2개 분리 → 1kΩ 저항의 양다리에 각각 연결',28)
t(90,752,'③ 저항과 클립은 물 밖에 둔 상태로 USB 재연결',28)
t(90,807,'온도센서의 빨강·노랑·검정 3선은 기존대로 연결해 둡니다.',25)
t(60,905,'기대값: 기존 R1·R2가 각각 1kΩ일 때 RAW 약 66.7. 염도 측정이 아닌 계측 회로 검사입니다.',22,'#53647b')
path=root/'1k_기준저항_계측회로검사.png'
im.save(path)
print(path)
