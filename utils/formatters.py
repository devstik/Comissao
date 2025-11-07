"""
Funções de formatação de dados
"""
from decimal import Decimal, ROUND_HALF_UP
import pandas as pd
from constants import PT_BR_MONTHS


def br_to_float(v):
    """Converte string BR para float"""
    try:
        return float(str(v).replace('.', '').replace(',', '.'))
    except:
        return 0.0


def br_to_decimal(v, places=2):
    """
    Converte valor para Decimal com precisão
    
    Args:
        v: Valor a converter (str, int, float, Decimal)
        places: Casas decimais (None para não arredondar)
    
    Returns:
        Decimal ou None
    """
    if v is None:
        return None
    
    if isinstance(v, Decimal):
        q = v
    elif isinstance(v, (int, float)):
        q = Decimal(str(v))
    else:
        s = str(v).strip()
        if s == "" or s.lower() == "none":
            return None
        s = s.replace('.', '').replace(',', '.')
        q = Decimal(s)
    
    if places is not None:
        exp = Decimal('1').scaleb(-places)
        q = q.quantize(exp, rounding=ROUND_HALF_UP)
    
    return q


def fmt_num(v, places=2):
    """
    Formata número no padrão brasileiro (1.234,56)
    
    Args:
        v: Valor a formatar
        places: Casas decimais
    
    Returns:
        String formatada
    """
    try:
        x = float(v)
        s = f"{x:,.{places}f}"
        return s.replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "0,00" if places == 2 else "0,0000"


def comp_br(date_like):
    """
    Converte data para formato competência brasileiro (Mês-Ano)
    
    Args:
        date_like: Data em qualquer formato
    
    Returns:
        String no formato "Jan-2024" ou vazio
    """
    d = pd.to_datetime(date_like, errors="coerce")
    if pd.isna(d):
        return ""
    return f"{PT_BR_MONTHS[d.month]}-{d.year}"


def prepare_df_for_display(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepara DataFrame para exibição (reseta índice)
    """
    return df.reset_index(drop=True)


def apply_display_formats(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica formatações de exibição no DataFrame
    
    Args:
        df: DataFrame original
    
    Returns:
        DataFrame formatado para exibição
    """
    df2 = df.copy()
    
    # Fix Prazo Médio (divide por 10 se >= 100)
    if "Prazo Médio" in df2.columns:
        def _fix_prazo(v):
            try:
                x = float(v)
                if x >= 100 and x % 10 == 0:
                    x = x / 10.0
                return fmt_num(x, 2)
            except:
                return "0,00"
        df2["Prazo Médio"] = df2["Prazo Médio"].apply(_fix_prazo)
    
    # Preços com 4 casas decimais
    for c in ["Preço Médio", "Preço Venda"]:
        if c in df2.columns:
            df2[c] = df2[c].apply(lambda x: fmt_num(x, 4))
    
    # Percentual de comissão
    if "Percentual_Comissao" in df2.columns:
        df2["Percentual_Comissao"] = df2["Percentual_Comissao"].apply(lambda x: fmt_num(x, 2))
    
    # Valores monetários com 2 casas decimais
    for c in ["Recebido", "ICMSST", "Frete", "Rec Liquido", "% Comissão", "Valor Comissão"]:
        if c in df2.columns:
            df2[c] = df2[c].apply(lambda x: fmt_num(x, 2))
    
    return df2


def to_float(s):
    """
    Converte string para float tratando formatos BR e US
    
    Args:
        s: String a converter
    
    Returns:
        float ou 0.0
    """
    if s is None:
        return 0.0
    
    s = str(s).strip()
    
    # Formato US (0.5081)
    if "." in s and "," not in s:
        try:
            return float(s)
        except:
            return 0.0
    
    # Formato BR (1.234,56)
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except:
        return 0.0


def norm_pct(p):
    """
    Normaliza percentual para float
    
    Args:
        p: Percentual (qualquer formato)
    
    Returns:
        float
    """
    try:
        x = float(str(p).replace(",", "."))
    except:
        x = 0.0
    return x