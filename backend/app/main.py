import logging
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings
from .ingestion import Ingestor
from .models import reading_is_fresh, thermal_status, utcnow
from .storage import InfluxRepository

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def create_app(settings: Settings | None = None, repository=None, start_mqtt=True) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        repo = repository or InfluxRepository(settings)
        ingestion = Ingestor(settings, repo)
        app.state.repository = repo
        app.state.ingestion = ingestion
        if start_mqtt:
            ingestion.start()
        try:
            yield
        finally:
            if start_mqtt:
                ingestion.stop()
            if repository is None:
                repo.close()

    application = FastAPI(
        title="ArcadeOS API", version="0.1.0", lifespan=lifespan,
        description="Telemetria de gabinetes arcade. A API não gera dados fictícios.",
    )
    application.add_middleware(
        CORSMiddleware, allow_origins=settings.cors_origins,
        allow_credentials=False, allow_methods=["GET"], allow_headers=["Content-Type"],
    )

    @application.get("/api/health")
    def health():
        return {"service": "ArcadeOS", "status": "running", "version": "0.1.0"}

    @application.get("/api/status")
    def status():
        # Read from InfluxDB, not a browser cache or an in-memory fake database.
        snapshot = application.state.ingestion.snapshot()
        latest = None
        influx_connected = False
        try:
            latest = application.state.repository.latest()
            influx_connected = True
        except Exception:
            snapshot["last_error"] = "Não foi possível consultar o InfluxDB. Verifique o serviço, bucket e token."
        online = reading_is_fresh(latest, settings.stale_after_seconds)
        return {
            "device": settings.public_device(), "latest": latest, "online": online,
            "thermal_status": thermal_status(latest["temperature"], settings.warning_temperature, settings.critical_temperature) if latest else None,
            "influx_connected": influx_connected, "server_time": utcnow().isoformat(), **snapshot,
        }

    @application.get("/api/history")
    def history(period: Literal["1h", "6h", "24h", "7d"] = Query(default="1h")):
        try:
            return application.state.repository.history(period)
        except Exception:
            raise HTTPException(status_code=503, detail="Histórico indisponível. Verifique o InfluxDB e as credenciais.") from None

    return application


app = create_app()
