FROM python:3.12-slim

WORKDIR /app

# libglib2.0-0 is required by opencv-python-headless's native module even
# without GUI support -- deliberately no libGL.so.1 here, the exact gotcha
# already hit once on the Oracle ARM VM when non-headless opencv-python got
# pulled in transitively (see requirements.txt note below).
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY face-worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip uninstall -y opencv-python \
    && pip install --no-cache-dir --force-reinstall opencv-python-headless==4.11.0.86

COPY face-worker/ .

EXPOSE 8001

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]
