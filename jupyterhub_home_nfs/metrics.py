from prometheus_client import Gauge

NAMESPACE = "dirsize"

TOTAL_SIZE = Gauge(
    "total_size_bytes",
    "Total Size of the Directory (in bytes)",
    namespace=NAMESPACE,
    labelnames=("directory",),
)

HARD_LIMIT = Gauge(
    "hard_limit_bytes",
    "Hard Limit of the Directory (in bytes)",
    namespace=NAMESPACE,
    labelnames=("directory",),
)
