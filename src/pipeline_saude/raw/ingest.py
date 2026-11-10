"""Carrega um snapshot completo dos três CSVs em uma única transação."""

import csv
import hashlib
import io
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import duckdb


TABLES = ("patients", "encounters", "medications")
METADATA = (
    "_source_file",
    "_source_sha256",
    "_source_row_number",
    "_ingested_at",
    "_batch_id",
)


def quote_identifier(value: str) -> str:
    """Protege nomes de colunas sem modificar o cabeçalho original."""
    return '"' + value.replace('"', '""') + '"'


def read_source(path: Path) -> tuple[list[str], list[list[str]], str]:
    """Lê bytes uma vez: o hash identifica exatamente o conteúdo importado."""
    content = path.read_bytes()
    reader = csv.reader(io.StringIO(content.decode("utf-8"), newline=""), strict=True)
    columns = next(reader, None)
    if not columns or any(not column or "\x00" in column for column in columns):
        raise ValueError(f"{path.name}: cabeçalho ausente ou inválido")
    normalized = [column.casefold() for column in columns]
    if len(set(normalized)) != len(columns) or set(normalized) & set(METADATA):
        raise ValueError(f"{path.name}: colunas repetidas ou conflito com metadados")
    rows = []
    for record_number, row in enumerate(reader, start=1):
        if len(row) != len(columns) or any("\x00" in value for value in row):
            raise ValueError(f"{path.name}: registro {record_number} inválido")
        rows.append(row)
    return columns, rows, hashlib.sha256(content).hexdigest()


def ingest_raw(data_dir: Path, database: Path) -> dict:
    """Substitui as três tabelas raw atomicamente, sem deduplicar a origem."""
    data_dir = Path(data_dir).resolve()
    database = Path(database).resolve()
    # Evita gravar bancos na pasta de origem ou sobrescrever algum CSV.
    if database == data_dir or data_dir in database.parents:
        raise ValueError("O banco deve ficar fora da pasta dos CSVs")
    sources = {table: read_source(data_dir / f"{table}.csv") for table in TABLES}
    batch_id = str(uuid4())
    ingested_at = datetime.now(timezone.utc)
    database.parent.mkdir(parents=True, exist_ok=True)
    results = []
    with duckdb.connect(str(database)) as connection:
        connection.execute("BEGIN TRANSACTION")
        try:
            connection.execute("CREATE SCHEMA IF NOT EXISTS raw")
            for table, (columns, rows, digest) in sources.items():
                definitions = [f"{quote_identifier(c)} VARCHAR" for c in columns]
                definitions += [
                    '"_source_file" VARCHAR NOT NULL',
                    '"_source_sha256" VARCHAR NOT NULL',
                    '"_source_row_number" BIGINT NOT NULL',
                    '"_ingested_at" TIMESTAMPTZ NOT NULL',
                    '"_batch_id" VARCHAR NOT NULL',
                ]
                target = f"raw.{quote_identifier(table)}"
                connection.execute(f"CREATE OR REPLACE TABLE {target} ({', '.join(definitions)})")
                if rows:
                    placeholders = ", ".join("?" for _ in range(len(columns) + len(METADATA)))
                    # Inserções em lotes evitam uma execução SQL por registro.
                    for offset in range(0, len(rows), 500):
                        batch = rows[offset:offset + 500]
                        values = [
                            row + [f"{table}.csv", digest, number, ingested_at, batch_id]
                            for number, row in enumerate(batch, start=offset + 1)
                        ]
                        connection.execute(
                            f"INSERT INTO {target} VALUES "
                            + ", ".join(f"({placeholders})" for _ in batch),
                            [value for row in values for value in row],
                        )
                count = connection.execute(f"SELECT count(*) FROM {target}").fetchone()[0]
                if count != len(rows):
                    raise RuntimeError(f"{table}: contagem divergente após ingestão")
                results.append({"table": f"raw.{table}", "expected": len(rows),
                                "obtained": count, "source_sha256": digest})
            connection.execute("COMMIT")
        except Exception:
            connection.execute("ROLLBACK")
            raise
    return {"database": str(database), "batch_id": batch_id,
            "ingested_at": ingested_at.isoformat(), "tables": results}
