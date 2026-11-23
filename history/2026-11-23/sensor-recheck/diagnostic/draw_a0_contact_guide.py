from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).resolve().parent
im = Image.new('RGB', (1500, 700), '#f7f9fc')
d = ImageDraw.Draw(im)
font_path = 'C:/Windows/Fonts/malgun.ttf'
def font(size):
    return ImageFont.truetype(font_path, size)
def text(x, y, value, size=26, color='#182538'):
    d.multiline_text((x, y), value, font=font(size), fill=color, spacing=12)

text(55, 35, '확인할 곳: A0 신호선의 양끝 접촉', 42)
text(55, 102, '연결 위치는 유지합니다. USB를 분리한 뒤 같은 자리에 단단히 꽂아 주세요.', 26)

d.rounded_rectangle((55, 205, 455, 470), radius=20, fill='white', outline='#94a8c2', width=3)
text(82, 232, 'ADS1115 보드', 34)
text(82, 300, '‘A0’라고 적힌 줄의\n‘A’ 신호 단자', 29)
d.rounded_rectangle((422, 350, 477, 395), radius=5, fill='#253b52')

d.rounded_rectangle((1045, 205, 1445, 470), radius=20, fill='white', outline='#94a8c2', width=3)
text(1070, 232, '기존 빵판 연결점', 32)
text(1070, 300, '같은 신호선의 반대쪽\n(저항으로 이어지는 쪽)', 25)
d.rounded_rectangle((1022, 350, 1072, 395), radius=5, fill='#253b52')
d.line([(478, 373), (1022, 373)], fill='#1877b8', width=12)
text(580, 281, '이미 연결되어 있는 A0 신호선', 26, '#125781')

for x, number in ((450, '1'), (1047, '2')):
    d.ellipse((x-43, 330, x+43, 416), outline='#d56b13', width=6)
    d.ellipse((x-20, 433, x+20, 473), fill='#d56b13')
    d.text((x-10, 435), number, font=font(27), fill='white')

text(55, 493, '위치는 실물의 A0 / A 글씨로 확인하세요. 이 그림은 실제 핀의 좌우 순서를 표시하지 않습니다.', 22, '#55647a')
d.rounded_rectangle((55, 555, 1445, 655), radius=14, fill='#e6eef8')
text(85, 580, '① USB 분리   →   ② 표시한 두 접점을 같은 자리에 밀착   →   ③ USB 재연결', 29)
path = root / 'A0_신호선_접촉확인.png'
im.save(path)
print(path)
