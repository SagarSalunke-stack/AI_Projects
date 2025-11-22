#!/usr/bin/env python3
"""
file_parser.py

A small, practical file parsing utility supporting:
- CSV / TSV
- JSON (single file)
- NDJSON (newline-delimited JSON)
- XML (simple conversion)
- INI (configparser)
- Plain text (lines)
- Fixed-width with a provided schema

Usage as module:
    from file_parser import FileParser
    parser = FileParser()
    for rec in parser.parse("data.csv"): ...
    
CLI:
    python file_parser.py path/to/file --format csv
"""

import csv
import json
import xml.etree.ElementTree as ET
from configparser import ConfigParser
from typing import Generator, Dict, List, Optional, Union, Iterable
import os
import sys
import argparse
import io

# ---------- helpers ----------
def _open_file(path: str, encoding: Optional[str] = None):
    """Open file with guessed encoding fallback to utf-8."""
    if encoding:
        return open(path, "r", encoding=encoding)
    # try utf-8, then latin-1
    try:
        return open(path, "r", encoding="utf-8")
    except UnicodeDecodeError:
        return open(path, "r", encoding="latin-1")

def _guess_format(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext in (".csv",):
        return "csv"
    if ext in (".tsv", ".tab"):
        return "tsv"
    if ext in (".json",):
        return "json"
    if ext in (".ndjson", ".jsonl"):
        return "ndjson"
    if ext in (".xml",):
        return "xml"
    if ext in (".ini", ".cfg"):
        return "ini"
    if ext in (".txt", ".log"):
        return "text"
    return "unknown"

# ---------- core parser ----------
class FileParser:
    def __init__(self, encoding: Optional[str] = None):
        """
        encoding: optional override (e.g., 'utf-8' or 'latin-1')
        """
        self.encoding = encoding

    def parse(self,
              path: Union[str, io.TextIOBase],
              fmt: Optional[str] = None,
              *,
              csv_delimiter: Optional[str] = None,
              fixed_schema: Optional[List[tuple]] = None,
              stream: bool = True) -> Union[List[Dict], Generator[Dict, None, None]]:
        """
        Parse a file and yield records as dicts.
        
        Parameters:
        - path: path to file or a file-like object.
        - fmt: one of 'csv', 'tsv', 'json', 'ndjson', 'xml', 'ini', 'text', 'fixed' or None (auto).
        - csv_delimiter: override delimiter (if provided).
        - fixed_schema: required for fixed-width parsing: list of (name, width) tuples.
        - stream: if True returns generator for memory efficiency; if False returns list.

        Returns:
        - generator or list of dicts
        """
        # determine format
        if fmt is None:
            fmt = _guess_format(path if isinstance(path, str) else getattr(path, "name", ""))
        fmt = fmt.lower()

        parser_map = {
            "csv": self._parse_csv,
            "tsv": self._parse_tsv,
            "json": self._parse_json,
            "ndjson": self._parse_ndjson,
            "jsonl": self._parse_ndjson,
            "xml": self._parse_xml,
            "ini": self._parse_ini,
            "text": self._parse_text,
            "log": self._parse_text,
            "fixed": self._parse_fixed_width,
            "unknown": self._parse_unknown,
        }

        if fmt not in parser_map:
            raise ValueError(f"Unsupported format: {fmt}")

        parser = parser_map[fmt]

        if isinstance(path, str):
            f = _open_file(path, encoding=self.encoding)
            close_after = True
        else:
            f = path
            close_after = False

        try:
            gen = parser(f,
                         csv_delimiter=csv_delimiter,
                         fixed_schema=fixed_schema)
            if stream:
                return gen
            else:
                return list(gen)
        finally:
            if close_after:
                f.close()

    # ---------- parsers ----------
    def _parse_csv(self, f: io.TextIOBase, *, csv_delimiter: Optional[str]=None, **_):
        delim = csv_delimiter if csv_delimiter is not None else ","
        reader = csv.DictReader(f, delimiter=delim)
        for row in reader:
            yield {k: v for k, v in row.items()}

    def _parse_tsv(self, f: io.TextIOBase, **_):
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            yield {k: v for k, v in row.items()}

    def _parse_json(self, f: io.TextIOBase, **_):
        # Load whole JSON (expecting list or dict)
        data = json.load(f)
        if isinstance(data, list):
            for item in data:
                yield item if isinstance(item, dict) else {"value": item}
        elif isinstance(data, dict):
            # yield the dict as single record
            yield data
        else:
            yield {"value": data}

    def _parse_ndjson(self, f: io.TextIOBase, **_):
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                yield obj if isinstance(obj, dict) else {"value": obj}
            except json.JSONDecodeError:
                # fallback: return raw line
                yield {"raw": line}

    def _parse_xml(self, f: io.TextIOBase, **_):
        # This is a simple XML->dict converter: yields direct child elements of root
        tree = ET.parse(f)
        root = tree.getroot()
        # if root has multiple children with same tag, yield each
        for child in root:
            rec = {}
            # include attributes
            rec.update(child.attrib)
            for sub in child:
                # if repeated tags, put into list
                if sub.tag in rec:
                    if isinstance(rec[sub.tag], list):
                        rec[sub.tag].append(sub.text)
                    else:
                        rec[sub.tag] = [rec[sub.tag], sub.text]
                else:
                    rec[sub.tag] = sub.text
            # if text content exists and no children
            if not rec and (child.text and child.text.strip()):
                rec = {"text": child.text.strip()}
            yield rec

    def _parse_ini(self, f: io.TextIOBase, **_):
        cfg = ConfigParser()
        cfg.read_file(f)
        for section in cfg.sections():
            # convert each section into a dict with section name
            record = {"__section__": section}
            for k, v in cfg.items(section):
                record[k] = v
            yield record

    def _parse_text(self, f: io.TextIOBase, **_):
        for i, line in enumerate(f, start=1):
            yield {"line_no": i, "text": line.rstrip("\n")}

    def _parse_fixed_width(self, f: io.TextIOBase, *, fixed_schema: Optional[List[tuple]] = None, **_):
        """
        fixed_schema: list of tuples (field_name, width)
        e.g., [('name', 20), ('age', 3), ('city', 15)]
        """
        if not fixed_schema:
            raise ValueError("fixed_schema is required for fixed-width parsing")
        widths = [w for (_, w) in fixed_schema]
        names = [n for (n, _) in fixed_schema]
        total_width = sum(widths)
        for line_no, line in enumerate(f, start=1):
            raw = line.rstrip("\n")
            # pad if shorter
            raw = raw.ljust(total_width)
            pos = 0
            rec = {}
            for name, width in zip(names, widths):
                chunk = raw[pos:pos+width]
                rec[name] = chunk.strip()
                pos += width
            rec["_line_no"] = line_no
            yield rec

    def _parse_unknown(self, f: io.TextIOBase, **_):
        # fallback: yield lines
        for i, line in enumerate(f, start=1):
            yield {"line_no": i, "text": line.rstrip("\n")}

# ---------- CLI ----------
def main(argv: Optional[Iterable[str]] = None):
    p = argparse.ArgumentParser(description="Simple file parser utility")
    p.add_argument("path", help="Path to input file")
    p.add_argument("--format", "-f", help="Format override (csv, tsv, json, ndjson, xml, ini, text, fixed)")
    p.add_argument("--encoding", "-e", help="File encoding (utf-8, latin-1, etc.)")
    p.add_argument("--no-stream", dest="stream", action="store_false", help="Return list instead of streaming (print all)")
    p.add_argument("--fixed-schema", help="For fixed format: comma-separated name:width pairs, e.g. name:20,age:3")
    p.add_argument("--delimiter", "-d", help="CSV/TSV delimiter override")
    args = p.parse_args(list(argv) if argv is not None else None)

    fp = FileParser(encoding=args.encoding)
    fixed_schema = None
    if args.fixed_schema:
        parts = args.fixed_schema.split(",")
        schema = []
        for part in parts:
            if ":" not in part:
                print("Invalid fixed-schema format, expected name:width", file=sys.stderr)
                return 2
            name, width = part.split(":", 1)
            schema.append((name.strip(), int(width.strip())))
        fixed_schema = schema

    gen_or_list = fp.parse(args.path,
                           fmt=args.format,
                           csv_delimiter=args.delimiter,
                           fixed_schema=fixed_schema,
                           stream=args.stream)
    if args.stream:
        for rec in gen_or_list:
            print(json.dumps(rec, ensure_ascii=False))
    else:
        # print pretty
        import pprint
        pprint.pprint(gen_or_list)

if __name__ == "__main__":
    main()
