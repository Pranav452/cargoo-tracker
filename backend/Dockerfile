FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

# --- THIS SECTION IS MANDATORY ---
RUN apt-get update && apt-get install -y xvfb
# ---------------------------------

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium

COPY . .

EXPOSE 8000

# Add a startup script to start Xvfb as a background service
RUN echo '#!/bin/bash\nXvfb :99 -screen 0 1920x1080x24 &\nexport DISPLAY=:99\nexec "$@"' > /entrypoint.sh && \
    chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

