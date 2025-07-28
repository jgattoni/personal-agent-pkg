"""
Core package pour l'agent personnel avec Zep Memory et PKG
"""

__version__ = "0.1.0"

# Imports principaux pour faciliter l'usage
try:
    from .protocols.a2a_manager import A2AManager, create_a2a_manager
    from .protocols.mcp_manager import MCPManager, create_mcp_manager
    from .graph.graphiti_engine import GraphitiEngine, create_graphiti_engine
except ImportError:
    # Évite les erreurs d'import si toutes les dépendances ne sont pas installées
    pass

__all__ = [
    "A2AManager",
    "create_a2a_manager", 
    "MCPManager",
    "create_mcp_manager",
    "GraphitiEngine",
    "create_graphiti_engine",
]