FROM python:3.11-slim

# System deps + git + gh + git-lfs
RUN apt-get update && apt-get install -y --no-install-recommends \
    git git-lfs curl ca-certificates gnupg build-essential \
 && rm -rf /var/lib/apt/lists/*

# (Optional) Install GitHub CLI
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
      | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
 && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
 && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
      > /etc/apt/sources.list.d/github-cli.list \
 && apt-get update && apt-get install -y --no-install-recommends gh \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

# Python deps
RUN if [ -f requirements.txt ]; then \
      pip install --no-cache-dir -r requirements.txt; \
    else \
      pip install --no-cache-dir requests beautifulsoup4 readability-lxml html2text python-dateutil; \
    fi

# Initialize git + lfs, then run
RUN printf '%s\n' \
'#!/usr/bin/env bash' \
'set -euo pipefail' \
'git config --global --add safe.directory /app || true' \
'git config --global user.name  "${GIT_AUTHOR_NAME:-codespaces-bot}"  || true' \
'git config --global user.email "${GIT_AUTHOR_EMAIL:-codespaces@example.com}" || true' \
'git lfs install --system || true' \
'echo "Base branch: ${BASE_BRANCH:-main}"' \
'exec python publish.py' \
> /usr/local/bin/docker-entrypoint.sh \
 && chmod +x /usr/local/bin/docker-entrypoint.sh

# Non-root
RUN useradd -m appuser
USER appuser

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
