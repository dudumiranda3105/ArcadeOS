import json
from datetime import datetime

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

from .config import Settings
from .models import Telemetry

PERIODS = {"1h": "10s", "6h": "1m", "24h": "5m", "7d": "30m"}


class InfluxRepository:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = InfluxDBClient(
            url=settings.influx_url, token=settings.influx_token,
            org=settings.influx_org, timeout=5000, retries=0,
        )
        self.writer = self.client.write_api(write_options=SYNCHRONOUS)
        self.query = self.client.query_api()

    def write(self, telemetry: Telemetry, received_at: datetime) -> None:
        point = (
            Point("arcade_telemetry")
            .tag("device_id", telemetry.device_id).tag("source", telemetry.source)
            .field("temperature", float(telemetry.temperature))
            .field("humidity", float(telemetry.humidity))
            .time(received_at, WritePrecision.NS)
        )
        self.writer.write(bucket=self.settings.influx_bucket, record=point)

    def _base(self, period: str) -> str:
        # Device and bucket are configuration, never interpolated without escaping.
        return f'''from(bucket: {json.dumps(self.settings.influx_bucket)})
          |> range(start: -{period})
          |> filter(fn: (r) => r._measurement == "arcade_telemetry"
            and r.device_id == {json.dumps(self.settings.device_id)}
            and (r._field == "temperature" or r._field == "humidity"))'''

    def _rows(self, query: str) -> list[dict]:
        result = []
        for table in self.query.query(query):
            for record in table.records:
                values = record.values
                if values.get("temperature") is None or values.get("humidity") is None:
                    continue
                result.append({
                    "time": values["_time"].isoformat(),
                    "temperature": round(float(values["temperature"]), 3),
                    "humidity": round(float(values["humidity"]), 3),
                    "source": values.get("source", "unknown"),
                })
        return sorted(result, key=lambda row: row["time"])

    def latest(self) -> dict | None:
        # One sample per field/source is sufficient to locate the last complete reading.
        query = self._base("30d") + '''
          |> last()
          |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
          |> group()
          |> sort(columns: ["_time"], desc: true)
          |> limit(n: 1)'''
        rows = self._rows(query)
        return rows[0] if rows else None

    def history(self, period: str) -> dict:
        if period not in PERIODS:
            raise ValueError("Período inválido")
        resolution = PERIODS[period]
        rows = self._rows(self._base(period) + f'''
          |> aggregateWindow(every: {resolution}, fn: mean, createEmpty: false, timeSrc: "_start")
          |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")''')
        # Statistics use raw points; downsampling must not conceal temperature peaks.
        stat_query = "data = " + self._base(period) + '''
          |> filter(fn: (r) => r._field == "temperature") |> group()
          union(tables: [
            data |> min() |> set(key: "stat", value: "minimum"),
            data |> max() |> set(key: "stat", value: "maximum"),
            data |> mean() |> set(key: "stat", value: "average"),
            data |> count() |> toFloat() |> set(key: "stat", value: "count")
          ])'''
        statistics = {"minimum": None, "maximum": None, "average": None, "count": 0}
        for table in self.query.query(stat_query):
            for record in table.records:
                statistics[record.values["stat"]] = record.get_value()
        statistics["count"] = int(statistics["count"])
        return {"readings": rows, "period": period, "resolution": resolution, "statistics": statistics}

    def close(self) -> None:
        self.writer.close()
        self.client.close()
