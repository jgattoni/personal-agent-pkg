"""
Claude Code Extension - Commandes slash personnalisées pour l'agent personnel

Fournit des commandes slash intégrées à Claude Code pour interagir avec l'agent personnel:
- /memory: Recherche et gestion mémoire Zep
- /notion: Synchronisation et accès Notion
- /agents: Gestion multi-agents et A2A
- /context: Analyse contexte et PKG
- /pkg: Évolution Personal Knowledge Graph
- /evolve: Apprentissage et amélioration continue
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import os
import sys


class CommandCategory(str, Enum):
    """Catégories de commandes slash"""
    MEMORY = "memory"
    NOTION = "notion" 
    AGENTS = "agents"
    CONTEXT = "context"
    PKG = "pkg"
    SYSTEM = "system"


class CommandScope(str, Enum):
    """Portée des commandes"""
    USER = "user"
    PROJECT = "project"
    GLOBAL = "global"


@dataclass
class SlashCommand:
    """Définition d'une commande slash Claude Code"""
    name: str
    category: CommandCategory
    description: str
    usage: str
    handler: Callable
    scope: CommandScope = CommandScope.USER
    aliases: List[str] = field(default_factory=list)
    requires_agent: bool = True
    requires_auth: bool = False
    examples: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ClaudeCodeExtension:
    """
    Extension Claude Code pour agent personnel
    
    Intègre les fonctionnalités de l'agent personnel directement dans Claude Code
    via des commandes slash personnalisées et une interface unifiée.
    """
    
    def __init__(
        self,
        agent=None,
        memory_engine=None,
        notion_bridge=None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialise l'extension Claude Code
        
        Args:
            agent: Instance BasePersonalAgent
            memory_engine: Moteur mémoire Zep
            notion_bridge: Bridge Notion-Zep
            config: Configuration extension
        """
        self.agent = agent
        self.memory_engine = memory_engine
        self.notion_bridge = notion_bridge
        self.config = config or {}
        self.logger = logging.getLogger("claude_extension")
        
        # État extension
        self.is_initialized = False
        self.commands: Dict[str, SlashCommand] = {}
        self.command_history: List[Dict[str, Any]] = []
        
        # Configuration
        self.enable_history = self.config.get("enable_history", True)
        self.max_history = self.config.get("max_history", 100)
        self.auto_sync = self.config.get("auto_sync", True)
        
        # Registre des handlers
        self._register_core_commands()
    
    def _register_core_commands(self) -> None:
        """Enregistre les commandes slash core"""
        
        # === COMMANDES MEMORY ===
        self.register_command(SlashCommand(
            name="memory",
            category=CommandCategory.MEMORY,
            description="Recherche dans la mémoire Zep",
            usage="/memory <query> [--limit=10] [--type=all]",
            handler=self._handle_memory_search,
            examples=[
                "/memory python projet",
                "/memory --type=preference --limit=5",
                "/memory \"réunion équipe\" --recent"
            ]
        ))
        
        self.register_command(SlashCommand(
            name="memory-add",
            category=CommandCategory.MEMORY,
            description="Ajoute une mémoire manuellement",
            usage="/memory-add <content> [--type=semantic] [--importance=medium]",
            handler=self._handle_memory_add,
            aliases=["mem-add", "remember"],
            examples=[
                "/memory-add \"J'aime le café le matin\" --type=preference",
                "/remember \"Réunion project X le vendredi\" --type=episodic"
            ]
        ))
        
        self.register_command(SlashCommand(
            name="memory-stats",
            category=CommandCategory.MEMORY,
            description="Statistiques mémoire et clusters",
            usage="/memory-stats [--detailed]",
            handler=self._handle_memory_stats,
            aliases=["mem-stats"]
        ))
        
        # === COMMANDES NOTION ===
        self.register_command(SlashCommand(
            name="notion",
            category=CommandCategory.NOTION,
            description="Synchronisation Notion → Zep",
            usage="/notion [sync|search|stats] [options]",
            handler=self._handle_notion,
            examples=[
                "/notion sync --full",
                "/notion search \"projet agent\"",
                "/notion stats --detailed"
            ]
        ))
        
        self.register_command(SlashCommand(
            name="notion-sync",
            category=CommandCategory.NOTION,
            description="Force une sync Notion complète",
            usage="/notion-sync [--full] [--pages=id1,id2]",
            handler=self._handle_notion_sync,
            aliases=["nsync"]
        ))
        
        # === COMMANDES AGENTS ===
        self.register_command(SlashCommand(
            name="agents",
            category=CommandCategory.AGENTS,
            description="Gestion multi-agents et A2A",
            usage="/agents [list|discover|status|delegate] [options]",
            handler=self._handle_agents,
            examples=[
                "/agents list",
                "/agents discover --network", 
                "/agents delegate task-id --to=agent-url"
            ]
        ))
        
        self.register_command(SlashCommand(
            name="agent-status",
            category=CommandCategory.AGENTS,
            description="Statut de l'agent personnel",
            usage="/agent-status [--detailed]",
            handler=self._handle_agent_status,
            aliases=["status", "health"]
        ))
        
        # === COMMANDES CONTEXT ===
        self.register_command(SlashCommand(
            name="context",
            category=CommandCategory.CONTEXT,
            description="Analyse contexte et PKG",
            usage="/context [analyze|graph|timeline] [query]",
            handler=self._handle_context,
            examples=[
                "/context analyze \"projet python\"",
                "/context graph --entities=person,project",
                "/context timeline --days=30"
            ]
        ))
        
        # === COMMANDES PKG ===
        self.register_command(SlashCommand(
            name="pkg",
            category=CommandCategory.PKG,
            description="Personal Knowledge Graph evolution",
            usage="/pkg [evolve|export|import|merge] [options]",
            handler=self._handle_pkg,
            examples=[
                "/pkg evolve --auto",
                "/pkg export --format=json --file=backup.json",
                "/pkg merge --source=external.json"
            ]
        ))
        
        # === COMMANDES SYSTEM ===
        self.register_command(SlashCommand(
            name="evolve",
            category=CommandCategory.SYSTEM,
            description="Apprentissage et amélioration agent",
            usage="/evolve [learn|adapt|feedback] [options]",
            handler=self._handle_evolve,
            examples=[
                "/evolve learn --from=conversation",
                "/evolve adapt --preferences",
                "/evolve feedback \"La réponse était parfaite\""
            ]
        ))
    
    def register_command(self, command: SlashCommand) -> None:
        """Enregistre une nouvelle commande slash"""
        self.commands[command.name] = command
        
        # Enregistrer les alias
        for alias in command.aliases:
            self.commands[alias] = command
        
        self.logger.debug(f"Registered command: /{command.name} ({command.category.value})")
    
    async def initialize(self) -> bool:
        """Initialise l'extension"""
        try:
            self.logger.info("Initializing Claude Code extension...")
            
            # Vérification des dépendances
            if not self.agent:
                self.logger.warning("No agent provided - some commands will be limited")
            
            if not self.memory_engine:
                self.logger.warning("No memory engine - memory commands disabled")
            
            if not self.notion_bridge:
                self.logger.warning("No Notion bridge - Notion commands disabled")
            
            # Configuration Claude Code
            await self._setup_claude_config()
            
            self.is_initialized = True
            self.logger.info(f"Claude Code extension initialized with {len(set(self.commands.keys()))} unique commands")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize extension: {str(e)}")
            return False
    
    async def _setup_claude_config(self) -> None:
        """Configure Claude Code avec les commandes slash"""
        config_dir = ".claude"
        config_file = os.path.join(config_dir, "agent-config.json")
        
        # Création répertoire config si nécessaire
        os.makedirs(config_dir, exist_ok=True)
        
        # Configuration Claude Code
        claude_config = {
            "name": "Personal Agent Extension",
            "version": "1.0.0",
            "description": "Agent personnel avec mémoire Zep et sync Notion",
            "commands": {},
            "settings": {
                "auto_sync_notion": self.auto_sync,
                "memory_cache_size": self.config.get("memory_cache_size", 1000),
                "enable_a2a_discovery": self.config.get("enable_a2a", True),
                "default_memory_type": "semantic",
                "response_language": "auto"
            },
            "integrations": {
                "zep_memory": {
                    "enabled": self.memory_engine is not None,
                    "auto_consolidate": True
                },
                "notion_sync": {
                    "enabled": self.notion_bridge is not None,
                    "sync_interval_hours": 24,
                    "auto_extract_entities": True
                },
                "a2a_protocol": {
                    "enabled": self.agent and hasattr(self.agent, 'a2a_manager'),
                    "discovery_enabled": True,
                    "agent_card_url": "/.well-known/agent-card"
                }
            }
        }
        
        # Ajout des commandes
        unique_commands = {}
        for cmd_name, command in self.commands.items():
            if command.name not in unique_commands:  # Éviter doublons avec alias
                unique_commands[command.name] = {
                    "name": command.name,
                    "category": command.category.value,
                    "description": command.description,
                    "usage": command.usage,
                    "scope": command.scope.value,
                    "aliases": command.aliases,
                    "examples": command.examples,
                    "requires_agent": command.requires_agent,
                    "requires_auth": command.requires_auth
                }
        
        claude_config["commands"] = unique_commands
        
        # Sauvegarde config
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(claude_config, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Claude config saved to {config_file}")
    
    async def execute_command(self, command_line: str) -> Dict[str, Any]:
        """
        Exécute une commande slash
        
        Args:
            command_line: Commande complète (ex: "/memory python --limit=5")
            
        Returns:
            Résultat de la commande avec status, content, etc.
        """
        start_time = datetime.now()
        
        try:
            # Parse de la commande
            parts = command_line.strip().split()
            if not parts or not parts[0].startswith('/'):
                return {
                    "status": "error",
                    "message": "Invalid command format. Commands must start with '/'",
                    "timestamp": start_time.isoformat()
                }
            
            cmd_name = parts[0][1:]  # Retirer le '/'
            args = parts[1:] if len(parts) > 1 else []
            
            # Recherche commande
            if cmd_name not in self.commands:
                return {
                    "status": "error",
                    "message": f"Unknown command: /{cmd_name}. Use /help for available commands.",
                    "available_commands": list(set(cmd.name for cmd in self.commands.values())),
                    "timestamp": start_time.isoformat()
                }
            
            command = self.commands[cmd_name]
            
            # Vérifications prérequis
            if command.requires_agent and not self.agent:
                return {
                    "status": "error",
                    "message": f"Command /{cmd_name} requires an active agent",
                    "timestamp": start_time.isoformat()
                }
            
            # Exécution
            self.logger.info(f"Executing command: /{cmd_name} {' '.join(args)}")
            result = await command.handler(args)
            
            # Ajout métadonnées
            result.update({
                "command": cmd_name,
                "execution_time": (datetime.now() - start_time).total_seconds(),
                "timestamp": start_time.isoformat()
            })
            
            # Historique
            if self.enable_history:
                self.command_history.append({
                    "command": command_line,
                    "result": result,
                    "timestamp": start_time.isoformat()
                })
                
                # Limite historique
                if len(self.command_history) > self.max_history:
                    self.command_history = self.command_history[-self.max_history:]
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error executing command {command_line}: {str(e)}")
            return {
                "status": "error",
                "message": f"Command execution failed: {str(e)}",
                "execution_time": (datetime.now() - start_time).total_seconds(),
                "timestamp": start_time.isoformat()
            }
    
    # === HANDLERS COMMANDES ===
    
    async def _handle_memory_search(self, args: List[str]) -> Dict[str, Any]:
        """Handler pour /memory"""
        if not self.memory_engine:
            return {"status": "error", "message": "Memory engine not available"}
        
        # Parse arguments
        query = ""
        limit = 10
        memory_type = "all"
        recent = False
        
        i = 0
        while i < len(args):
            arg = args[i]
            if arg.startswith("--limit="):
                limit = int(arg.split("=")[1])
            elif arg.startswith("--type="):
                memory_type = arg.split("=")[1]
            elif arg == "--recent":
                recent = True
            else:
                query += arg + " "
            i += 1
        
        query = query.strip()
        if not query:
            return {"status": "error", "message": "Query required. Usage: /memory <query>"}
        
        try:
            # Recherche mémoires
            results = await self.memory_engine.search_memories(query, limit=limit)
            
            # Formatage résultats
            memories = []
            for result in results:
                memories.append({
                    "id": result.memory_id[:8],
                    "content": result.content[:100] + "..." if len(result.content) > 100 else result.content,
                    "type": result.context.memory_type.value if hasattr(result, 'context') else "unknown",
                    "importance": result.context.importance.value if hasattr(result, 'context') else "medium",
                    "timestamp": result.context.timestamp.isoformat() if hasattr(result, 'context') else None
                })
            
            return {
                "status": "success",
                "query": query,
                "results_count": len(memories),
                "memories": memories,
                "message": f"Found {len(memories)} memories matching '{query}'"
            }
            
        except Exception as e:
            return {"status": "error", "message": f"Memory search failed: {str(e)}"}
    
    async def _handle_memory_add(self, args: List[str]) -> Dict[str, Any]:
        """Handler pour /memory-add"""
        if not self.memory_engine:
            return {"status": "error", "message": "Memory engine not available"}
        
        # Parse arguments
        content = ""
        memory_type = "semantic"
        importance = "medium"
        
        i = 0
        while i < len(args):
            arg = args[i]
            if arg.startswith("--type="):
                memory_type = arg.split("=")[1]
            elif arg.startswith("--importance="):
                importance = arg.split("=")[1]
            else:
                content += arg + " "
            i += 1
        
        content = content.strip()
        if not content:
            return {"status": "error", "message": "Content required. Usage: /memory-add <content>"}
        
        try:
            from ...core.personal_agent_core.memory.zep_engine import MemoryType, MemoryImportance
            
            # Conversion types
            mem_type = getattr(MemoryType, memory_type.upper(), MemoryType.SEMANTIC)
            mem_importance = getattr(MemoryImportance, importance.upper(), MemoryImportance.MEDIUM)
            
            # Ajout mémoire
            memory = await self.memory_engine.add_memory(
                content=content,
                memory_type=mem_type,
                importance=mem_importance,
                metadata={"source": "claude_code_extension", "manual": True}
            )
            
            return {
                "status": "success",
                "memory_id": memory.memory_id[:8],
                "content": content,
                "type": memory_type,
                "importance": importance,
                "message": f"Memory added successfully (ID: {memory.memory_id[:8]})"
            }
            
        except Exception as e:
            return {"status": "error", "message": f"Failed to add memory: {str(e)}"}
    
    async def _handle_memory_stats(self, args: List[str]) -> Dict[str, Any]:
        """Handler pour /memory-stats"""
        if not self.memory_engine:
            return {"status": "error", "message": "Memory engine not available"}
        
        detailed = "--detailed" in args
        
        try:
            stats = self.memory_engine.get_stats()
            
            result = {
                "status": "success",
                "stats": stats,
                "message": f"Memory engine contains {stats.get('total_memories', 0)} memories in {stats.get('total_clusters', 0)} clusters"
            }
            
            if detailed:
                # Stats détaillées par type
                type_stats = {}
                for memory in self.memory_engine.memory_cache.values():
                    mem_type = memory.context.memory_type.value if hasattr(memory, 'context') else 'unknown'
                    type_stats[mem_type] = type_stats.get(mem_type, 0) + 1
                
                result["type_distribution"] = type_stats
                
                # Top clusters
                clusters = []
                for cluster_id, cluster in self.memory_engine.cluster_cache.items():
                    clusters.append({
                        "id": cluster_id[:8],
                        "keywords": cluster.keywords[:5],  # Top 5
                        "memories_count": len(cluster.memory_ids),
                        "theme": cluster.theme
                    })
                
                result["top_clusters"] = sorted(clusters, key=lambda x: x["memories_count"], reverse=True)[:10]
            
            return result
            
        except Exception as e:
            return {"status": "error", "message": f"Failed to get memory stats: {str(e)}"}
    
    async def _handle_notion_sync(self, args: List[str]) -> Dict[str, Any]:
        """Handler pour /notion-sync"""
        if not self.notion_bridge:
            return {"status": "error", "message": "Notion bridge not available"}
        
        force_full = "--full" in args
        specific_pages = None
        
        # Parse page IDs
        for arg in args:
            if arg.startswith("--pages="):
                specific_pages = arg.split("=")[1].split(",")
        
        try:
            # Lancement sync
            result = await self.notion_bridge.sync_notion_to_zep(
                page_ids=specific_pages,
                force_full_sync=force_full
            )
            
            return {
                "status": "success",
                "sync_status": result.status.value,
                "pages_processed": result.pages_processed,
                "entities_extracted": result.entities_extracted,
                "memories_created": result.memories_created,
                "duration": f"{result.duration_seconds:.1f}s",
                "errors": result.errors,
                "message": f"Sync completed: {result.pages_processed} pages processed, {result.memories_created} memories created"
            }
            
        except Exception as e:
            return {"status": "error", "message": f"Notion sync failed: {str(e)}"}
    
    async def _handle_notion(self, args: List[str]) -> Dict[str, Any]:
        """Handler pour /notion"""
        if not args:
            return await self._handle_notion_sync([])
        
        subcommand = args[0]
        
        if subcommand == "sync":
            return await self._handle_notion_sync(args[1:])
        elif subcommand == "search":
            return await self._handle_notion_search(args[1:])
        elif subcommand == "stats":
            return await self._handle_notion_stats(args[1:])
        else:
            return {"status": "error", "message": f"Unknown notion subcommand: {subcommand}"}
    
    async def _handle_notion_search(self, args: List[str]) -> Dict[str, Any]:
        """Handler pour notion search"""
        if not self.notion_bridge:
            return {"status": "error", "message": "Notion bridge not available"}
        
        query = " ".join(args)
        if not query:
            return {"status": "error", "message": "Search query required"}
        
        try:
            results = await self.notion_bridge.search_notion_content(query, limit=10)
            
            pages = []
            for page in results:
                pages.append({
                    "id": page.page_id[:8],
                    "title": page.title,
                    "type": page.page_type.value,
                    "content_preview": page.content[:100] + "..." if len(page.content) > 100 else page.content,
                    "url": page.url,
                    "last_edited": page.last_edited.strftime("%Y-%m-%d %H:%M")
                })
            
            return {
                "status": "success",
                "query": query,
                "results_count": len(pages),
                "pages": pages,
                "message": f"Found {len(pages)} Notion pages matching '{query}'"
            }
            
        except Exception as e:
            return {"status": "error", "message": f"Notion search failed: {str(e)}"}
    
    async def _handle_notion_stats(self, args: List[str]) -> Dict[str, Any]:
        """Handler pour notion stats"""
        if not self.notion_bridge:
            return {"status": "error", "message": "Notion bridge not available"}
        
        try:
            stats = self.notion_bridge.get_sync_stats()
            
            return {
                "status": "success",
                "stats": stats,
                "message": f"Notion bridge: {stats['pages_synced']} pages synced, {stats['total_syncs']} syncs completed"
            }
            
        except Exception as e:
            return {"status": "error", "message": f"Failed to get Notion stats: {str(e)}"}
    
    async def _handle_agents(self, args: List[str]) -> Dict[str, Any]:
        """Handler pour /agents"""
        if not self.agent:
            return {"status": "error", "message": "Agent not available"}
        
        if not args:
            subcommand = "list"
        else:
            subcommand = args[0]
        
        if subcommand == "list":
            return await self._handle_agents_list(args[1:])
        elif subcommand == "status":
            return await self._handle_agent_status(args[1:])
        elif subcommand == "discover":
            return await self._handle_agents_discover(args[1:])
        else:
            return {"status": "error", "message": f"Unknown agents subcommand: {subcommand}"}
    
    async def _handle_agents_list(self, args: List[str]) -> Dict[str, Any]:
        """Liste des agents disponibles"""
        agents = [{
            "name": "Personal Agent",
            "type": "local",
            "status": self.agent.state.value if self.agent else "unknown",
            "capabilities": [c.value for c in self.agent.context.capabilities] if self.agent else [],
            "url": "local://personal-agent"
        }]
        
        # Agents A2A si disponible
        if hasattr(self.agent, 'a2a_manager') and self.agent.a2a_manager:
            try:
                discovered = await self.agent.a2a_manager.discover_agents()
                for agent_info in discovered:
                    agents.append({
                        "name": agent_info.get("name", "Unknown"),
                        "type": "remote",
                        "status": "available",
                        "capabilities": agent_info.get("capabilities", []),
                        "url": agent_info.get("url", "")
                    })
            except:
                pass
        
        return {
            "status": "success",
            "agents": agents,
            "count": len(agents),
            "message": f"Found {len(agents)} agents"
        }
    
    async def _handle_agents_discover(self, args: List[str]) -> Dict[str, Any]:
        """Découverte agents A2A"""
        if not self.agent or not hasattr(self.agent, 'a2a_manager') or not self.agent.a2a_manager:
            return {"status": "error", "message": "A2A manager not available"}
        
        try:
            discovered = await self.agent.a2a_manager.discover_agents()
            
            return {
                "status": "success",
                "discovered": discovered,
                "count": len(discovered),
                "message": f"Discovered {len(discovered)} remote agents"
            }
            
        except Exception as e:
            return {"status": "error", "message": f"Agent discovery failed: {str(e)}"}
    
    async def _handle_agent_status(self, args: List[str]) -> Dict[str, Any]:
        """Handler pour /agent-status"""
        if not self.agent:
            return {"status": "error", "message": "Agent not available"}
        
        detailed = "--detailed" in args
        
        try:
            health = await self.agent.health_check()
            stats = await self.agent.get_stats()
            
            result = {
                "status": "success",
                "agent_status": self.agent.state.value,
                "health": health,
                "stats": stats,
                "message": f"Agent is {self.agent.state.value}"
            }
            
            if detailed:
                result.update({
                    "capabilities": [c.value for c in self.agent.context.capabilities],
                    "integrations": {
                        "memory_engine": self.memory_engine is not None,
                        "notion_bridge": self.notion_bridge is not None,
                        "a2a_enabled": hasattr(self.agent, 'a2a_manager') and self.agent.a2a_manager is not None,
                        "mcp_enabled": hasattr(self.agent, 'mcp_manager') and self.agent.mcp_manager is not None,
                        "graphiti_enabled": hasattr(self.agent, 'graphiti_engine') and self.agent.graphiti_engine is not None
                    },
                    "uptime": stats.get("uptime_seconds", 0),
                    "memory_usage": stats.get("memory_usage", "unknown")
                })
            
            return result
            
        except Exception as e:
            return {"status": "error", "message": f"Failed to get agent status: {str(e)}"}
    
    async def _handle_context(self, args: List[str]) -> Dict[str, Any]:
        """Handler pour /context"""
        if not self.memory_engine and not self.notion_bridge:
            return {"status": "error", "message": "No context sources available"}
        
        subcommand = args[0] if args else "analyze"
        
        if subcommand == "analyze":
            return await self._handle_context_analyze(args[1:])
        elif subcommand == "graph":
            return await self._handle_context_graph(args[1:])
        elif subcommand == "timeline":
            return await self._handle_context_timeline(args[1:])
        else:
            return {"status": "error", "message": f"Unknown context subcommand: {subcommand}"}
    
    async def _handle_context_analyze(self, args: List[str]) -> Dict[str, Any]:
        """Analyse contextuelle"""
        query = " ".join(args) if args else ""
        
        context = {
            "memories": [],
            "notion_pages": [],
            "entities": [],
            "themes": []
        }
        
        try:
            # Recherche mémoires
            if self.memory_engine and query:
                memories = await self.memory_engine.search_memories(query, limit=5)
                for memory in memories:
                    context["memories"].append({
                        "content": memory.content[:100] + "...",
                        "type": memory.context.memory_type.value if hasattr(memory, 'context') else 'unknown'
                    })
            
            # Recherche Notion
            if self.notion_bridge and query:
                pages = await self.notion_bridge.search_notion_content(query, limit=3)
                for page in pages:
                    context["notion_pages"].append({
                        "title": page.title,
                        "type": page.page_type.value,
                        "preview": page.content[:100] + "..."
                    })
            
            return {
                "status": "success",
                "query": query,
                "context": context,
                "message": f"Context analysis for '{query}'" if query else "Current context overview"
            }
            
        except Exception as e:
            return {"status": "error", "message": f"Context analysis failed: {str(e)}"}
    
    async def _handle_context_graph(self, args: List[str]) -> Dict[str, Any]:
        """Analyse graphe de connaissances"""
        # Placeholder - nécessite GraphitiEngine
        return {
            "status": "info", 
            "message": "Knowledge graph analysis not yet implemented",
            "todo": "Implement with GraphitiEngine integration"
        }
    
    async def _handle_context_timeline(self, args: List[str]) -> Dict[str, Any]:
        """Timeline contextuelle"""
        days = 7
        for arg in args:
            if arg.startswith("--days="):
                days = int(arg.split("=")[1])
        
        # Placeholder - nécessite analyse temporelle
        return {
            "status": "info",
            "message": f"Timeline analysis for last {days} days not yet implemented",
            "todo": "Implement temporal memory analysis"
        }
    
    async def _handle_pkg(self, args: List[str]) -> Dict[str, Any]:
        """Handler pour /pkg"""
        subcommand = args[0] if args else "status"
        
        return {
            "status": "info",
            "message": f"PKG {subcommand} not yet implemented",
            "todo": "Implement Personal Knowledge Graph evolution features"
        }
    
    async def _handle_evolve(self, args: List[str]) -> Dict[str, Any]:
        """Handler pour /evolve"""
        subcommand = args[0] if args else "status"
        
        return {
            "status": "info",
            "message": f"Evolution {subcommand} not yet implemented", 
            "todo": "Implement agent learning and adaptation features"
        }
    
    def get_command_help(self, command_name: str = None) -> Dict[str, Any]:
        """Obtient l'aide pour une commande ou toutes les commandes"""
        if command_name:
            if command_name not in self.commands:
                return {"status": "error", "message": f"Unknown command: {command_name}"}
            
            cmd = self.commands[command_name]
            return {
                "status": "success",
                "command": {
                    "name": cmd.name,
                    "category": cmd.category.value,
                    "description": cmd.description,
                    "usage": cmd.usage,
                    "aliases": cmd.aliases,
                    "examples": cmd.examples
                }
            }
        
        # Aide générale
        commands_by_category = {}
        unique_commands = {}
        
        # Éviter doublons avec alias
        for cmd_name, command in self.commands.items():
            if command.name not in unique_commands:
                unique_commands[command.name] = command
                category = command.category.value
                if category not in commands_by_category:
                    commands_by_category[category] = []
                commands_by_category[category].append({
                    "name": command.name,
                    "description": command.description,
                    "usage": command.usage
                })
        
        return {
            "status": "success",
            "categories": commands_by_category,
            "total_commands": len(unique_commands),
            "message": f"Available commands in {len(commands_by_category)} categories"
        }


# Factory function
async def create_claude_extension(
    agent=None,
    memory_engine=None, 
    notion_bridge=None,
    config: Optional[Dict[str, Any]] = None
) -> ClaudeCodeExtension:
    """
    Factory pour créer et initialiser l'extension Claude Code
    
    Args:
        agent: BasePersonalAgent instance
        memory_engine: ZepPersonalMemoryEngine instance
        notion_bridge: NotionZepBridge instance
        config: Configuration extension
        
    Returns:
        Extension Claude Code initialisée
    """
    extension = ClaudeCodeExtension(
        agent=agent,
        memory_engine=memory_engine,
        notion_bridge=notion_bridge,
        config=config or {}
    )
    
    await extension.initialize()
    
    return extension