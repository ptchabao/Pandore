FROM python:3.11-slim

WORKDIR /app
ENV TERM=xterm-256color

COPY . /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg curl tzdata && \
    ln -fs /usr/share/zoneinfo/Europe/Paris /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

CMD ["python3", "-m", "src.app"]
