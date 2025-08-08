"""
BasePersonalAgent - Agent personnel principal avec intégrations A2A/MCP/Graphiti/Zep
Architecture évolutive avec mémoire persistante et protocoles modernes
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Union, Callable
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import json
from pydantic import BaseModel, Field
import uuid

from ..protocols.a2a_manager import A2AManager, A2ATask, TaskStatus
from ..protocols.mcp_manager import MCPManager, MCPTool
from ..graph.graphiti_engine import GraphitiEngine, GraphitiEpisode, EntityType


class AgentCapability(str, Enum):
    """Capacités de l'agent personnel"""
    MEMORY_MANAGEMENT = "memory_management"
    TASK_EXECUTION = "task_execution"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    PROTOCOL_A2A = "protocol_a2a"
    PROTOCOL_MCP = "protocol_mcp"
    NOTION_SYNC = "notion_sync"
    EDGE_PROCESSING = "edge_processing"
    LEARNING = "learning"
    PREFERENCE_TRACKING = "preference_tracking"


class AgentState(str, Enum):
    """États possibles de l'agent"""
    INITIALIZING = "initializing"
    READY = "ready"
    PROCESSING = "processing"
    LEARNING = "learning"
    SYNCING = "syncing"
    ERROR = "error"
    SHUTDOWN = "shutdown"


@dataclass
class AgentContext:
    """Contexte d'exécution de l'agent"""
    user_id: str
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    capabilities: List[AgentCapability] = field(default_factory=list)
    active_protocols: Dict[str, bool] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    
    def update_activity(self):
        """Met à jour le timestamp de dernière activité"""
        self.last_activity = datetime.now()


class AgentMessage(BaseModel):
    """Message traité par l'agent"""
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str = Field(..., description="Contenu du message")
    source: str = Field(..., description="Source du message (user, notion, mcp, etc.)")
    timestamp: datetime = Field(default_factory=datetime.now)
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)
    requires_memory: bool = Field(default=True, description="Si le message doit être mémorisé")
    priority: int = Field(default=5, description="Priorité 1-10")


