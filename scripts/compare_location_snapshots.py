"""Compare upazila labels in the app snapshot with a community JSON snapshot.

This deliberately performs literal, case-insensitive parent/name matching only.
It reports candidate discrepancies; it does not infer aliases or certify authority.
"""

import argparse
from collections import Counter
import json
import re
from pathlib import Path


def load_json(path):
    with Path(path).open(encoding="utf-8") as source:
        return json.load(source)


def key(parent, name):
    normalize = lambda value: re.sub(r"\s+", " ", value.strip()).casefold()
    return normalize(parent), normalize(name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app_snapshot", help="App-format document with records")
    parser.add_argument("community_snapshot", help="Nested community bd_locations.json")
    args = parser.parse_args()

    app_doc = load_json(args.app_snapshot)
    community_doc = load_json(args.community_snapshot)
    app_rows = [
        (key(record["parent_path"][-1], record["name_en"]), record)
        for record in app_doc["records"]
        if record["level"] == "UPAZILA"
    ]
    community_rows = []
    community_bbs_codes = []
    for division in community_doc["divisions"]:
        for district in division["districts"]:
            for unit in district["upazilas"]:
                if unit.get("type") != "thana":
                    community_rows.append((key(district["name"], unit["name"]), unit))
                    if unit.get("bbsCode"):
                        community_bbs_codes.append(unit["bbsCode"])

    app_keys = {row_key for row_key, _ in app_rows}
    community_keys = {row_key for row_key, _ in community_rows}
    common = app_keys & community_keys
    community_only = community_keys - app_keys
    app_only = app_keys - community_keys
    print(f"literal_parent_name_matches={len(common)}")
    print(f"community_only_literal_keys={len(community_only)}")
    print(f"app_only_literal_keys={len(app_only)}")
    print(f"community_duplicate_parent_name_keys={sum(n > 1 for n in Counter(k for k, _ in community_rows).values())}")
    print(f"app_duplicate_parent_name_keys={sum(n > 1 for n in Counter(k for k, _ in app_rows).values())}")
    print(f"community_duplicate_ids={sum(n > 1 for n in Counter(row['id'] for _, row in community_rows).values())}")
    print(f"community_duplicate_nonempty_bbs_codes={sum(n > 1 for n in Counter(community_bbs_codes).values())}")
    print("community_only:")
    for parent, name in sorted(community_only):
        print(f"  {name} — {parent}")
    print("app_only:")
    for parent, name in sorted(app_only):
        print(f"  {name} — {parent}")


if __name__ == "__main__":
    main()
