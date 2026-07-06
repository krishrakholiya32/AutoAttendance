FROM python:3.12-slim

WORKDIR /app

# libglib2.0-0 is required by opencv-python-headless's native module even
# without GUI support. Kept minimal deliberately -- no libGL.so.1 here, which
# is exactly the gotcha this project already hit once on the Oracle ARM VM
# when the non-headless opencv-python got pulled in transitively.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip uninstall -y opencv-python \
    && pip install --no-cache-dir --force-reinstall opencv-python-headless==4.11.0.86

COPY backend/ .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
