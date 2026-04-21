# 추가된 12가지 기능을 한 번에 시연
import math as m
class 캐릭터:
    def __init__(self, 이름, 체력=100):
        self.이름 = 이름
        self.체력 = 체력
class 적(캐릭터):
    def __init__(self, 이름, 체력=50):
        self.이름 = 이름
        self.체력 = 체력
def 더하기(a, b=1):
    return a + b
print(더하기(10))
print(더하기(10, 5))
a, b = 1, 2
print(a)
print(b)
숫자들 = [10, 20, 30, 40, 50]
print(숫자들[2-1:4])
print(숫자들[2-1:])
print(숫자들[:3])
제곱 = (lambda x: x * x)
print(제곱(7))
합 = (lambda a, b: a + b)
print(합(3, 4))
print("\033[31m" + str("빨강 글자") + "\033[0m")
print("\033[32m" + str("초록 글자") + "\033[0m")
print(("\033[33m" + str("섞어서 쓰기") + "\033[0m"))
try:
    x = 1 / 0
except ZeroDivisionError as e:
    print(f"0 나누기 실패: {e}")
finally:
    print("정리 완료")
with open("demo_out.txt", "w", encoding="utf-8") as f:
    f.write("데모 파일 내용")
with open("demo_out.txt", "r", encoding="utf-8") as f:
    내용 = f.read()
    print(f"파일 내용: {내용}")