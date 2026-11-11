"""Interface de linha de comando do projeto."""

import argparse
import csv
import json
import sys
from pathlib import Path

import duckdb

from pipeline_saude.config import DATABASE_PATH
from pipeline_saude.raw.ingest import ingest_raw
from pipeline_saude.refined.transform import run_refined
from pipeline_saude.marts.transform import run_marts


def main() -> int:
    parser = argparse.ArgumentParser(description="Pipeline de saúde")
    commands = parser.add_subparsers(dest="command", required=True)
    raw = commands.add_parser("raw", help="Ingerir os três CSVs no schema raw")
    raw.add_argument("--data-dir", type=Path, default=Path("data"),
                     help="Pasta dos CSVs (padrão: data)")
    raw.add_argument("--database", type=Path, default=DATABASE_PATH,
                     help="Banco de destino (padrão: artifacts/saude.duckdb)")
    refined = commands.add_parser("refined", help="Transformar RAW em REFINED")
    refined.add_argument("--database", type=Path, default=DATABASE_PATH)
    marts = commands.add_parser("marts", help="Materializar indicadores analíticos")
    marts.add_argument("--database", type=Path, default=DATABASE_PATH)
    args = parser.parse_args()
    try:
        if args.command == "raw":
            result = ingest_raw(args.data_dir, args.database)
        elif args.command == "refined":
            result = run_refined(args.database)
        else:
            result = run_marts(args.database)
    except (OSError, ValueError, csv.Error, duckdb.Error, RuntimeError) as error:
        print(f"Falha na etapa {args.command}: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
