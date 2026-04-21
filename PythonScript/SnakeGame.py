import time
import msvcrt
import sys
import random

def _get_key():
    c = msvcrt.getch()
    if c in (b'\xe0', b'\x00'):
        k = msvcrt.getch()
        return {b'H': 'up', b'P': 'down', b'K': 'left', b'M': 'right'}.get(k, '')
    return c.decode('utf-8', errors='ignore')
def _frame_wait(fps):
    now = time.perf_counter()
    last = getattr(_frame_wait, '_last', now)
    target = last + 1.0 / fps
    if now < target:
        time.sleep(target - now)
    _frame_wait._last = max(now, target)

import os
너비 = 50
높이 = 30
def 그리기(뱀, 먹이, 점수):
    _frame_buf = []
    for y in range(0, 높이+2):
        for x in range(0, 너비+2):
            if y == 0 or y == 높이 + 1:
                _frame_buf.append(str(("\033[34m" + str("#") + "\033[0m")))
            elif x == 0 or x == 너비 + 1:
                _frame_buf.append(str(("\033[34m" + str("#") + "\033[0m")))
            elif [x, y] == 먹이:
                _frame_buf.append(str(("\033[33m" + str("@") + "\033[0m")))
            elif [x, y] == 뱀[0]:
                _frame_buf.append(str(("\033[32m" + str("O") + "\033[0m")))
            elif [x, y] in 뱀:
                _frame_buf.append(str(("\033[32m" + str("o") + "\033[0m")))
            else:
                _frame_buf.append(str(" "))
        _frame_buf.append("\n")
    _frame_buf.append(str(f"점수: {점수}  조작: WASD/방향키  Q 종료") + "\n")
    sys.stdout.write("\033[H" + "".join(_frame_buf) + "\033[J"); sys.stdout.flush()
(os.system("") if os.name == "nt" else None); sys.stdout.write("\033[2J\033[H\033[?25l"); sys.stdout.flush(); _frame_buf = []
뱀 = [[10, 5]]
방향 = "오른쪽"
먹이 = [random.randint(1, 너비), random.randint(1, 높이)]
점수 = 0
while True:
    그리기(뱀, 먹이, 점수)
    if msvcrt.kbhit():
        키 = _get_key()
        if (키 == "w" or 키 == "위") and 방향 != "아래":
            방향 = "위"
        elif (키 == "s" or 키 == "아래") and 방향 != "위":
            방향 = "아래"
        elif (키 == "a" or 키 == "왼쪽") and 방향 != "오른쪽":
            방향 = "왼쪽"
        elif (키 == "d" or 키 == "오른쪽") and 방향 != "왼쪽":
            방향 = "오른쪽"
        elif 키 == "q":
            break
    머리x, 머리y = 뱀[0]
    if 방향 == "오른쪽":
        머리x = 머리x + 1
    elif 방향 == "왼쪽":
        머리x = 머리x - 1
    elif 방향 == "위":
        머리y = 머리y - 1
    else:
        머리y = 머리y + 1
    if 머리x <= 0 or 머리x > 너비 or 머리y <= 0 or 머리y > 높이:
        break
    if [머리x, 머리y] in 뱀:
        break
    뱀.insert(0, [머리x, 머리y])
    if [머리x, 머리y] == 먹이:
        점수 = 점수 + 1
        먹이 = [random.randint(1, 너비), random.randint(1, 높이)]
    else:
        뱀.pop()
    _frame_wait(15)
print(f"게임 오버! 최종 점수: {점수}")