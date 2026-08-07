import json
from zipfile import ZipFile

from multical.io.xlsx import write_report_workbook, write_workbook


def test_write_workbook_creates_portable_xlsx(tmp_path):
  destination = tmp_path / "report.xlsx"

  result = write_workbook(destination, [
    ("Summary", [["metric", "value"], ["RMS", 0.25]]),
    ("invalid/name", [["passed", True]])
  ])

  assert result == destination
  assert result.is_file()
  with ZipFile(result) as archive:
    names = set(archive.namelist())
    assert "[Content_Types].xml" in names
    assert "xl/workbook.xml" in names
    assert "xl/worksheets/sheet1.xml" in names
    workbook = archive.read("xl/workbook.xml").decode("utf-8")
    assert 'name="Summary"' in workbook
    assert 'name="invalid_name"' in workbook


def test_write_report_workbook_serializes_nested_values(tmp_path):
  destination = tmp_path / "evaluation.xlsx"
  report = {
    "summary": {"matched_count": 2},
    "points": [
      {"frame": "P01", "error_xyz": [0.1, 0.0, -0.1]},
      {"frame": "P02", "error_xyz": [0.0, 0.0, 0.0]}
    ]
  }

  write_report_workbook(destination, report, title="Evaluation")

  with ZipFile(destination) as archive:
    summary = archive.read("xl/worksheets/sheet1.xml").decode("utf-8")
    points = archive.read("xl/worksheets/sheet2.xml").decode("utf-8")
    assert "summary.matched_count" in summary
    assert json.dumps([0.1, 0.0, -0.1]) in points
