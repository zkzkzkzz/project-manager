FROM python:3.10-slim

WORKDIR /app

COPY pip_requirements.txt .

RUN pip install --no-cache-dir -r pip_requirements.txt

COPY backend/ /app/backend/

EXPOSE 8000

#this runs the fastapi app
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

