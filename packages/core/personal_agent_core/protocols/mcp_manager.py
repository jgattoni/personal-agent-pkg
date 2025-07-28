"""
Model Context Protocol Manager avec serveurs officiels MCP 2025
"""

import asyncio
import json
import logging
import subprocess
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
import aiohttp
from pydantic import BaseModel, Field


class MCPServer(BaseModel):
    """Configuration d'un serveur MCP"""
    name: str = Field(..., description="Nom du serveur MCP")
    command: str = Field(..., description="Commande d'exécution")
    args: List[str] = Field(default_factory=list, description="Arguments")
    env: Optional[Dict[str, str]] = Field(default_factory=dict, description="Variables d'environnement")
    capabilities: List[str] = Field(default_factory=list, description="Capabilities du serveur")
    status: str = Field(default="stopped", description="Status du serveur")
    process: Optional[Any] = Field(None, exclude=True, description="Process handle")


class MCPTool(BaseModel):
    """Outil MCP disponible"""
    name: str = Field(..., description="Nom de l'outil")
    description: str = Field(..., description="Description de l'outil")
    input_schema: Dict[str, Any] = Field(..., description="Schema d'entrée JSON")
    server: str = Field(..., description="Serveur MCP source")


class MCPManager:
    """
    Manager pour serveurs MCP avec intégration serveurs officiels
    Supporte Cloudflare, Notion, Git, Filesystem et custom servers
    """
    
    def __init__(self, config_dir: str = ".claude"):
        self.config_dir = Path(config_dir)
        self.logger = logging.getLogger("mcp_manager")
        self.servers: Dict[str, MCPServer] = {}
        self.available_tools: Dict[str, MCPTool] = {}
        self.session = None
        
        # Configuration serveurs MCP officiels selon recherche
        self.official_servers = {
            "filesystem": {
                "name": "filesystem",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "/Users/julien"],
                "capabilities": ["read_file", "write_file", "list_directory", "search_files"],
                "description": "Accès filesystem local sécurisé"
            },
            "git": {
                "name": "git",
                "command": "npx", 
                "args": ["-y", "@modelcontextprotocol/server-git", "--repository", "."],
                "capabilities": ["git_log", "git_diff", "git_show", "git_status"],
                "description": "Opérations Git avancées"
            },
            "cloudflare": {
                "name": "cloudflare",
                "command": "npx",
                "args": ["-y", "@cloudflare/mcp-server-cloudflare"],
                "env": {"CLOUDFLARE_API_TOKEN": ""},
                "capabilities": ["dns_records", "workers_management", "analytics", "purge_cache"],
                "description": "Gestion infrastructure Cloudflare"
            },
            "notion": {
                "name": "notion", 
                "command": "python",
                "args": ["-m", "notion_mcp_server"],
                "env": {"NOTION_TOKEN": ""},
                "capabilities": ["search_pages", "create_page", "update_page", "query_database"],
                "description": "Intégration Notion complète"
            }
        }
    
    async def initialize(self) -> bool:
        """Initialisation du manager MCP"""
        try:
            # Création du répertoire de configuration
            self.config_dir.mkdir(exist_ok=True)
            
            # Initialisation session HTTP
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
            
            # Configuration des serveurs officiels
            await self._setup_official_servers()
            
            # Chargement de la configuration utilisateur
            await self._load_user_config()
            
            self.logger.info("MCP Manager initialized with official servers")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize MCP Manager: {str(e)}")
            return False
    
    async def _setup_official_servers(self) -> None:
        """Configuration des serveurs MCP officiels"""
        for server_id, config in self.official_servers.items():
            server = MCPServer(
                name=config["name"],
                command=config["command"],
                args=config["args"],
                env=config.get("env", {}),
                capabilities=config["capabilities"]
            )
            
            self.servers[server_id] = server
            self.logger.info(f"Configured official MCP server: {server_id}")
    
    async def _load_user_config(self) -> None:
        """Chargement configuration utilisateur depuis .claude/mcp_servers.json"""
        config_file = self.config_dir / "mcp_servers.json"
        
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    user_config = json.load(f)
                
                for server_id, config in user_config.get("servers", {}).items():
                    if server_id not in self.servers:
                        server = MCPServer(**config)
                        self.servers[server_id] = server
                        self.logger.info(f"Loaded user MCP server: {server_id}")
                        
            except Exception as e:
                self.logger.error(f"Error loading user MCP config: {str(e)}")
        else:
            # Création du fichier de configuration par défaut
            await self._create_default_config()
    
    async def _create_default_config(self) -> None:
        """Création configuration MCP par défaut"""
        default_config = {
            "mcpServers": {
                "filesystem": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/Users/julien"],
                    "capabilities": ["read_file", "write_file", "list_directory"]
                },
                "git": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-git", "--repository", "."],
                    "capabilities": ["git_log", "git_diff", "git_show"]
                }
            }
        }
        
        config_file = self.config_dir / "mcp_servers.json"
        with open(config_file, 'w') as f:
            json.dump(default_config, f, indent=2)
        
        self.logger.info("Created default MCP configuration")
    
    async def start_server(self, server_id: str) -> bool:
        """Démarrage d'un serveur MCP"""
        if server_id not in self.servers:
            self.logger.error(f"MCP server {server_id} not found")
            return False
        
        server = self.servers[server_id]
        
        if server.status == "running":
            self.logger.info(f"MCP server {server_id} already running")
            return True
        
        try:
            # Préparation des variables d'environnement
            env = dict(os.environ)
            env.update(server.env)
            
            # Démarrage du process
            process = await asyncio.create_subprocess_exec(
                server.command,
                *server.args,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.PIPE
            )
            
            server.process = process
            server.status = "running"
            
            # Discovery des outils disponibles
            await self._discover_server_tools(server_id)
            
            self.logger.info(f"Started MCP server: {server_id}")
            return True
            
        except Exception as e:
            server.status = "failed"
            self.logger.error(f"Failed to start MCP server {server_id}: {str(e)}")
            return False
    
    async def stop_server(self, server_id: str) -> bool:
        """Arrêt d'un serveur MCP"""
        if server_id not in self.servers:
            return False
        
        server = self.servers[server_id]
        
        if server.process and server.status == "running":
            try:
                server.process.terminate()
                await server.process.wait()
                server.process = None
                server.status = "stopped"
                
                # Nettoyage des outils de ce serveur
                tools_to_remove = [
                    tool_name for tool_name, tool in self.available_tools.items()
                    if tool.server == server_id
                ]
                for tool_name in tools_to_remove:
                    del self.available_tools[tool_name]
                
                self.logger.info(f"Stopped MCP server: {server_id}")
                return True
                
            except Exception as e:
                self.logger.error(f"Error stopping MCP server {server_id}: {str(e)}")
                return False
        
        return True
    
    async def _discover_server_tools(self, server_id: str) -> None:
        """Discovery des outils disponibles sur un serveur MCP"""
        try:
            server = self.servers[server_id]
            
            # Simulation de la discovery - en production, utiliser le protocole MCP
            for capability in server.capabilities:
                tool = MCPTool(
                    name=f"{server_id}_{capability}",
                    description=f"{capability} via {server_id} MCP server",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "input": {"type": "string", "description": "Input parameter"}
                        },
                        "required": ["input"]
                    },
                    server=server_id
                )
                
                self.available_tools[tool.name] = tool
            
            self.logger.info(f"Discovered {len(server.capabilities)} tools for {server_id}")
            
        except Exception as e:
            self.logger.error(f"Error discovering tools for {server_id}: {str(e)}")
    
    async def execute_tool(
        self, 
        tool_name: str, 
        parameters: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Exécution d'un outil MCP"""
        if tool_name not in self.available_tools:
            self.logger.error(f"Tool {tool_name} not available")
            return None
        
        tool = self.available_tools[tool_name]
        server = self.servers[tool.server]
        
        if server.status != "running":
            self.logger.error(f"Server {tool.server} not running")
            return None
        
        try:
            # Construction de la requête MCP
            request = {
                "jsonrpc": "2.0",
                "id": f"req_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "method": "tools/call",
                "params": {
                    "name": tool_name.replace(f"{tool.server}_", ""),
                    "arguments": parameters
                }
            }
            
            # Envoi via stdin du process (simulation)
            if server.process and server.process.stdin:
                request_json = json.dumps(request) + "\n"
                server.process.stdin.write(request_json.encode())
                await server.process.stdin.drain()
                
                # Lecture de la réponse (simulation)
                # En production, implémenter le parsing JSON-RPC complet
                
                return {
                    "success": True,
                    "result": f"Executed {tool_name} with parameters: {parameters}",
                    "tool": tool_name,
                    "server": tool.server
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error executing tool {tool_name}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def list_available_tools(self) -> Dict[str, Dict[str, Any]]:
        """Liste des outils MCP disponibles"""
        tools_info = {}
        
        for tool_name, tool in self.available_tools.items():
            server = self.servers[tool.server]
            tools_info[tool_name] = {
                "name": tool.name,
                "description": tool.description,
                "server": tool.server,
                "server_status": server.status,
                "capabilities": server.capabilities
            }
        
        return tools_info
    
    async def get_server_status(self) -> Dict[str, Dict[str, Any]]:
        """Status de tous les serveurs MCP"""
        status = {}
        
        for server_id, server in self.servers.items():
            status[server_id] = {
                "name": server.name,
                "status": server.status,
                "capabilities": server.capabilities,
                "tools_count": len([
                    t for t in self.available_tools.values() 
                    if t.server == server_id
                ])
            }
        
        return status
    
    async def start_essential_servers(self) -> Dict[str, bool]:
        """Démarrage des serveurs MCP essentiels"""
        essential_servers = ["filesystem", "git"]
        results = {}
        
        for server_id in essential_servers:
            if server_id in self.servers:
                results[server_id] = await self.start_server(server_id)
            else:
                results[server_id] = False
        
        return results
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check du manager MCP"""
        running_servers = sum(1 for s in self.servers.values() if s.status == "running")
        
        return {
            "status": "healthy",
            "servers_configured": len(self.servers),
            "servers_running": running_servers,
            "tools_available": len(self.available_tools),
            "protocol_version": "MCP-2025-06-18",
            "timestamp": datetime.now().isoformat()
        }
    
    async def cleanup(self) -> None:
        """Nettoyage des ressources MCP"""
        # Arrêt de tous les serveurs
        for server_id in list(self.servers.keys()):
            await self.stop_server(server_id)
        
        # Fermeture session HTTP
        if self.session:
            await self.session.close()
            self.session = None
        
        self.logger.info("MCP Manager cleanup completed")


# Factory function pour création simplifiée
async def create_mcp_manager(config_dir: str = ".claude") -> MCPManager:
    """Factory function pour créer et initialiser un MCPManager"""
    manager = MCPManager(config_dir)
    await manager.initialize()
    return manager