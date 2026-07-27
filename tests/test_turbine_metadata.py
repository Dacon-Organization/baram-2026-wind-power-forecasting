from pathlib import Path

import pandas as pd
import pytest

from baram.features.turbine_metadata import (
  GROUP_CAPACITY_MW,
  GROUP_TURBINE_COUNTS,
  INFO_HEADER_MARKERS,
  TURBINE_COUNT,
  load_turbine_locations,
  parse_dms_coordinate,
)
from baram.features.turbine_spatial import TURBINE_LOCATION_COLUMNS


def findOfficialInfoPath():
  """worktree에는 원자료가 없으므로 상위 경로를 거슬러 올라가며 공식 파일을 찾는다."""
  for parent in Path(__file__).resolve().parents:
    candidate = parent / "data" / "raw" / "open" / "info.xlsx"
    if candidate.is_file():
      return candidate
  return None


OFFICIAL_INFO_PATH = findOfficialInfoPath()

INFO_HEADER = [
  "단계",
  "명칭",
  "제작사",
  "모델명",
  "호기",
  "좌표(Google)",
  "KPX그룹",
  "Hub Height(m)",
  "Rotor Diameter(m)",
  "설비용량(MW)",
  "그룹설비용량(MW)",
]

TURBINE_ROWS = [
  (1, "태백가덕산", "VESTAS", "V126", 1, "37°16'55.61\"N 128°57'02.10\"E", 1, 117, 126, 3.6, 21.6),
  (1, "태백가덕산", "VESTAS", "V126", 2, "37°17'04.05\"N 128°56'58.35\"E", None, 117, 126, 3.6, None),
  (1, "태백가덕산", "VESTAS", "V126", 3, "37°17'11.49\"N 128°56'58.99\"E", None, 117, 126, 3.6, None),
  (1, "태백가덕산", "VESTAS", "V126", 4, "37°17'23.11\"N 128°57'03.68\"E", None, 117, 126, 3.6, None),
  (1, "태백가덕산", "VESTAS", "V126", 5, "37°17'28.20\"N 128°57'15.58\"E", None, 117, 126, 3.6, None),
  (1, "태백가덕산", "VESTAS", "V126", 6, "37°17'19.48\"N 128°57'24.96\"E", None, 117, 126, 3.6, None),
  (1, "태백가덕산", "VESTAS", "V126", 7, "37°17'16.20\"N 128°57'34.67\"E", 2, 117, 126, 3.6, 21.6),
  (1, "태백가덕산", "VESTAS", "V126", 8, "37°17'11.29\"N 128°57'47.24\"E", None, 117, 126, 3.6, None),
  (1, "태백가덕산", "VESTAS", "V126", 9, "37°17'00.97\"N 128°57'57.44\"E", None, 117, 126, 3.6, None),
  (1, "태백가덕산", "VESTAS", "V126", 10, "37°16'52.77\"N 128°58'04.18\"E", None, 117, 126, 3.6, None),
  (1, "태백가덕산", "VESTAS", "V126", 11, "37°16'44.89\"N 128°58'01.12\"E", None, 117, 126, 3.6, None),
  (1, "태백가덕산", "VESTAS", "V126", 12, "37°16'30.58\"N 128°58'02.54\"E", None, 117, 126, 3.6, None),
  (2, "태백가덕산", "UNISON", "U136", 1, "37°16'59.73\"N 128°57'44.97\"E", 3, 117, 136, 4.2, 21.0),
  (2, "태백원동", "UNISON", "U136", 2, "37°16'40.41\"N 128°58'13.80\"E", None, 117, 136, 4.2, None),
  (2, "태백원동", "UNISON", "U136", 3, "37°16'28.03\"N 128°58'22.54\"E", None, 117, 136, 4.2, None),
  (2, "태백원동", "UNISON", "U136", 4, "37°16'18.58\"N 128°58'29.01\"E", None, 117, 136, 4.2, None),
  (2, "태백원동", "UNISON", "U136", 5, "37°16'06.83\"N 128°58'35.68\"E", None, 117, 136, 4.2, None),
]


def writeInfoWorkbook(path, *, rows=None, header=None, titleRows=3):
  """공식 info.xlsx와 같은 배치(제목 → 빈 줄 → 헤더 → 데이터)로 fixture를 만든다."""
  usedRows = TURBINE_ROWS if rows is None else rows
  usedHeader = INFO_HEADER if header is None else header
  table = [[None] * len(usedHeader) for _ in range(titleRows)]
  table[0][0] = "태백가덕산풍력발전 정보"
  table.append(list(usedHeader))
  for row in usedRows:
    table.append(list(row))
  pd.DataFrame(table).to_excel(path, index=False, header=False)
  return path


@pytest.fixture
def infoWorkbook(tmp_path):
  return writeInfoWorkbook(tmp_path / "info.xlsx")


class TestDmsParsing:
  def test_공식_표기를_십진수로_변환한다(self):
    latitude, longitude = parse_dms_coordinate("37°16'55.61\"N 128°57'02.10\"E")
    assert latitude == pytest.approx(37.282114, abs=1e-6)
    assert longitude == pytest.approx(128.950583, abs=1e-6)

  def test_남반구와_서경은_부호를_뒤집는다(self):
    latitude, longitude = parse_dms_coordinate("10°30'00.00\"S 20°15'00.00\"W")
    assert latitude == pytest.approx(-10.5)
    assert longitude == pytest.approx(-20.25)

  def test_공백이_여러_개여도_읽는다(self):
    latitude, _ = parse_dms_coordinate("  37°16'55.61\"N   128°57'02.10\"E  ")
    assert latitude == pytest.approx(37.282114, abs=1e-6)

  @pytest.mark.parametrize(
    "text",
    [
      "37.282114, 128.950583",
      "37°16'55.61\"N",
      "37°16'55.61\"X 128°57'02.10\"E",
      "",
      None,
    ],
  )
  def test_형식이_다르면_거부한다(self, text):
    with pytest.raises(ValueError, match="좌표"):
      parse_dms_coordinate(text)

  def test_분초_범위를_벗어나면_거부한다(self):
    with pytest.raises(ValueError, match="분/초"):
      parse_dms_coordinate("37°61'55.61\"N 128°57'02.10\"E")


