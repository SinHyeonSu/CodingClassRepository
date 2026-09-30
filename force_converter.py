import tkinter as tk
from tkinter import ttk

def convert_force():
    try:
        value = float(value_entry.get())
        unit = unit_combobox.get()

        if unit == "kN":
            force_n = value * 1000
        elif unit == "kgf":
            force_n = value * 9.80665
        else:
            force_n = value
        force_kn = force_n / 1000
        force_kgf = force_n / 9.80665
        result_label.config(
            text=f"결과: {force_n:.2f} N\n{force_kn:.2f} kN, {force_kgf:.2f} kgf",
            foreground="black",
        )
    except ValueError:
        result_label.config(
            text="잘못된 입력입니다. 숫자를 입력하세요.",
            foreground="red",
        )

def clear_all():
    value_entry.delete(0, tk.END)
    unit_combobox.set("kN")
    result_label.config(text="결과가 여기에 표시됩니다.", foreground="black")

window = tk.Tk()
window.title("힘 단위 변환기")
window.resizable(False, False)
main_frame = ttk.Frame(window, padding=20)
main_frame.grid()

ttk.Label(main_frame, text="힘 단위 변환기", font=("맑은 고딕", 16, "bold")).grid(
    row=0, column=0, columnspan=2, pady=(0, 15)
)
ttk.Label(main_frame, text="숫자 입력").grid(row=1, column=0, sticky="w", pady=5)
value_entry = ttk.Entry(main_frame, width=20)
value_entry.grid(row=1, column=1, pady=5)
ttk.Label(main_frame, text="입력 단위").grid(row=2, column=0, sticky="w", pady=5)
unit_combobox = ttk.Combobox(main_frame, values=("kN", "N", "kgf"), state="readonly", width=17)
unit_combobox.set("kN")
unit_combobox.grid(row=2, column=1, pady=5)

ttk.Button(main_frame, text="변환", command=convert_force).grid(
    row=3, column=0, padx=(0, 5), pady=15
)
ttk.Button(main_frame, text="초기화", command=clear_all).grid(
    row=3, column=1, padx=(5, 0), pady=15
)
result_label = ttk.Label(main_frame, text="결과가 여기에 표시됩니다.", justify="center")
result_label.grid(row=4, column=0, columnspan=2, pady=(5, 0))

value_entry.focus()
window.mainloop()
