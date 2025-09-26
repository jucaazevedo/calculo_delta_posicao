import sqlite3
import sys
import csv

def format_brazilian_currency(number):
    """Formata um número para o padrão monetário brasileiro (ex: 1.234,56)."""
    return f'{number:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')

def get_margin_from_db(asset, cursor):
    """Busca a margem de um ativo no banco de dados."""
    cursor.execute("SELECT margem FROM margens WHERE ativo = ?", (asset,))
    result = cursor.fetchone()
    if result:
        margin_str = result[0]
        try:
            if ',' in margin_str and '.' in margin_str:
                return float(margin_str.replace('.', '').replace(',', '.'))
            elif ',' in margin_str:
                return float(margin_str.replace(',', '.'))
            return float(margin_str)
        except (ValueError, TypeError):
            return 0.0
    return 0.0

def calculate_margins(position_file, cursor):
    """Calcula as margens (total, calls, puts) para um arquivo de posição e imprime os detalhes."""
    total_margin = 0.0
    call_margin_subtotal = 0.0
    put_margin_subtotal = 0.0
    
    print("--- Detalhamento do Cálculo de Margem ---")
    try:
        with open(position_file, 'r', newline='', encoding='utf-8') as f:
            for line in f:
                cleaned_line = line.split('#')[0].strip()
                if not cleaned_line: continue

                try:
                    parts = cleaned_line.split(';')
                    if len(parts) < 2: continue

                    quantity = int(parts[0].strip())
                    asset = parts[1].strip()
                    
                    unit_margin = get_margin_from_db(asset, cursor)
                    calculated_margin = quantity * unit_margin
                    total_margin += calculated_margin

                    # Acumula subtotais para Calls e Puts
                    if len(asset) > 4:
                        option_type_char = asset[4].upper()
                        if 'A' <= option_type_char <= 'L':
                            call_margin_subtotal += calculated_margin
                        elif 'M' <= option_type_char <= 'X':
                            put_margin_subtotal += calculated_margin
                    
                    is_stock = not any(char.isdigit() for char in asset[4:])
                    if unit_margin == 0.0 and not is_stock:
                        print(f"- Ativo: {asset:<12} | Qtd: {quantity:<5} | Margem Unit.: R$ {format_brazilian_currency(unit_margin):>10} | Margem Calc.: R$ {format_brazilian_currency(calculated_margin):>12} (Aviso: Margem não encontrada)")
                    else:
                        print(f"- Ativo: {asset:<12} | Qtd: {quantity:<5} | Margem Unit.: R$ {format_brazilian_currency(unit_margin):>10} | Margem Calc.: R$ {format_brazilian_currency(calculated_margin):>12}")

                except (ValueError, IndexError) as e:
                    print(f"Aviso: Linha mal formatada ignorada: '{cleaned_line}' - Erro: {e}")

    except FileNotFoundError:
        print(f"Erro: Arquivo de posição não encontrado em '{position_file}'.")
        return None, None, None
        
    return total_margin, call_margin_subtotal, put_margin_subtotal

def main():
    """Função principal para calcular a margem da posição."""
    if len(sys.argv) != 2:
        print(f"Uso: python3 {sys.argv[0]} <caminho_para_o_arquivo_de_posicao.csv>")
        sys.exit(1)

    position_file = sys.argv[1]
    db_name = 'margem.db'

    try:
        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()
            total_margin, call_subtotal, put_subtotal = calculate_margins(position_file, cursor)
            
            if total_margin is not None:
                print("-----------------------------------------")
                print(f"Margem Parcial de Calls:  R$ {format_brazilian_currency(call_subtotal)}")
                print(f"Margem Parcial de Puts:   R$ {format_brazilian_currency(put_subtotal)}")
                print("-----------------------------------------")
                print(f"Margem Líquida Calculada: R$ {format_brazilian_currency(total_margin)}")

    except sqlite3.Error as e:
        print(f"Erro ao conectar ou ler o banco de dados '{db_name}': {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()