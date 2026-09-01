FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# build-essential + libminiupnpc-dev: miniupnpc has a C extension that needs
# a build toolchain and the miniupnpc headers to compile against.
# git: lib-arcade is installed as a git dependency (see requirements.txt),
# and pip needs the git CLI to clone it during the build.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libminiupnpc-dev git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# requirements.txt pins lib-arcade to @main, not a commit -- its literal
# content never changes, so without a cache-buster here Docker would
# reuse the very first pip install forever.
ARG CACHEBUST=1
RUN pip install --no-cache-dir -r requirements.txt
COPY adapter.py rcon.py .

CMD ["python3", "adapter.py"]