class TestLoadTurbineLocations:
  def test_공간_pooler가_요구하는_스키마를_돌려준다(self, infoWorkbook):
    frame = load_turbine_locations(infoWorkbook)
    assert list(frame.columns) == list(TURBINE_LOCATION_COLUMNS)
    assert len(frame) == TURBINE_COUNT

  def test_터빈_id는_제작사와_호기로_만든다(self, infoWorkbook):
    frame = load_turbine_locations(infoWorkbook)
    assert frame["turbine_id"].tolist()[:2] == ["VESTAS-01", "VESTAS-02"]
    assert frame["turbine_id"].tolist()[-1] == "UNISON-05"
    assert frame["turbine_id"].is_unique

  def test_KPX그룹은_전방_채움으로_복원한다(self, infoWorkbook):
    frame = load_turbine_locations(infoWorkbook)
    counts = frame["group_id"].value_counts().to_dict()
    assert counts == GROUP_TURBINE_COUNTS
    assert frame.loc[frame["turbine_id"] == "VESTAS-06", "group_id"].item() == "group_1"
    assert frame.loc[frame["turbine_id"] == "VESTAS-07", "group_id"].item() == "group_2"

  def test_좌표를_십진수로_변환한다(self, infoWorkbook):
    frame = load_turbine_locations(infoWorkbook)
    first = frame.iloc[0]
    assert first["latitude"] == pytest.approx(37.282114, abs=1e-6)
    assert first["longitude"] == pytest.approx(128.950583, abs=1e-6)

  def test_그룹_설비용량이_터빈_합과_일치한다(self, infoWorkbook):
    frame = load_turbine_locations(infoWorkbook)
    totals = frame.groupby("group_id")["capacity_mw"].sum().round(6).to_dict()
    assert totals == pytest.approx(GROUP_CAPACITY_MW)

  def test_결정론적으로_같은_순서를_돌려준다(self, infoWorkbook):
    left = load_turbine_locations(infoWorkbook)
    right = load_turbine_locations(infoWorkbook)
    pd.testing.assert_frame_equal(left, right)

  def test_헤더_행_위치가_달라도_찾는다(self, tmp_path):
    path = writeInfoWorkbook(tmp_path / "shifted.xlsx", titleRows=6)
    frame = load_turbine_locations(path)
    assert len(frame) == TURBINE_COUNT

  def test_헤더_마커가_없으면_거부한다(self, tmp_path):
    path = writeInfoWorkbook(
      tmp_path / "bad_header.xlsx",
      header=["a"] * len(INFO_HEADER),
    )
    with pytest.raises(ValueError, match="헤더"):
      load_turbine_locations(path)

  def test_터빈_수가_다르면_거부한다(self, tmp_path):
    path = writeInfoWorkbook(tmp_path / "short.xlsx", rows=TURBINE_ROWS[:-1])
    with pytest.raises(ValueError, match="터빈 수"):
      load_turbine_locations(path)

  def test_첫_행에_그룹이_없으면_거부한다(self, tmp_path):
    rows = [list(row) for row in TURBINE_ROWS]
    rows[0][6] = None
    path = writeInfoWorkbook(tmp_path / "no_first_group.xlsx", rows=rows)
    with pytest.raises(ValueError, match="KPX그룹"):
      load_turbine_locations(path)

  def test_그룹_용량이_어긋나면_거부한다(self, tmp_path):
    rows = [list(row) for row in TURBINE_ROWS]
    rows[0][9] = 9.9
    path = writeInfoWorkbook(tmp_path / "bad_capacity.xlsx", rows=rows)
    with pytest.raises(ValueError, match="설비용량"):
      load_turbine_locations(path)

  def test_없는_파일을_거부한다(self, tmp_path):
    with pytest.raises(FileNotFoundError):
      load_turbine_locations(tmp_path / "missing.xlsx")


@pytest.mark.skipif(
  OFFICIAL_INFO_PATH is None,
  reason="공식 info.xlsx는 로컬에만 두므로 CI에서는 건너뛴다",
)
class TestOfficialInfoWorkbook:
  def test_공식_파일에서도_17기_3그룹을_읽는다(self):
    frame = load_turbine_locations(OFFICIAL_INFO_PATH)
    assert len(frame) == TURBINE_COUNT
    assert frame["group_id"].value_counts().to_dict() == GROUP_TURBINE_COUNTS
    assert frame["capacity_mw"].sum() == pytest.approx(64.2)

  def test_공식_좌표는_태백_풍력단지_범위_안에_있다(self):
    frame = load_turbine_locations(OFFICIAL_INFO_PATH)
    assert frame["latitude"].between(37.2, 37.4).all()
    assert frame["longitude"].between(128.8, 129.1).all()


def test_헤더_마커는_좌표와_그룹_컬럼을_포함한다():
  assert "좌표(Google)" in INFO_HEADER_MARKERS
  assert "KPX그룹" in INFO_HEADER_MARKERS