class AgentResponse(BaseModel):
    """Réponse de l'agent"""
    response_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    message_id: str = Field(..., description="ID du message source")
    content: str = Field(..., description="Contenu de la réponse")
    confidence: float = Field(default=1.0, description="Confiance 0-1")
    sources: List[str] = Field(default_factory=list, description="Sources utilisées")
    actions_taken: List[str] = Field(default_factory=list, description="Actions effectuées")
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BasePersonalAgent:
    """
    Agent personnel principal avec architecture modulaire
    Intègre A2A, MCP, Graphiti et Zep pour une expérience unifiée
    """
    
    def __init__(
        self,
        user_id: str,
        agent_name: str = "PersonalAgent",
        zep_client=None,
        enable_a2a: bool = True,
        enable_mcp: bool = True,
        enable_graphiti: bool = True,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialise l'agent personnel avec toutes les intégrations
        
        Args:
            user_id: Identifiant unique de l'utilisateur
            agent_name: Nom de l'agent
            zep_client: Client Zep pour la mémoire persistante
            enable_a2a: Activer le protocole A2A
            enable_mcp: Activer le protocole MCP
            enable_graphiti: Activer le knowledge graph Graphiti
            config: Configuration additionnelle
        """
        self.user_id = user_id
        self.agent_name = agent_name
        self.config = config or {}
        self.logger = logging.getLogger(f"agent.{user_id}.{agent_name}")
        
        # État et contexte
        self.state = AgentState.INITIALIZING
        self.context = AgentContext(
            user_id=user_id,
            capabilities=self._determine_capabilities(enable_a2a, enable_mcp, enable_graphiti),
            active_protocols={
                "a2a": enable_a2a,
                "mcp": enable_mcp,
                "graphiti": enable_graphiti
            }
        )
        
        # Intégrations principales
        self.zep_client = zep_client
        self.memory_engine = None  # Sera initialisé avec ZepPersonalMemoryEngine
        
        # Protocoles
        self.a2a_manager = None
        self.mcp_manager = None
        self.graphiti_engine = None
        
        # Message processing
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.response_cache: Dict[str, AgentResponse] = {}
        
        # Callbacks et hooks
        self.event_handlers: Dict[str, List[Callable]] = {}
        
        # Stats et monitoring
        self.stats = {
            "messages_processed": 0,
            "memories_created": 0,
            "entities_discovered": 0,
            "tasks_completed": 0,
            "errors": 0
        }
    
    def _determine_capabilities(
        self, 
        enable_a2a: bool, 
        enable_mcp: bool, 
        enable_graphiti: bool
    ) -> List[AgentCapability]:
        """Détermine les capacités de l'agent selon la configuration"""
        capabilities = [
            AgentCapability.MEMORY_MANAGEMENT,
            AgentCapability.TASK_EXECUTION
        ]
        
        if enable_a2a:
            capabilities.append(AgentCapability.PROTOCOL_A2A)
        if enable_mcp:
            capabilities.append(AgentCapability.PROTOCOL_MCP)
        if enable_graphiti:
            capabilities.append(AgentCapability.KNOWLEDGE_GRAPH)
        
        # Capacités additionnelles selon config
        if self.config.get("enable_notion", False):
            capabilities.append(AgentCapability.NOTION_SYNC)
        if self.config.get("enable_learning", True):
            capabilities.append(AgentCapability.LEARNING)
        if self.config.get("enable_preferences", True):
            capabilities.append(AgentCapability.PREFERENCE_TRACKING)
        
        return capabilities
    
    async def initialize(self) -> None:
        """
        Initialise l'agent et toutes ses intégrations
        """
        try:
            self.logger.info(f"Initializing {self.agent_name} for user {self.user_id}")
            
            # 1. Initialisation A2A si activé
            if self.context.active_protocols.get("a2a"):
                await self._init_a2a()
            
            # 2. Initialisation MCP si activé
            if self.context.active_protocols.get("mcp"):
                await self._init_mcp()
            
            # 3. Initialisation Graphiti si activé
            if self.context.active_protocols.get("graphiti"):
                await self._init_graphiti()
            
            # 4. Initialisation Memory Engine (toujours requis)
            await self._init_memory_engine()
            
            # 5. Chargement contexte utilisateur depuis Zep
            await self._load_user_context()
            
            # 6. Démarrage processeur de messages
            asyncio.create_task(self._process_message_queue())
            
            self.state = AgentState.READY
            self.logger.info(f"Agent {self.agent_name} initialized successfully with capabilities: {self.context.capabilities}")
            
            # Trigger event
            await self._trigger_event("agent_initialized", {"agent": self.agent_name})
            
        except Exception as e:
            self.state = AgentState.ERROR
            self.logger.error(f"Failed to initialize agent: {str(e)}")
            raise
    
    async def _init_a2a(self) -> None:
        """Initialise le manager A2A"""
        try:
            self.a2a_manager = A2AManager(
                agent_id=f"{self.agent_name}_{self.user_id}",
                base_url=self.config.get("a2a_base_url", "http://localhost:8080")
            )
            await self.a2a_manager.initialize()
            
            # Enregistrement des capacités A2A
            await self.a2a_manager.register_capability(
                "memory_search",
                "Search user's personal memory",
                {"query": "string", "limit": "number"}
            )
            await self.a2a_manager.register_capability(
                "knowledge_query",
                "Query personal knowledge graph",
                {"entity_type": "string", "filters": "object"}
            )
            
            self.logger.info("A2A protocol initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize A2A: {str(e)}")
            self.context.active_protocols["a2a"] = False
    
    async def _init_mcp(self) -> None:
        """Initialise le manager MCP"""
        try:
            self.mcp_manager = MCPManager(
                agent_id=f"{self.agent_name}_{self.user_id}"
            )
            
            # Connexion aux serveurs MCP configurés
            mcp_servers = self.config.get("mcp_servers", ["filesystem"])
            for server in mcp_servers:
                if server == "filesystem":
                    await self.mcp_manager.connect_filesystem_server()
                elif server == "git":
                    await self.mcp_manager.connect_git_server()
                elif server == "notion":
                    notion_token = self.config.get("notion_token")
                    if notion_token:
                        await self.mcp_manager.connect_notion_server(notion_token)
            
            self.logger.info(f"MCP protocol initialized with servers: {mcp_servers}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize MCP: {str(e)}")
            self.context.active_protocols["mcp"] = False
    
    async def _init_graphiti(self) -> None:
        """Initialise le moteur Graphiti"""
        try:
            from ..graph.graphiti_engine import create_graphiti_engine
            
            self.graphiti_engine = await create_graphiti_engine(
                user_id=self.user_id,
                zep_client=self.zep_client
            )
            
            self.logger.info("Graphiti knowledge graph initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Graphiti: {str(e)}")
            self.context.active_protocols["graphiti"] = False
    
    async def _init_memory_engine(self) -> None:
        """Initialise le moteur de mémoire Zep"""
        try:
            # Import différé pour éviter les dépendances circulaires
            from ..memory.zep_engine import ZepPersonalMemoryEngine
            
            self.memory_engine = ZepPersonalMemoryEngine(
                user_id=self.user_id,
                zep_client=self.zep_client,
                graphiti_engine=self.graphiti_engine
            )
            
            await self.memory_engine.initialize()
            
            self.logger.info("Zep memory engine initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize memory engine: {str(e)}")
            # Memory engine est critique, on propage l'erreur
            raise
    
    async def _load_user_context(self) -> None:
        """Charge le contexte utilisateur depuis la mémoire"""
        try:
            if self.memory_engine:
                # Récupération des préférences
                preferences = await self.memory_engine.get_user_preferences()
                self.context.metadata["preferences"] = preferences
                
                # Récupération des entités importantes
                if self.graphiti_engine:
                    important_entities = await self.graphiti_engine.search_entities_by_type(
                        EntityType.PERSON, limit=5
                    )
                    self.context.metadata["important_contacts"] = [
                        e.name for e in important_entities
                    ]
                
                self.logger.info(f"Loaded user context with {len(preferences)} preferences")
                
        except Exception as e:
            self.logger.warning(f"Could not load full user context: {str(e)}")
    
    async def process_message(self, message: Union[str, AgentMessage]) -> AgentResponse:
        """
        Traite un message et génère une réponse
        
        Args:
            message: Message à traiter (string ou AgentMessage)
            
        Returns:
            AgentResponse avec la réponse de l'agent
        """
        try:
            # Conversion en AgentMessage si nécessaire
            if isinstance(message, str):
                agent_message = AgentMessage(
                    content=message,
                    source="user"
                )
            else:
                agent_message = message
            
            self.logger.info(f"Processing message {agent_message.message_id} from {agent_message.source}")
            
            # Mise à jour contexte
            self.context.update_activity()
            self.state = AgentState.PROCESSING
            
            # 1. Extraction d'entités et enrichissement via Graphiti
            if self.graphiti_engine and agent_message.requires_memory:
                episode = await self.graphiti_engine.ingest_episode(
                    content=agent_message.content,
                    source=agent_message.source,
                    metadata=agent_message.context or {}
                )
                self.stats["entities_discovered"] += len(episode.entities_extracted)
            
            # 2. Recherche mémoire pertinente
            memory_context = None
            if self.memory_engine:
                memory_context = await self.memory_engine.search_memories(
                    query=agent_message.content,
                    limit=5
                )
            
            # 3. Détection d'intention et routing
            intent = await self._detect_intent(agent_message.content)
            
            # 4. Exécution selon l'intention
            response_content = ""
            actions_taken = []
            sources = []
            
            if intent == "task_execution" and self.a2a_manager:
                # Exécution via A2A
                task = await self.a2a_manager.create_task(
                    task_type="user_request",
                    input_data={"message": agent_message.content},
                    metadata={"user_id": self.user_id}
                )
                result = await self.a2a_manager.execute_task(task.task_id)
                response_content = result.get("response", "Task completed")
                actions_taken.append(f"Executed A2A task {task.task_id}")
                sources.append("a2a_execution")
                
            elif intent == "knowledge_query" and self.graphiti_engine:
                # Requête sur le knowledge graph
                entities = await self._query_knowledge_graph(agent_message.content)
                response_content = self._format_knowledge_response(entities)
                actions_taken.append("Queried knowledge graph")
                sources.append("graphiti_kg")
                
            elif intent == "file_operation" and self.mcp_manager:
                # Opération fichier via MCP
                result = await self._execute_mcp_operation(agent_message.content)
                response_content = result.get("output", "Operation completed")
                actions_taken.append(f"Executed MCP operation")
                sources.append("mcp_tool")
                
            else:
                # Réponse basée sur la mémoire et le contexte
                response_content = await self._generate_contextual_response(
                    message=agent_message.content,
                    memory_context=memory_context
                )
                actions_taken.append("Generated contextual response")
                sources.append("memory_context")
            
            # 5. Sauvegarde en mémoire si requis
            if agent_message.requires_memory and self.memory_engine:
                await self.memory_engine.add_memory(
                    content=agent_message.content,
                    response=response_content,
                    metadata={
                        "source": agent_message.source,
                        "intent": intent,
                        "timestamp": agent_message.timestamp.isoformat()
                    }
                )
                self.stats["memories_created"] += 1
            
            # 6. Création de la réponse
            response = AgentResponse(
                message_id=agent_message.message_id,
                content=response_content,
                confidence=0.9,  # TODO: Calculer vraie confiance
                sources=sources,
                actions_taken=actions_taken,
                metadata={
                    "intent": intent,
                    "processing_time": (datetime.now() - agent_message.timestamp).total_seconds()
                }
            )
            
            # 7. Cache et stats
            self.response_cache[agent_message.message_id] = response
            self.stats["messages_processed"] += 1
            
            self.state = AgentState.READY
            
            # Trigger event
            await self._trigger_event("message_processed", {
                "message_id": agent_message.message_id,
                "intent": intent
            })
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error processing message: {str(e)}")
            self.stats["errors"] += 1
            self.state = AgentState.ERROR
            
            return AgentResponse(
                message_id=agent_message.message_id if isinstance(message, AgentMessage) else "",
                content=f"I encountered an error processing your message. Please try again.",
                confidence=0.0,
                sources=[],
                actions_taken=["error_handling"],
                metadata={"error": str(e)}
            )
    
    async def _detect_intent(self, content: str) -> str:
        """Détecte l'intention du message"""
        content_lower = content.lower()
        
        # Détection simple basée sur mots-clés (à remplacer par LLM)
        if any(word in content_lower for word in ["do", "execute", "run", "perform", "task"]):
            return "task_execution"
        elif any(word in content_lower for word in ["who", "what", "when", "where", "tell me about"]):
            return "knowledge_query"
        elif any(word in content_lower for word in ["file", "folder", "directory", "read", "write"]):
            return "file_operation"
        elif any(word in content_lower for word in ["remember", "recall", "memory", "did i"]):
            return "memory_query"
        else:
            return "general_conversation"
    
    async def _query_knowledge_graph(self, query: str) -> List[Any]:
        """Interroge le knowledge graph"""
        if not self.graphiti_engine:
            return []
        
        # Extraction du type d'entité recherché (simple version)
        for entity_type in EntityType:
            if entity_type.value in query.lower():
                return await self.graphiti_engine.search_entities_by_type(
                    entity_type, 
                    limit=5
                )
        
        # Recherche générale
        return []
    
    def _format_knowledge_response(self, entities: List[Any]) -> str:
        """Formate la réponse depuis les entités du KG"""
        if not entities:
            return "I couldn't find relevant information in your knowledge graph."
        
        response = "Based on your personal knowledge graph:\n"
        for entity in entities[:3]:
            response += f"- {entity.name} ({entity.entity_type})"
            if entity.description:
                response += f": {entity.description}"
            response += "\n"
        
        return response
    
    async def _execute_mcp_operation(self, content: str) -> Dict[str, Any]:
        """Exécute une opération MCP"""
        if not self.mcp_manager:
            return {"output": "MCP protocol not available"}
        
        # Détection de l'outil MCP à utiliser (simple version)
        if "read" in content.lower():
            # Utiliser filesystem pour lire
            tools = await self.mcp_manager.discover_tools("filesystem")
            if tools:
                # Exécution du premier outil trouvé (à améliorer)
                result = await self.mcp_manager.execute_tool(
                    "filesystem",
                    tools[0].name,
                    {"path": "./"}  # Paramètres à extraire du message
                )
                return {"output": str(result)}
        
        return {"output": "Could not determine MCP operation"}
    
    async def _generate_contextual_response(
        self, 
        message: str, 
        memory_context: Optional[Any]
    ) -> str:
        """Génère une réponse contextuelle basée sur la mémoire"""
        # Version simple - à remplacer par LLM
        if memory_context:
            return f"Based on your previous interactions, I understand you're asking about: {message}. Let me help you with that."
        else:
            return f"I'm processing your request: {message}. How can I assist you further?"
    
    async def _process_message_queue(self) -> None:
        """Processeur asynchrone de la queue de messages"""
        while self.state not in [AgentState.SHUTDOWN, AgentState.ERROR]:
            try:
                # Attente d'un message avec timeout
                message = await asyncio.wait_for(
                    self.message_queue.get(), 
                    timeout=1.0
                )
                
                # Traitement du message
                await self.process_message(message)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Error in message queue processor: {str(e)}")
    
    async def _trigger_event(self, event_name: str, data: Dict[str, Any]) -> None:
        """Déclenche un événement et appelle les handlers enregistrés"""
        if event_name in self.event_handlers:
            for handler in self.event_handlers[event_name]:
                try:
                    await handler(data)
                except Exception as e:
                    self.logger.error(f"Error in event handler for {event_name}: {str(e)}")
    
    def register_event_handler(self, event_name: str, handler: Callable) -> None:
        """Enregistre un handler pour un événement"""
        if event_name not in self.event_handlers:
            self.event_handlers[event_name] = []
        self.event_handlers[event_name].append(handler)
    
    async def learn_from_interaction(
        self, 
        message: AgentMessage, 
        response: AgentResponse, 
        feedback: Optional[str] = None
    ) -> None:
        """
        Apprentissage depuis une interaction
        Met à jour les préférences et le knowledge graph
        """
        if AgentCapability.LEARNING not in self.context.capabilities:
            return
        
        try:
            self.state = AgentState.LEARNING
            
            # 1. Extraction de préférences depuis le feedback
            if feedback and self.graphiti_engine:
                await self.graphiti_engine.ingest_episode(
                    content=f"User feedback: {feedback} for response: {response.content}",
                    source="feedback",
                    metadata={
                        "message_id": message.message_id,
                        "response_id": response.response_id,
                        "sentiment": "positive" if "good" in feedback.lower() else "negative"
                    }
                )
            
            # 2. Mise à jour des patterns de comportement
            if self.memory_engine:
                await self.memory_engine.update_behavior_patterns({
                    "intent": response.metadata.get("intent"),
                    "success": feedback and "good" in feedback.lower(),
                    "timestamp": datetime.now().isoformat()
                })
            
            self.state = AgentState.READY
            self.logger.info(f"Learned from interaction {message.message_id}")
            
        except Exception as e:
            self.logger.error(f"Error in learning: {str(e)}")
            self.state = AgentState.READY
    
    async def sync_with_cloud(self) -> None:
        """Synchronise l'état local avec le cloud (Zep)"""
        if self.state == AgentState.SYNCING:
            self.logger.warning("Already syncing, skipping")
            return
        
        try:
            self.state = AgentState.SYNCING
            
            # 1. Sync memory engine
            if self.memory_engine:
                await self.memory_engine.sync_to_cloud()
            
            # 2. Sync knowledge graph
            if self.graphiti_engine:
                stats = await self.graphiti_engine.get_graph_stats()
                self.logger.info(f"Graph stats: {stats}")
            
            # 3. Sync agent stats
            if self.zep_client:
                await self.zep_client.add_memory(
                    session_id=f"agent_stats_{self.user_id}",
                    messages=[{
                        "role": "system",
                        "content": f"Agent stats: {json.dumps(self.stats)}",
                        "metadata": {
                            "agent_name": self.agent_name,
                            "timestamp": datetime.now().isoformat()
                        }
                    }]
                )
            
            self.state = AgentState.READY
            self.logger.info("Cloud sync completed")
            
        except Exception as e:
            self.logger.error(f"Error during cloud sync: {str(e)}")
            self.state = AgentState.ERROR
    
    async def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de l'agent"""
        stats = self.stats.copy()
        
        # Ajout stats des composants
        if self.graphiti_engine:
            graph_stats = await self.graphiti_engine.get_graph_stats()
            stats["knowledge_graph"] = graph_stats
        
        if self.a2a_manager:
            stats["a2a_tasks"] = len(self.a2a_manager.active_tasks)
        
        if self.mcp_manager:
            stats["mcp_servers"] = len(self.mcp_manager.connected_servers)
        
        stats["state"] = self.state.value
        stats["capabilities"] = [c.value for c in self.context.capabilities]
        stats["uptime"] = (datetime.now() - self.context.created_at).total_seconds()
        
        return stats
    
    async def health_check(self) -> Dict[str, Any]:
        """Vérifie la santé de l'agent et ses composants"""
        health = {
            "status": "healthy" if self.state == AgentState.READY else "unhealthy",
            "agent_state": self.state.value,
            "components": {}
        }
        
        # Check memory engine
        health["components"]["memory"] = "healthy" if self.memory_engine else "unavailable"
        
        # Check protocols
        health["components"]["a2a"] = "healthy" if self.a2a_manager else "disabled"
        health["components"]["mcp"] = "healthy" if self.mcp_manager else "disabled"
        health["components"]["graphiti"] = "healthy" if self.graphiti_engine else "disabled"
        
        # Check Zep connection
        health["components"]["zep"] = "healthy" if self.zep_client else "disconnected"
        
        return health
    
    async def shutdown(self) -> None:
        """Arrêt propre de l'agent"""
        self.logger.info(f"Shutting down agent {self.agent_name}")
        self.state = AgentState.SHUTDOWN
        
        # Sync final
        await self.sync_with_cloud()
        
        # Fermeture des connexions
        if self.mcp_manager:
            await self.mcp_manager.disconnect_all()
        
        # Trigger shutdown event
        await self._trigger_event("agent_shutdown", {"agent": self.agent_name})
        
        self.logger.info(f"Agent {self.agent_name} shutdown complete")


# Factory function pour création simplifiée
async def create_personal_agent(
    user_id: str,
    zep_client=None,
    config: Optional[Dict[str, Any]] = None
) -> BasePersonalAgent:
    """
    Factory function pour créer et initialiser un agent personnel
    
    Args:
        user_id: ID utilisateur
        zep_client: Client Zep pour la mémoire
        config: Configuration optionnelle
        
    Returns:
        Agent personnel initialisé
    """
    agent = BasePersonalAgent(
        user_id=user_id,
        agent_name=f"PersonalAgent_{user_id}",
        zep_client=zep_client,
        config=config or {}
    )
    
    await agent.initialize()
    
    return agent