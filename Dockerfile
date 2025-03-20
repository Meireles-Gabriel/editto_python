FROM python:3.9-slim

WORKDIR /app

# Copiar arquivos de dependências primeiro para aproveitar o cache
COPY staff/src/staff/requirements.txt .

# Instalar dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o restante do código
COPY staff/src/staff/ .

# Configurar variáveis de ambiente
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Expor porta utilizada pelo Cloud Run
EXPOSE 8080

# Comando para iniciar o aplicativo
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app