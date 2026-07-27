import json

import pytest

from baram.feature_config import (
  DEFAULT_FEATURE_SET,
  FEATURE_SETS,
  FeatureSetConfig,
  ResolvedFeatureSet,
  SPATIAL_SCOPES,
  SpatialPoolingConfig,
  feature_set_sha256,
  feature_set_to_dict,
  get_feature_set,
  resolve_feature_set,
)


def writeYaml(tmp_path, text, name="override.yaml"):
  path = tmp_path / name
  path.write_text(text, encoding="utf-8")
  return path


class TestPresetContract:
  def test_기본_피처셋은_official_mean이다(self):
    assert DEFAULT_FEATURE_SET == "official_mean"
    assert DEFAULT_FEATURE_SET in FEATURE_SETS

  def test_프리셋은_설계서에_고정한_4종이다(self):
    assert sorted(FEATURE_SETS) == [
      "expanded_vector",
      "official_mean",
      "spatial_idw2_all_group",
      "spatial_nearest_own_group",
    ]

  def test_official_mean은_공식_baseline_전처리와_같다(self):
    config = get_feature_set("official_mean")
    assert config.statistics == ("mean",)
    assert config.include_lead is False
    assert config.wind_vector is False
    assert config.spatial is None
    assert config.calendar is True

  def test_expanded_vector는_통계_4종과_lead_vector를_켠다(self):
    config = get_feature_set("expanded_vector")
    assert config.statistics == ("mean", "std", "min", "max")
    assert config.include_lead is True
    assert config.wind_vector is True
    assert config.spatial is None

  def test_채택_후보는_all_group_idw_p2다(self):
    config = get_feature_set("spatial_idw2_all_group")
    assert config.spatial.methods == ("idw",)
    assert config.spatial.idw_power == pytest.approx(2.0)
    assert config.spatial.scope == "all_group"

  def test_축소_대안은_own_group_nearest다(self):
    config = get_feature_set("spatial_nearest_own_group")
    assert config.spatial.methods == ("nearest",)
    assert config.spatial.scope == "own_group"

  def test_공간_프리셋은_expanded_vector_전처리를_상속한다(self):
    baseline = get_feature_set("expanded_vector")
    for name in ("spatial_idw2_all_group", "spatial_nearest_own_group"):
      config = get_feature_set(name)
      assert config.statistics == baseline.statistics
      assert config.include_lead == baseline.include_lead
      assert config.wind_vector == baseline.wind_vector

  def test_없는_프리셋_이름은_거부한다(self):
    with pytest.raises(ValueError, match="알 수 없는 피처셋"):
      get_feature_set("no_such_preset")

  def test_프리셋은_불변이다(self):
    config = get_feature_set("official_mean")
    with pytest.raises(Exception):
      config.statistics = ("mean", "std")


class TestConfigValidation:
  def test_통계_순서가_바뀌면_거부한다(self):
    with pytest.raises(ValueError, match="statistics 순서"):
      FeatureSetConfig(name="bad", statistics=("std", "mean"))

  def test_중복_통계를_거부한다(self):
    with pytest.raises(ValueError, match="statistics 순서"):
      FeatureSetConfig(name="bad", statistics=("mean", "mean"))

  def test_지원하지_않는_통계를_거부한다(self):
    with pytest.raises(ValueError, match="지원하지 않는 통계"):
      FeatureSetConfig(name="bad", statistics=("median",))

  def test_빈_통계를_거부한다(self):
    with pytest.raises(ValueError, match="하나 이상"):
      FeatureSetConfig(name="bad", statistics=())

  def test_리스트로_준_통계는_tuple로_정규화한다(self):
    config = FeatureSetConfig(name="ok", statistics=["mean", "std"])
    assert config.statistics == ("mean", "std")

  def test_이름이_비면_거부한다(self):
    with pytest.raises(ValueError, match="name"):
      FeatureSetConfig(name="  ")

  def test_bool이_아닌_플래그를_거부한다(self):
    with pytest.raises(TypeError, match="include_lead"):
      FeatureSetConfig(name="bad", include_lead=1)

  def test_지원하지_않는_pooling_method를_거부한다(self):
    with pytest.raises(ValueError, match="지원하지 않는 pooling"):
      SpatialPoolingConfig(methods=("kriging",))

  def test_pooling_method_순서가_바뀌면_거부한다(self):
    with pytest.raises(ValueError, match="methods 순서"):
      SpatialPoolingConfig(methods=("idw", "nearest"))

  def test_scope는_허용값만_받는다(self):
    assert SPATIAL_SCOPES == ("all_group", "own_group")
    with pytest.raises(ValueError, match="scope"):
      SpatialPoolingConfig(methods=("idw",), scope="per_turbine")

  def test_idw_power는_양의_유한값이어야_한다(self):
    for badPower in (0.0, -1.0, float("nan"), float("inf")):
      with pytest.raises(ValueError, match="idw_power"):
        SpatialPoolingConfig(methods=("idw",), idw_power=badPower)

  def test_spatial에_잘못된_타입을_거부한다(self):
    with pytest.raises(TypeError, match="spatial"):
      FeatureSetConfig(name="bad", spatial={"methods": ["idw"]})


