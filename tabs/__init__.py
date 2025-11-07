# =====================================================
# ARQUIVO 2: tabs/__init__.py
# =====================================================
"""
Pacote das abas do sistema
Exporta as 3 abas principais
"""

from .tab_consulta import TabConsulta
from .tab_extrato import TabExtrato
from .tab_consolidados import TabConsolidados

__all__ = [
    "TabConsulta",
    "TabExtrato",
    "TabConsolidados"
]
