#!/bin/bash

# Verifica se o nome do arquivo foi fornecido como argumento
if [ -z "$1" ]; then
    echo "Erro: Nenhum arquivo de entrada fornecido."
    echo "Uso: $0 <arquivo_de_entrada>"
    exit 1
fi

# Verifica se o arquivo de entrada existe
if [ ! -f "$1" ]; then
    echo "Erro: O arquivo '$1' não foi encontrado."
    exit 1
fi

# Processa o arquivo de entrada com awk e gera o arquivo convertido.csv
awk 'BEGIN{FS=","; OFS=";"} {
    qty = $3;
    if (tolower($2) == "v") {
        qty = -qty;
    }
    print qty, $1;
}' "$1" > convertido.csv

echo "Arquivo '$1' convertido com sucesso para 'convertido.csv'."
