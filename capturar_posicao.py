"""Extrai posições da tabela de opções do BTG Pactual por OCR local."""

import argparse
import csv
import io
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory

from PIL import Image, ImageOps


PASTA_PROJETO = Path(__file__).resolve().parent
EXTENSOES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff", ".gif"}
CODIGO_OPCAO = re.compile(r"[A-Z][A-Z0-9]{3}[A-X][0-9]+(?:W[1-5])?")
DIGITOS_OCR = str.maketrans("OISZB", "01528")
QUANTIDADE = re.compile(r"[+-]?(?:[0-9]+|[0-9]{1,3}(?:\.[0-9]{3})+)")


def executar_ocr(imagem, modo, *, caracteres=None, tsv=False):
    entrada = io.BytesIO()
    imagem.save(entrada, format="PNG")
    comando = ["tesseract", "stdin", "stdout", "-l", "eng", "--psm", str(modo)]
    if caracteres:
        comando += [
            "-c", f"tessedit_char_whitelist={caracteres}",
            "-c", "load_system_dawg=0", "-c", "load_freq_dawg=0",
        ]
    if tsv:
        comando.append("tsv")
    ambiente = os.environ.copy()
    ambiente.setdefault("OMP_THREAD_LIMIT", "1")
    resultado = subprocess.run(comando, input=entrada.getvalue(), capture_output=True, env=ambiente)
    if resultado.returncode:
        raise ValueError(resultado.stderr.decode(errors="replace").strip())
    return resultado.stdout.decode().strip()


def localizar_colunas(imagem):
    ampliada = imagem.resize((imagem.width * 2, imagem.height * 2), Image.Resampling.LANCZOS)
    texto = executar_ocr(ImageOps.invert(ampliada), 11, tsv=True)
    palavras = list(csv.DictReader(io.StringIO(texto), delimiter="\t"))
    for ativo in palavras:
        if ativo["text"].lower() != "ativo":
            continue
        altura = int(ativo["height"])
        esquerda, topo = int(ativo["left"]), int(ativo["top"])
        linha = {
            palavra["text"].lower().rstrip("."): int(palavra["left"])
            for palavra in palavras
            if palavra["text"] and abs(int(palavra["top"]) - topo) <= altura / 2
        }
        if not esquerda < linha.get("strike", 0) < linha.get("peso", 0):
            continue
        escala = int(ativo["width"]) / 66
        qtd = next((linha[nome] for nome in ("qtd", "qt") if nome in linha),
                   linha["peso"] + 144 * escala)
        return (
            round(topo / 2 + 13 * escala),
            (round(esquerda / 2 + 20 * escala), round(linha["strike"] / 2 - 26 * escala)),
            (round(linha["peso"] / 2 + 37 * escala), round(qtd / 2 + 35 * escala)),
        )
    raise ValueError("cabeçalho da tabela de opções não encontrado")


def linhas_visiveis(coluna):
    """Encontra as faixas de texto claras entre os separadores da tabela."""
    pixels = coluna.load()
    inicio = None
    for y in range(coluna.height + 1):
        tem_texto = y < coluna.height and any(pixels[x, y] >= 130 for x in range(coluna.width))
        if tem_texto and inicio is None:
            inicio = y
        if not tem_texto and inicio is not None:
            if y - inicio >= 5:
                yield inicio, y
            inicio = None


def ler_celula(celula, caracteres):
    ampliada = celula.resize((celula.width * 4, celula.height * 4), Image.Resampling.LANCZOS)
    preparada = ImageOps.expand(ImageOps.invert(ampliada), border=12, fill=255)
    return "".join(executar_ocr(preparada, 7, caracteres=caracteres).split())


def tirar_seta(celula):
    # A seta fica à direita do código, com um espaço maior que o espaço entre letras.
    pixels = celula.load()
    anterior = None
    for x in range(celula.width):
        if any(pixels[x, y] >= 130 for y in range(celula.height)):
            if anterior is not None and x - anterior >= 6:
                return celula.crop((0, 0, anterior + 2, celula.height))
            anterior = x
    return celula


def normalizar_codigo(codigo):
    # O sufixo é numérico, com W e o número da semana nas opções semanais.
    raiz_e_serie, sufixo = codigo[:5], codigo[5:]
    return raiz_e_serie + sufixo.translate(DIGITOS_OCR)


