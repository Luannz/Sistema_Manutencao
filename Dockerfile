# Usa uma imagem leve do Python
FROM python:3.11-slim

# Variáveis de ambiente para o Python não gerar arquivos desnecessários
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Define a pasta de trabalho dentro do container
WORKDIR /app

# Instala dependências do sistema necessárias para o PostgreSQL e compilação
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Instala as dependências do Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do código do projeto
COPY . .

# Comando para rodar o Gunicorn (servidor de produção)
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]