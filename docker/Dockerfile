# Guardrailed agentic MLOps - offline research API.
# Builds the repository into a container serving the FastAPI evidence API.
# The API is read-only with respect to the lifecycle; research endpoints write
# only under artifacts/research_ui/.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SMARTGRID_MLOPS_APP_ENV=production

WORKDIR /app

COPY pyproject.toml requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY product/ ./product/
COPY artifacts/research_tables/ ./artifacts/research_tables/
COPY artifacts/experimental_design/ ./artifacts/experimental_design/
COPY artifacts/model_registry/ ./artifacts/model_registry/
COPY artifacts/governance/ ./artifacts/governance/
COPY artifacts/mlops/ ./artifacts/mlops/
COPY artifacts/research_ui/ ./artifacts/research_ui/
COPY config/ ./config/
COPY data/manifests/ ./data/manifests/

EXPOSE 8000
# product.backend_api is a regular package inside the image (product/__init__.py present).
CMD ["python", "-m", "uvicorn", "product.backend_api.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
