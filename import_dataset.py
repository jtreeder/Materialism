#!/usr/bin/env python3
"""CLI tool for importing HSP datasets into the Materialism database.

Usage:
    python import_dataset.py --file path/to/data.csv --id my_dataset
    python import_dataset.py --file data.xlsx --analyze-only
    python import_dataset.py --id my_dataset --remove
    python import_dataset.py --list
"""

import argparse
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from lib.import_utils import (
    analyze_dataset,
    detect_file_type,
    load_manifest,
    normalize_and_write,
    remove_dataset,
)


def print_analysis(report):
    """Pretty-print an analysis report."""
    print()
    print(f"  File type:    {report['file_type']}")
    print(f"  Rows:         {report['row_count']}")
    print(f"  Detected as:  {report['detected_type']}")
    print()

    print("  Column mapping:")
    for orig, canon in sorted(report["column_mapping"].items()):
        print(f"    {orig:30s} -> {canon}")
    if report["unmapped_columns"]:
        print(f"  Unmapped:     {', '.join(report['unmapped_columns'])}")
    print()

    print(f"  HSP coverage:    {report['hsp_coverage']}%")
    print(f"  CAS coverage:    {report['cas_coverage']}%")
    print(f"  SMILES coverage: {report['smiles_coverage']}%")

    if report["quality_issues"]:
        print()
        print("  Quality issues:")
        for issue in report["quality_issues"]:
            icon = "!!" if issue["severity"] == "error" else " >"
            print(f"    {icon} {issue['message']}")

    if report["sample_rows"]:
        print()
        print("  Sample rows (first 5):")
        for i, sample in enumerate(report["sample_rows"][:5]):
            name = sample.get("name", "?")
            dd = sample.get("delta_d", "?")
            dp = sample.get("delta_p", "?")
            dh = sample.get("delta_h", "?")
            cas = sample.get("cas_number", "")
            print(f"    {i+1}. {name:40s}  dD={dd:>6s} dP={dp:>6s} dH={dh:>6s}  CAS={cas}")
    print()


def cmd_analyze(args):
    filepath = os.path.abspath(args.file)
    if not os.path.exists(filepath):
        print(f"Error: file not found: {filepath}")
        return 1

    print(f"Analyzing: {filepath}")
    report = analyze_dataset(filepath)
    print_analysis(report)
    return 0


def cmd_import(args):
    filepath = os.path.abspath(args.file)
    if not os.path.exists(filepath):
        print(f"Error: file not found: {filepath}")
        return 1

    dataset_id = args.id
    if not dataset_id:
        # Auto-generate from filename
        base = os.path.splitext(os.path.basename(filepath))[0]
        dataset_id = base.lower().replace(" ", "_").replace("-", "_")

    print(f"Analyzing: {filepath}")
    report = analyze_dataset(filepath)
    print_analysis(report)

    if report["quality_issues"]:
        errors = [i for i in report["quality_issues"] if i["severity"] == "error"]
        if errors:
            print("ERROR: Cannot import — critical issues found:")
            for e in errors:
                print(f"  !! {e['message']}")
            return 1

    # Perform import
    print(f"Importing as dataset '{dataset_id}'...")
    metadata = {
        "name": args.name or dataset_id,
        "source_url": args.source_url or "",
        "description": args.description or "",
    }

    entry = normalize_and_write(
        filepath=filepath,
        dataset_id=dataset_id,
        column_mapping=report["column_mapping"] if not args.auto_map else None,
        metadata=metadata,
        confidence_tier=args.confidence or 0.30,
    )

    print(f"  Imported: {entry['chemical_count']} chemicals, {entry['polymer_count']} polymers")
    print(f"  Dataset directory: data/datasets/{dataset_id}/")
    print(f"  Manifest updated.")
    return 0


def cmd_remove(args):
    dataset_id = args.id
    if remove_dataset(dataset_id):
        print(f"Removed dataset: {dataset_id}")
        return 0
    else:
        print(f"Dataset not found: {dataset_id}")
        return 1


def cmd_list(args):
    manifest = load_manifest()
    datasets = manifest.get("datasets", {})
    if not datasets:
        print("No datasets imported yet.")
        return 0

    print(f"{'ID':30s} {'Chems':>6s} {'Polys':>6s} {'Active':>7s} {'Name'}")
    print("-" * 90)
    for ds_id, ds in sorted(datasets.items()):
        active = "yes" if ds.get("active", True) else "no"
        print(f"{ds_id:30s} {ds.get('chemical_count', 0):>6d} "
              f"{ds.get('polymer_count', 0):>6d} {active:>7s} {ds.get('name', '')}")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Import HSP datasets into Materialism")
    sub = parser.add_subparsers(dest="command")

    # analyze
    p_analyze = sub.add_parser("analyze", help="Analyze a file without importing")
    p_analyze.add_argument("--file", required=True, help="Path to data file")

    # import
    p_import = sub.add_parser("import", help="Import a dataset")
    p_import.add_argument("--file", required=True, help="Path to data file")
    p_import.add_argument("--id", help="Dataset ID (auto-generated from filename if omitted)")
    p_import.add_argument("--name", help="Display name for the dataset")
    p_import.add_argument("--source-url", help="Source URL")
    p_import.add_argument("--description", help="Dataset description")
    p_import.add_argument("--confidence", type=float, help="Base confidence tier (0.0-1.0)")
    p_import.add_argument("--auto-map", action="store_true",
                          help="Re-run column auto-mapping (ignore cached mapping)")

    # remove
    p_remove = sub.add_parser("remove", help="Remove a dataset")
    p_remove.add_argument("--id", required=True, help="Dataset ID to remove")

    # list
    sub.add_parser("list", help="List all datasets")

    args = parser.parse_args()

    if args.command == "analyze":
        return cmd_analyze(args)
    elif args.command == "import":
        return cmd_import(args)
    elif args.command == "remove":
        return cmd_remove(args)
    elif args.command == "list":
        return cmd_list(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