class TestConfigHash:
  def test_같은_config는_같은_hash를_낸다(self):
    left = get_feature_set("spatial_idw2_all_group")
    right = FEATURE_SETS["spatial_idw2_all_group"]
    assert feature_set_sha256(left) == feature_set_sha256(right)

  def test_프리셋마다_hash가_다르다(self):
    digests = {name: feature_set_sha256(config) for name, config in FEATURE_SETS.items()}
    assert len(set(digests.values())) == len(FEATURE_SETS)

  def test_idw_power가_다르면_hash가_달라진다(self):
    base = get_feature_set("spatial_idw2_all_group")
    changed = FeatureSetConfig(
      name=base.name,
      statistics=base.statistics,
      include_lead=base.include_lead,
      wind_vector=base.wind_vector,
      spatial=SpatialPoolingConfig(methods=("idw",), idw_power=1.0, scope="all_group"),
    )
    assert feature_set_sha256(base) != feature_set_sha256(changed)

  def test_직렬화는_정렬된_JSON이며_float를_문자열로_고정한다(self):
    payload = feature_set_to_dict(get_feature_set("spatial_idw2_all_group"))
    assert payload["spatial"]["idw_power"] == "2"
    text = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    assert json.loads(text) == payload

  def test_tuple은_list로_직렬화된다(self):
    payload = feature_set_to_dict(get_feature_set("expanded_vector"))
    assert payload["statistics"] == ["mean", "std", "min", "max"]
    assert payload["spatial"] is None


