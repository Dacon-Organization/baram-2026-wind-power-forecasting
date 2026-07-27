import pytest

from baram.feature_config import (
  DEFAULT_FEATURE_SET,
  FEATURE_SETS,
  feature_set_sha256,
  get_feature_set,
  resolve_feature_set,
)
from baram.registry import (
  MODEL_METADATA_SCHEMA_VERSION,
  PREPROCESSING_CONTRACT,
  build_feature_set_record,
  build_preprocessing_contract,
)
from baram.reproducibility import sha256_text, stable_json_dumps


def contractHash(contract):
  return sha256_text(stable_json_dumps(contract))


class TestGoldenRegression:
  def test_official_mean_파생은_legacy_상수와_완전히_같다(self):
    """G2 골든 — 이 등가성이 깨지면 승격 전 제출물과 hash가 달라진다."""
    derived = build_preprocessing_contract(get_feature_set(DEFAULT_FEATURE_SET))
    assert derived == PREPROCESSING_CONTRACT
    assert contractHash(derived) == contractHash(PREPROCESSING_CONTRACT)

  def test_인자를_생략하면_official_mean과_같다(self):
    assert build_preprocessing_contract() == PREPROCESSING_CONTRACT

  def test_legacy_계약에는_공간_wind_vector_키가_없다(self):
    assert "spatial_pooling" not in PREPROCESSING_CONTRACT
    assert "wind_vector" not in PREPROCESSING_CONTRACT
    assert "lead_feature" in PREPROCESSING_CONTRACT


class TestDerivedContract:
  def test_통계가_계약에_반영된다(self):
    contract = build_preprocessing_contract(get_feature_set("expanded_vector"))
    assert contract["weather_aggregation"]["statistics"] == ["mean", "std", "min", "max"]

  def test_wind_vector를_켜면_파생_규약이_남는다(self):
    contract = build_preprocessing_contract(get_feature_set("expanded_vector"))
    assert contract["wind_vector"]["derived_from"] == "raw grid rows before aggregation"
    assert contract["wind_vector"]["specs"]["ldaps"] == ["10m"]
    assert contract["wind_vector"]["specs"]["gfs"] == ["10m", "80m", "100m"]

  def test_공간_pooling_설정이_계약에_남는다(self):
    contract = build_preprocessing_contract(get_feature_set("spatial_idw2_all_group"))
    assert contract["spatial_pooling"]["methods"] == ["idw"]
    assert contract["spatial_pooling"]["idw_power"] == pytest.approx(2.0)
    assert contract["spatial_pooling"]["scope"] == "all_group"

  def test_scope가_다르면_계약_hash가_달라진다(self):
    allGroup = build_preprocessing_contract(get_feature_set("spatial_idw2_all_group"))
    ownGroup = build_preprocessing_contract(get_feature_set("spatial_nearest_own_group"))
    assert contractHash(allGroup) != contractHash(ownGroup)

  def test_프리셋마다_계약_hash가_모두_다르다(self):
    digests = {
      name: contractHash(build_preprocessing_contract(config))
      for name, config in FEATURE_SETS.items()
    }
    assert len(set(digests.values())) == len(FEATURE_SETS)

  def test_공통_계약_항목은_프리셋과_무관하게_유지된다(self):
    for config in FEATURE_SETS.values():
      contract = build_preprocessing_contract(config)
      assert contract["weather_cutoff"]["on_violation"] == "fail"
      assert contract["missing_values"]["strategy"] == "median"
      assert contract["target_training"]["models"] == "one model per target"
      assert contract["prediction_bounds"]["lower"] == 0

  def test_FeatureSetConfig가_아니면_거부한다(self):
    with pytest.raises(TypeError, match="FeatureSetConfig"):
      build_preprocessing_contract("official_mean")


class TestFeatureSetRecord:
  def test_metadata_schema는_1_1이다(self):
    assert MODEL_METADATA_SCHEMA_VERSION == "1.1"

  def test_legacy_경로는_official_mean으로_기록한다(self):
    record = build_feature_set_record()
    assert record["name"] == DEFAULT_FEATURE_SET
    assert record["source"] == "legacy"
    assert record["resolved_sha256"] == feature_set_sha256(
      get_feature_set(DEFAULT_FEATURE_SET)
    )

  def test_해석된_피처셋의_이름과_hash를_남긴다(self):
    resolved = resolve_feature_set(name="spatial_idw2_all_group")
    record = build_feature_set_record(resolved)
    assert record["name"] == "spatial_idw2_all_group"
    assert record["source"] == "preset"
    assert record["resolved_sha256"] == resolved.sha256
    assert record["scope"] == "all_group"

  def test_파이프라인을_주면_target별_컬럼_수를_남긴다(self):
    class FakePipeline:
      feature_columns = tuple(f"f{index}" for index in range(550))
      target_feature_columns = {
        "kpx_group_1": tuple(f"f{index}" for index in range(396)),
        "kpx_group_2": tuple(f"f{index}" for index in range(396)),
        "kpx_group_3": tuple(f"f{index}" for index in range(396)),
      }

    resolved = resolve_feature_set(name="spatial_nearest_own_group")
    record = build_feature_set_record(resolved, FakePipeline())
    assert record["feature_count"] == 550
    assert record["target_feature_counts"] == {
      "kpx_group_1": 396,
      "kpx_group_2": 396,
      "kpx_group_3": 396,
    }
    assert record["scope"] == "own_group"
