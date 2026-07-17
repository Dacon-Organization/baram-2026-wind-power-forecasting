import numpy as np
import pandas as pd
import pytest

from baram.features.wind_vector import (
  WindVectorSpec,
  derive_wind_vector_features,
)


def makeWindFrame(source="ldaps"):
  frame = pd.DataFrame(
    {
      "forecast_kst_dtm": pd.to_datetime(["2024-01-01 01:00"] * 4),
      "grid_id": ["g0", "g1", "g2", "g3"],
      "heightAboveGround_10_10u": [3.0, 0.0, -1.0, 1.0],
      "heightAboveGround_10_10v": [4.0, -1.0, 0.0, 0.0],
    }
  )
  if source == "gfs":
    frame["heightAboveGround_80_u"] = [6.0, 0.0, -2.0, 2.0]
    frame["heightAboveGround_80_v"] = [8.0, -2.0, 0.0, 0.0]
    frame["heightAboveGround_100_100u"] = [9.0, 0.0, -3.0, 3.0]
    frame["heightAboveGround_100_100v"] = [12.0, -3.0, 0.0, 0.0]
  return frame


def testMissingRequiredWindComponentFailsClosed():
  frame = makeWindFrame().drop(columns=["heightAboveGround_10_10v"])

  with pytest.raises(ValueError, match="필수 U/V 컬럼 누락.*heightAboveGround_10_10v"):
    derive_wind_vector_features(frame, source="ldaps")


@pytest.mark.parametrize("badValue", ["문자", True, 1 + 2j])
def testNonRealWindComponentFailsClosed(badValue):
  frame = makeWindFrame()
  frame["heightAboveGround_10_10u"] = badValue

  with pytest.raises(ValueError, match="실수형이 아닌 U/V 컬럼"):
    derive_wind_vector_features(frame, source="ldaps")


def testExistingDerivedFeatureNameCollisionFailsClosed():
  frame = makeWindFrame()
  frame["windvec_10m_speed"] = 0.0

  with pytest.raises(ValueError, match="파생 feature 이름 충돌.*windvec_10m_speed"):
    derive_wind_vector_features(frame, source="ldaps")


def testDuplicateSpecNameFailsClosed():
  duplicateSpecs = (
    WindVectorSpec("same", "heightAboveGround_10_10u", "heightAboveGround_10_10v"),
    WindVectorSpec("same", "heightAboveGround_10_10u", "heightAboveGround_10_10v"),
  )

  with pytest.raises(ValueError, match="중복 파생 feature 이름"):
    derive_wind_vector_features(
      makeWindFrame(),
      source="ldaps",
      component_specs=duplicateSpecs,
    )


@pytest.mark.parametrize("badThreshold", [-1.0, np.nan, np.inf, True, "0.1"])
def testInvalidCalmSpeedThresholdFailsClosed(badThreshold):
  with pytest.raises(ValueError, match="calm_speed_threshold"):
    derive_wind_vector_features(
      makeWindFrame(),
      source="ldaps",
      calm_speed_threshold=badThreshold,
    )


def testThreeFourFiveMagnitudeAndMeteorologicalDirection():
  result = derive_wind_vector_features(makeWindFrame(), source="ldaps")

  assert result.loc[0, "windvec_10m_speed"] == pytest.approx(5.0)
  assert result.loc[0, "windvec_10m_from_sin"] == pytest.approx(-3.0 / 5.0)
  assert result.loc[0, "windvec_10m_from_cos"] == pytest.approx(-4.0 / 5.0)


def testMeteorologicalWindFromCompassQuadrants():
  frame = makeWindFrame()
  frame["heightAboveGround_10_10u"] = [0.0, -1.0, 0.0, 1.0]
  frame["heightAboveGround_10_10v"] = [-1.0, 0.0, 1.0, 0.0]

  result = derive_wind_vector_features(frame, source="ldaps")

  assert result["windvec_10m_from_sin"].to_numpy() == pytest.approx(
    [0.0, 1.0, 0.0, -1.0]
  )
  assert result["windvec_10m_from_cos"].to_numpy() == pytest.approx(
    [1.0, 0.0, -1.0, 0.0]
  )


def testCalmDirectionIsMissingButSpeedIsPreserved():
  frame = makeWindFrame()
  frame.loc[0, ["heightAboveGround_10_10u", "heightAboveGround_10_10v"]] = [0.0, 0.0]
  frame.loc[1, ["heightAboveGround_10_10u", "heightAboveGround_10_10v"]] = [3e-7, 4e-7]

  result = derive_wind_vector_features(
    frame,
    source="ldaps",
    calm_speed_threshold=5e-7,
  )

  assert result.loc[0, "windvec_10m_speed"] == 0.0
  assert result.loc[1, "windvec_10m_speed"] == pytest.approx(5e-7)
  assert result.loc[[0, 1], ["windvec_10m_from_sin", "windvec_10m_from_cos"]].isna().all().all()


def testMissingComponentPropagatesToAllThreeDerivedValues():
  frame = makeWindFrame()
  frame.loc[0, "heightAboveGround_10_10u"] = np.nan

  result = derive_wind_vector_features(frame, source="ldaps")

  assert result.loc[
    0,
    ["windvec_10m_speed", "windvec_10m_from_sin", "windvec_10m_from_cos"],
  ].isna().all()


def testInputIsUnchangedAndOutputOrderIsDeterministic():
  frame = makeWindFrame("gfs")
  original = frame.copy(deep=True)

  result = derive_wind_vector_features(frame, source="gfs")

  pd.testing.assert_frame_equal(frame, original)
  expectedDerived = [
    f"windvec_{height}_{suffix}"
    for height in ["10m", "80m", "100m"]
    for suffix in ["speed", "from_sin", "from_cos"]
  ]
  assert list(result.columns) == [*original.columns, *expectedDerived]


def testDefaultSpecsExcludeStressAndComponentExtrema():
  frame = makeWindFrame()
  frame["heightAboveGround_5_XBLWS"] = 1.0
  frame["heightAboveGround_5_YBLWS"] = 2.0
  frame["heightAboveGround_50_50MUmax"] = 3.0
  frame["heightAboveGround_50_50MVmax"] = 4.0

  result = derive_wind_vector_features(frame, source="ldaps")
  derivedColumns = [column for column in result.columns if column.startswith("windvec_")]

  assert derivedColumns == [
    "windvec_10m_speed",
    "windvec_10m_from_sin",
    "windvec_10m_from_cos",
  ]


def testUnsupportedSourceFailsClosed():
  with pytest.raises(ValueError, match="지원하지 않는 weather source"):
    derive_wind_vector_features(makeWindFrame(), source="wrf")
