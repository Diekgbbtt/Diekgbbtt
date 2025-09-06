# DISCLAIMER: DISCONTINUED temporarily, in favour of repo service at https://github.com/Diekgbbtt/readme-update-coding-stats - AUTOMATION TO BE IMPLEMENTED

FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt update_relevant_repos.py ./
RUN pip install --no-cache-dir -r requirements.txt
