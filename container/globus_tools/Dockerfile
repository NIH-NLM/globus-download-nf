FROM python:3.12-slim

# Nextflow needs ps inside the container
RUN apt-get update \
 && apt-get install -y --no-install-recommends procps \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY auth.py globus_list.py globus_download.py md5_verify.py globus_login.py /opt/globus_tools/
