"""저장된 weather_20251008_20251014.csv에서 기온 그래프를 만든다. API는 호출하지 않는다."""

import csv
import math
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.dates as mdates


def load_temperature(path):
    """CSV의 시각을 datetime으로 변환하고 기온 결측을 NaN으로 읽어 정렬한다."""
    observations = {}
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not {"datetime", "temperature_C"}.issubset(reader.fieldnames or []):
            raise ValueError("CSV에 datetime, temperature_C 열이 필요합니다.")
        for line_number, row in enumerate(reader, start=2):
            try:
                stamp = datetime.fromisoformat(row["datetime"].strip())
                if stamp.tzinfo is not None or stamp.minute or stamp.second or stamp.microsecond:
                    raise ValueError
                token = row["temperature_C"].strip()
                temperature = float(token) if token else math.nan
                if math.isinf(temperature):
                    raise ValueError
            except (ValueError, TypeError, AttributeError):
                raise ValueError(f"CSV {line_number}행의 시각 또는 기온을 확인하세요.") from None
            if stamp in observations:
                raise ValueError(f"중복 시각이 있습니다: {stamp}. CSV를 확인하세요.")
            observations[stamp] = temperature
    if not observations:
        raise ValueError("CSV에 자료 행이 없습니다.")
    return dict(sorted(observations.items()))


def fill_hourly_gaps(observations):
    """첫 시각부터 마지막 시각까지 1시간 간격을 만들고 누락 시각에 NaN을 넣는다."""
    times, temperatures, missing = [], [], []
    stamp, last = min(observations), max(observations)
    while stamp <= last:
        times.append(stamp)
        temperatures.append(observations.get(stamp, math.nan))
        if stamp not in observations:
            missing.append(stamp)
        stamp += timedelta(hours=1)
    return times, temperatures, missing


def plot_temperature(times, temperatures, output):
    """NaN 구간에서는 선을 끊고, PNG로 저장한 뒤 화면에 표시한다."""
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(times, temperatures, color="tab:blue", linewidth=1.3)
    ax.set_title("Temperature over time")
    ax.set_xlabel("Time (KST)")
    ax.set_ylabel("Temperature (°C)")
    locator = mdates.AutoDateLocator()
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output, dpi=180)
    print(f"그래프 저장 위치: {output}")
    plt.show()
    plt.close(fig)


def main():
    """파일과 같은 폴더의 CSV를 읽어 누락을 확인하고 그래프를 만든다."""
    directory = Path(__file__).resolve().parent
    try:
        observations = load_temperature(directory / "weather_20251008_20251014.csv")
        times, temperatures, missing = fill_hourly_gaps(observations)
        print(f"누락 시각 수: {len(missing)} (첫 관측~마지막 관측 범위)")
        for stamp in missing:
            print(f"  {stamp:%Y-%m-%d %H:%M:%S}")
        print(f"기온 결측 수 (누락 시각 포함): {sum(math.isnan(t) for t in temperatures)}")
        plot_temperature(times, temperatures, directory / "temperature_20251008_20251014.png")
    except (OSError, ValueError) as error:
        print(f"그래프 생성 실패: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
