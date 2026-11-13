#!/usr/bin/env python3
"""Check explicitly selected OBS INI/JSON files before chezmoi add or Git commit.

This catches known credential fields, not every possible secret. Review the diff too.
No file contents or credential values are printed.
"""
import configparser
import json
from pathlib import Path
import re
import sys

SENSITIVE = re.compile(r"password|passwd|secret|salt|token|auth|stream.?key", re.I)
CREDENTIAL_URL = re.compile(r"://[^/\s]+@|[?&](?:key|token|password|auth)=", re.I)


def check(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if SENSITIVE.search(key) and item not in (None, "", False, 0, {}, []):
                raise ValueError("認証情報・Portal復元トークンを含む可能性のあるフィールド")
            check(item)
    elif isinstance(value, list):
        for item in value:
            check(item)
    elif isinstance(value, str) and CREDENTIAL_URL.search(value):
        raise ValueError("認証情報を含む可能性のあるURL")


def validate(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError("通常ファイル以外")
    if ("plugin_config" in path.parts or "plugin_manager" in path.parts
            or path.name.removesuffix(".tmpl") == "service.json"):
        raise ValueError("プラグイン設定はローカル専用")
    name = path.name.removesuffix(".tmpl")
    if name.endswith(".ini"):
        data = configparser.ConfigParser(interpolation=None, strict=False)
        data.read_string(path.read_text())
        check({section: dict(data[section]) for section in data.sections()})
    elif name.endswith(".json"):
        check(json.loads(path.read_text()))
    else:
        raise ValueError("対象はINI/JSONのみ")


def main(paths):
    if not paths:
        print("usage: python3 scripts/check-obs-config.py FILE...", file=sys.stderr)
        return 2
    failed = False
    for filename in paths:
        try:
            validate(Path(filename))
        except Exception:
            # No raw parse errors: they can contain the sensitive input.
            print(f"NG: {filename}（形式・機密フィールド・通常ファイルかを確認）", file=sys.stderr)
            failed = True
    if not failed:
        print(f"OK: {len(paths)} files（既知の機密フィールド検査。差分の目視確認も必要）")
    return int(failed)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
