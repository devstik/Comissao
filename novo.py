def build_query_866(
    dt_ini: str,
    dt_fim: str,
    vendedor: str | None = None,
) -> tuple[str, list]:
    """
    Retorna (sql, params).
    dt_ini, dt_fim no formato 'YYYYMMDD'
    vendedor: se informado, aplica R.NmLot LIKE '%texto%'
    tipo_data: "Recebimento" ou "Emissao" (usa uma OU outra no filtro final)
    """

    # ===== filtro por vendedor (NmLot) =====
    nm_lot_filter_sql = "AND ( ? = '' OR R.NmLot LIKE ? )"
    nm_lot_params = ["", ""]
    if vendedor:
        padrao = f"%{vendedor}%"
        nm_lot_params = [vendedor, padrao]

    sql = f"""
    SET NOCOUNT ON;

    IF OBJECT_ID('tempdb..#Mch') IS NOT NULL DROP TABLE #Mch;
    IF OBJECT_ID('tempdb..#TitulosDeCheque') IS NOT NULL DROP TABLE #TitulosDeCheque;
    IF OBJECT_ID('tempdb..#Titulos') IS NOT NULL DROP TABLE #Titulos;
    IF OBJECT_ID('tempdb..#Devolucoes') IS NOT NULL DROP TABLE #Devolucoes;
    IF OBJECT_ID('tempdb..#Tmp') IS NOT NULL DROP TABLE #Tmp;

    /* ========================= CHEQUES  ========================= */
    SELECT Mch1.CdChq, Mch1.CdMch, Mch1.DtMch
      INTO #Mch
      FROM TbMch Mch1
      JOIN TbTop Top2 on Top2.CdTop = Mch1.CdTop and Top2.TpTopCtg = 5110
     WHERE Mch1.DtMch between ? and ?;

    SELECT Tch.CdRct
         , DtMch = Max(Mch.DtMch)
         , Valor = Sum(Tch.VrTch)
      INTO #TitulosDeCheque
      FROM TbTch Tch
      JOIN TbMch Mch on Mch.CdMch = (SELECT Top 1 Mch1.CdMch
                                       FROM #Mch Mch1
                                      WHERE Mch1.CdChq = Tch.CdChq
                                      ORDER BY Mch1.DtMch)
    GROUP BY Tch.CdRct;

    /* ========================= TITULOS (parte 1) ========================= */
    SELECT Rcm.CdRcm, Rcm.CdEmd, Rct.CdRct, Rcd.CdUne, Rcd.CdLotVen, Rcd.CdRcd,
           Rcd.DtRcdEmi, Rct.DtRctVen,
           DataRecebimento = Case When Mpg.TpMpg = 3 Then Tch.DtMch Else Rcm.DtRcmMov End,
           Tch.DtMch, Tch.Valor, Rcd.CdCli, Rcd.CdFpg, Rcd.VrRcd, Rcd.NrRcd, Rct.NrRctOrd,
           Rcm.DtRcmMov, Mpg.TpMpg, Mpg.NmMpg, Rco.VrRco, Rco.CdFvo, Rco.CdObj, Rco.CdRco
      INTO #Titulos
      FROM TbRcm Rcm
      JOIN TbRct Rct on Rct.CdRct = Rcm.CdRct
      JOIN TbRco Rco on Rco.CdRcd = Rct.CdRcd
      JOIN TbRcd Rcd on Rcd.CdRcd = Rct.CdRcd
      JOIN TbUne Une on Une.CdUne = Rcd.CdUne
      JOIN TbEmd Emd on Emd.CdEmd = Rcm.CdEmd
      JOIN TbMde Mde on Mde.CdMde = Emd.CdMde
      JOIN TbMpg Mpg on Mpg.CdMpg = Mde.CdMpg
      LEFT JOIN #TitulosDeCheque Tch on Tch.CdRct = Rct.CdRct
     WHERE Rcm.CdEmd is not null
       AND Case When Mpg.TpMpg = 3 Then Tch.DtMch Else Rcm.DtRcmMov End between ? and ?
       AND (0 = 0 or Rcd.CdlotVen = 0)
       AND (0 = 0 or Rcd.CdRcd = 0)
       AND (0 = 0 or Exists (Select 1 From TbArvCli Where CdCliFil = Rcd.CdCli and CdCli = 0));

    /* ========================= TITULOS (parte 2 - com RcdRel) ========================= */
    INSERT INTO #Titulos
    SELECT Rcm.CdRcm, Rcm.CdEmd, Rct.CdRct, Rcd.CdUne, RcdRel.CdLotVen, Rcd.CdRcd,
           Rcd.DtRcdEmi, Rct.DtRctVen,
           DataRecebimento = Case When Mpg.TpMpg = 3 Then Tch.DtMch Else Rcm.DtRcmMov End,
           Tch.DtMch, Tch.Valor, Rcd.CdCli, Rcd.CdFpg, Rcd.VrRcd, Rcd.NrRcd, Rct.NrRctOrd,
           Rcm.DtRcmMov, Mpg.TpMpg, Mpg.NmMpg, Rco.VrRco, Rco.CdFvo, Rco.CdObj, Rco.CdRco
      FROM TbRcm Rcm
      JOIN TbRct Rct on Rct.CdRct = Rcm.CdRct
      JOIN TbRcr Rcr on Rcr.CdRcd = Rct.CdRcd
      JOIN TbRcd RcdRel on RcdRel.CdRcd = Rcr.CdRcdRel
      JOIN TbRco Rco on Rco.CdRcd = Rcr.CdRcdRel
      JOIN TbRcd Rcd on Rcd.CdRcd = Rct.CdRcd
      JOIN TbUne Une on Une.CdUne = Rcd.CdUne
      JOIN TbEmd Emd on Emd.CdEmd = Rcm.CdEmd
      JOIN TbMde Mde on Mde.CdMde = Emd.CdMde
      JOIN TbMpg Mpg on Mpg.CdMpg = Mde.CdMpg
      LEFT JOIN #TitulosDeCheque Tch on Tch.CdRct = Rct.CdRct
     WHERE Rcm.CdEmd is not null
       AND Case When Mpg.TpMpg = 3 Then Tch.DtMch Else Rcm.DtRcmMov End between ? and ?
       AND (0 = 0 or RcdRel.CdlotVen = 0)
       AND (0 = 0 or Rcd.CdRcd = 0)
       AND (0 = 0 or Exists (Select 1 From TbArvCli Where CdCliFil = Rcd.CdCli and CdCli = 0));

    /* ========================= DEVOLUÇÕES ========================= */
    SELECT Rcd.CdRcd, Obj.CdObjMae, Obj.CdObjLin, CdLotVen = RcdRef.CdLotven,
           Rcd.CdCli, Rcd.DtRcdEmi,
           Valor = -Sum(Tuc.VrTuc * Rco.VrRco / Rcd.VrRcd)
      INTO #Devolucoes
      FROM TbTuc Tuc
      JOIN TbRcd Rcd on Rcd.CdRcd = Tuc.CdRcd
      JOIN TbTop Top1 on Top1.CdTop = Rcd.CdTop and Top1.TpTopCtg = 3205
      JOIN TbRco Rco on Rco.CdRcd = Rcd.CdRcd
      JOIN TbRco RcoRef on RcoRef.CdRco = Rco.CdRcoRef
      JOIN TbRcd RcdRef on RcdRef.CdRcd = RcoRef.CdRcd
      JOIN TbObj Obj on obj.CdObj = Rco.CdObj
     WHERE (0 = 0 or RcdRef.CdLotven = 0)
       AND (0 = 0 or Rcd.CdRcd = 0)
       AND (0 = 0 or Exists (Select 1 From TbArvCli Where CdCliFil = Rcd.CdCli and CdCli = 0))
       AND Rcd.DtRcdEmi between ? and ?
    GROUP BY Rcd.CdRcd, Obj.CdObjMae, Obj.CdObjLin, RcdRef.CdLotven, Rcd.CdCli, Rcd.DtRcdEmi;

    /* ========================= Consolidação em #Tmp ========================= */
    SELECT CdRct = 0, LotVen.CdLot, LotVen.NmLot, Doc = d.CdRcd, Titulo = '',
           Cliente = Pes.NmPes, CdObjMae = Mae.CdObj, Artigo = Mae.NmObj, Recebido = d.Valor,
           ICMSST = Valor, Frete = 0,
           RecebimentoLiquido = d.Valor,
           DataEmissao = d.DtRcdEmi, DataVencimento = d.DtRcdEmi, DataRecebimento = d.DtRcdEmi,
           PrazoMedio = 0, PrecoMedio = 0, MeioPagamento = 'Devolução',
           Linha = Lin.NmObj, UF = Loc.SgLoc
      Into #Tmp
      FROM #Devolucoes d
      JOIN TbLot Lotven on Lotven.CdLot = d.CdLotVen
      JOIN TbCli Cli on Cli.CdCli = d.CdCli
      JOIN TbPes Pes on Pes.CdPes = Cli.CdPes
      JOIN TbObj Mae on Mae.CdObj = d.CdObjMae
      JOIN TbObj Lin on Lin.CdObj = d.CdObjLin
      LEFT JOIN TbArvLoc ArvLoc on ArvLoc.CdLocFil = Pes.CdLoc
      JOIN TbLoc Loc on Loc.CdLoc = ArvLoc.CdLoc and Loc.TpLoc = 3

    UNION ALL

    -- Títulos (partes 1 e 2)
    SELECT Rcm.CdRct, LotVen.CdLot, LotVen.NmLot, Doc = Rcm.CdRcd,
           Titulo = Une.SgUne + '.' + Rcm.NrRcd + '/' + Convert(varchar, Rcm.NrRctOrd),
           Cliente = Pes.NmPes, CdObjMae = Mae.CdObj, Artigo = Mae.NmObj,
           Recebido = (Case When Rcm.TpMpg = 3 Then Sum(Rcm.Valor * (Rcm.VrRco / Rcm.VrRcd))
                            Else Sum(Rcn.VrRcn * (Rcm.VrRco / Rcm.VrRcd)) End),
           ICMSST = IsNull(
                      Sum(RcsICMSST.VrRcs) *
                      ((Case When Rcm.TpMpg = 3 Then Sum(Rcm.Valor * (Rcm.VrRco / Rcm.VrRcd))
                             Else Sum(Rcn.VrRcn * (Rcm.VrRco / Rcm.VrRcd)) End) / Sum(Rcm.VrRco)), 0),
           Frete = IsNull(
                      Sum(RcsFrete.VrRcs) *
                      ((Case When Rcm.TpMpg = 3 Then Sum(Rcm.Valor * (Rcm.VrRco / Rcm.VrRcd))
                             Else Sum(Rcn.VrRcn * (Rcm.VrRco / Rcm.VrRcd)) End) / Sum(Rcm.VrRco)), 0),
           RecebimentoLiquido =
               (Case When Rcm.TpMpg = 3 Then Sum(Rcm.Valor * (Rcm.VrRco / Rcm.VrRcd))
                     Else Sum(Rcn.VrRcn * (Rcm.VrRco / Rcm.VrRcd)) End)
             - IsNull(
                 Sum(RcsICMSST.VrRcs) *
                 ((Case When Rcm.TpMpg = 3 Then Sum(Rcm.Valor * (Rcm.VrRco / Rcm.VrRcd))
                        Else Sum(Rcn.VrRcn * (Rcm.VrRco / Rcm.VrRcd)) End) / Sum(Rcm.VrRco)), 0)
             - IsNull(
                 Sum(RcsFrete.VrRcs) *
                 ((Case When Rcm.TpMpg = 3 Then Sum(Rcm.Valor * (Rcm.VrRco / Rcm.VrRcd))
                        Else Sum(Rcn.VrRcn * (Rcm.VrRco / Rcm.VrRcd)) End) / Sum(Rcm.VrRco)), 0),
           DataEmissao = Rcm.DtRcdEmi, DataVencimento = Rcm.DtRctVen, DataRecebimento = Rcm.DataRecebimento,
           PrazoMedio = Fpg.QtFpgPrzMed, PrecoMedio = Sum(PM.ValorLiq) / Nullif(Sum(PM.Quantidade), 0),
           MeioPagamento = Rcm.NmMpg, Linha = Lin.NmObj, UF = Loc.SgLoc
      FROM TbRcn Rcn
      JOIN #Titulos Rcm on Rcm.CdRcm = Rcn.CdRcm
      LEFT JOIN TbFvo Fvo on Fvo.CdFvo = Rcm.CdFvo
      LEFT JOIN TbVpo Vpo on Vpo.CdVpo = Fvo.CdVpo
      JOIN TbUne Une on Une.CdUne = Rcm.CdUne
      JOIN TbLot LotVen on LotVen.CdLot = Rcm.CdLotVen
      JOIN TbObj Obj on Obj.CdObj = Rcm.CdObj
      JOIN TbObj Mae on Mae.CdObj = Obj.CdObjMae
      LEFT JOIN (
            SELECT Vpo.CdVpd, Mae.CdObj,
                   Valor = Sum(Vpo.VrVpo), ValorLiq = Sum(VrVpoMerLiq), Quantidade = Sum(Vpo.QtVpo)
              FROM TbVpo Vpo
              JOIN TbObj Obj on Obj.CdObj = Vpo.CdObj
              JOIN TbObj Mae on Mae.CdObj = Obj.CdObjMae
            GROUP BY Vpo.CdVpd, Mae.CdObj
      ) PM on PM.CdVpd = Vpo.CdVpd and PM.CdObj = Mae.CdObj
      JOIN TbOes Oes on Oes.CdOes = Rcn.CdOes and Oes.TpOesVal = 21
      JOIN TbCli Cli on Cli.CdCli = Rcm.CdCli
      JOIN TbPes Pes on Pes.CdPes = Cli.CdPes
      LEFT JOIN TbFpg Fpg on Fpg.CdFpg = Rcm.CdFpg
      LEFT JOIN TbRcs RcsICMSST on RcsICMSST.CdRco = Rcm.CdRco and RcsICMSST.CdOes = 365
      LEFT JOIN TbRcs RcsFrete on RcsFrete.CdRco = Rcm.CdRco and RcsFrete.CdOes = 57
      JOIN TbObj Lin on Lin.CdObj = Obj.CdObjLin
      LEFT JOIN TbArvLoc ArvLoc on ArvLoc.CdLocFil = Pes.CdLoc
      JOIN TbLoc Loc on Loc.CdLoc = ArvLoc.CdLoc and Loc.TpLoc = 3
     GROUP BY Rcm.CdRct, LotVen.CdLot, LotVen.NmLot, Rcm.CdRcd, Pes.NmPes, Mae.NmObj,
              Fpg.QtFpgPrzMed, Rcm.NmMpg, Rcm.DtRcdEmi, Rcm.DtRctVen,
              Rcm.TpMpg, Case When Rcm.TpMpg = 3 Then Rcm.DtMch Else Rcm.DtRcmMov End,
              Une.SgUne + '.' + Rcm.NrRcd + '/' + Convert(varchar, Rcm.NrRctOrd), Rcm.DataRecebimento,
              Lin.NmObj, Loc.SgLoc, Mae.CdObj

    UNION ALL

    -- Baixa com saldo
    SELECT Rcm.CdRct, LotVen.CdLot, LotVen.NmLot, Doc = Rcd.CdRcd,
           Titulo = Une.SgUne + '.' + Rcd.NrRcd + '/' + Convert(varchar, Rct.NrRctOrd),
           Cliente = Pes.NmPes, CdObjMae = Mae.CdObj, Artigo = Mae.NmObj,
           Recebido = Sum(Rcn.VrRcn * (Rco.VrRco / Rcd.VrRcd)),
           ICMSST = IsNull(
                      Sum(RcsICMSST.VrRcs) * ( Sum(Rcn.VrRcn * (Rco.VrRco / Rcd.VrRcd)) / Sum(Rco.VrRco) ), 0),
           Frete  = IsNull(
                      Sum(RcsFrete.VrRcs)  * ( Sum(Rcn.VrRcn * (Rco.VrRco / Rcd.VrRcd)) / Sum(Rco.VrRco) ), 0),
           RecebimentoLiquido =
               Sum(Rcn.VrRcn * (Rco.VrRco / Rcd.VrRcd))
             - IsNull(
                 Sum(RcsICMSST.VrRcs) * ( Sum(Rcn.VrRcn * (Rco.VrRco / Rcd.VrRcd)) / Sum(Rco.VrRco) ), 0)
             - IsNull(
                 Sum(RcsFrete.VrRcs)  * ( Sum(Rcn.VrRcn * (Rco.VrRco / Rcd.VrRcd)) / Sum(Rco.VrRco) ), 0),
           DataEmissao = Rcd.DtRcdEmi, DataVencimento = Rct.DtRctVen, DataRecebimento = Rcm.DtRcmMov,
           PrazoMedio = Fpg.QtFpgPrzMed, PrecoMedio = Sum(PM.ValorLiq) / Nullif(Sum(PM.Quantidade), 0),
           MeioPagamento = 'Baixa com Saldo', Linha = Lin.NmObj, UF = Loc.SgLoc
      FROM TbRcn Rcn
      JOIN TbRcm Rcm on Rcm.CdRcm = Rcn.CdRcm
      JOIN TbTuc Tuc on Tuc.CdRcm = Rcm.CdRcm
      JOIN TbRct Rct on Rct.CdRct = Rcm.CdRct
      JOIN TbRco Rco on Rco.CdRcd = Rct.CdRcd
      JOIN TbRcd Rcd on Rcd.CdRcd = Rct.CdRcd
      JOIN TbUne Une on Une.CdUne = Rcd.CdUne
      JOIN TbLot LotVen on LotVen.CdLot = Rcd.CdLotVen
      JOIN TbObj Obj on Obj.CdObj = Rco.CdObj
      JOIN TbObj Mae on Mae.CdObj = Obj.CdObjMae
      JOIN TbOes Oes on Oes.CdOes = Rcn.CdOes and Oes.TpOesVal = 21
      JOIN TbCli Cli on Cli.CdCli = Rcd.CdCli
      JOIN TbPes Pes on Pes.CdPes = Cli.CdPes
      LEFT JOIN TbFpg Fpg on Fpg.CdFpg = Rcd.CdFpg
      LEFT JOIN TbFvo Fvo on Fvo.CdFvo = Rco.CdFvo
      LEFT JOIN TbVpo Vpo on Vpo.CdVpo = Fvo.CdVpo
      LEFT JOIN (
            SELECT Vpo.CdVpd, Mae.CdObj,
                   Valor = Sum(Vpo.VrVpo), ValorLiq = Sum(VrVpoMerLiq), Quantidade = Sum(Vpo.QtVpo)
              FROM TbVpo Vpo
              JOIN TbObj Obj on Obj.CdObj = Vpo.CdObj
              JOIN TbObj Mae on Mae.CdObj = Obj.CdObjMae
            GROUP BY Vpo.CdVpd, Mae.CdObj
      ) PM on PM.CdVpd = Vpo.CdVpd and PM.CdObj = Mae.CdObj
      LEFT JOIN TbRcs RcsICMSST on RcsICMSST.CdRco = Rco.CdRco and RcsICMSST.CdOes = 365
      LEFT JOIN TbRcs RcsFrete on RcsFrete.CdRco = Rco.CdRco and RcsFrete.CdOes = 57
      JOIN TbObj Lin on Lin.CdObj = Obj.CdObjLin
      LEFT JOIN TbArvLoc ArvLoc on ArvLoc.CdLocFil = Pes.CdLoc
      JOIN TbLoc Loc on Loc.CdLoc = ArvLoc.CdLoc and Loc.TpLoc = 3
     WHERE Tuc.CdRcm is not null
       AND Rcm.DtRcmMov between ? and ?
       AND (0 = 0 or Rcd.CdlotVen = 0)
       AND (0 = 0 or Rcd.CdRcd = 0)
       AND (0 = 0 or Exists (Select 1 From TbArvCli Where CdCliFil = Rcd.CdCli and CdCli = 0))
     GROUP BY Rcm.CdRct, LotVen.CdLot, LotVen.NmLot, Rcd.CdRcd,
              Une.SgUne + '.' + Rcd.NrRcd + '/' + Convert(varchar, Rct.NrRctOrd),
              Pes.NmPes, Mae.NmObj, Rcd.DtRcdEmi, Rct.DtRctVen, Rcm.DtRcmMov,
              Fpg.QtFpgPrzMed, Lin.NmObj, Loc.SgLoc, Mae.CdObj

    -- ===== FILTRO FINAL (usa uma OU outra data) =====
    SELECT
          ID             = R.Doc,
          VendedorID     = R.CdLot,
          Vendedor       = R.NmLot,
          Titulo         = R.Titulo,
          Cliente        = R.Cliente,
          UF             = R.UF,
          CdObjMae       = R.CdObjMae,
          Artigo         = R.Artigo,
          Linha          = R.Linha,
          Recebido       = ISNULL(R.Recebido, 0),
          ICMSST         = ISNULL(R.ICMSST, 0),
          Frete          = ISNULL(R.Frete, 0),
          [Rec Liquido]  = ISNULL(R.RecebimentoLiquido, 0),
          [Prazo Médio]  = ISNULL(R.PrazoMedio, 0),
          [Preço Médio]  = ISNULL(R.PrecoMedio, 0),
          [Preço Venda]  = COALESCE(X.VrVenda, R.PrecoMedio, 0),
          [M Pagamento]  = R.MeioPagamento,
          [Emissão]      = R.DataEmissao,
          [Vencimento]   = R.DataVencimento,
          [Recebimento]  = R.DataRecebimento,
          Percentual_Comissao = CASE
                                    WHEN X.VrVenda > 0 AND Comissao.Percentual IS NOT NULL THEN Comissao.Percentual
                                    WHEN X.VrVenda > 0 THEN 0.01
                                    ELSE 0.01
                                 END
    FROM #Tmp R
    OUTER APPLY (
        SELECT VrVenda = CAST(
                       SUM(CAST(Rco.VrRcoBru AS DECIMAL(38,10))) /
                       NULLIF(SUM(CAST(Rco.QtRco   AS DECIMAL(38,10))), 0)
                     AS DECIMAL(19,4))
        FROM TbRco Rco
        JOIN TbObj Obj ON Obj.CdObj = Rco.CdObj
        JOIN TbObj Mae ON Mae.CdObj = Obj.CdObjMae
        WHERE Rco.CdRcd = R.Doc
          AND Mae.NmObj = R.Artigo
    ) X
    OUTER APPLY (
        SELECT TOP 1 C.Percentual
        FROM STIK_COMERCIAL_TabelaRateada C
        WHERE 
            C.CdObjMae = R.CdObjMae
            AND C.Min <> 0.0000 AND C.Max <> 0.0000
            AND X.VrVenda BETWEEN C.Min AND (C.Max + 0.0001)
            AND (
                (C.IDTb = 1 AND R.UF IN ('BAHIA', 'ALAGOAS', 'SERGIPE', 'PARAIBA', 'RIO GRANDE DO NORTE', 'PIAUI', 'MARANHAO')) OR
                (C.IDTb = 2 AND R.UF IN ('Santa Catarina', 'Rio Grande do Sul')) OR
                (C.IDTb = 3 AND R.UF IN ('Rio de Janeiro', 'Goiás', 'SP', 'Minas Gerais')) OR
                (C.IDTb = 4 AND R.UF = 'PE') OR
                (C.IDTb = 5 AND R.UF = 'CE')
            )
    ) Comissao
    WHERE R.DataRecebimento BETWEEN ? AND ?
      {nm_lot_filter_sql};

    DROP TABLE #Mch; DROP TABLE #Titulos; DROP TABLE #TitulosDeCheque; DROP TABLE #Devolucoes; DROP TABLE #Tmp;
    """

    # ordem dos parâmetros deve casar com os "?" do SQL acima
    params: list = []
    params += [dt_ini, dt_fim]  # #Mch
    params += [dt_ini, dt_fim]  # #Titulos 1 (usa recebimento/mov)
    params += [dt_ini, dt_fim]  # #Titulos 2 (usa recebimento/mov)
    params += [dt_ini, dt_fim]  # Devoluções (usa emissão)
    params += [dt_ini, dt_fim]  # Baixa com saldo (usa mov)
    params += [dt_ini, dt_fim]  # Filtro final (usa Emissão OU Recebimento)
    params += nm_lot_params     # filtro de vendedor (NmLot)

    return sql, params