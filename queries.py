def build_query_866(
    dt_ini: str,
    dt_fim: str,
    vendedor: str | None = None   # campo "Vendedor" (NmLot LIKE) opcional
) -> tuple[str, list]:
    """
    Retorna (sql, params).
    dt_ini, dt_fim no formato 'YYYYMMDD'
    vendedor: se informado, aplica R.NmLot LIKE '%texto%'
    """

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

  ------------------------------------------------------------
  -- 1) Movimentações de cheque (#Mch) e títulos de cheque
  ------------------------------------------------------------
  SELECT Mch1.CdChq,
        Mch1.CdMch,
        Mch1.DtMch
  INTO #Mch
  FROM TbMch Mch1
  JOIN TbTop Top2
    ON Top2.CdTop = Mch1.CdTop
  AND Top2.TpTopCtg = 5110;
  -- (Sem filtro por data aqui, pois o corte é feito por emissão)

  SELECT
      Tch.CdRct,
      DtMch = MAX(Mch.DtMch),
      Valor = SUM(Tch.VrTch)
  INTO #TitulosDeCheque
  FROM TbTch Tch
  JOIN TbMch Mch
    ON Mch.CdMch = (
          SELECT TOP 1 Mch1.CdMch
          FROM #Mch Mch1
          WHERE Mch1.CdChq = Tch.CdChq
          ORDER BY Mch1.DtMch
      )
  GROUP BY Tch.CdRct;

  ------------------------------------------------------------
  -- 2) Títulos recebíveis por emissão (#Titulos)
  ------------------------------------------------------------
  SELECT
      Rcm.CdRcm,
      Rcm.CdEmd,
      Rct.CdRct,
      Rcd.CdUne,
      Rcd.CdLotVen,
      Rcd.CdRcd,
      Rcd.DtRcdEmi,
      Rct.DtRctVen,
      DataRecebimento = CASE WHEN Mpg.TpMpg = 3 THEN Tch.DtMch ELSE Rcm.DtRcmMov END,
      Tch.DtMch,
      Tch.Valor,
      Rcd.CdCli,
      Rcd.CdFpg,
      Rcd.VrRcd,
      Rcd.NrRcd,
      Rct.NrRctOrd,
      Rcm.DtRcmMov,
      Mpg.TpMpg,
      Mpg.NmMpg,
      Rco.VrRco,
      Rco.CdFvo,
      Rco.CdObj,
      Rco.CdRco
  INTO #Titulos
  FROM TbRcm Rcm
  JOIN TbRct Rct               ON Rct.CdRct = Rcm.CdRct
  JOIN TbRco Rco               ON Rco.CdRcd = Rct.CdRcd
  JOIN TbRcd Rcd               ON Rcd.CdRcd = Rct.CdRcd
  JOIN TbUne Une               ON Une.CdUne = Rcd.CdUne
  JOIN TbEmd Emd               ON Emd.CdEmd = Rcm.CdEmd
  JOIN TbMde Mde               ON Mde.CdMde = Emd.CdMde
  JOIN TbMpg Mpg               ON Mpg.CdMpg = Mde.CdMpg
  LEFT JOIN #TitulosDeCheque Tch ON Tch.CdRct = Rct.CdRct
  WHERE Rcm.CdEmd IS NOT NULL
    AND Rcd.DtRcdEmi BETWEEN ? AND ?           -- << filtro por EMISSÃO
    AND (0 = 0 OR Rcd.CdlotVen = 0)
    AND (0 = 0 OR Rcd.CdRcd    = 0)
    AND (0 = 0 OR EXISTS (SELECT 1 FROM TbArvCli WHERE CdCliFil = Rcd.CdCli AND CdCli = 0))

  UNION

  SELECT
      Rcm.CdRcm,
      Rcm.CdEmd,
      Rct.CdRct,
      Rcd.CdUne,
      RcdRel.CdLotVen,
      Rcd.CdRcd,
      Rcd.DtRcdEmi,
      Rct.DtRctVen,
      DataRecebimento = CASE WHEN Mpg.TpMpg = 3 THEN Tch.DtMch ELSE Rcm.DtRcmMov END,
      Tch.DtMch,
      Tch.Valor,
      Rcd.CdCli,
      Rcd.CdFpg,
      Rcd.VrRcd,
      Rcd.NrRcd,
      Rct.NrRctOrd,
      Rcm.DtRcmMov,
      Mpg.TpMpg,
      Mpg.NmMpg,
      Rco.VrRco,
      Rco.CdFvo,
      Rco.CdObj,
      Rco.CdRco
  FROM TbRcm Rcm
  JOIN TbRct Rct               ON Rct.CdRct = Rcm.CdRct
  JOIN TbRcr Rcr               ON Rcr.CdRcd = Rct.CdRcd
  JOIN TbRcd RcdRel            ON RcdRel.CdRcd = Rcr.CdRcdRel
  JOIN TbRco Rco               ON Rco.CdRcd = Rcr.CdRcdRel
  JOIN TbRcd Rcd               ON Rcd.CdRcd = Rct.CdRcd
  JOIN TbUne Une               ON Une.CdUne = Rcd.CdUne
  JOIN TbEmd Emd               ON Emd.CdEmd = Rcm.CdEmd
  JOIN TbMde Mde               ON Mde.CdMde = Emd.CdMde
  JOIN TbMpg Mpg               ON Mpg.CdMpg = Mde.CdMpg
  LEFT JOIN #TitulosDeCheque Tch ON Tch.CdRct = Rct.CdRct
  WHERE Rcm.CdEmd IS NOT NULL
    AND Rcd.DtRcdEmi BETWEEN ? AND ?           -- << filtro por EMISSÃO
    AND (0 = 0 OR RcdRel.CdlotVen = 0)
    AND (0 = 0 OR Rcd.CdRcd      = 0)
    AND (0 = 0 OR EXISTS (SELECT 1 FROM TbArvCli WHERE CdCliFil = Rcd.CdCli AND CdCli = 0));

  ------------------------------------------------------------
  -- 3) Créditos de devolução 
  ------------------------------------------------------------
  SELECT
      Rcd.CdRcd,
      Obj.CdObjMae,
      Obj.CdObjLin,
      CdLotVen     = RcdRef.CdLotven,
      Rcd.CdCli,
      Rcd.DtRcdEmi,
      Valor        = -SUM(Tuc.VrTuc * Rco.VrRco / Rcd.VrRcd)
  INTO #Devolucoes
  FROM TbTuc Tuc
  JOIN TbRcd Rcd           ON Rcd.CdRcd = Tuc.CdRcd
  JOIN TbTop Top1          ON Top1.CdTop = Rcd.CdTop AND Top1.TpTopCtg = 3205
  JOIN TbRco Rco           ON Rco.CdRcd = Rcd.CdRcd
  JOIN TbRco RcoRef        ON RcoRef.CdRco = Rco.CdRcoRef
  JOIN TbRcd RcdRef        ON RcdRef.CdRcd = RcoRef.CdRcd
  JOIN TbObj Obj           ON Obj.CdObj = Rco.CdObj
  WHERE (0 = 0 OR RcdRef.CdLotven = 0)
    AND (0 = 0 OR Rcd.CdRcd       = 0)
    AND (0 = 0 OR EXISTS (SELECT 1 FROM TbArvCli WHERE CdCliFil = Rcd.CdCli AND CdCli = 0))
    AND Rcd.DtRcdEmi BETWEEN ? AND ?
  GROUP BY
      Rcd.CdRcd,
      Obj.CdObjMae,
      Obj.CdObjLin,
      RcdRef.CdLotven,
      Rcd.CdCli,
      Rcd.DtRcdEmi;

  ------------------------------------------------------------
  -- 4) Devoluções + Recebimentos normais
  ------------------------------------------------------------
  SELECT
      CdRct              = 0,
      LotVen.CdLot,
      LotVen.NmLot,
      Doc                = d.CdRcd,
      Titulo             = '',
      Cliente            = Pes.NmPes,
      Artigo             = Mae.NmObj,
      Recebido           = d.Valor,
      ICMSST             = Valor,
      Frete              = 0,
      RecebimentoLiquido = d.Valor,
      DataEmissao        = d.DtRcdEmi,
      DataVencimento     = d.DtRcdEmi,
      DataRecebimento    = d.DtRcdEmi,
      PrazoMedio         = 0,
      PrecoMedio         = 0,
      MeioPagamento      = 'Devolução',
      Linha              = Lin.NmObj,
      UF                 = Loc.SgLoc
  INTO #Tmp
  FROM #Devolucoes d
  JOIN TbLot Lotven       ON Lotven.CdLot = d.CdLotVen
  JOIN TbCli Cli          ON Cli.CdCli    = d.CdCli
  JOIN TbPes Pes          ON Pes.CdPes    = Cli.CdPes
  JOIN TbObj Mae          ON Mae.CdObj    = d.CdObjMae
  JOIN TbObj Lin          ON Lin.CdObj    = d.CdObjLin
  LEFT JOIN TbArvLoc ArvLoc ON ArvLoc.CdLocFil = Pes.CdLoc
  JOIN TbLoc Loc            ON Loc.CdLoc = ArvLoc.CdLoc AND Loc.TpLoc = 3 -- UF

  UNION ALL

  SELECT
      Rcm.CdRct,                   -- Rcm.CdRcm
      LotVen.CdLot,
      LotVen.NmLot,
      Doc                = Rcm.CdRcd,
      Titulo             = Une.SgUne + '.' + Rcm.NrRcd + '/' + CONVERT(varchar, Rcm.NrRctOrd),
      Cliente            = Pes.NmPes,
      Artigo             = Mae.NmObj,
      Recebido           = (CASE
                              WHEN Rcm.TpMpg = 3
                                THEN SUM(Rcm.Valor * (Rcm.VrRco / Rcm.VrRcd))
                              ELSE SUM(Rcn.VrRcn * (Rcm.VrRco / Rcm.VrRcd))
                            END),
      ICMSST             = ISNULL(
                            SUM(RcsICMSST.VrRcs) *
                            (
                              (CASE WHEN Rcm.TpMpg = 3
                                    THEN SUM(Rcm.Valor * (Rcm.VrRco / Rcm.VrRcd))
                                    ELSE SUM(Rcn.VrRcn * (Rcm.VrRco / Rcm.VrRcd))
                                END)
                              / SUM(Rcm.VrRco)
                            ), 0),
      Frete              = ISNULL(
                            SUM(RcsFrete.VrRcs) *
                            (
                              (CASE WHEN Rcm.TpMpg = 3
                                    THEN SUM(Rcm.Valor * (Rcm.VrRco / Rcm.VrRcd))
                                    ELSE SUM(Rcn.VrRcn * (Rcm.VrRco / Rcm.VrRcd))
                                END)
                              / SUM(Rcm.VrRco)
                            ), 0),
      RecebimentoLiquido =
          (CASE WHEN Rcm.TpMpg = 3
                THEN SUM(Rcm.Valor * (Rcm.VrRco / Rcm.VrRcd))
                ELSE SUM(Rcn.VrRcn * (Rcm.VrRco / Rcm.VrRcd))
            END)
        - ISNULL(
            SUM(RcsICMSST.VrRcs) *
            (
              (CASE WHEN Rcm.TpMpg = 3
                    THEN SUM(Rcm.Valor * (Rcm.VrRco / Rcm.VrRcd))
                    ELSE SUM(Rcn.VrRcn * (Rcm.VrRco / Rcm.VrRcd))
                END)
              / SUM(Rcm.VrRco)
            ), 0)
        - ISNULL(
            SUM(RcsFrete.VrRcs) *
            (
              (CASE WHEN Rcm.TpMpg = 3
                    THEN SUM(Rcm.Valor * (Rcm.VrRco / Rcm.VrRcd))
                    ELSE SUM(Rcn.VrRcn * (Rcm.VrRco / Rcm.VrRcd))
                END)
              / SUM(Rcm.VrRco)
            ), 0),
      DataEmissao        = Rcm.DtRcdEmi,
      DataVencimento     = Rcm.DtRctVen,
      DataRecebimento    = Rcm.DataRecebimento,
      PrazoMedio         = Fpg.QtFpgPrzMed,
      PrecoMedio         = SUM(PM.ValorLiq) / NULLIF(SUM(PM.Quantidade), 0),
      MeioPagamento      = Rcm.NmMpg,
      Linha              = Lin.NmObj,
      UF                 = Loc.SgLoc
  FROM TbRcn Rcn
  JOIN #Titulos Rcm           ON Rcm.CdRcm = Rcn.CdRcm
  LEFT JOIN TbFvo Fvo         ON Fvo.CdFvo = Rcm.CdFvo
  LEFT JOIN TbVpo Vpo         ON Vpo.CdVpo = Fvo.CdVpo
  JOIN TbUne Une              ON Une.CdUne = Rcm.CdUne
  JOIN TbLot LotVen           ON LotVen.CdLot = Rcm.CdLotVen
  JOIN TbObj Obj              ON Obj.CdObj = Rcm.CdObj
  JOIN TbObj Mae              ON Mae.CdObj = Obj.CdObjMae
  LEFT JOIN (
      SELECT
          Vpo.CdVpd,
          Mae.CdObj,
          Valor     = SUM(Vpo.VrVpo),
          ValorLiq  = SUM(VrVpoMerLiq),
          Quantidade= SUM(Vpo.QtVpo)
      FROM TbVpo Vpo
      JOIN TbObj Obj ON Obj.CdObj = Vpo.CdObj
      JOIN TbObj Mae ON Mae.CdObj = Obj.CdObjMae
      GROUP BY Vpo.CdVpd, Mae.CdObj
  ) PM
    ON PM.CdVpd = Vpo.CdVpd
  AND PM.CdObj = Mae.CdObj
  JOIN TbOes Oes              ON Oes.CdOes = Rcn.CdOes AND Oes.TpOesVal = 21 -- Principal
  JOIN TbCli Cli              ON Cli.CdCli = Rcm.CdCli
  JOIN TbPes Pes              ON Pes.CdPes = Cli.CdPes
  LEFT JOIN TbFpg Fpg         ON Fpg.CdFpg = Rcm.CdFpg
  LEFT JOIN TbRcs RcsICMSST   ON RcsICMSST.CdRco = Rcm.CdRco AND RcsICMSST.CdOes = 365 -- ICMSST-Valor
  LEFT JOIN TbRcs RcsFrete    ON RcsFrete.CdRco  = Rcm.CdRco AND RcsFrete.CdOes  = 57  -- Frete
  JOIN TbObj Lin              ON Lin.CdObj = Obj.CdObjLin
  LEFT JOIN TbArvLoc ArvLoc   ON ArvLoc.CdLocFil = Pes.CdLoc
  JOIN TbLoc Loc              ON Loc.CdLoc = ArvLoc.CdLoc AND Loc.TpLoc = 3 -- UF
  GROUP BY
      Rcm.CdRct,
      LotVen.CdLot,
      LotVen.NmLot,
      Rcm.CdRcd,
      Pes.NmPes,
      Mae.NmObj,
      Fpg.QtFpgPrzMed,
      Rcm.NmMpg,
      Rcm.DtRcdEmi,
      Rcm.DtRctVen,
      Rcm.TpMpg,
      CASE WHEN Rcm.TpMpg = 3 THEN Rcm.DtMch ELSE Rcm.DtRcmMov END,
      Une.SgUne + '.' + Rcm.NrRcd + '/' + CONVERT(varchar, Rcm.NrRctOrd),
      Rcm.DataRecebimento,
      Lin.NmObj,
      Loc.SgLoc,
      Une.SgUne + '.' + Rcm.NrRcd + '/' + CONVERT(varchar, Rcm.NrRctOrd)

  UNION ALL

  SELECT
      Rcm.CdRct,                   -- Rcm.CdRcm
      LotVen.CdLot,
      LotVen.NmLot,
      Doc                = Rcd.CdRcd,
      Titulo             = Une.SgUne + '.' + Rcd.NrRcd + '/' + CONVERT(varchar, Rct.NrRctOrd),
      Cliente            = Pes.NmPes,
      Artigo             = Mae.NmObj,
      Recebido           = SUM(Rcn.VrRcn * (Rco.VrRco / Rcd.VrRcd)),
      ICMSST             = ISNULL(
                            SUM(RcsICMSST.VrRcs) *
                            (
                              SUM(Rcn.VrRcn * (Rco.VrRco / Rcd.VrRcd))
                              / SUM(Rco.VrRco)
                            ), 0),
      Frete              = ISNULL(
                            SUM(RcsFrete.VrRcs) *
                            (
                              SUM(Rcn.VrRcn * (Rco.VrRco / Rcd.VrRcd))
                              / SUM(Rco.VrRco)
                            ), 0),
      RecebimentoLiquido =
          SUM(Rcn.VrRcn * (Rco.VrRco / Rcd.VrRcd))
        - ISNULL(
            SUM(RcsICMSST.VrRcs) *
            (
              SUM(Rcn.VrRcn * (Rco.VrRco / Rcd.VrRcd))
              / SUM(Rco.VrRco)
            ), 0)
        - ISNULL(
            SUM(RcsFrete.VrRcs) *
            (
              SUM(Rcn.VrRcn * (Rco.VrRco / Rcd.VrRcd))
              / SUM(Rco.VrRco)
            ), 0),
      DataEmissao        = Rcd.DtRcdEmi,
      DataVencimento     = Rct.DtRctVen,
      DataRecebimento    = Rcm.DtRcmMov,
      PrazoMedio         = Fpg.QtFpgPrzMed,
      PrecoMedio         = SUM(PM.ValorLiq) / NULLIF(SUM(PM.Quantidade), 0),
      MeioPagamento      = 'Baixa com Saldo',
      Linha              = Lin.NmObj,
      UF                 = Loc.SgLoc
  FROM TbRcn Rcn
  JOIN TbRcm Rcm             ON Rcm.CdRcm = Rcn.CdRcm
  JOIN TbTuc Tuc             ON Tuc.CdRcm = Rcm.CdRcm
  JOIN TbRct Rct             ON Rct.CdRct = Rcm.CdRct
  JOIN TbRco Rco             ON Rco.CdRcd = Rct.CdRcd
  JOIN TbRcd Rcd             ON Rcd.CdRcd = Rct.CdRcd
  JOIN TbUne Une             ON Une.CdUne = Rcd.CdUne
  JOIN TbLot LotVen          ON LotVen.CdLot = Rcd.CdLotVen
  JOIN TbObj Obj             ON Obj.CdObj = Rco.CdObj
  JOIN TbObj Mae             ON Mae.CdObj = Obj.CdObjMae
  JOIN TbOes Oes             ON Oes.CdOes = Rcn.CdOes AND Oes.TpOesVal = 21 -- Principal
  JOIN TbCli Cli             ON Cli.CdCli = Rcd.CdCli
  JOIN TbPes Pes             ON Pes.CdPes = Cli.CdPes
  LEFT JOIN TbFpg Fpg        ON Fpg.CdFpg = Rcd.CdFpg
  LEFT JOIN TbFvo Fvo        ON Fvo.CdFvo = Rco.CdFvo
  LEFT JOIN TbVpo Vpo        ON Vpo.CdVpo = Fvo.CdVpo
  LEFT JOIN (
      SELECT
          Vpo.CdVpd,
          Mae.CdObj,
          Valor     = SUM(Vpo.VrVpo),
          ValorLiq  = SUM(VrVpoMerLiq),
          Quantidade= SUM(Vpo.QtVpo)
      FROM TbVpo Vpo
      JOIN TbObj Obj ON Obj.CdObj = Vpo.CdObj
      JOIN TbObj Mae ON Mae.CdObj = Obj.CdObjMae
      GROUP BY Vpo.CdVpd, Mae.CdObj
  ) PM
    ON PM.CdVpd = Vpo.CdVpd
  AND PM.CdObj = Mae.CdObj
  LEFT JOIN TbRcs RcsICMSST   ON RcsICMSST.CdRco = Rco.CdRco AND RcsICMSST.CdOes = 365 -- ICMSST-Valor
  LEFT JOIN TbRcs RcsFrete    ON RcsFrete.CdRco  = Rco.CdRco AND RcsFrete.CdOes  = 57  -- Frete
  JOIN TbObj Lin              ON Lin.CdObj = Obj.CdObjLin
  LEFT JOIN TbArvLoc ArvLoc   ON ArvLoc.CdLocFil = Pes.CdLoc
  JOIN TbLoc Loc              ON Loc.CdLoc = ArvLoc.CdLoc AND Loc.TpLoc = 3 -- UF
  WHERE Tuc.CdRcm IS NOT NULL
    AND Rcd.DtRcdEmi BETWEEN ? AND ?           -- << filtro por EMISSÃO
    AND (0 = 0 OR Rcd.CdlotVen = 0)
    AND (0 = 0 OR Rcd.CdRcd    = 0)
    AND (0 = 0 OR EXISTS (SELECT 1 FROM TbArvCli WHERE CdCliFil = Rcd.CdCli AND CdCli = 0))
  GROUP BY
      Rcm.CdRct,
      LotVen.CdLot,
      LotVen.NmLot,
      Rcd.CdRcd,
      Une.SgUne + '.' + Rcd.NrRcd + '/' + CONVERT(varchar, Rct.NrRctOrd),
      Pes.NmPes,
      Mae.NmObj,
      Rcd.DtRcdEmi,
      Rct.DtRctVen,
      Rcm.DtRcmMov,
      Fpg.QtFpgPrzMed,
      Lin.NmObj,
      Loc.SgLoc
    ORDER BY LotVen.NmLot;

  ------------------------------------------------------------
  -- 5) Resultado final
  ------------------------------------------------------------
  -- FINAL (datas PARAMETRIZADAS)
    SELECT
          ID             = R.Doc,
          VendedorID     = R.CdLot,
          Vendedor       = R.NmLot,
          Titulo         = R.Titulo,
          Cliente        = R.Cliente,
          UF             = R.UF,
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
          [Recebimento]  = R.DataRecebimento
  FROM #Tmp R
  OUTER APPLY (
      SELECT VrVenda = CAST(
                SUM(CAST(Rco.VrRcoBru AS DECIMAL(38,10))) /
                NULLIF(SUM(CAST(Rco.QtRco    AS DECIMAL(38,10))), 0)
            AS DECIMAL(19,4))
      FROM TbRco Rco
      JOIN TbObj Obj ON Obj.CdObj = Rco.CdObj
      JOIN TbObj Mae ON Mae.CdObj = Obj.CdObjMae
      WHERE Rco.CdRcd = R.Doc
        AND Mae.NmObj = R.Artigo
  ) X
  WHERE R.DataRecebimento BETWEEN ? AND ?
    {nm_lot_filter_sql};

    
    """

    params: list = []
    params += [dt_ini, dt_fim]  # #Mch
    params += [dt_ini, dt_fim]  # #Titulos 1
    params += [dt_ini, dt_fim]  # #Titulos 2
    params += [dt_ini, dt_fim]  # Devoluções
    params += [dt_ini, dt_fim]  # Baixa com saldo
    params += [dt_ini, dt_fim]  # Final
    params += nm_lot_params
    return sql, params