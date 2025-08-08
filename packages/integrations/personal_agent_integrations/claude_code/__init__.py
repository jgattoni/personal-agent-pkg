"""
Claude Code Integration Package

Extension pour Claude Code avec commandes slash personnalisées
"""

from .extension import ClaudeCodeExtension, SlashCommand, create_claude_extension

__all__ = ['ClaudeCodeExtension', 'SlashCommand', 'create_claude_extension']