class TestYamlOverride:
  def test_extends만_있으면_프리셋과_동일한_hash를_낸다(self, tmp_path):
    path = writeYaml(tmp_path, "extends: spatial_idw2_all_group\n")
    resolved = resolve_feature_set(config_path=path)
    preset = get_feature_set("spatial_idw2_all_group")
    assert feature_set_sha256(resolved.config) == feature_set_sha256(preset)

  def test_공백과_주석은_hash에_영향을_주지_않는다(self, tmp_path):
    plain = writeYaml(tmp_path, "extends: expanded_vector\n", name="a.yaml")
    noisy = writeYaml(
      tmp_path,
      "# 주석\n\nextends:   expanded_vector\n\n\n",
      name="b.yaml",
    )
    left = resolve_feature_set(config_path=plain)
    right = resolve_feature_set(config_path=noisy)
    assert feature_set_sha256(left.config) == feature_set_sha256(right.config)

  def test_spatial은_부분_병합한다(self, tmp_path):
    path = writeYaml(
      tmp_path,
      "extends: spatial_idw2_all_group\noverrides:\n  spatial:\n    idw_power: 1.0\n",
    )
    resolved = resolve_feature_set(config_path=path)
    assert resolved.config.spatial.methods == ("idw",)
    assert resolved.config.spatial.scope == "all_group"
    assert resolved.config.spatial.idw_power == pytest.approx(1.0)

  def test_spatial을_null로_제거할_수_있다(self, tmp_path):
    path = writeYaml(tmp_path, "extends: spatial_idw2_all_group\noverrides:\n  spatial: null\n")
    resolved = resolve_feature_set(config_path=path)
    assert resolved.config.spatial is None

  def test_이름을_지정하지_않으면_파일_stem을_붙인다(self, tmp_path):
    path = writeYaml(tmp_path, "extends: expanded_vector\n", name="idw1.yaml")
    resolved = resolve_feature_set(config_path=path)
    assert resolved.config.name == "expanded_vector+idw1"

  def test_이름을_지정하면_그대로_쓴다(self, tmp_path):
    path = writeYaml(tmp_path, "extends: expanded_vector\noverrides:\n  name: my_set\n")
    resolved = resolve_feature_set(config_path=path)
    assert resolved.config.name == "my_set"

  def test_extends가_없으면_거부한다(self, tmp_path):
    path = writeYaml(tmp_path, "overrides:\n  include_lead: true\n")
    with pytest.raises(ValueError, match="extends"):
      resolve_feature_set(config_path=path)

  def test_알_수_없는_최상위_키를_거부한다(self, tmp_path):
    path = writeYaml(tmp_path, "extends: expanded_vector\nextra: 1\n")
    with pytest.raises(ValueError, match="알 수 없는 키"):
      resolve_feature_set(config_path=path)

  def test_알_수_없는_override_키를_거부한다(self, tmp_path):
    path = writeYaml(tmp_path, "extends: expanded_vector\noverrides:\n  includelead: true\n")
    with pytest.raises(ValueError, match="알 수 없는 키"):
      resolve_feature_set(config_path=path)

  def test_알_수_없는_spatial_키를_거부한다(self, tmp_path):
    path = writeYaml(
      tmp_path,
      "extends: spatial_idw2_all_group\noverrides:\n  spatial:\n    power: 1.0\n",
    )
    with pytest.raises(ValueError, match="알 수 없는 키"):
      resolve_feature_set(config_path=path)

  def test_spatial이_없는_프리셋에_부분_병합하면_거부한다(self, tmp_path):
    path = writeYaml(
      tmp_path,
      "extends: expanded_vector\noverrides:\n  spatial:\n    idw_power: 1.0\n",
    )
    with pytest.raises(ValueError, match="methods"):
      resolve_feature_set(config_path=path)

  def test_존재하지_않는_프리셋을_상속하면_거부한다(self, tmp_path):
    path = writeYaml(tmp_path, "extends: nope\n")
    with pytest.raises(ValueError, match="알 수 없는 피처셋"):
      resolve_feature_set(config_path=path)

  def test_매핑이_아닌_YAML을_거부한다(self, tmp_path):
    path = writeYaml(tmp_path, "- extends: expanded_vector\n")
    with pytest.raises(ValueError, match="매핑"):
      resolve_feature_set(config_path=path)

  def test_없는_파일을_거부한다(self, tmp_path):
    with pytest.raises(FileNotFoundError):
      resolve_feature_set(config_path=tmp_path / "missing.yaml")


class TestResolve:
  def test_인자가_없으면_기본_프리셋을_돌려준다(self):
    resolved = resolve_feature_set()
    assert isinstance(resolved, ResolvedFeatureSet)
    assert resolved.config.name == DEFAULT_FEATURE_SET
    assert resolved.source == "preset"

  def test_프리셋_이름을_주면_source가_preset이다(self):
    resolved = resolve_feature_set(name="expanded_vector")
    assert resolved.source == "preset"
    assert resolved.sha256 == feature_set_sha256(get_feature_set("expanded_vector"))

  def test_YAML을_주면_source에_파일명이_남는다(self, tmp_path):
    path = writeYaml(tmp_path, "extends: expanded_vector\n", name="idw1.yaml")
    resolved = resolve_feature_set(config_path=path)
    assert resolved.source == "yaml:idw1.yaml"

  def test_이름과_파일을_동시에_주면_거부한다(self, tmp_path):
    path = writeYaml(tmp_path, "extends: expanded_vector\n")
    with pytest.raises(ValueError, match="동시에"):
      resolve_feature_set(name="expanded_vector", config_path=path)
