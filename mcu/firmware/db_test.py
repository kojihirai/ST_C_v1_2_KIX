#!/usr/bin/env python3
"""
dbtester.py

Quickly fetches and prints the most recent N entries from an InfluxDB v2 bucket.

Usage:
    # Fetch the 5 most recent records (default)
    python dbtester.py

    # Or override the number of records via environment variable:
    INFLUX_LIMIT=10 python dbtester.py
"""

import os
import sys
from influxdb_client import InfluxDBClient

# ─── CONFIG FROM ENVIRONMENT ────────────────────────────────────────────────────
INFLUX_URL    = os.getenv("INFLUXDB_URL",    "http://10.147.18.184:8086")
INFLUX_TOKEN  = os.getenv("INFLUXDB_TOKEN",  "rluK849_LVDKPRXuOqXFyI3tlJFoU-k4EHI0jb_dVa8ewNavNnAE4WV2-U2hIvUJ4uBx7fa5YXNsbAaOJOJEXw==")
INFLUX_ORG    = os.getenv("INFLUXDB_ORG",    "sandwerx")
INFLUX_BUCKET = os.getenv("INFLUXDB_BUCKET", "vehicle_telem")
LIMIT         = int(os.getenv("INFLUX_LIMIT", "5"))

if not all([INFLUX_TOKEN, INFLUX_ORG, INFLUX_BUCKET]):
    print("ERROR: Please set INFLUXDB_TOKEN, INFLUXDB_ORG, and INFLUXDB_BUCKET", file=sys.stderr)
    sys.exit(1)

# ─── INIT CLIENT ────────────────────────────────────────────────────────────────
client = InfluxDBClient(
    url=INFLUX_URL,
    token=INFLUX_TOKEN,
    org=INFLUX_ORG,
    timeout=600_000,     # 10 minutes in ms
    enable_gzip=True
)
query_api = client.query_api()

# ─── FLUX QUERY FOR MOST RECENT ENTRIES ────────────────────────────────────────
flux = f'''
from(bucket: "{INFLUX_BUCKET}")
  |> range(start: 0)
  |> sort(columns: ["_time"], desc: true)
  |> limit(n: {LIMIT})
'''

# ─── RUN QUERY AND PRINT RESULTS ───────────────────────────────────────────────
print(f"Fetching the {LIMIT} most recent records from bucket '{INFLUX_BUCKET}'...\n")
tables = query_api.query(flux, org=INFLUX_ORG)

for table in tables:
    for record in table.records:
        time        = record.get_time()
        measurement = record.get_measurement()
        field       = record.get_field()
        value       = record.get_value()
        host        = record.values.get("host", "")
        topic       = record.values.get("topic", "")

        print(
            f"{time} | "
            f"{measurement}.{field} = {value} | "
            f"host={host} | topic={topic}"
        )

client.close()
