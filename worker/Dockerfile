# Exact upstream image digest; no packages or downloaded experiment code.
FROM python:3.13.5-slim@sha256:4c2cf9917bd1cbacc5e9b07320025bdb7cdf2df7b0ceaccb55e9dd7e30987419
WORKDIR /app
COPY counterlab /app/counterlab
COPY cases /app/cases
COPY worker.py sources.json /app/
USER 65532:65532
ENTRYPOINT ["python", "-I", "-B", "-u", "/app/worker.py"]
