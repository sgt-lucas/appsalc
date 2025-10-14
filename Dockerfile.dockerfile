# Usar uma imagem oficial do Python, versão 3.11, otimizada (slim).
FROM python:3.11-slim

# Define o diretório de trabalho dentro do container.
WORKDIR /app

# Copia o arquivo de dependências para o container.
COPY requirements.txt .

# Instala as dependências. A flag --no-cache-dir economiza espaço.
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o resto do código do seu projeto para o container.
COPY . .

# Expõe a porta 8000, que é a porta que a aplicação usará para comunicação.
EXPOSE 8000

# O comando final que será executado quando o container iniciar.
# Ele inicia o servidor Uvicorn, tornando a API acessível.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]