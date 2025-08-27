import os
import csv
import json
import sys
from urllib import request, error
from typing import Optional, Dict

# Constantes
API_BASE_URL = "https://api.oplab.com.br/v3/market"

def get_asset_data(symbol: str, token: str) -> Optional[Dict[str, float]]:
    """
    Obtém o delta, price e strike de um ativo. Para ações, o delta é 1.
    Para opções, consulta a API da OpLab usando o endpoint de Black-Scholes.
    """
    if len(symbol) <= 6:
        print(f"INFO: {symbol} é uma ação. Delta = 1.")
        return {"delta": 1.0, "price": 0.0, "strike": 0.0, "volatility": 0.0}

    print(f"INFO: {symbol} é uma opção. Consultando API para obter dados...")
    headers = {"Access-Token": token}
    
    # Usando o endpoint /market/options/bs com irate=15
    url = f"{API_BASE_URL}/options/bs?symbol={symbol}&irate=15"
    req = request.Request(url, headers=headers)

    try:
        with request.urlopen(req) as response:
            if response.status == 200:
                response_body = response.read().decode("utf-8")
                data = json.loads(response_body)
                
                delta = data.get("delta")
                price = data.get("price")
                strike = data.get("strike")
                volatility = data.get("volatility")

                if delta is not None and price is not None and strike is not None and volatility is not None:
                    return {"delta": delta, "price": price, "strike": strike, "volatility": volatility}
                else:
                    print(f"ERRO: A resposta da API para {symbol} não contém os campos 'delta', 'price', 'strike' e 'volatility'.")
                    return None
            else:
                print(f"ERRO: Falha ao obter dados para {symbol}. Status: {response.status}")
                return None
    except error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else "Nenhuma resposta."
        print(f"ERRO: Falha ao obter dados para {symbol}. Status: {e.code}, Resposta: {error_body}")
        return None
    except error.URLError as e:
        print(f"ERRO: Ocorreu um erro de conexão ao consultar a API para {symbol}: {e.reason}")
        return None

def main():
    """
    Função principal para calcular o delta total da posição.
    """
    print("--- Iniciando cálculo de delta da carteira ---")

    if len(sys.argv) < 2:
        print("ERRO: O nome do arquivo de posição deve ser fornecido como argumento.")
        print("Uso: python calculo_delta.py <nome_do_arquivo>")
        return

    posicao_filename = sys.argv[1]

    token = os.getenv("TOKEN_OPLAB")
    if not token:
        print("ERRO FATAL: A variável de ambiente TOKEN_OPLAB não foi definida.")
        print("Por favor, defina o token para continuar: export TOKEN_OPLAB='seu_token_aqui'")
        return

    print("INFO: Token da API carregado com sucesso.")

    total_delta = 0.0
    try:
        with open(posicao_filename, mode='r', encoding='utf-8') as csvfile:
            non_comment_lines = (line for line in csvfile if not line.lstrip().startswith('#'))
            reader = csv.reader(non_comment_lines, delimiter=';')
#            next(reader)  # Pular o cabeçalho
            for row in reader:
                if not row or len(row) < 2:
                    continue
                
                try:
                    symbol = row[1].strip().upper()
                    quantity = int(row[0])
                except (ValueError, IndexError) as e:
                    print(f"AVISO: Ignorando linha malformada: {row}. Erro: {e}")
                    continue

                print(f"\nProcessando ativo: {symbol}, Quantidade: {quantity}")
                asset_data = get_asset_data(symbol, token)

                if asset_data is not None:
                    delta_value = asset_data['delta']
                    price_value = asset_data['price']
                    strike_value = asset_data['strike']
                    volatility_value = asset_data['volatility']

                    if len(symbol) > 6: # Apenas para opções
                        print(f"INFO: Delta: {delta_value:.4f}, Preço: {price_value:.2f}, Strike: {strike_value:.2f}, Volatilidade: {volatility_value:.2f}%")

                    position_delta = quantity * delta_value
                    total_delta += position_delta
                    print(f"INFO: Delta da posição para {symbol}: {position_delta:.2f}")

    except FileNotFoundError:
        print(f"ERRO FATAL: O arquivo '{posicao_filename}' não foi encontrado no diretório.")
        return
    except Exception as e:
        print(f"ERRO FATAL: Ocorreu um erro inesperado ao processar o arquivo: {e}")
        return

    print("\n--- Cálculo Finalizado ---")
    print(f"O delta total da sua carteira é: {total_delta:.2f}")


if __name__ == "__main__":
    main()