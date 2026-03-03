# ---- builder stage ----
FROM python:3.11-slim AS builder

WORKDIR /app
COPY pyproject.toml ./
COPY agent_sdk/ agent_sdk/

RUN pip install --no-cache-dir .[server]

# ---- runtime stage ----
FROM python:3.11-slim AS runtime

WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY agent_sdk/ agent_sdk/

EXPOSE 8000
CMD ["uvicorn", "agent_sdk.composability.server:app", "--host", "0.0.0.0", "--port", "8000"]
