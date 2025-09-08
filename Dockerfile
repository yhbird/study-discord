FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN apt-get update && apt-get install -y tzdata
ENV TZ=Asia/Seoul
ENV MPLCONFIGDIR=/tmp/matplotlib
ENV PYTHON_RUN_ENV=prd
RUN mkdir -p /tmp/matplotlib
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]