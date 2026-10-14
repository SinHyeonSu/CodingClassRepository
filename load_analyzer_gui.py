import csv
import math
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.ticker import MultipleLocator


SECTION_DIMENSIONS = {
    "사각형": (("rect_b", "폭 b (mm)", "10"), ("rect_h", "높이 h (mm)", "10")),
    "원형봉": (("bar_d", "지름 d (mm)", "20"),),
    "원형관": (
        ("round_tube_D", "외경 D (mm)", "40"),
        ("round_tube_t", "두께 t (mm)", "5"),
    ),
    "사각형관": (
        ("rect_tube_B", "외측 폭 B (mm)", "40"),
        ("rect_tube_H", "외측 높이 H (mm)", "60"),
        ("rect_tube_t", "두께 t (mm)", "5"),
    ),
    "H형강": (
        ("h_beam_H", "전체 높이 H (mm)", "100"),
        ("h_beam_B", "플랜지 폭 B (mm)", "80"),
        ("h_beam_tw", "웨브 두께 tw (mm)", "5"),
        ("h_beam_tf", "플랜지 두께 tf (mm)", "8"),
    ),
}


def read_valid_rows(csv_path: Path) -> tuple[list[tuple[float, float]], int]:
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
            raise ValueError(
                f"CSV에 필요한 열이 없습니다: {', '.join(sorted(missing_columns))}"
            )

        time_index = header.index("time_s")
        force_index = header.index("force_N")

        for line in csv_file:
            if not line.strip():
                continue

            try:
                row = next(csv.reader([line], strict=True))
            except csv.Error:
                excluded_rows += 1
                continue

            if len(row) != len(header):
                excluded_rows += 1
                continue

            try:
                time_s = float(row[time_index])
                force_n = float(row[force_index])
            except ValueError:
                excluded_rows += 1
                continue

            if not math.isfinite(time_s) or not math.isfinite(force_n):
                excluded_rows += 1
                continue

            valid_rows.append((time_s, force_n))

    return valid_rows, excluded_rows


class LoadAnalyzerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("하중-응력 분석기")
        self.root.geometry("900x700")
        self.root.minsize(760, 580)

        self.csv_path: Path | None = None
        self.valid_rows: list[tuple[float, float]] = []
        self.path_var = tk.StringVar(value="")
        self.data_count_var = tk.StringVar(value="CSV 파일을 선택하세요.")
        self.shape_var = tk.StringVar(value="사각형")
        self.dimension_fields: dict[str, tuple[ttk.Label, ttk.Entry]] = {}
        self.result_vars = {
            "area": tk.StringVar(value="-"),
            "force": tk.StringVar(value="-"),
            "stress": tk.StringVar(value="-"),
            "time": tk.StringVar(value="-"),
        }

        self._build_layout()

    def _build_layout(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(3, weight=1)

        file_frame = ttk.LabelFrame(self.root, text="입력 CSV", padding=10)
        file_frame.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        file_frame.columnconfigure(1, weight=1)

        ttk.Button(file_frame, text="CSV 찾아보기", command=self._browse_csv).grid(
            row=0, column=0, padx=(0, 8)
        )
        path_entry = ttk.Entry(file_frame, textvariable=self.path_var, state="readonly")
        path_entry.grid(row=0, column=1, sticky="ew")
        ttk.Label(file_frame, textvariable=self.data_count_var).grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(8, 0)
        )

        input_frame = ttk.LabelFrame(self.root, text="단면 설정", padding=10)
        input_frame.grid(row=1, column=0, sticky="ew", padx=12, pady=6)
        input_frame.columnconfigure(3, weight=1)
        self.input_frame = input_frame

        ttk.Label(input_frame, text="단면 종류").grid(row=0, column=0, sticky="w")
        self.shape_box = ttk.Combobox(
            input_frame,
            textvariable=self.shape_var,
            values=tuple(SECTION_DIMENSIONS),
            state="readonly",
            width=12,
        )
        self.shape_box.grid(row=0, column=1, sticky="w", padx=(8, 18))
        self.shape_box.bind("<<ComboboxSelected>>", self._on_shape_changed)

        ttk.Button(input_frame, text="분석", command=self._analyze).grid(
            row=0, column=2, columnspan=2, sticky="e"
        )
        self._show_dimension_fields()

        result_frame = ttk.LabelFrame(self.root, text="분석 결과", padding=10)
        result_frame.grid(row=2, column=0, sticky="ew", padx=12, pady=6)
        for column in range(4):
            result_frame.columnconfigure(column, weight=1)

        result_items = (
            ("단면적", "area", "mm²"),
            ("최대 하중", "force", "N"),
            ("최대 응력", "stress", "MPa"),
            ("발생 시간", "time", "s"),
        )
        for column, (label, key, unit) in enumerate(result_items):
            ttk.Label(result_frame, text=label).grid(
                row=0, column=column, sticky="w", padx=6
            )
            ttk.Label(
                result_frame,
                textvariable=self.result_vars[key],
                font=("TkDefaultFont", 12, "bold"),
                wraplength=190,
            ).grid(row=1, column=column, sticky="w", padx=6, pady=(4, 0))
            ttk.Label(result_frame, text=unit).grid(
                row=2, column=column, sticky="w", padx=6
            )

        graph_frame = ttk.LabelFrame(self.root, text="응력 시계열 그래프", padding=8)
        graph_frame.grid(
            row=3, column=0, sticky="nsew", padx=12, pady=(6, 12)
        )
        graph_frame.columnconfigure(0, weight=1)
        graph_frame.rowconfigure(0, weight=1)

        self.figure = Figure(figsize=(8, 4), dpi=100)
        self.axes = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=graph_frame)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")
        self._draw_empty_graph()

    def _on_shape_changed(self, event: tk.Event) -> None:
        del event
        self._show_dimension_fields()
        self._clear_results()

    def _show_dimension_fields(self) -> None:
        for label, entry in self.dimension_fields.values():
            label.grid_remove()
            entry.grid_remove()

        for index, (key, label_text, default_value) in enumerate(
            SECTION_DIMENSIONS[self.shape_var.get()]
        ):
            if key not in self.dimension_fields:
                label = ttk.Label(self.input_frame, text=label_text)
                entry = ttk.Entry(self.input_frame, width=12)
                entry.insert(0, default_value)
                self.dimension_fields[key] = (label, entry)

            label, entry = self.dimension_fields[key]
            label.configure(text=label_text)
            row = 1 + index // 2
            column = (index % 2) * 2
            label.grid(row=row, column=column, sticky="w", padx=(0, 6), pady=(8, 0))
            entry.grid(
                row=row, column=column + 1, sticky="w", padx=(0, 16), pady=(8, 0)
            )

    def _browse_csv(self) -> None:
        selected_file = filedialog.askopenfilename(
            title="하중 데이터 CSV 선택",
            initialdir=Path(__file__).parent,
            filetypes=(("CSV 파일", "*.csv"), ("모든 파일", "*.*")),
        )
        if not selected_file:
            return

        self.csv_path = Path(selected_file)
        self.path_var.set(str(self.csv_path))
        self._clear_results()

        try:
            self.valid_rows, excluded_rows = read_valid_rows(self.csv_path)
        except (OSError, UnicodeError, ValueError) as error:
            self.valid_rows = []
            self.data_count_var.set("유효 데이터 수: 읽기 오류")
            messagebox.showerror("CSV 읽기 오류", str(error), parent=self.root)
            return

        self.data_count_var.set(
            f"유효 데이터 수: {len(self.valid_rows)} (제외 행: {excluded_rows})"
        )

    def _positive_dimension(self, entry: ttk.Entry, label: str) -> float:
        raw_value = entry.get().strip()
        if not raw_value:
            raise ValueError(f"{label}을(를) 입력하세요.")
        try:
            value = float(raw_value)
        except ValueError as error:
            raise ValueError(f"{label}은(는) 숫자로 입력하세요.") from error
        if not math.isfinite(value):
            raise ValueError(f"{label}은(는) 유한한 숫자여야 합니다.")
        if value == 0:
            raise ValueError(f"{label}은(는) 0일 수 없습니다. 0보다 큰 값을 입력하세요.")
        if value < 0:
            raise ValueError(f"{label}은(는) 음수일 수 없습니다. 0보다 큰 값을 입력하세요.")
        return value

    def _get_area_mm2(self) -> float:
        shape = self.shape_var.get()
        dimensions = {}
        for specification in SECTION_DIMENSIONS[shape]:
            key, label = specification[0], specification[1]
            dimensions[key] = self._positive_dimension(
                self.dimension_fields[key][1], label
            )

        try:
            if shape == "사각형":
                area_mm2 = dimensions["rect_b"] * dimensions["rect_h"]
            elif shape == "원형봉":
                area_mm2 = math.pi * dimensions["bar_d"] ** 2 / 4
            elif shape == "원형관":
                outer_diameter = dimensions["round_tube_D"]
                thickness = dimensions["round_tube_t"]
                if 2 * thickness >= outer_diameter:
                    raise ValueError("원형관은 2t < D 조건을 만족해야 합니다.")
                inner_diameter = outer_diameter - 2 * thickness
                area_mm2 = math.pi * (
                    outer_diameter**2 - inner_diameter**2
                ) / 4
            elif shape == "사각형관":
                outer_width = dimensions["rect_tube_B"]
                outer_height = dimensions["rect_tube_H"]
                thickness = dimensions["rect_tube_t"]
                if 2 * thickness >= outer_width or 2 * thickness >= outer_height:
                    raise ValueError(
                        "사각형관은 2t < B 및 2t < H 조건을 만족해야 합니다."
                    )
                area_mm2 = outer_width * outer_height - (
                    outer_width - 2 * thickness
                ) * (outer_height - 2 * thickness)
            else:
                total_height = dimensions["h_beam_H"]
                flange_width = dimensions["h_beam_B"]
                web_thickness = dimensions["h_beam_tw"]
                flange_thickness = dimensions["h_beam_tf"]
                if 2 * flange_thickness >= total_height:
                    raise ValueError("H형강은 2tf < H 조건을 만족해야 합니다.")
                if web_thickness >= flange_width:
                    raise ValueError("H형강은 tw < B 조건을 만족해야 합니다.")
                area_mm2 = (
                    2 * flange_width * flange_thickness
                    + (total_height - 2 * flange_thickness) * web_thickness
                )
        except OverflowError as error:
            raise ValueError("입력 치수 범위가 너무 커 단면적을 계산할 수 없습니다.") from error

        if not math.isfinite(area_mm2) or area_mm2 <= 0:
            raise ValueError("계산된 단면적이 유효한 양수가 아닙니다.")
        return area_mm2

    def _analyze(self) -> None:
        if self.csv_path is None:
            messagebox.showwarning(
                "파일 선택 필요", "먼저 분석할 CSV 파일을 선택하세요.", parent=self.root
            )
            return

        try:
            area_mm2 = self._get_area_mm2()
        except ValueError as error:
            self._clear_results()
            messagebox.showerror("치수 입력 오류", str(error), parent=self.root)
            return

        try:
            valid_rows, excluded_rows = read_valid_rows(self.csv_path)
            if not valid_rows:
                raise ValueError("유효한 데이터가 없어 분석할 수 없습니다.")
        except (OSError, UnicodeError, ValueError) as error:
            self.valid_rows = []
            self.data_count_var.set("유효 데이터 수: 읽기 오류")
            self._clear_results()
            messagebox.showerror("CSV 분석 오류", str(error), parent=self.root)
            return

        self.valid_rows = valid_rows
        self.data_count_var.set(
            f"유효 데이터 수: {len(valid_rows)} (제외 행: {excluded_rows})"
        )

        times = [row[0] for row in valid_rows]
        forces = [row[1] for row in valid_rows]
        stresses = [force_n / area_mm2 for force_n in forces]
        maximum_force = max(forces)
        maximum_stress = max(stresses)
        maximum_stress_indices = [
            index for index, stress in enumerate(stresses) if stress == maximum_stress
        ]
        maximum_times = [times[index] for index in maximum_stress_indices]

        self._draw_graph(times, stresses, maximum_stress_indices)
        self.result_vars["area"].set(f"{area_mm2:g}")
        self.result_vars["force"].set(f"{maximum_force:g}")
        self.result_vars["stress"].set(f"{maximum_stress:g}")
        self.result_vars["time"].set(", ".join(f"{time_s:g}" for time_s in maximum_times))

    def _draw_graph(
        self, times: list[float], stresses: list[float], maximum_indices: list[int]
    ) -> None:
        self.axes.clear()
        self.axes.plot(times, stresses, marker="o")
        maximum_times = [times[index] for index in maximum_indices]
        maximum_stresses = [stresses[index] for index in maximum_indices]
        self.axes.scatter(
            maximum_times,
            maximum_stresses,
            color="crimson",
            marker="D",
            s=80,
            zorder=3,
        )
        first_maximum = maximum_indices[0]
        self.axes.annotate(
            f"Max: {stresses[first_maximum]:g} MPa\nTime: {times[first_maximum]:g} s",
            xy=(times[first_maximum], stresses[first_maximum]),
            xytext=(10, -34),
            textcoords="offset points",
            color="crimson",
            arrowprops={"arrowstyle": "->", "color": "crimson", "linewidth": 0.8},
        )
        self.axes.set_xlabel("Time (s)")
        self.axes.set_ylabel("Stress (MPa)")
        self.axes.xaxis.set_major_locator(MultipleLocator(2))
        self.axes.yaxis.set_major_locator(MultipleLocator(1))
        self.axes.grid(
            True, which="major", axis="both", linestyle="-", linewidth=0.6, alpha=0.3
        )
        self.figure.tight_layout()
        self.canvas.draw_idle()

    def _draw_empty_graph(self) -> None:
        self.axes.clear()
        self.axes.set_xlabel("Time (s)")
        self.axes.set_ylabel("Stress (MPa)")
        self.axes.grid(
            True, which="major", axis="both", linestyle="-", linewidth=0.6, alpha=0.3
        )
        self.figure.tight_layout()
        self.canvas.draw_idle()

    def _clear_results(self) -> None:
        for result_var in self.result_vars.values():
            result_var.set("-")
        self._draw_empty_graph()


def main() -> None:
    root = tk.Tk()
    LoadAnalyzerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
