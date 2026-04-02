"""
🔍 AUDITORIA DETALHADA DE SINCRONIZAÇÃO
Script para diagnosticar diferenças entre TopManager e Comissys
"""
from config import DBConfig, get_conn
from queries import build_query_866
from utils.formatters import br_to_decimal
from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd

def auditoria_vendedor(vendedor, competencia_inicio, competencia_fim):
    """
    Executa auditoria completa para um vendedor
    
    Args:
        vendedor: Nome do vendedor
        competencia_inicio: Data inicial (date)
        competencia_fim: Data final (date)
    """
    cfg = DBConfig()
    
    print("=" * 100)
    print(f"🔍 AUDITORIA - Vendedor: {vendedor}")
    print(f"📅 Período: {competencia_inicio.strftime('%d/%m/%Y')} a {competencia_fim.strftime('%d/%m/%Y')}")
    print("=" * 100)
    
    # ========== TOPMANAGER ==========
    print("\n📊 BUSCANDO DADOS DO TOPMANAGER...")
    di = competencia_inicio.strftime('%Y%m%d')
    df = competencia_fim.strftime('%Y%m%d')
    
    sql, params = build_query_866(di, df, vendedor)
    
    with get_conn(cfg) as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        while cur.description is None and cur.nextset():
            pass
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
    
    df_tm = pd.DataFrame.from_records(rows, columns=cols)
    
    if "NmLot" in df_tm.columns:
        df_tm.rename(columns={"NmLot": "Vendedor"}, inplace=True)
    
    print(f"✅ TopManager: {len(df_tm)} registro(s)")
    
    # ========== COMISSYS ==========
    print("\n📊 BUSCANDO DADOS DO COMISSYS...")
    
    query = """
        SELECT 
            Id as DBId,
            Doc as ID,
            Titulo,
            Artigo,
            Vendedor,
            CONVERT(VARCHAR(10), DataRecebimento, 23) as DataRecebimentoISO,
            RecebimentoLiq,
            Recebido,
            PercComissao,
            PrecoVenda,
            Consolidado
        FROM dbo.Stik_Extrato_Comissoes
        WHERE DataRecebimento BETWEEN ? AND ?
          AND Vendedor = ?
          AND Consolidado = 0
        ORDER BY Vendedor, Doc, DataRecebimento
    """
    
    with get_conn(cfg) as conn:
        cur = conn.cursor()
        cur.execute(query, (competencia_inicio, competencia_fim, vendedor))
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
    
    df_cs = pd.DataFrame.from_records(rows, columns=cols)
    
    print(f"✅ Comissys: {len(df_cs)} registro(s)")
    
    # ========== ANÁLISE DE TOTAIS ==========
    print("\n" + "=" * 100)
    print("💰 TOTALIZAÇÕES")
    print("=" * 100)
    
    # TopManager
    if len(df_tm) > 0:
        # Tenta extrair Recebimento como decimal
        recebimentos_tm = []
        for idx, row in df_tm.iterrows():
            try:
                # Tenta múltiplas variações
                val = row.get('Recebido') or row.get('Recebimento') or row.get('Rec Liquido') or 0
                dec = br_to_decimal(val, 2) if val else Decimal('0')
                recebimentos_tm.append(dec if dec else Decimal('0'))
            except Exception as e:
                print(f"⚠️ Erro ao converter TopManager linha {idx}: {e}")
                recebimentos_tm.append(Decimal('0'))
        
        total_tm = sum(recebimentos_tm)
        print(f"\n📊 TopManager:")
        print(f"   Total de registros: {len(df_tm)}")
        print(f"   Total Recebido: R$ {total_tm:,.2f}")
    else:
        print(f"\n📊 TopManager: VAZIO!")
        total_tm = Decimal('0')
    
    # Comissys
    if len(df_cs) > 0:
        recebidos_cs = []
        for idx, row in df_cs.iterrows():
            try:
                val = row.get('Recebido')
                if val is None or pd.isna(val):
                    recebidos_cs.append(Decimal('0'))
                else:
                    dec = br_to_decimal(val, 2)
                    recebidos_cs.append(dec if dec else Decimal('0'))
            except Exception as e:
                print(f"⚠️ Erro ao converter Comissys linha {idx}: {e}")
                recebidos_cs.append(Decimal('0'))
        
        total_cs = sum(recebidos_cs)
        print(f"\n📊 Comissys:")
        print(f"   Total de registros: {len(df_cs)}")
        print(f"   Total Recebido: R$ {total_cs:,.2f}")
    else:
        print(f"\n📊 Comissys: VAZIO!")
        total_cs = Decimal('0')
    
    # Diferença
    diferenca_total = total_tm - total_cs
    print(f"\n⚠️  DIFERENÇA: R$ {diferenca_total:,.2f}")
    
    if abs(diferenca_total) > Decimal('0.01'):
        percentual_diff = (abs(diferenca_total) / total_tm * 100) if total_tm > 0 else 0
        print(f"   ❌ DIFERENÇA CRÍTICA! ({percentual_diff:.2f}% de diferença)")
    else:
        print(f"   ✅ Diferença aceitável (< R$ 0,01)")
    
    # ========== ANÁLISE POR REGISTRO ==========
    print("\n" + "=" * 100)
    print("🔎 ANÁLISE POR REGISTRO")
    print("=" * 100)
    
    # Cria chaves para comparação
    df_tm['_chave'] = df_tm.apply(
        lambda x: (
            str(x.get('ID', '')).strip().lower(),
            str(x.get('Titulo', '')).strip().lower(),
            str(x.get('Artigo', '')).strip().lower(),
        ),
        axis=1
    )
    
    df_cs['_chave'] = df_cs.apply(
        lambda x: (
            str(x.get('ID', '')).strip().lower(),
            str(x.get('Titulo', '')).strip().lower(),
            str(x.get('Artigo', '')).strip().lower(),
        ),
        axis=1
    )
    
    chaves_tm = set(df_tm['_chave'])
    chaves_cs = set(df_cs['_chave'])
    
    # Encontrar diferenças
    faltando = chaves_tm - chaves_cs
    sobrando = chaves_cs - chaves_tm
    em_comum = chaves_tm & chaves_cs
    
    print(f"\n📋 Estatísticas:")
    print(f"   Em sincronia: {len(em_comum)}")
    print(f"   Faltando no Comissys: {len(faltando)}")
    print(f"   Sobrando no Comissys: {len(sobrando)}")
    
    # ========== REGISTROS COM VALORES DIFERENTES ==========
    print("\n" + "=" * 100)
    print("💔 REGISTROS COM VALORES DIFERENTES (Recebido)")
    print("=" * 100)
    
    tm_idx = df_tm.set_index('_chave')
    cs_idx = df_cs.set_index('_chave')
    
    diferentes = []
    
    for k in em_comum:
        try:
            row_tm = tm_idx.loc[k]
            row_cs = cs_idx.loc[k]
            
            # Extrai valores de Recebido
            val_tm = row_tm.get('Recebido') or row_tm.get('Recebimento') or 0
            val_cs = row_cs.get('Recebido')
            
            dec_tm = br_to_decimal(val_tm, 2) if val_tm else Decimal('0')
            dec_cs = br_to_decimal(val_cs, 2) if val_cs else Decimal('0')
            
            diferenca = abs(dec_tm - dec_cs)
            
            if diferenca >= Decimal('0.01'):  # Apenas se diferença >= 1 centavo
                diferentes.append({
                    'id': row_tm.get('ID'),
                    'titulo': row_tm.get('Titulo'),
                    'artigo': row_tm.get('Artigo'),
                    'tm': dec_tm,
                    'cs': dec_cs,
                    'diff': diferenca
                })
        except Exception as e:
            print(f"⚠️ Erro ao comparar: {e}")
    
    if diferentes:
        # Ordena por maior diferença
        diferentes.sort(key=lambda x: x['diff'], reverse=True)
        
        print(f"\n❌ {len(diferentes)} registro(s) com diferenças:")
        print("\nTop 20 maiores diferenças:\n")
        
        for idx, item in enumerate(diferentes[:20], 1):
            print(f"{idx:2d}. Doc {item['id']}: {item['titulo'][:30]}")
            print(f"    TM:       R$ {item['tm']:>12,.2f}")
            print(f"    CS:       R$ {item['cs']:>12,.2f}")
            print(f"    DIFF:     R$ {item['diff']:>12,.2f}  {'⚠️ CRÍTICO' if item['diff'] > Decimal('10') else ''}")
            print()
        
        if len(diferentes) > 20:
            print(f"\n... e mais {len(diferentes) - 20} registro(s)")
            
            # Soma das diferenças
            soma_diffs = sum(d['diff'] for d in diferentes)
            print(f"\n📊 Total de diferenças: R$ {soma_diffs:,.2f}")
    else:
        print("\n✅ Nenhum registro com diferenças detectado (todos estão OK)")
    
    # ========== REGISTROS FALTANDO ==========
    if faltando:
        print("\n" + "=" * 100)
        print(f"📥 {len(faltando)} REGISTRO(S) FALTANDO NO COMISSYS")
        print("=" * 100)
        
        for idx, k in enumerate(list(faltando)[:10], 1):
            row = tm_idx.loc[k]
            val = br_to_decimal(row.get('Recebido') or row.get('Recebimento') or 0, 2)
            print(f"{idx:2d}. Doc {row.get('ID')}: {row.get('Titulo')[:40]} = R$ {val:>12,.2f}")
        
        if len(faltando) > 10:
            print(f"... e mais {len(faltando) - 10}")
    
    # ========== REGISTROS SOBRANDO ==========
    if sobrando:
        print("\n" + "=" * 100)
        print(f"📤 {len(sobrando)} REGISTRO(S) SOBRANDO NO COMISSYS")
        print("=" * 100)
        
        for idx, k in enumerate(list(sobrando)[:10], 1):
            row = cs_idx.loc[k]
            val = br_to_decimal(row.get('Recebido'), 2) if row.get('Recebido') else Decimal('0')
            print(f"{idx:2d}. Doc {row.get('ID')}: {row.get('Titulo')[:40]} = R$ {val:>12,.2f}")
        
        if len(sobrando) > 10:
            print(f"... e mais {len(sobrando) - 10}")
    
    print("\n" + "=" * 100)
    print("🏁 FIM DA AUDITORIA")
    print("=" * 100)
    
    return {
        'total_tm': total_tm,
        'total_cs': total_cs,
        'diferenca': diferenca_total,
        'registros_diferentes': len(diferentes),
        'faltando': len(faltando),
        'sobrando': len(sobrando),
    }


