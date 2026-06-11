import os

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg://postcard:postcard@localhost:5434/postcard",
)

# A claim on a staged lead older than this is reclaimable (stale-claim recovery, TRD §3).
CLAIM_TTL_SECONDS = 60 * 60
