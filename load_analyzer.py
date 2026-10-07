import csv
import math
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import MultipleLocator


area_mm2 = 100
REFERENCE_STRESS_MPA = 6


def main():
    csv_path = Path(__file__).with_name("load_data.csv")
    result_path = Path(__file__).with_name("load_result.csv")
    plot_path = Path(__file__).with_name("stress_plot.png")
    valid_rows = []
    excluded_rows = 0

    with csv_path.open("r", newline="", encoding="utf-8-sig") as csv_file:
        header_line = csv_file.readline()
        try:
            header = next(csv.reader([header_line], strict=True))
        except (csv.Error, StopIteration) as error:
            raise ValueError("CSV 헤더를 읽을 수 없습니다.") from error

        required_columns = {"time_s", "force_N"}
        missing_columns = required_columns.difference(header)
        if missing_columns:
            raise ValueError(f"CSV에 필요한 열이 없습니다: {', '.join(sorted(missing_columns))}")

        time_index = header.index("time_s")
        force_index = header.index("force_N")

        for row_number, line in enumerate(csv_file, start=2):
            if not line.strip():
                continue

            try:
                row = next(csv.reader([line], strict=True))
            except csv.Error as error:
                print(f"{csv_path.name} {row_number}행: CSV 형식 오류 ({error}), 제외합니다.")
                excluded_rows += 1
                continue

            if len(row) != len(header):
                print(
                    f"{csv_path.name} {row_number}행: 열 개수 불일치 "
                    f"(예상 {len(header)}, 실제 {len(row)}), 제외합니다."
                )
                excluded_rows += 1
                continue

            parsed_values = {}
            invalid_values = []
            for column, column_index in (("time_s", time_index), ("force_N", force_index)):
                raw_value = row[column_index]
                try:
                    numeric_value = float(raw_value)
                except ValueError:
                    reason = "빈 값" if not raw_value.strip() else "숫자가 아님"
                    invalid_values.append(f"{column}={raw_value!r} ({reason})")
                    continue

                if not math.isfinite(numeric_value):
                    invalid_values.append(f"{column}={raw_value!r} (유한한 숫자가 아님)")
                    continue

                parsed_values[column] = numeric_value

            if invalid_values:
                print(f"{csv_path.name} {row_number}행: {', '.join(invalid_values)}, 계산에서 제외합니다.")
                excluded_rows += 1
                continue

            valid_rows.append((parsed_values["time_s"], parsed_values["force_N"]))

    print(f"제외한 행 수: {excluded_rows}")
    print(f"유효한 데이터 수: {len(valid_rows)}")
    if not valid_rows:
        print("유효한 데이터가 없어 계산과 그래프 생성을 중단합니다.")
        print("원본 CSV는 수정하지 않았습니다.")
        return

    data = pd.DataFrame(valid_rows, columns=["time_s", "force_N"])
    data["stress_MPa"] = data["force_N"] / area_mm2
    data.to_csv(result_path, index=False)

    maximum_force = data["force_N"].max()
    maximum_times = data.loc[data["force_N"] == maximum_force, "time_s"]
    maximum_stress = data["stress_MPa"].max()
    maximum_stress_rows = data[data["stress_MPa"] == maximum_stress]
    maximum_stress_times = maximum_stress_rows["time_s"]
    above_reference_count = int((data["stress_MPa"] > REFERENCE_STRESS_MPA).sum())

    plt.plot(data["time_s"], data["stress_MPa"], marker="o")
    plt.scatter(
        maximum_stress_rows["time_s"],
        maximum_stress_rows["stress_MPa"],
        color="crimson",
        marker="D",
        s=80,
        zorder=3,
    )
    maximum_point = maximum_stress_rows.iloc[0]
    plt.annotate(
        f"Max: {maximum_stress:g} MPa\nTime: {maximum_point['time_s']:g} s",
        xy=(maximum_point["time_s"], maximum_point["stress_MPa"]),
        xytext=(10, -34),
        textcoords="offset points",
        color="crimson",
        arrowprops={"arrowstyle": "->", "color": "crimson", "linewidth": 0.8},
    )
    plt.xlabel("Time(s)")
    plt.ylabel("Stress(MPa)")
    plt.gca().xaxis.set_major_locator(MultipleLocator(2))
    plt.gca().yaxis.set_major_locator(MultipleLocator(1))
    plt.grid(True, which="major", axis="both", linestyle="-", linewidth=0.6, alpha=0.3)
    plt.savefig(plot_path)
    plt.close()

    print(f"최대 하중: {maximum_force:g} N")
    print(f"해당 시간: {', '.join(f'{time:g}' for time in maximum_times)} s")
    print(f"단면적: {area_mm2:g} mm²")
    print(f"최대 평균 수직 응력: {maximum_stress:g} MPa")
    print(f"최대 응력 시간: {', '.join(f'{time:g}' for time in maximum_stress_times)} s")
    print(f"기준 응력 {REFERENCE_STRESS_MPA:g} MPa 초과 데이터 개수: {above_reference_count}")
    print(f"결과 저장: {result_path.name}")
    print(f"그래프 저장: {plot_path.name}")


if __name__ == "__main__":
    main()