def extrair_posicoes(caminho):
    with Image.open(caminho) as arquivo:
        imagem = ImageOps.exif_transpose(arquivo).convert("L")
    topo, ativo, qtd = localizar_colunas(imagem)
    # Sob o cabeçalho, o espaço à esquerda do ícone tem a cor uniforme do painel.
    x_painel = max(0, ativo[0] - round((ativo[1] - ativo[0]) * 0.55))
    fundo = imagem.getpixel((x_painel, topo))
    fim = imagem.height
    for y in range(topo, imagem.height - 3):
        if all(abs(imagem.getpixel((x_painel, y + dy)) - fundo) > 8 for dy in range(4)):
            fim = y
            break

    coluna_ativo = imagem.crop((ativo[0], topo, ativo[1], fim))
    coluna_qtd = imagem.crop((qtd[0], topo, qtd[1], fim))
    posicoes = []
    for inicio, final in linhas_visiveis(coluna_ativo):
        superior = max(0, inicio - 3)
        inferior = min(coluna_ativo.height, final + 3)
        celula_ativo = coluna_ativo.crop((0, superior, coluna_ativo.width, inferior))
        codigo = normalizar_codigo(ler_celula(
            tirar_seta(celula_ativo), "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"))
        quantidade = ler_celula(coluna_qtd.crop(
            (0, superior, coluna_qtd.width, inferior)), "+-0123456789.")
        if not CODIGO_OPCAO.fullmatch(codigo) or not QUANTIDADE.fullmatch(quantidade):
            raise ValueError(f"linha na altura {topo + inicio}: ativo {codigo!r}, quantidade {quantidade!r}")
        posicoes.append((codigo, int(quantidade.replace(".", ""))))
    if not posicoes:
        raise ValueError("nenhuma posição encontrada")
    return posicoes


def gravar_csvs(posicoes, pasta):
    grupos = {}
    for codigo, quantidade in sorted(posicoes.items()):
        grupos.setdefault(codigo[:4], []).append((quantidade, codigo))

    pasta.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=pasta) as temporaria:
        for prefixo, linhas in grupos.items():
            arquivo = Path(temporaria) / f"{prefixo}.csv"
            with arquivo.open("w", encoding="utf-8", newline="") as saida:
                csv.writer(saida, delimiter=";", lineterminator="\n").writerows(linhas)
        for arquivo in sorted(Path(temporaria).iterdir()):
            arquivo.replace(pasta / arquivo.name)
    return len(grupos)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capturas", type=Path, default=PASTA_PROJETO / "capturas",
                        help="pasta com as imagens (padrão: capturas do projeto)")
    parser.add_argument("--saida", type=Path, default=PASTA_PROJETO,
                        help="pasta de destino dos CSVs (padrão: pasta do programa)")
    args = parser.parse_args()
    try:
        imagens = sorted(
            ((caminho.stat().st_mtime_ns, caminho) for caminho in args.capturas.iterdir()
             if caminho.is_file() and caminho.suffix.lower() in EXTENSOES),
            reverse=True,
        )
        if not imagens:
            raise ValueError(f"nenhuma imagem encontrada em {args.capturas}")
        if not shutil.which("tesseract"):
            raise ValueError("Tesseract não encontrado no PATH. Instale tesseract-ocr e tesseract-ocr-eng.")

        posicoes = {}
        for _, caminho in imagens:
            try:
                for codigo, quantidade in extrair_posicoes(caminho):
                    anterior = posicoes.setdefault(codigo, quantidade)
                    if anterior != quantidade:
                        print(f"Aviso: {codigo} tem quantidade {quantidade} em {caminho.name}. "
                              f"Mantida a primeira leitura ({anterior}).", file=sys.stderr)
            except (OSError, ValueError) as erro:
                raise ValueError(f"{caminho.name}: {erro}") from erro
        total_csvs = gravar_csvs(posicoes, args.saida)
    except (OSError, ValueError) as erro:
        parser.exit(1, f"Erro: {erro}\n")
    print(f"{len(posicoes)} posições em {total_csvs} CSVs em {args.saida}")


if __name__ == "__main__":
    main()
