from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

root=Path(__file__).resolve().parent
im=Image.new('RGB',(1600,910),'#f7f9fc')
d=ImageDraw.Draw(im)
def f(n):return ImageFont.truetype('C:/Windows/Fonts/malgun.ttf',n)
def t(x,y,s,n=28,c='#192b42'):d.multiline_text((x,y),s,font=f(n),fill=c,spacing=12)
t(60,28,'시험저항을 빼고, 헤드를 원래대로 연결',43)
t(60,100,'빵판에 꽂힌 기존 저항·핀과 온도센서 3선은 그대로 둡니다.',28)
d.rounded_rectangle((60,175,465,535),radius=20,fill='#e6eef8',outline='#a2b1c4',width=3)
t(95,210,'기존 빵판 회로',34)
t(95,294,'빵판 배선은 그대로',27)
t(95,370,'기존 전극선 2개',27)

d.rounded_rectangle((980,235,1515,510),radius=20,fill='white',outline='#9dadc1',width=3)
t(1020,265,'기존 헤드',33)
for x,label in ((1110,'원래 전극 ①'),(1385,'원래 전극 ②')):
 d.rounded_rectangle((x-23,350,x+23,550),radius=10,fill='#aebac5',outline='#5e7182',width=3)
 t(x-92,575,label,26)
d.line([(465,320),(765,320),(765,385),(1090,385)],fill='#315c8b',width=10)
d.line([(465,465),(835,465),(835,432),(1360,432)],fill='#91632f',width=10)
for x,y in ((1000,350),(1270,397)):
 d.rounded_rectangle((x,y,x+102,y+70),radius=9,fill='#33485c')
t(525,195,'악어클립을 각각 원래 물렸던 전극에 연결',26)

d.rounded_rectangle((530,505,895,610),radius=15,fill='#edf0f4',outline='#9aa8b8',width=2)
t(550,525,'클립 사이에 넣었던\n시험용 1kΩ만 분리',24)

d.rounded_rectangle((60,665,1540,850),radius=18,fill='#e6eef8')
t(90,690,'① USB 분리  →  ② 시험용 1kΩ 분리  →  ③ 클립을 원래 전극에 연결',28)
t(90,748,'④ USB 재연결  →  ⑤ 준비된 0.6% 용액에 자작 헤드만 담그기',28)
t(90,800,'온도센서의 빨강·노랑·검정 3선은 기존대로 유지합니다.',24)
t(60,870,'연결 관계를 보여주는 그림입니다. 선 색과 전극의 좌우 위치는 실물 배치를 뜻하지 않습니다.',22,'#53647b')
path=root/'헤드_원래연결_복원.png'
im.save(path)
print(path)
