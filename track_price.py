#!/usr/bin/env python3
"""Fetch and record the latest ANTAM 1 g buyback price."""

from __future__ import annotations

import csv
import io
import sys
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parent
HISTORY_FILE = ROOT / "history.csv"
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
                "source_updated_at": str(row.get("source_updated_at") or ""),
            })
    if not candidates:
        raise ValueError("CSV cadangan belum punya data buyback Antam 1 gram")
    return max(candidates, key=lambda row: str(row["price_date"]))


def get_price() -> dict[str, object]:
    try:
        return fetch_csv_fallback()
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        raise RuntimeError(f"Sumber arsip harga tidak bisa diakses: {exc}") from exc


def record(price: dict[str, object]) -> None:
    now = datetime.now(ZoneInfo("Asia/Jakarta"))
    price_date = str(price.get("price_date") or "")
    freshness = "tanggal_sesuai" if price_date == now.date().isoformat() else "perlu_dicek"
    row = {
        "fetched_at_wib": now.strftime("%Y-%m-%d %H:%M:%S"),
        "price_date": price_date,
        "freshness": freshness,
        "source": price["source"],
        "source_updated_at_wib": price.get("source_updated_at") or "",
        "buyback_rp_per_gram": price["buyback"],
        "sell_rp_per_gram": price.get("sell") or "",
    }
    fieldnames = list(row)
    records = []
    if HISTORY_FILE.exists() and HISTORY_FILE.stat().st_size:
        with HISTORY_FILE.open(newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            records = list(reader)
            fieldnames = list(reader.fieldnames or [])
        for field in row:
            if field not in fieldnames:
                fieldnames.append(field)

    # Keep one point per date/price and refresh its check time on scheduled runs.
    if records and all(records[-1].get(key, "") == str(row[key]) for key in ("price_date", "source", "buyback_rp_per_gram", "sell_rp_per_gram")):
        records[-1].update(row)
    else:
        records.append(row)

    with HISTORY_FILE.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
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
