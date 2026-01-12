"""
Gerador de PDFs para extratos de comissão
"""
import os
import pandas as pd
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from .formatters import fmt_num, to_float, norm_pct


def gerar_pdf_extrato(path: str, df_src: pd.DataFrame):
    """
    Gera PDF com extrato de comissão no formato paisagem
    
    Args:
        path: Caminho do arquivo PDF a ser gerado
        df_src: DataFrame com os dados do extrato
    """
    # Prepara os dados
    df = _preparar_dados(df_src)
    
    # Configurações do PDF
    W, H = landscape(A4)
    margin_l = 12 * mm
    margin_r = 12 * mm
    usable_r = W - margin_r
    top = H - 18 * mm
    
    # Cria o canvas
    c = canvas.Canvas(path, pagesize=landscape(A4))
    
    # Tenta encontrar a logo
    logo_path = _find_logo()
    
    # Especificações das colunas (nome, largura em mm)
    col_specs = [
        ("Doc",          20),
        ("Cliente",      55),
        ("Título",       48),
        ("Artigo",       33),
        ("Valor Receb.", 28),
        ("Rec. Líquido", 28),
        ("Preço Venda",  24),
        ("%Com",         16),
        ("Valor Com.",   28),
    ]
    
    # Calcula posições X das colunas
    x_pos = [margin_l]
    for _, w in col_specs[:-1]:
        x_pos.append(x_pos[-1] + w * mm)
    x_end = usable_r
    
    # Gera o PDF por vendedor
    for vend, dfv in df.groupby("Vendedor"):
        line = _page_header(c, vend, logo_path, col_specs, x_pos, x_end, W, H, top)
        total_rec = 0.0
        total_com = 0.0
        
        # Linhas de dados
        for _, r in dfv.iterrows():
            if line < 20 * mm:
                c.showPage()
                line = _page_header(c, vend, logo_path, col_specs, x_pos, x_end, W, H, top)
            
            line, rec, com = _draw_row(c, r, col_specs, x_pos, x_end, line)
            total_rec += rec
            total_com += com
        
        # Linha de totais
        _draw_totals(c, total_rec, total_com, col_specs, x_pos, x_end, line)
        c.showPage()
    
    c.save()


def _preparar_dados(df_src: pd.DataFrame) -> pd.DataFrame:
    """Prepara e normaliza os dados do DataFrame"""
    df = df_src.copy()
    
    if "Vendedor" not in df.columns:
        raise RuntimeError("Coluna 'Vendedor' não encontrada.")
    
    # Normaliza campos numéricos
    df["Valor Recebido"]  = df.get("Recebido", 0).apply(to_float)
    df["Rec Liquido"]     = df.get("Rec Liquido", 0).apply(to_float)
    df["Preço Venda"]     = df.get("Preço Venda", 0).apply(to_float)
    df["% Comissão"]      = df.get("% Comissão", 0).apply(norm_pct)
    df["Valor Comissão"]  = df.get("Valor Comissão", 0).apply(to_float)
    
    return df


def _find_logo() -> str:
    """Procura o arquivo de logo nos diretórios possíveis"""
    logo_candidates = [
        os.path.join(os.path.dirname(__file__), "..", "logo.png"),
        os.path.join(os.path.dirname(__file__), "..", "logo1-removebg-preview.png"),
        "logo.png",
        "logo1-removebg-preview.png"
    ]
    return next((p for p in logo_candidates if os.path.exists(p)), None)


def _page_header(c, vendedor: str, logo_path: str, col_specs: list, 
                 x_pos: list, x_end: float, W: float, H: float, top: float) -> float:
    """
    Desenha o cabeçalho da página e retorna a linha atual
    
    Returns:
        float: Posição Y da linha atual após o cabeçalho
    """
    # Logo
    if logo_path:
        try:
            img = ImageReader(logo_path)
            c.drawImage(img, 12*mm, H - 18*mm, width=30*mm, height=12*mm,
                       preserveAspectRatio=True, mask='auto')
        except Exception:
            pass
    
    # Título
    c.setFont("Helvetica-Bold", 16)
    c.drawString(12*mm + (34*mm if logo_path else 0), H - 12*mm,
                f"Extrato de Comissão – {vendedor}")
    
    # Cabeçalho das colunas
    line = H - 26*mm
    c.setFont("Helvetica-Bold", 10)
    for i, (title, _) in enumerate(col_specs):
        if i == len(col_specs) - 1:
            c.drawRightString(x_end, line, title)
        else:
            c.drawString(x_pos[i], line, title)
    
    line -= 2*mm
    c.line(12*mm, line, x_end, line)
    line -= 4*mm
    c.setFont("Helvetica", 10)
    
    return line


def _draw_row(c, row, col_specs: list, x_pos: list, x_end: float, line: float) -> tuple:
    """
    Desenha uma linha de dados no PDF
    
    Returns:
        tuple: (nova_linha, rec_liquido, valor_comissao)
    """
    doc   = str(row.get("ID", ""))
    cli   = str(row.get("Cliente", ""))[:35]
    tit   = str(row.get("Titulo", ""))[:35]
    art   = str(row.get("Artigo", ""))[:28]
    vr    = row.get("Valor Recebido", 0.0)
    rl    = row.get("Rec Liquido", 0.0)
    pv    = row.get("Preço Venda", 0.0)
    pct   = row.get("% Comissão", 0.0)
    vcom  = row.get("Valor Comissão", 0.0)
    
    # Texto
    c.drawString(x_pos[0], line, doc)
    c.drawString(x_pos[1], line, cli)
    c.drawString(x_pos[2], line, tit)
    c.drawString(x_pos[3], line, art)
    
    # Números alinhados à direita
    c.drawRightString(x_pos[4] + (col_specs[4][1]*mm - 2*mm), line, fmt_num(vr, 2))
    c.drawRightString(x_pos[5] + (col_specs[5][1]*mm - 2*mm), line, fmt_num(rl, 2))
    c.drawRightString(x_pos[6] + (col_specs[6][1]*mm - 2*mm), line, fmt_num(pv, 4))
    c.drawRightString(x_pos[7] + (col_specs[7][1]*mm - 4*mm), line, f"{pct:.2f}%")
    c.drawRightString(x_end, line, fmt_num(vcom, 2))
    
    line -= 6*mm
    
    return line, float(rl), float(vcom)


def _draw_totals(c, total_rec: float, total_com: float, col_specs: list, 
                 x_pos: list, x_end: float, line: float):
    """Desenha a linha de totais"""
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(x_pos[5] + (col_specs[5][1]*mm - 2*mm), line, fmt_num(total_rec, 2))
    c.drawRightString(x_end, line, fmt_num(total_com, 2))
    c.setFont("Helvetica", 10)