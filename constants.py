"""
Constantes do sistema - Usuários, E-mails e Mapeamentos
"""

# ======================= Usuários e perfis =======================
USERS = {
    "admin":   {"pwd": "123456", "role": "admin"},
    "karen":   {"pwd": "159753", "role": "gestora"},        # pode validar/editar % e Valor Comissão
    "jessica": {"pwd": "246810", "role": "controladoria"},  # pode enviar e consolidar (após validado)
}

# ======================= E-mails do Sistema =======================
EMAIL_GESTORA = "thiago.pereira@stik.com.br"
EMAIL_CONTROLADORIA = "thiago.pereira@stik.com.br"
EMAIL_COPIA_COMISSOES = f"{EMAIL_GESTORA}, {EMAIL_CONTROLADORIA}"

# ======================= Vendedores e E-mails =======================
VENDEDOR_EMAIL = {
    "André Ricardo": "thiago.pereira@stik.com.br",
    "Bruno Viana": "bruno.stik@outlook.com",
    "Carlos Pereira": "carlosppeixoto901@gmail.com",
    "Vicente Zepka": "vicentezf@yahoo.com.br",
    "Dijacy Cunha":  "dj.rep@outlook.com",
    "Dionilda Dias": "dionilda.dias@stik.com.br",
    "Eugenio Gomes": "eugeniovendas2005@hotmail.com",
    "Gustavo La Bella": "llb@llb.com.br",
    "Leudo Neto": "leudorep@yahoo.com.br",
    "Luciano Filho": "lucianodecastrof2@gmail.com",
    "Rafael Torquato": "rafael.rep@icloud.com",
    "Reinaldo Honorato": "reinaldo.rep@outlook.com",
    "Rildo Representações": "vieirarildo@gmail.com",
    "Suene Salgado": "suene.salgado@stik.com.br",
    "Gerlanda Alexandre": "gerlanda.stik@hotmail.com",
    "Horrana Félix": "horrana.felix@hotmail.com",
    "Handressa": "handressa.rodrigues@stik.com.br",
    "WJA Representações": "wj-arepresentacoes@hotmail.com",
    "PSI Representações": "escritorio@psirepresentacoes.com",
    "Ponte Vendedora":  "pontevendedora@gmail.com",
    "Motta Sul Representações": "Mottasul@contato.net",
    "Luciano Rezende": "lucianosancris@hotmail.com",
    "GTEX Representações":  "gtex@outlook.com.br"
}

# Versão normalizada (uppercase) para busca case-insensitive
VENDEDOR_EMAIL_NORMALIZADO = {k.strip().upper(): v for k, v in VENDEDOR_EMAIL.items()}

# ======================= Meses em Português =======================
PT_BR_MONTHS = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"
}

# ======================= Configurações de E-mail =======================
SMTP_CONFIG = {
    "host": "smtp.stik.com.br",
    "port": 25,
    "user": "suporte@stik.com.br",
    "password": "Stk@400$",
    "use_tls": False
}