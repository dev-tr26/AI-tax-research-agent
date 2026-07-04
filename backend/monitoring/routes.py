# metrics api router /metrics,  /metrics/recent , /metrics/health endpoints 

from fastapi import APIRouter
from monitoring.metrics import get_metrics

router = APIRouter(prefix="/metrics", tags =["metrics"])


# full metrics summary P50 / P95 latency breakdown ans SLA compliance 
@router.get("")
async def get_summary():
    return get_metrics().summary()



@router.get("/recent")
async def get_recent(n: int =20):
    # last n query metrics record 
    return {"records": get_metrics().recent(n)}


@router.get("/health")
async def metrics_health():
    summary = get_metrics().summary()
    sla = summary.get("sla_compliance", {})
    all_pass = all(sla.values()) if sla else True
    return {
        "status": "healthy" if all_pass else "degraded",
        "sla":  sla,
        "total_queries": summary.get("total_queries", 0),
    }