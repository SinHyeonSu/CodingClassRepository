"""Week 7: ASOS 시간자료 요청과 응답 확인."""

import getpass
import json
import re
import sys
import csv
import math
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, quote_plus

import requests

API_URL = "https://apihub.kma.go.kr/api/typ01/url/kma_sfctm3.php"
START_TIME = "202510080000"
END_TIME = "202510142300"
CSV_FILENAME = "weather_20251008_20251014.csv"

FIELDS = ["datetime", "temperature_C", "humidity_pct", "wind_speed_ms"]
POSITIONS = {"TM": 1, "WS": 4, "TA": 12, "HM": 14}


def parse_weather(body):
    """설명과 자료를 분리하고 헤더 번호를 검증한 뒤 필요한 네 열을 만든다."""
    comments, data = [], []
    for line in body.splitlines():
        if line.lstrip().startswith("#"):
            comments.append(line)
        elif line.strip():
            data.append(line.split())  # 연속 공백과 탭을 모두 구분자로 처리
    found = {}
    for line in comments:
        match = re.match(r"^\s*#\s*(\d+)\s*[.)]?\s+([A-Z_]+)\b", line)
        if match and match[2] in POSITIONS:
            found[match[2]] = int(match[1])
    if found != POSITIONS:
        raise ValueError("응답의 TM(1), WS(4), TA(12), HM(14) 헤더 번호를 확인할 수 없습니다. 원본 응답을 확인하세요.")
    print("헤더 확인: TM(1), WS(4), TA(12), HM(14)")

    def number(token, field):
        # TA의 -9, -9.0 등 영하 기온은 보존한다. 큰 음수 결측 코드만 비운다.
        # WS/HM은 물리적으로 음수가 될 수 없으므로 음수 코드는 모두 결측이다.
        if token.upper() in {"NA", "NAN", "NULL", "-", "/", "///"}:
            return None
        value = float(token)
        if not math.isfinite(value) or (value <= -99 if field == "TA" else value < 0):
            return None
        return value

    records = []
    for fields in data:
        if len(fields) < 14:
            raise ValueError("14개 미만의 열을 가진 자료 행이 있습니다.")
        if fields[1] != "108":
            raise ValueError("요청한 관측소 108 이외의 자료가 있습니다.")
        try:
            if not re.fullmatch(r"\d{12}", fields[0]):
                raise ValueError
            stamp = datetime.strptime(fields[0], "%Y%m%d%H%M")
            if not datetime.strptime(START_TIME, "%Y%m%d%H%M") <= stamp <= datetime.strptime(END_TIME, "%Y%m%d%H%M"):
                raise ValueError
            values = [number(fields[11], "TA"), number(fields[13], "HM"), number(fields[3], "WS")]
        except ValueError:
            raise ValueError("자료 행에 유효하지 않은 시각 또는 숫자가 있습니다.") from None
        records.append(dict(zip(FIELDS, [stamp, *values])))
    if not records:
        raise ValueError("저장할 자료 행이 없습니다.")
    records.sort(key=lambda row: row["datetime"])
    return records


def save_weather(body, directory):
    """원본을 매 실행마다 보관하고 시간순 CSV 및 품질 요약을 저장·출력한다."""
    raw = directory / ("weather_raw_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f") + ".txt")
    raw.write_text(body, encoding="utf-8")
    print(f"원본 응답: {raw}")
    records = parse_weather(body)
    duplicates = len(records) - len({row["datetime"] for row in records})
    print(f"중복 시각 행 수: {duplicates} (원자료 보존, 삭제하지 않음)")
    output = directory / CSV_FILENAME
    with output.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()  # 행 인덱스 없이 지정된 네 열만 저장
        for row in records:
            writer.writerow({**row, "datetime": row["datetime"].strftime("%Y-%m-%d %H:%M:%S")})
    print(f"행 수: {len(records)}")
    for field in FIELDS:
        print(f"{field} 결측 수: {sum(row[field] is None for row in records)}")
    print(f"첫 시각 (KST): {records[0]['datetime']}")
    print(f"마지막 시각 (KST): {records[-1]['datetime']}")
    print(f"저장 위치: {output}")


def redact(text, key):
    """서버가 키나 요청 주소를 되돌려 보내더라도 숨긴다."""
    text = re.sub(r"https?://\S+", "[요청 주소 숨김]", text)
    for value in {key, quote(key, safe=""), quote_plus(key)}:
        if value:
            text = text.replace(value, "[인증키 숨김]")
    return text


def failure_message(body):
    try:
        payload = json.loads(body)
    except ValueError:
        payload = None
    if isinstance(payload, dict):
        message = payload.get("message")
        if message:
            return str(message)
    for line in body.splitlines():
        if re.search(r"message|error|오류|실패|인증", line, re.I):
            return line.strip()[:1000]
    return "응답에 message가 없습니다. API 활용신청과 조회 조건을 확인하세요."


def main():
    # getpass가 화면에 보이는 입력으로 대체되는 상황을 허용하지 않는다.
    import warnings
    warnings.simplefilter("error", getpass.GetPassWarning)
    try:
        key = getpass.getpass("기상청 API 인증키 (화면에 표시되지 않음): ").strip()
    except (EOFError, KeyboardInterrupt, getpass.GetPassWarning):
        print("입력이 취소되었거나 안전한 입력을 사용할 수 없습니다. 터미널에서 실행하세요.")
        return 1
    if not key:
        print("인증키가 비어 있습니다.")
        return 1

    params = {
        "tm1": START_TIME,
        "tm2": END_TIME,
        "stn": "108",
        "help": "1",
        "authKey": key,
    }
    try:
        response = requests.get(API_URL, params=params, timeout=(10, 30), allow_redirects=False)
    except requests.Timeout:
        print("요청 시간이 초과되었습니다. 잠시 후 다시 실행하세요.")
        return 1
    except requests.RequestException:
        # 예외 문자열에는 인증키가 포함된 URL이 들어갈 수 있다.
        print("요청에 실패했습니다. 인터넷 연결과 API 주소를 확인하세요.")
        return 1

    print(f"HTTP 상태: {response.status_code}")
    charset = requests.utils.get_encoding_from_headers(response.headers)
    if not re.search(r"charset\s*=", response.headers.get("Content-Type", ""), re.I):
        charset = response.apparent_encoding or "utf-8"
    try:
        body = response.content.decode(charset or "utf-8", errors="replace")
    except LookupError:
        body = response.content.decode("utf-8", errors="replace")
    body = redact(body, key)
    rows = [line for line in body.splitlines() if re.match(r"^\s*\d{12}\s+108\s+", line)]
    if response.status_code != 200 or not rows:
        print("요청 실패: " + failure_message(body))
        return 1

    print("\n응답 본문 앞 15줄:")
    print("\n".join(body.splitlines()[:15]))
    print("\n실제 데이터행 3개:")
    print("\n".join(rows[:3]))
    try:
        save_weather(body, Path(__file__).resolve().parent)
    except ValueError as error:
        print(f"변환 중단: {error}")
        return 1
    except OSError:
        print("파일 저장에 실패했습니다. 폴더의 쓰기 권한을 확인하세요.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
