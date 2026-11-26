#!/usr/bin/env python3
"""Fetch and record the latest ANTAM 1 g buyback price."""

from __future__ import annotations

import csv
import io
import json
import sys
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parent
HISTORY_FILE = ROOT / "history.csv"
API_URL = "https://logam-mulia-api.iamutaki.workers.dev/api/prices/logammulia"
FALLBACK_CSV_URL = "https://gold.hafidznrg.my.id/data/csv/logammulia-antam.csv"
TIMEOUT_SECONDS = 20


def download(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "antam-buyback-tracker/1.0"})
    with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return response.read()


def as_number(value: object) -> int | None:
    try:
        return int(float(str(value).replace(",", "")))
    except (TypeError, ValueError):
        return None


def fetch_api() -> dict[str, object]:
    payload = json.loads(download(API_URL).decode("utf-8"))
    records = payload.get("data", []) if isinstance(payload, dict) else []
    if isinstance(records, dict):
        records = [records]
    if not isinstance(records, list):
        raise ValueError("Format respons API tidak dikenali")

    candidates = []
    for record in records:
        if not isinstance(record, dict):
            continue
        provider = str(record.get("source", "")).lower()
        brand = str(record.get("materialType", "")).lower()
        weight = as_number(record.get("weight"))
        buyback = as_number(record.get("buybackPrice"))
        if provider == "logammulia" and "antam" in brand and weight == 1 and buyback:
            candidates.append({
                "price_date": str(record.get("recordedDate") or ""),
                "source": "Logam Mulia (via API komunitas)",
                "buyback": buyback,
                "sell": as_number(record.get("sellPrice")),
            })
    if not candidates:
        raise ValueError("API belum mengembalikan harga buyback Antam 1 gram")
    return candidates[0]


def fetch_csv_fallback() -> dict[str, object]:
    text = download(FALLBACK_CSV_URL).decode("utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(text)))
    candidates = []
    for row in rows:
        brand = str(row.get("brand", "")).lower()
        weight = as_number(row.get("weight_g"))
        buyback = as_number(row.get("buyback_price"))
        if "antam" in brand and weight == 1 and buyback:
            candidates.append({
                "price_date": str(row.get("date") or ""),
                "source": "Momen Emas (arsip CSV)",
                "buyback": buyback,
                "sell": as_number(row.get("sell_price")),
            })
    if not candidates:
        raise ValueError("CSV cadangan belum punya data buyback Antam 1 gram")
    return max(candidates, key=lambda row: str(row["price_date"]))


def get_price() -> dict[str, object]:
    errors = []
    for fetcher in (fetch_api, fetch_csv_fallback):
        try:
            return fetcher()
        except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"{fetcher.__name__}: {exc}")
    raise RuntimeError("Semua sumber gagal. " + " | ".join(errors))


def record(price: dict[str, object]) -> None:
    now = datetime.now(ZoneInfo("Asia/Jakarta"))
    price_date = str(price.get("price_date") or "")
    freshness = "tanggal_sesuai" if price_date == now.date().isoformat() else "perlu_dicek"
    row = {
        "fetched_at_wib": now.strftime("%Y-%m-%d %H:%M:%S"),
        "price_date": price_date,
        "freshness": freshness,
        "source": price["source"],
        "buyback_rp_per_gram": price["buyback"],
        "sell_rp_per_gram": price.get("sell") or "",
    }
    write_header = not HISTORY_FILE.exists() or HISTORY_FILE.stat().st_size == 0
    with HISTORY_FILE.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=row.keys())
        if write_header:
            writer.writeheader()
        writer.writerow(row)
    print(f"Buyback Antam 1 g: Rp{int(price['buyback']):,}".replace(",", "."))
    print(f"Tanggal data: {price_date or 'tidak dicantumkan'}")
    if freshness != "tanggal_sesuai":
        print("PERHATIAN: tanggal data bukan hari ini atau tidak tersedia; cek harga resmi sebelum transaksi.")
    print(f"Sumber: {price['source']}")


if __name__ == "__main__":
    try:
        record(get_price())
    except Exception as error:
        print(f"Gagal mengambil harga: {error}", file=sys.stderr)
        raise SystemExit(1)
