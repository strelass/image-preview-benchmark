FROM python:3.13-slim

WORKDIR /app

RUN apt-get update  \
    && apt-get install -y gcc libvips-dev poppler-utils libmagickwand-dev ghostscript --no-install-recommends \
    && sed -i 's/rights="none" pattern="PDF"/rights="read|write" pattern="PDF"/' /etc/ImageMagick-6/policy.xml \
    && rm -rf /var/lib/apt/lists/*

COPY . .
RUN pip install --no-cache-dir -r requirements.txt

ENTRYPOINT ["python", "main.py"]
