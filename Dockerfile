FROM python:3.12.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_LINK_MODE=copy
RUN pip install --no-cache-dir uv==0.9.28
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src ./src
RUN uv sync --locked --no-dev --no-editable
COPY app.py ./
COPY examples/live ./examples/live
COPY evidence/lean-verification.json ./evidence/lean-verification.json
COPY evidence/migration-lean.json ./evidence/migration-lean.json
COPY lean/Ledger.lean lean/lean-toolchain lean/lakefile.toml ./lean/
COPY lean/Migration.lean ./lean/Migration.lean
RUN useradd --uid 10001 --create-home owed && mkdir -p /var/data/owed
# The Python entrypoint prepares only the mounted data root, then drops to uid 10001.
ENV WORKBENCH_CONTAINER=true WORKBENCH_MODE=hosted WORKBENCH_LIVE_ENABLED=false WORKBENCH_DATA_DIR=/var/data/owed
EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s CMD /app/.venv/bin/python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.getenv('PORT','8501')+'/_stcore/health',timeout=3)"
CMD ["/app/.venv/bin/python", "-m", "anomalon_workbench.serve"]
