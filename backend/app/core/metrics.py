from prometheus_client import Counter

liveness_reject_total = Counter(
    "liveness_reject_total",
    "Number of face-liveness checks that rejected a spoofed (photo/screen) face",
    ["context"],  # "enroll" or "mark"
)
