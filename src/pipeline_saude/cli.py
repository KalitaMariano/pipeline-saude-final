"""Interface de linha de comando do projeto."""

import argparse
import csv
import json
import sys
from pathlib import Path

import duckdb

from pipeline_saude.raw.ingest import ingest_raw


def main() -> int:
    parser = argparse.ArgumentParser(description="Pipeline de saúde")
    commands = parser.add_subparsers(dest="command", required=True)
    raw = commands.add_parser("raw", help="Ingerir os três CSVs no schema raw")
    raw.add_argument("--data-dir", type=Path, default=Path("data"),
                     help="Pasta dos CSVs (padrão: data)")
    raw.add_argument("--database", type=Path, default=Path("artifacts/saude.duckdb"),
                     help="Banco de destino (padrão: artifacts/saude.duckdb)")
    args = parser.parse_args()
    try:
        result = ingest_raw(args.data_dir, args.database)
    except (OSError, ValueError, csv.Error, duckdb.Error, RuntimeError) as error:
        print(f"Falha na ingestão raw: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
