from decimal import Decimal, ROUND_HALF_UP

comissys = '''
396,81
450,51
291,64
520,58
2.011,84
2.082,31
681,97
1.080,00
493,79
1.537,00
1.206,15
2.580,60
2.295,36
1.296,90
1.115,96
510,23
1.588,18
1.246,31
2.666,54
2.371,80
1.340,09
1.647,14
1.630,13
1.274,83
128,13
109,53
205,42
422,95
317,82
2.781,22
4.432,44
8.351,14
3.124,70
4.536,71
3.170,62
2.246,80
616,26
228,71
551,44
4.240,00
254,75
723,31
301,07
1.416,97
518,13
1.250,97
42,33
868,33
448,35
115,99
2.559,34
2.644,56
2.165,70
2.237,81
911,37
347,84
76,78
560
656,81
290,86
292,95
510,86
681,98
510,86
1.363,96
405
129,73
753,13
339,13
468,26
804,48
792,28
2.237,43
2.833,93
555,81
668,16
2.045,93
3.616,55
1.049,87
501,82
3.200,00
'''

topmanager = '''
2165,7
1274,83
1630,13
555,81
2833,93
753,13
2246,8
3170,62
129,73
292,95
616,26
290,86
656,81
301,07
2644,56
2559,34
3124,7
4432,44
4536,71
2781,22
8351,14
723,31
254,75
1647,14
405
560
115,99
448,35
868,33
42,33
317,82
422,95
510,23
1115,96
1588,18
2371,8
1340,09
2666,54
1246,31
493,79
1080
1537
2295,36
1296,9
2580,6
1206,15
4240
1049,866666
501,823333
681,97
3616,55
2082,309999
2011,84
520,58
396,806082
450,508704
291,635214
1363,96
510,86
76,776664
347,843336
2237,429998
681,98
510,86
911,37
468,259351
792,278902
804,482218
339,12953
2045,930001
668,16
518,125
1250,965
551,44
228,71
3200
1416,97
128,13
205,42
109,53
2237,81
'''


def parse_br_list(s):
    out = []
    for line in s.strip().splitlines():
        t = line.strip()
        if not t:
            continue
        # remove thousand separators (dots), replace comma decimal with dot
        t = t.replace('.', '').replace(',', '.')
        try:
            out.append(Decimal(t))
        except Exception as e:
            print('Erro parse:', t, e)
    return out

c_list = parse_br_list(comissys)
t_list = parse_br_list(topmanager)

# Sum methods
sum_comissys = sum(c_list)
# Sum of topmanager raw values, then round final
sum_top_raw = sum(t_list)
sum_top_rounded = sum_top_raw.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

# Sum of Comissys treating values as already rounded (quantize per line then sum)
sum_comissys_perline = sum([x.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) for x in c_list])

print('Sum Comissys (raw sum):', sum_comissys)
print('Sum Comissys (per-line quantize then sum):', sum_comissys_perline)
print('Sum TopManager (raw sum):', sum_top_raw)
print('Sum TopManager (rounded total):', sum_top_rounded)
print('Difference (Comissys_perline - TopManager_rounded):', (sum_comissys_perline - sum_top_rounded))
print('Difference (Comissys_raw - TopManager_rounded):', (sum_comissys - sum_top_rounded))
