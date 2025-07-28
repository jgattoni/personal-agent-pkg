"""
Core package pour l'agent personnel avec Zep Memory et PKG
"""

__version__ = "0.1.0"

# Import depuis le package restructuré
from .personal_agent_core import *

__all__ = [
    "A2AManager",
    "create_a2a_manager", 
    "MCPManager",
    "create_mcp_manager",
    "GraphitiEngine",
    "create_graphiti_engine",
]