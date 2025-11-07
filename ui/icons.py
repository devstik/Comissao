"""
Sistema de Ícones do Sistema
Ícones Unicode modernos para uso consistente em toda aplicação
"""

class Icons:
    """Biblioteca de ícones Unicode para o sistema"""
    
    # Ações principais
    SEARCH = "🔍"
    ADD = "➕"
    EDIT = "✏️"
    DELETE = "🗑️"
    SAVE = "💾"
    REFRESH = "🔄"
    SEND = "📧"
    EXPORT = "📤"
    DOWNLOAD = "⬇️"
    UPLOAD = "⬆️"
    
    # Navegação
    BACK = "◀️"
    FORWARD = "▶️"
    UP = "⬆️"
    DOWN = "⬇️"
    
    # Status
    SUCCESS = "✅"
    ERROR = "❌"
    WARNING = "⚠️"
    INFO = "ℹ️"
    LOADING = "⏳"
    
    # Documentos
    FILE = "📄"
    PDF = "📑"
    EXCEL = "📊"
    FOLDER = "📁"
    
    # Pessoas
    USER = "👤"
    USERS = "👥"
    
    # Dinheiro
    MONEY = "💰"
    CASH = "💵"
    CHART = "📈"
    
    # Filtros
    FILTER = "🔽"
    CALENDAR = "📅"
    CLOCK = "🕐"
    
    # Comunicação
    EMAIL = "✉️"
    PHONE = "📞"
    
    # Validação
    CHECK = "✓"
    LOCK = "🔒"
    UNLOCK = "🔓"
    
    # Outros
    SETTINGS = "⚙️"
    HELP = "❓"
    STAR = "⭐"
    FLAG = "🚩"
    
    @staticmethod
    def get(name: str, default: str = "") -> str:
        """
        Retorna um ícone pelo nome
        
        Args:
            name: Nome do ícone (ex: "SEARCH", "ADD")
            default: Ícone padrão se não encontrar
        
        Returns:
            String do ícone
        """
        return getattr(Icons, name.upper(), default)


def icon_button_text(icon: str, text: str) -> str:
    """
    Formata texto de botão com ícone
    
    Args:
        icon: Ícone unicode
        text: Texto do botão
    
    Returns:
        String formatada "🔍 Buscar"
    """
    return f"{icon} {text}"