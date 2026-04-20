import time
import msvcrt

import os
import random

너비 = 50
높이 = 30

def 그리기(뱀, 먹이, 점수):
    os.system("cls" if os.name == "nt" else "clear")
    for y in range(0, 높이+2):
        for x in range(0, 너비+2):
            if y == 0 or y == 높이+1:
                print("#", end="")
            elif x == 0 or x == 너비+1:
                print("#", end="")
            elif [x, y] == 먹이:
                print("@", end="")
            elif [x, y] == 뱀[0]:
                print("O", end="")
            elif [x, y] in 뱀:
                print("o", end="")
            else:
                print(" ", end="")
        print()
    print(f"점수: {점수}  조작: WASD 이동  Q 종료")

뱀 = [[10, 5]]
방향 = "오른쪽"
먹이 = [random.randint(1, 너비), random.randint(1, 높이)]
점수 = 0

while True:
    그리기(뱀, 먹이, 점수)

    if msvcrt.kbhit():
        키 = msvcrt.getch().decode('utf-8', errors='ignore')
        if 키 == "w" and 방향 != "아래":
            방향 = "위"
        elif 키 == "s" and 방향 != "위":
            방향 = "아래"
        elif 키 == "a" and 방향 != "오른쪽":
            방향 = "왼쪽"
        elif 키 == "d" and 방향 != "왼쪽":
            방향 = "오른쪽"
        elif 키 == "q":
            break

    머리x = 뱀[0][0]
    머리y = 뱀[0][1]

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

    time.sleep(100 / 1000)

print(f"게임 오버! 최종 점수: {점수}")
