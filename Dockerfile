FROM python:3.13-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

RUN mkdir -p /app/runs

COPY requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

EXPOSE 8501

ENTRYPOINT ["streamlit", "run", "app/streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
