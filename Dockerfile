FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py config.py states.py services.py notes.py ./

RUN mkdir -p /app/data

CMD ["python", "bot.py"]
