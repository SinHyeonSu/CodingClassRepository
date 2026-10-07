# 힘 변환 및 하중 분석

Python으로 만든 힘 단위 변환기와 CSV 하중 분석기입니다.

## 실행 환경

- Python 3
- `load_analyzer.py`에 필요한 패키지: `pandas`, `matplotlib`
- `force_converter.py`에는 별도 패키지가 필요하지 않습니다. Tkinter는 일반적인 Windows Python 설치에 포함됩니다.

분석기 패키지는 다음 명령으로 설치합니다.

```bash
python -m pip install pandas matplotlib
```

## 힘 단위 변환기

프로젝트 폴더에서 실행합니다.

```bash
python force_converter.py
```

숫자를 입력하고 `kN`, `N`, `kgf` 중 단위를 선택한 다음 **변환**을 누르면 세 단위의 값이 표시됩니다. **초기화**를 누르면 입력과 결과가 지워집니다.

변환 기준은 `1 kN = 1000 N`, `1 kgf = 9.80665 N`입니다. 결과는 소수점 둘째 자리까지 표시됩니다.

## 하중 데이터 분석기

프로젝트 폴더에서 실행합니다.

```bash
python load_analyzer.py
```

분석기는 스크립트와 같은 폴더의 `load_data.csv`를 읽습니다. CSV에는 `time_s`와 `force_N` 열이 필요합니다.

```csv
time_s,force_N
0,0
1,100
2,250
```

단면적은 `load_analyzer.py`의 `area_mm2` 값으로 설정하며, 현재 값은 `100 mm²`입니다. 평균 수직 응력은 다음과 같이 계산합니다.

```text
stress_MPa = force_N / area_mm2
1 N/mm² = 1 MPa
```

분석기는 데이터 개수, 최대 하중과 시간, 최대 평균 수직 응력과 시간을 출력합니다. 또한 기준 응력 `6 MPa`를 **초과하는** 데이터 행의 개수를 출력합니다. 기준값은 `load_analyzer.py`의 `REFERENCE_STRESS_MPA`에서 변경할 수 있습니다.

응력 그래프는 각 데이터 지점을 표시하고 선으로 연결합니다. 최대 응력 지점은 빨간 마커와 응력값·시간 주석으로 강조됩니다. x축은 `Time(s)`, y축은 `Stress(MPa)`이며, x축에는 2초 간격, y축에는 1 MPa 간격의 희미한 실선 격자가 표시됩니다.

### 입력 오류 처리

`time_s` 또는 `force_N` 값이 비었거나 숫자가 아니면 원본 CSV의 행 번호와 문제 값을 출력하고 해당 행을 제외합니다. 열 개수가 맞지 않거나 CSV 형식을 읽을 수 없는 행도 제외합니다. 제외한 행 수와 유효한 데이터 수를 출력한 뒤 유효한 행만으로 분석을 계속합니다.

유효한 데이터가 없으면 계산과 결과 생성을 중단합니다. 원본 CSV는 수정하지 않습니다.

### 생성 파일

- `load_result.csv`: `time_s`, `force_N`, `stress_MPa` 열을 저장합니다.
- `stress_plot.png`: 시간-응력 그래프를 저장합니다.
