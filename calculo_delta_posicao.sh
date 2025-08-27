#!/bin/bash

# --- calculo_delta_posicao.sh ---
#
# Este script calcula o delta total de uma carteira de ações e opções.
# Ele replica a funcionalidade do script Python 'calculo_delta.py'.
#
# Dependências:
# - curl: para fazer requisições HTTP.
# - jq: para processar a resposta JSON da API.
# - awk: para cálculos de ponto flutuante.
#
# Uso:
# 1. Exporte seu token da Oplab:
#    export TOKEN_OPLAB='seu_token_aqui'
# 2. Dê permissão de execução ao script:
#    chmod +x calculo_delta_posicao.sh
# 3. Execute o script com o arquivo de posição:
#    ./calculo_delta_posicao.sh seu_arquivo.csv

echo "--- Iniciando cálculo de delta da carteira ---"

# 1. Validação de entrada
if [ -z "$1" ]; then
    echo "ERRO: O nome do arquivo de posição deve ser fornecido como argumento."
    echo "Uso: ./calculo_delta_posicao.sh <nome_do_arquivo>"
    exit 1
fi

posicao_filename="$1"

if [ ! -f "$posicao_filename" ]; then
    echo "ERRO FATAL: O arquivo '$posicao_filename' não foi encontrado no diretório."
    exit 1
fi

if [ -z "$TOKEN_OPLAB" ]; then
    echo "ERRO FATAL: A variável de ambiente TOKEN_OPLAB não foi definida."
    echo "Por favor, defina o token para continuar: export TOKEN_OPLAB='seu_token_aqui'"
    exit 1
fi

echo "INFO: Token da API carregado com sucesso."

# 2. Inicialização
total_delta=0.0
API_BASE_URL="https://api.oplab.com.br/v3/market"

# 3. Processamento do arquivo
while IFS=';' read -r quantity symbol; do
    # Ignora linhas vazias ou malformadas
    if [ -z "$symbol" ] || [ -z "$quantity" ]; then
        continue
    fi

    # Remove espaços em branco e converte para maiúsculas
    symbol=$(echo "$symbol" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | tr 'a-z' 'A-Z')
    quantity=$(echo "$quantity" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

    # Ignora a linha se o símbolo ou a quantidade estiverem vazios após a limpeza
    if [ -z "$symbol" ] || [ -z "$quantity" ]; then
        continue
    fi

    echo ""
    echo "Processando ativo: $symbol, Quantidade: $quantity"

    # Verifica se é ação ou opção
    if [ ${#symbol} -le 6 ]; then
        # É uma ação
        echo "INFO: $symbol é uma ação. Delta = 1."
        delta_value=1.0
    else
        # É uma opção, consulta a API
        echo "INFO: $symbol é uma opção. Consultando API para obter dados..."
        url="$API_BASE_URL/options/bs?symbol=$symbol&irate=15"
        
        # O -f faz com que o curl retorne um erro se o status HTTP não for 2xx
        response=$(curl -s -f -H "Access-Token: $TOKEN_OPLAB" "$url")
        
        if [ $? -ne 0 ]; then
            echo "ERRO: Falha ao obter dados para $symbol. Verifique o símbolo, o token ou a conexão."
            continue
        fi

        # Extrai dados usando jq
        delta_value=$(echo "$response" | jq -r '.delta')
        price_value=$(echo "$response" | jq -r '.price')
        strike_value=$(echo "$response" | jq -r '.strike')
        volatility_value=$(echo "$response" | jq -r '.volatility')

        if [ "$delta_value" = "null" ] || [ "$price_value" = "null" ] || [ "$strike_value" = "null" ] || [ "$volatility_value" = "null" ]; then
            echo "ERRO: A resposta da API para $symbol não contém os campos esperados."
            continue
        fi
        
        # Formata e imprime os dados da opção
        printf "INFO: Delta: %.4f, Preço: %.2f, Strike: %.2f, Volatilidade: %.2f%%\n" \
            "$delta_value" "$price_value" "$strike_value" "$volatility_value"
    fi

    # 4. Cálculo do Delta
    position_delta=$(awk -v q="$quantity" -v d="$delta_value" 'BEGIN { printf "%.2f", q * d }')
    total_delta=$(awk -v t="$total_delta" -v p="$position_delta" 'BEGIN { printf "%.2f", t + p }')
    
    echo "INFO: Delta da posição para $symbol: $position_delta"

done < <(grep -v '^[[:space:]]*#' "$posicao_filename")

echo ""
echo "--- Cálculo Finalizado ---"
printf "O delta total da sua carteira é: %.2f\n" "$total_delta"
