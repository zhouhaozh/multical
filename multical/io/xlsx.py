"""Small dependency-free XLSX writer for calibration reports.

The project previously generated workbooks through a machine-local Node.js
package.  This module intentionally supports only the tabular data needed by
Multical reports, keeping report generation portable without adding a runtime
dependency.
"""

import json
import math
import re
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile


_INVALID_SHEET_CHARACTERS = re.compile(r"[\\/*?:\[\]]")


def _column_name(index):
  result = ""
  while index:
    index, remainder = divmod(index - 1, 26)
    result = chr(65 + remainder) + result
  return result


def _xml_text(value):
  return escape(str(value), {'"': "&quot;", "'": "&apos;"})


def _cell_xml(reference, value):
  if value is None:
    return '<c r="{}"/>'.format(reference)
  if isinstance(value, bool):
    return '<c r="{}" t="b"><v>{}</v></c>'.format(
      reference, 1 if value else 0
    )
  if isinstance(value, (int, float)) and not isinstance(value, bool):
    number = float(value)
    if math.isfinite(number):
      rendered = str(value) if isinstance(value, int) else repr(number)
      return '<c r="{}"><v>{}</v></c>'.format(reference, rendered)
  if isinstance(value, (dict, list, tuple)):
    value = json.dumps(value, ensure_ascii=False, sort_keys=True)
  return (
    '<c r="{}" t="inlineStr"><is><t xml:space="preserve">{}</t></is></c>'
  ).format(reference, _xml_text(value))


def _worksheet_xml(rows):
  rendered_rows = []
  for row_index, row in enumerate(rows, start=1):
    cells = [
      _cell_xml("{}{}".format(_column_name(column_index), row_index), value)
      for column_index, value in enumerate(row, start=1)
    ]
    rendered_rows.append(
      '<row r="{}">{}</row>'.format(row_index, "".join(cells))
    )
  return (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<worksheet xmlns="http://schemas.openxmlformats.org/'
    'spreadsheetml/2006/main"><sheetData>{}</sheetData></worksheet>'
  ).format("".join(rendered_rows))


def _sheet_names(names):
  used = set()
  result = []
  for index, name in enumerate(names, start=1):
    base = _INVALID_SHEET_CHARACTERS.sub("_", str(name)).strip("'")[:31]
    base = base or "Sheet{}".format(index)
    candidate = base
    suffix = 2
    while candidate.casefold() in used:
      tail = "_{}".format(suffix)
      candidate = base[:31 - len(tail)] + tail
      suffix += 1
    used.add(candidate.casefold())
    result.append(candidate)
  return result


def write_workbook(filename, sheets):
  """Write ``[(sheet_name, rows), ...]`` to a minimal valid XLSX file."""
  destination = Path(filename)
  destination.parent.mkdir(parents=True, exist_ok=True)
  items = list(sheets)
  if not items:
    items = [("Report", [["No data"]])]
  names = _sheet_names(name for name, _ in items)

  content_types = [
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
    '<Default Extension="xml" ContentType="application/xml"/>',
    '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
    '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>',
  ]
  content_types.extend(
    '<Override PartName="/xl/worksheets/sheet{}.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'.format(index)
    for index in range(1, len(items) + 1)
  )
  content_types.append('</Types>')

  workbook_sheets = "".join(
    '<sheet name="{}" sheetId="{}" r:id="rId{}"/>'.format(
      _xml_text(name), index, index
    )
    for index, name in enumerate(names, start=1)
  )
  workbook = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
    '<sheets>{}</sheets></workbook>'
  ).format(workbook_sheets)

  workbook_relationships = [
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">',
  ]
  workbook_relationships.extend(
    '<Relationship Id="rId{}" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
    'Target="worksheets/sheet{}.xml"/>'.format(index, index)
    for index in range(1, len(items) + 1)
  )
  workbook_relationships.append(
    '<Relationship Id="rId{}" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
    'Target="styles.xml"/>'.format(len(items) + 1)
  )
  workbook_relationships.append('</Relationships>')

  root_relationships = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
    'Target="xl/workbook.xml"/></Relationships>'
  )
  styles = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
    '<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>'
    '<fills count="1"><fill><patternFill patternType="none"/></fill></fills>'
    '<borders count="1"><border/></borders>'
    '<cellStyleXfs count="1"><xf/></cellStyleXfs>'
    '<cellXfs count="1"><xf xfId="0"/></cellXfs>'
    '</styleSheet>'
  )

  with ZipFile(destination, "w", compression=ZIP_DEFLATED) as archive:
    archive.writestr("[Content_Types].xml", "".join(content_types))
    archive.writestr("_rels/.rels", root_relationships)
    archive.writestr("xl/workbook.xml", workbook)
    archive.writestr(
      "xl/_rels/workbook.xml.rels", "".join(workbook_relationships)
    )
    archive.writestr("xl/styles.xml", styles)
    for index, (_, rows) in enumerate(items, start=1):
      archive.writestr(
        "xl/worksheets/sheet{}.xml".format(index),
        _worksheet_xml(rows)
      )
  return destination


def _mapping_rows(value, prefix=""):
  rows = []
  if isinstance(value, dict):
    for key, item in value.items():
      path = "{}.{}".format(prefix, key) if prefix else str(key)
      if isinstance(item, dict):
        rows.extend(_mapping_rows(item, path))
      else:
        rows.append([path, item])
  else:
    rows.append([prefix or "value", value])
  return rows


def write_report_workbook(filename, report, title="Multical report"):
  """Write a nested report mapping as readable summary and table sheets."""
  sheets = [("Summary", [[title], ["Field", "Value"]] + _mapping_rows(report))]
  if isinstance(report, dict):
    for key, value in report.items():
      if not isinstance(value, list) or not value:
        continue
      mapping_rows = [item for item in value if isinstance(item, dict)]
      if len(mapping_rows) != len(value):
        continue
      columns = []
      for item in mapping_rows:
        for column in item:
          if column not in columns:
            columns.append(column)
      rows = [columns]
      rows.extend([[item.get(column) for column in columns] for item in mapping_rows])
      sheets.append((key, rows))
  return write_workbook(filename, sheets)
