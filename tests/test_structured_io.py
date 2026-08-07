import json

import pytest
import yaml

from multical.io.structured import load_json_or_yaml


@pytest.mark.parametrize("suffix", [".json", ".yaml"])
def test_load_json_or_yaml_mapping(tmp_path, suffix):
  path = tmp_path / ("document" + suffix)
  payload = {"camera": "cam0", "points": [[1, 2, 3]]}
  if suffix == ".json":
    path.write_text(json.dumps(payload), encoding="utf-8")
  else:
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")

  assert load_json_or_yaml(path, require_mapping=True) == payload


def test_load_json_or_yaml_reports_invalid_mapping(tmp_path):
  path = tmp_path / "document.yaml"
  path.write_text("- one\n- two\n", encoding="utf-8")

  with pytest.raises(ValueError, match="must contain a mapping"):
    load_json_or_yaml(path, description="correspondences", require_mapping=True)
