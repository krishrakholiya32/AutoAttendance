import redis
from prometheus_client import Counter, Histogram
from prometheus_client.core import GaugeMetricFamily
from prometheus_client.registry import Collector

from app.core.config import settings

liveness_reject_total = Counter(
    "liveness_reject_total",
    "Number of face-liveness checks that rejected a spoofed (photo/screen) face",
    ["context"],  # "enroll" or "mark"
)

match_confidence = Histogram(
    "face_match_confidence",
    "Cosine similarity of accepted face matches during attendance-marking",
    buckets=(0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0),
)


class QueueDepthCollector(Collector):
    """Reports the arq attendance-marking queue depth on every /metrics scrape.
    arq schedules jobs in a Redis sorted set (ZADD), not a list, so depth is
    ZCARD rather than LLEN. Polled on-demand rather than via a background loop
    since a Prometheus scrape is already the only consumer of this value."""

    def __init__(self) -> None:
        self._redis = redis.Redis.from_url(settings.redis_url)

    def collect(self):
        try:
            depth = self._redis.zcard("arq:queue")
        except redis.RedisError:
            depth = -1
        gauge = GaugeMetricFamily(
            "attendance_queue_depth", "Pending/scheduled jobs in the arq attendance-marking queue"
        )
        gauge.add_metric([], depth)
        yield gauge
