"""
Agent to Agent Protocol Manager conforme A2A spec 0.2
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import aiohttp
from pydantic import BaseModel, Field


class AgentCard(BaseModel):
    """Agent Card conforme A2A specification"""
    name: str = Field(..., description="Nom de l'agent")
    description: str = Field(..., description="Description des capabilities")
    version: str = Field(default="1.0.0", description="Version de l'agent")
    capabilities: List[str] = Field(..., description="Liste des capabilities")
    endpoints: Dict[str, str] = Field(..., description="Endpoints disponibles")
    authentication: Optional[Dict[str, Any]] = Field(None, description="Schema d'authentification")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class A2ATask(BaseModel):
    """Tâche A2A avec lifecycle management"""
    task_id: str = Field(..., description="ID unique de la tâche")
    status: str = Field(default="pending", description="pending|in_progress|completed|failed|canceled")
    input_data: Dict[str, Any] = Field(..., description="Données d'entrée")
    output_data: Optional[Dict[str, Any]] = Field(None, description="Résultats")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class A2AManager:
    """
    Manager pour communication A2A selon spécification officielle
    Supporte Agent Discovery, Task Management, et Communication sécurisée
    """
    
    def __init__(self, agent_id: str, base_url: str = "http://localhost:8080"):
        self.agent_id = agent_id
        self.base_url = base_url
        self.logger = logging.getLogger(f"a2a.{agent_id}")
        self.session = None
        self.agent_registry: Dict[str, AgentCard] = {}
        self.active_tasks: Dict[str, A2ATask] = {}
        
        # Configuration agents distants selon spec A2A 0.2
        self.remote_agents = {
            "claude_code_a2a": {
                "agent_card_url": "https://claude-api.anthropic.com/.well-known/agent-card",
                "base_url": "https://claude-api.anthropic.com/v1/a2a",
                "capabilities": ["code_analysis", "development_assistance", "memory_integration"]
            },
            "notion_a2a": {
                "agent_card_url": "https://api.notion.com/.well-known/agent-card", 
                "base_url": "https://api.notion.com/v1/a2a",
                "capabilities": ["page_management", "database_queries", "content_extraction"]
            },
            "zep_cloud_a2a": {
                "agent_card_url": "https://api.getzep.com/.well-known/agent-card",
                "base_url": "https://api.getzep.com/v1/a2a", 
                "capabilities": ["memory_search", "context_assembly", "temporal_queries"]
            }
        }
    
    async def initialize(self) -> bool:
        """Initialisation du manager A2A avec session HTTP"""
        try:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={
                    "User-Agent": f"PersonalAgent-A2A/{self.agent_id}",
                    "Content-Type": "application/json"
                }
            )
            
            # Publication de notre Agent Card
            await self._publish_agent_card()
            
            # Discovery des agents distants
            await self._discover_remote_agents()
            
            self.logger.info(f"A2A Manager initialized for {self.agent_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize A2A Manager: {str(e)}")
            return False
    
    async def _publish_agent_card(self) -> None:
        """Publication de notre Agent Card selon A2A spec"""
        agent_card = AgentCard(
            name=f"PersonalAgent-{self.agent_id}",
            description="Agent personnel avec mémoire Zep et PKG évolutif",
            version="0.1.0",
            capabilities=[
                "memory_management",
                "knowledge_graph_evolution", 
                "notion_integration",
                "temporal_queries",
                "context_assembly"
            ],
            endpoints={
                "base": self.base_url,
                "tasks": f"{self.base_url}/a2a/tasks",
                "messages": f"{self.base_url}/a2a/messages",
                "health": f"{self.base_url}/a2a/health"
            },
            authentication={
                "type": "bearer",
                "required": False
            },
            metadata={
                "protocols": ["A2A-0.2", "MCP-2025-06-18"],
                "created_at": datetime.now().isoformat(),
                "memory_provider": "zep_cloud",
                "knowledge_graph": "temporal_pkg"
            }
        )
        
        # Stockage local de notre card (en production, publier via /.well-known/agent-card)
        self.agent_registry[self.agent_id] = agent_card
        self.logger.info(f"Published Agent Card for {self.agent_id}")
    
    async def _discover_remote_agents(self) -> None:
        """Discovery des agents distants via Agent Cards"""
        for agent_name, config in self.remote_agents.items():
            try:
                agent_card = await self._fetch_agent_card(config["agent_card_url"])
                if agent_card:
                    self.agent_registry[agent_name] = agent_card
                    self.logger.info(f"Discovered remote agent: {agent_name}")
                else:
                    self.logger.warning(f"Failed to discover agent: {agent_name}")
                    
            except Exception as e:
                self.logger.error(f"Error discovering {agent_name}: {str(e)}")
    
    async def _fetch_agent_card(self, card_url: str) -> Optional[AgentCard]:
        """Récupération Agent Card depuis URL .well-known"""
        try:
            if not self.session:
                return None
                
            async with self.session.get(card_url) as response:
                if response.status == 200:
                    card_data = await response.json()
                    return AgentCard(**card_data)
                else:
                    self.logger.warning(f"Agent card not found: {card_url} (status: {response.status})")
                    return None
                    
        except Exception as e:
            self.logger.error(f"Error fetching agent card from {card_url}: {str(e)}")
            return None
    
    async def send_task_to_agent(
        self, 
        target_agent: str, 
        task_data: Dict[str, Any],
        task_id: Optional[str] = None
    ) -> Optional[A2ATask]:
        """Envoi de tâche à un agent distant via A2A"""
        try:
            if target_agent not in self.agent_registry:
                self.logger.error(f"Agent {target_agent} not found in registry")
                return None
            
            if not task_id:
                task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{target_agent}"
            
            # Création de la tâche A2A
            task = A2ATask(
                task_id=task_id,
                status="pending",
                input_data=task_data,
                metadata={
                    "source_agent": self.agent_id,
                    "target_agent": target_agent,
                    "protocol": "A2A-0.2"
                }
            )
            
            # Stockage local de la tâche
            self.active_tasks[task_id] = task
            
            # Envoi vers l'agent distant
            agent_config = self.remote_agents.get(target_agent)
            if agent_config:
                task_endpoint = f"{agent_config['base_url']}/tasks"
                
                payload = {
                    "task_id": task_id,
                    "source_agent": self.agent_id,
                    "input": task_data,
                    "capabilities_required": agent_config["capabilities"]
                }
                
                if not self.session:
                    await self.initialize()
                
                async with self.session.post(task_endpoint, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        task.status = "in_progress"
                        task.updated_at = datetime.now()
                        task.metadata["remote_task_id"] = result.get("task_id")
                        
                        self.logger.info(f"Task {task_id} sent to {target_agent}")
                        return task
                    else:
                        task.status = "failed"
                        task.metadata["error"] = f"HTTP {response.status}"
                        self.logger.error(f"Failed to send task to {target_agent}: {response.status}")
            
            return task
            
        except Exception as e:
            self.logger.error(f"Error sending task to {target_agent}: {str(e)}")
            return None
    
    async def get_task_status(self, task_id: str) -> Optional[A2ATask]:
        """Récupération du statut d'une tâche A2A"""
        return self.active_tasks.get(task_id)
    
    async def list_available_agents(self) -> Dict[str, Dict[str, Any]]:
        """Liste des agents disponibles avec leurs capabilities"""
        agents_info = {}
        
        for agent_name, agent_card in self.agent_registry.items():
            agents_info[agent_name] = {
                "name": agent_card.name,
                "description": agent_card.description,
                "capabilities": agent_card.capabilities,
                "version": agent_card.version,
                "status": "available" if agent_name in self.remote_agents else "local"
            }
        
        return agents_info
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check du manager A2A"""
        return {
            "agent_id": self.agent_id,
            "status": "healthy",
            "session_active": self.session is not None,
            "agents_discovered": len(self.agent_registry),
            "active_tasks": len(self.active_tasks),
            "protocol_version": "A2A-0.2",
            "timestamp": datetime.now().isoformat()
        }
    
    async def cleanup(self) -> None:
        """Nettoyage des ressources"""
        if self.session:
            await self.session.close()
            self.session = None
        
        self.logger.info(f"A2A Manager cleanup completed for {self.agent_id}")


# Factory function pour création simplifiée
async def create_a2a_manager(agent_id: str, base_url: str = "http://localhost:8080") -> A2AManager:
    """Factory function pour créer et initialiser un A2AManager"""
    manager = A2AManager(agent_id, base_url)
    await manager.initialize()
    return manager