#!/bin/bash

# Passo 1: Garante que todas as dependências do requirements.txt estão instaladas.
# Esta linha força a instalação antes de tentar qualquer outra coisa.
pip install -r requirements.txt

# Passo 2: Inicia o servidor Uvicorn usando o método explícito de módulo Python.
# Este comando só é executado depois do passo 1 ser bem-sucedido.
python -m uvicorn main:app --host 0.0.0.0 --port $PORT
