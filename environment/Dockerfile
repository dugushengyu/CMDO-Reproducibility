FROM python:3.11.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MPLBACKEND=Agg

RUN apt-get update \
    && apt-get install -y --no-install-recommends git libgl1 libglib2.0-0 p7zip-full \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /cmdo
COPY environment/requirements-replay.txt /cmdo/environment/requirements-replay.txt
RUN python -m pip install --no-cache-dir --upgrade pip==24.3.1 \
    && python -m pip install --no-cache-dir -r environment/requirements-replay.txt
COPY . /cmdo

ENTRYPOINT ["python", "RUN_REPRODUCTION.py"]
CMD ["audit"]
