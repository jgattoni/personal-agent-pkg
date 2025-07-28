"""
Protocoles de communication pour agents (A2A, MCP, ACP)
"""

from .a2a_manager import A2AManager, create_a2a_manager
from .mcp_manager import MCPManager, create_mcp_manager

__all__ = [
    "A2AManager",
    "create_a2a_manager",
    "MCPManager", 
    "create_mcp_manager",
]