# Cálculo de Delta de Carteira

Este projeto consiste em um script Python que calcula o delta total de uma carteira de ações e opções. O script lê as posições de um arquivo CSV, consulta a API da [OpLab](https://oplab.com.br/) para obter dados de mercado em tempo real para as opções e, em seguida, calcula e exibe o delta ponderado para cada posição e o delta total da carteira.

## Funcionalidades

*   Calcula o delta para ações (considerado 1.0) e opções.
*   Obtém dados em tempo real para opções (delta, preço, strike) da API da Oplab.
*   Lê as posições de um arquivo CSV customizável.
*   Utiliza uma variável de ambiente para a autenticação segura na API.
*   Exibe informações detalhadas para cada ativo processado.

## Requisitos

*   Python 3.x
*   Uma chave de API (token) da Oplab.

## Configuração

Antes de executar o script, você precisa configurar sua chave de API da Oplab como uma variável de ambiente. Execute o seguinte comando no seu terminal, substituindo `'seu_token_aqui'` pelo seu token real:

```bash
export TOKEN_OPLAB='seu_token_aqui'
```

## Formato do Arquivo de Posição

O script espera um arquivo CSV como entrada. Cada linha neste arquivo deve representar uma posição e conter a quantidade e o símbolo do ativo, separados por um ponto e vírgula (`;`).

**Formato:** `quantidade;codigo_do_ativo`

### Exemplo de `posicao.csv`

```csv
-300;BOVAJ33
100;BOVA11
400;BBASI192
-500;BBASI195
```

## Como Usar

Para executar o script, passe o nome do seu arquivo de posições como um argumento de linha de comando.

```bash
python calculo_delta.py seu_arquivo_de_posicoes.csv
```

### Exemplo de Execução

```bash
python calculo_delta.py posicao.csv
```

O script irá processar cada linha do arquivo, exibindo os detalhes de cada ativo e, ao final, o delta total da carteira.

## Obtenção de Dados de Margem

O script `obter_margens.py` é responsável por baixar um PDF com as margens de garantia do BTG Pactual, extrair os dados e salvá-los localmente.

### Funcionalidades

*   Baixa o PDF de margens do site do BTG Pactual.
*   Extrai os dados de ativos e suas respectivas margens.
*   Salva os dados em um banco de dados SQLite (`margem.db`) e em um arquivo CSV (`margem.csv`).

### Como Usar

Para executar o script, basta rodar o seguinte comando:

```bash
python obter_margens.py
```

## Cálculo de Margem da Posição

O script `calcular_margem_posicao.py` calcula a margem total de uma carteira com base nos dados de posição e nas margens previamente obtidas.

### Funcionalidades

*   Lê um arquivo de posições no mesmo formato do `calculo_delta.py`.
*   Consulta o banco de dados `margem.db` para obter a margem de cada ativo.
*   Calcula a margem total da carteira e os subtotais para opções de compra (calls) e venda (puts).
*   Exibe um relatório detalhado do cálculo.

### Como Usar

Para executar o script, passe o nome do seu arquivo de posições como argumento:

```bash
python calcular_margem_posicao.py seu_arquivo_de_posicoes.csv
```

