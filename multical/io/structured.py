"""Shared JSON/YAML loading at application I/O boundaries."""

import json
from pathlib import Path

import yaml


def load_json_or_yaml(filename, description="document", require_mapping=False):
  path = Path(filename).expanduser().resolve()
  if not path.is_file():
    raise FileNotFoundError("{} not found: {}".format(description, path))
  text = path.read_text(encoding="utf-8")
  try:
    data = (
      json.loads(text)
      if path.suffix.lower() == ".json"
      else yaml.safe_load(text)
    )
  except (json.JSONDecodeError, yaml.YAMLError) as error:
    raise ValueError(
      "{} is not valid JSON/YAML: {}".format(description, path)
    ) from error
  if require_mapping and not isinstance(data, dict):
    raise ValueError("{} must contain a mapping".format(description))
  return data