if __name__ == "__main__":
    from datetime import date
    
    print("\n🔍 FERRAMENTA DE AUDITORIA DE SINCRONIZAÇÃO\n")
    
    # Solicita dados do usuário
    vendedor = input("👤 Digite o nome do vendedor (ou enter para TODOS): ").strip() or None
    
    data_inicio = input("📅 Data inicial (dd/mm/yyyy) [padrão: 1º dia do mês atual]: ").strip()
    if not data_inicio:
        hoje = date.today()
        competencia_inicio = date(hoje.year, hoje.month, 1)
    else:
        try:
            d, m, y = map(int, data_inicio.split('/'))
            competencia_inicio = date(y, m, d)
        except:
            print("❌ Data inválida!")
            exit(1)
    
    data_fim = input("📅 Data final (dd/mm/yyyy) [padrão: hoje]: ").strip()
    if not data_fim:
        competencia_fim = date.today()
    else:
        try:
            d, m, y = map(int, data_fim.split('/'))
            competencia_fim = date(y, m, d)
        except:
            print("❌ Data inválida!")
            exit(1)
    
    # Executa auditoria
    resultado = auditoria_vendedor(vendedor, competencia_inicio, competencia_fim)
    
    # Resumo final
    print(f"""
╔════════════════════════════════════════════════════════════════╗
║                    RESUMO DA AUDITORIA                          ║
╠════════════════════════════════════════════════════════════════╣
║  Total TopManager:              R$ {resultado['total_tm']:>20,.2f}   ║
║  Total Comissys:                R$ {resultado['total_cs']:>20,.2f}   ║
║  DIFERENÇA:                     R$ {resultado['diferenca']:>20,.2f}   ║
║                                                                 ║
║  Registros com valores diferentes:  {resultado['registros_diferentes']:>10d}   ║
║  Faltando no Comissys:              {resultado['faltando']:>10d}   ║
║  Sobrando no Comissys:              {resultado['sobrando']:>10d}   ║
╚════════════════════════════════════════════════════════════════╝
""")
