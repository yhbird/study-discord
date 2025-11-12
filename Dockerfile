FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

ENV TZ=Asia/Seoul \
    MPLCONFIGDIR=/tmp/matplotlib \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHON_RUN_ENV=prd

RUN apt-get update \
    && apt-get install -y tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
RUN mkdir -p /tmp/matplotlib 

COPY . .

CMD ["python", "main.py"]