import requests
import pdfplumber
import sqlite3
import csv
import io

def extrair_dados_pdf(url):
    """Baixa o PDF, extrai e retorna os dados de margem com base na estrutura de múltiplos ativos por linha."""
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Erro ao baixar o PDF: {e}")
        return None

    dados = []
    with pdfplumber.open(io.BytesIO(response.content)) as pdf:
        for page in pdf.pages:
            text = page.extract_text(x_tolerance=2, y_tolerance=2)
            if not text:
                continue
            
            for line in text.split('\n'):
                parts = line.split()
                if not parts or 'ativo' in line.lower() or 'margem' in line.lower() or len(parts) < 2:
                    continue

                i = 0
                while i < len(parts):
                    # Heurística para encontrar um ativo: não é um número e tem um tamanho razoável
                    if not parts[i].replace('.','').isdigit() and len(parts[i]) >= 4:
                        # Caso 1: Padrão (ATIVO, R$, VALOR)
                        if i + 2 < len(parts) and parts[i+1] == 'R$':
                            ativo = parts[i]
                            margem = parts[i+2]
                            dados.append({'ativo': ativo, 'margem': margem})
                            i += 3
                        # Caso 2: Padrão (ATIVO, VALOR)
                        elif i + 1 < len(parts) and any(char.isdigit() for char in parts[i+1]):
                            ativo = parts[i]
                            margem = parts[i+1]
                            dados.append({'ativo': ativo, 'margem': margem})
                            i += 2
                        else:
                            i += 1
                    else:
                        i += 1
    return dados

def salvar_no_sqlite(dados, db_name='margem.db'):
    """Salva os dados em um banco de dados SQLite."""
    if not dados:
        print("Nenhum dado para salvar no SQLite.")
        return

    with sqlite3.connect(db_name) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS margens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ativo TEXT NOT NULL,
            margem TEXT NOT NULL
        );
        """)
        cursor.execute("DELETE FROM margens;")
        
        for item in dados:
            cursor.execute("INSERT INTO margens (ativo, margem) VALUES (?, ?);", (item['ativo'], item['margem']))
        conn.commit()
    print(f"Dados salvos com sucesso em '{db_name}'.")

def salvar_no_csv(dados, csv_name='margem.csv'):
    """Salva os dados em um arquivo CSV."""
    if not dados:
        print("Nenhum dado para salvar no CSV.")
        return

    with open(csv_name, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['ativo', 'margem']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        writer.writerows(dados)
    print(f"Dados salvos com sucesso em '{csv_name}'.")

def main():
    """Função principal para orquestrar a extração e salvamento dos dados."""
    pdf_url = 'https://investimentos.btgpactual.com/opcoes/margens'
    
    print("Iniciando extração de dados do PDF...")
    dados_extraidos = extrair_dados_pdf(pdf_url)
    
    if dados_extraidos:
        print(f"{len(dados_extraidos)} registros encontrados.")
        salvar_no_sqlite(dados_extraidos)
        salvar_no_csv(dados_extraidos)
    else:
        print("Não foi possível extrair dados do PDF.")

if __name__ == '__main__':
    main()