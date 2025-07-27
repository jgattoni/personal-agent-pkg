# Development Plan - Agent Personnel avec Personal Knowledge Graph

## 🏗️ Architecture technique complète

### Vision du projet
Développer un agent personnel intelligent qui s'intègre avec Notion et fonctionne sur mobile/desktop, utilisant les protocoles agent-to-agent de pointe (A2A, ACP, MCP), un Personal Knowledge Graph évolutif, Zep comme couche mémoire state-of-the-art, et Claude Code comme interface desktop principale.

### Stack technologique 2025
- **Package Manager** : UV (10-100x plus rapide que Poetry, gestion Python automatique)
- **Memory Layer** : Zep Cloud (+100% précision, -90% latence vs approches traditionnelles)
- **Desktop Interface** : Claude Code avec extensions personnalisées
- **Mobile Interface** : React Native/PWA avec sync Zep
- **Knowledge Graph** : Zep + Neo4j + Qdrant hybride
- **Protocols** : MCP (tools), ACP (local agents), A2A (remote agents)

### Architecture de communication agents
```python
# Agents locaux (ACP) - Performance maximale
AGENTS_LOCAL = {
    "personal_agent_desktop": "http://localhost:8080/acp",
    "zep_memory_service": "http://localhost:8081/acp", 
    "notion_bridge": "http://localhost:8082/acp",
    "edge_mobile_sync": "http://localhost:8083/acp",
    "pkg_evolution_engine": "http://localhost:8084/acp"
}

# Agents distants (A2A) - Intégrations externes
AGENTS_REMOTE = {
    "notion_mcp": "https://api.notion.com/mcp",
    "claude_code_remote": "https://claude-code.anthropic.com/a2a",
    "zep_cloud": "https://api.getzep.com/a2a"
}
```

## 📁 Structure modulaire du projet

```
personal-agent-pkg/
├── CLAUDE.md                    # Mémoire Claude Code
├── DEVELOPMENT_PLAN.md          # Ce fichier
├── TASKS.md                     # Statut phases + todos
├── .python-version              # 3.12
├── pyproject.toml               # UV dependencies
├── .claude/
│   ├── agent-config.json        # Configuration Claude Code
│   └── commands/                # Commandes slash personnalisées
│       ├── memory.md
│       ├── notion.md
│       ├── agents.md
│       ├── context.md
│       └── pkg.md
├── core/
│   ├── agents/                  # BasePersonalAgent + spécialisations
│   │   ├── __init__.py
│   │   ├── base_agent.py
│   │   └── orchestrator.py
│   ├── protocols/               # MCP, ACP, A2A managers
│   │   ├── __init__.py
│   │   ├── mcp_manager.py
│   │   ├── acp_manager.py
│   │   ├── a2a_manager.py
│   │   └── discovery.py
│   ├── graph/                   # Personal Knowledge Graph + évolution
│   │   ├── __init__.py
│   │   ├── pkg_engine.py
│   │   ├── temporal_engine.py
│   │   └── neo4j_bridge.py
│   └── memory/                  # Zep Memory Engine + caching
│       ├── __init__.py
│       ├── zep_engine.py
│       ├── zep_config.py
│       └── local_cache.py
├── integrations/
│   ├── notion/                  # Bridge Notion MCP ↔ Zep
│   │   ├── __init__.py
│   │   ├── notion_agent.py
│   │   └── notion_zep_bridge.py
│   ├── claude_code/             # Extension Claude Code
│   │   ├── __init__.py
│   │   ├── extension.py
│   │   └── commands.py
│   └── mobile/                  # Agent mobile companion
│       ├── __init__.py
│       └── mobile_sync.py
├── edge/
│   ├── local_processing/        # Ollama + processing local
│   │   ├── __init__.py
│   │   ├── ollama_client.py
│   │   └── edge_agent.py
│   └── sync/                    # Sync intelligence cloud ↔ edge
│       ├── __init__.py
│       └── sync_manager.py
├── interfaces/
│   ├── api/                     # FastAPI orchestration backend
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── routes/
│   │   └── websocket.py
│   └── web/                     # Web overlay pour Claude Code
│       ├── static/
│       └── templates/
├── config/
│   ├── __init__.py
│   ├── settings.py
│   └── logging.py
├── tests/
│   ├── test_agents/
│   ├── test_memory/
│   ├── test_integrations/
│   └── conftest.py
└── docs/
    ├── api/
    └── deployment/
```

## 🔧 Composants Core - Implémentation détaillée

### 1. BasePersonalAgent (core/agents/base_agent.py)

```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from zep_python import ZepClient
from core.protocols.acp_manager import ACPManager
from core.protocols.mcp_manager import MCPManager

class BasePersonalAgent:
    """Classe de base pour tous les agents avec support Zep Memory et protocoles"""
    
    def __init__(self, agent_id: str, user_id: str):
        self.agent_id = agent_id
        self.user_id = user_id
        self.zep_client = ZepClient(api_key=os.getenv("ZEP_API_KEY"))
        self.acp_manager = ACPManager()
        self.mcp_tools = MCPManager()
        self.logger = self._setup_logging()
        
    def _setup_logging(self) -> logging.Logger:
        """Configuration logging structuré"""
        logger = logging.getLogger(f"agent.{self.agent_id}")
        logger.setLevel(logging.INFO)
        
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
        
    async def process_with_memory(self, input_data: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Processing avec mémoire Zep optimisée"""
        self.logger.info(f"Processing input: {input_data[:100]}...")
        
        try:
            # Récupération mémoire Zep intelligente (1.6k tokens optimisé)
            relevant_memory = await self.zep_client.memory.search_memory(
                session_id=f"session_{self.user_id}",
                text=input_data,
                limit=5,
                search_type="similarity"
            )
            
            # Assembly contexte enrichi
            enriched_context = {
                "user_input": input_data,
                "relevant_memory": relevant_memory,
                "additional_context": context or {},
                "timestamp": datetime.now().isoformat()
            }
            
            # Processing principal (à overrider dans les classes filles)
            response = await self.process(enriched_context)
            
            # Mise à jour mémoire temporelle Zep
            await self.zep_client.memory.add_memory(
                session_id=f"session_{self.user_id}",
                messages=[{
                    "role": "user", 
                    "content": input_data,
                    "metadata": {
                        "agent_id": self.agent_id,
                        "timestamp": datetime.now().isoformat(),
                        "enriched": True,
                        "response_generated": True
                    }
                }]
            )
            
            self.logger.info("Processing completed successfully")
            return response
            
        except Exception as e:
            self.logger.error(f"Error in process_with_memory: {str(e)}")
            raise
    
    async def process(self, enriched_context: Dict[str, Any]) -> Dict[str, Any]:
        """Méthode principale à overrider dans les classes filles"""
        raise NotImplementedError("Subclasses must implement process method")
    
    async def communicate_with_agent(self, target_agent_url: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """Communication avec autres agents via ACP ou A2A"""
        if target_agent_url.startswith("http://localhost"):
            # Communication ACP locale
            return await self.acp_manager.send_message(target_agent_url, message)
        else:
            # Communication A2A distante (future implementation)
            self.logger.warning(f"A2A communication not yet implemented for {target_agent_url}")
            return {"status": "not_implemented"}
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check de l'agent"""
        return {
            "agent_id": self.agent_id,
            "status": "healthy",
            "memory_connected": bool(self.zep_client),
            "timestamp": datetime.now().isoformat()
        }
```

### 2. ZepPersonalMemoryEngine (core/memory/zep_engine.py)

```python
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from zep_python import ZepClient, Memory, Message
from core.graph.pkg_engine import PersonalKnowledgeGraphEngine

class ZepPersonalMemoryEngine:
    """Moteur mémoire Zep avec Personal Knowledge Graph évolutif"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.zep_client = ZepClient(api_key=os.getenv("ZEP_API_KEY"))
        self.session_id = f"personal_session_{user_id}"
        self.pkg_engine = PersonalKnowledgeGraphEngine()
        
    async def initialize_session(self) -> bool:
        """Initialisation session utilisateur Zep"""
        try:
            # Création ou récupération session
            session = await self.zep_client.memory.add_session(
                session_id=self.session_id,
                user_id=self.user_id,
                metadata={
                    "type": "personal_assistant",
                    "created_at": datetime.now().isoformat(),
                    "pkg_enabled": True
                }
            )
            
            # Initialisation PKG si nouvelle session
            if session.created_at == datetime.now().date():
                await self.pkg_engine.initialize_personal_graph(self.user_id)
                
            return True
            
        except Exception as e:
            logging.error(f"Failed to initialize Zep session: {str(e)}")
            return False
    
    async def evolve_personal_graph(self, new_interaction: Dict[str, Any]) -> Dict[str, Any]:
        """Auto-évolution PKG avec Zep (100% gains précision)"""
        try:
            # Extraction entités et relations via Zep + LLM
            entities = await self._extract_entities_temporal(new_interaction)
            relationships = await self._infer_relationships_temporal(entities, new_interaction)
            
            # Mise à jour bi-temporelle (event + system timeline)
            evolution_result = await self._update_temporal_knowledge(entities, relationships)
            
            # Sync avec Neo4j pour visualisations complexes  
            await self.pkg_engine.sync_neo4j_updates(entities, relationships)
            
            return {
                "entities_extracted": len(entities),
                "relationships_inferred": len(relationships),
                "graph_evolution": evolution_result,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logging.error(f"Error in evolve_personal_graph: {str(e)}")
            return {"error": str(e)}
    
    async def semantic_search_with_context(self, query: str, limit: int = 10, include_temporal: bool = True) -> List[Dict]:
        """Recherche sémantique Zep avec contexte temporel"""
        try:
            # Recherche dans Zep Memory
            memory_results = await self.zep_client.memory.search_memory(
                session_id=self.session_id,
                text=query,
                limit=limit,
                search_type="similarity"
            )
            
            enriched_results = []
            for result in memory_results:
                enriched = {
                    "content": result.message.content,
                    "relevance_score": result.dist,
                    "timestamp": result.message.created_at,
                    "metadata": result.message.metadata
                }
                
                # Ajout contexte temporel si demandé
                if include_temporal:
                    temporal_context = await self._get_temporal_context(result.message.created_at)
                    enriched["temporal_context"] = temporal_context
                    
                enriched_results.append(enriched)
            
            return enriched_results
            
        except Exception as e:
            logging.error(f"Error in semantic search: {str(e)}")
            return []
    
    async def assemble_intelligent_context(self, query: str, max_tokens: int = 1600) -> Dict[str, Any]:
        """Assembly contexte optimisé Zep (1.6k tokens vs 115k traditionnel)"""
        try:
            # Recherche mémoire pertinente
            relevant_memories = await self.semantic_search_with_context(query, limit=5)
            
            # Récupération contexte PKG
            graph_context = await self.pkg_engine.get_contextual_subgraph(query)
            
            # Optimisation tokens avec Zep
            optimized_context = await self._optimize_context_tokens(
                memories=relevant_memories,
                graph_context=graph_context,
                max_tokens=max_tokens
            )
            
            return {
                "optimized_context": optimized_context,
                "tokens_used": len(optimized_context.split()),
                "compression_ratio": f"90% reduction vs traditional",
                "memories_included": len(relevant_memories),
                "graph_entities": len(graph_context.get("entities", []))
            }
            
        except Exception as e:
            logging.error(f"Error in assemble_intelligent_context: {str(e)}")
            return {"error": str(e)}
    
    async def _extract_entities_temporal(self, interaction: Dict[str, Any]) -> List[Dict]:
        """Extraction entités avec conscience temporelle"""
        # Implementation extraction entités avec LLM + temporal awareness
        # Utilise Zep's built-in entity extraction ou custom LLM
        pass
    
    async def _infer_relationships_temporal(self, entities: List[Dict], interaction: Dict[str, Any]) -> List[Dict]:
        """Inférence relations avec contexte temporel"""
        # Implementation inférence relations entre entités
        pass
    
    async def _update_temporal_knowledge(self, entities: List[Dict], relationships: List[Dict]) -> Dict[str, Any]:
        """Mise à jour knowledge graph avec bi-temporal tracking"""
        # Implementation mise à jour PKG avec event + system timelines
        pass
    
    async def _get_temporal_context(self, timestamp: datetime) -> Dict[str, Any]:
        """Récupération contexte temporel pour une date donnée"""
        # Implementation récupération contexte historique
        pass
    
    async def _optimize_context_tokens(self, memories: List[Dict], graph_context: Dict, max_tokens: int) -> str:
        """Optimisation contexte pour respecter limite tokens"""
        # Implementation compression intelligente contexte
        pass
```

### 3. NotionZepBridge (integrations/notion/notion_zep_bridge.py)

```python
import asyncio
from typing import Dict, List, Any, Optional
from notion_client import Client as NotionClient
from core.agents.base_agent import BasePersonalAgent
from core.memory.zep_engine import ZepPersonalMemoryEngine

class NotionZepBridge(BasePersonalAgent):
    """Bridge bidirectionnel Notion MCP ↔ Zep Memory"""
    
    def __init__(self, user_id: str, notion_token: str):
        super().__init__(agent_id="notion_zep_bridge", user_id=user_id)
        self.notion_client = NotionClient(auth=notion_token)
        self.zep_memory = ZepPersonalMemoryEngine(user_id)
        
    async def sync_notion_to_zep(self, pages_limit: int = 10, database_id: Optional[str] = None) -> Dict[str, Any]:
        """Synchronisation Notion → Zep Memory avec extraction entités"""
        try:
            self.logger.info(f"Starting Notion → Zep sync (limit: {pages_limit})")
            
            # Récupération pages Notion
            if database_id:
                pages = await self._get_database_pages(database_id, pages_limit)
            else:
                pages = await self._search_all_pages(pages_limit)
            
            sync_results = {
                "pages_processed": 0,
                "entities_extracted": 0,
                "memories_added": 0,
                "errors": []
            }
            
            for page in pages:
                try:
                    # Extraction contenu page
                    page_content = await self._extract_page_content(page)
                    
                    # Extraction entités et métadonnées
                    entities = await self._extract_entities_from_page(page_content)
                    
                    # Ajout à Zep Memory avec contexte riche
                    memory_result = await self.zep_memory.zep_client.memory.add_memory(
                        session_id=self.zep_memory.session_id,
                        messages=[{
                            "role": "system",
                            "content": f"Notion Page: {page_content['title']}\n\nContent: {page_content['content']}",
                            "metadata": {
                                "source": "notion",
                                "page_id": page["id"],
                                "title": page_content["title"],
                                "url": page_content.get("url"),
                                "last_edited": page_content.get("last_edited_time"),
                                "entities": entities,
                                "sync_timestamp": datetime.now().isoformat()
                            }
                        }]
                    )
                    
                    # Évolution PKG avec nouvelles entités
                    await self.zep_memory.evolve_personal_graph({
                        "source": "notion_page",
                        "content": page_content,
                        "entities": entities
                    })
                    
                    sync_results["pages_processed"] += 1
                    sync_results["entities_extracted"] += len(entities)
                    sync_results["memories_added"] += 1
                    
                    self.logger.info(f"Synced page: {page_content['title']}")
                    
                except Exception as page_error:
                    error_msg = f"Error processing page {page.get('id', 'unknown')}: {str(page_error)}"
                    self.logger.error(error_msg)
                    sync_results["errors"].append(error_msg)
            
            self.logger.info(f"Notion → Zep sync completed: {sync_results}")
            return sync_results
            
        except Exception as e:
            self.logger.error(f"Error in sync_notion_to_zep: {str(e)}")
            return {"error": str(e)}
    
    async def sync_zep_to_notion(self, create_summary_page: bool = True) -> Dict[str, Any]:
        """Synchronisation Zep Memory → Notion (création pages résumés)"""
        try:
            self.logger.info("Starting Zep → Notion sync")
            
            # Récupération insights récents de Zep
            recent_insights = await self.zep_memory.semantic_search_with_context(
                query="insights learnings patterns preferences",
                limit=20,
                include_temporal=True
            )
            
            if create_summary_page and recent_insights:
                # Création page résumé dans Notion
                summary_content = await self._generate_insights_summary(recent_insights)
                
                notion_page = await self._create_notion_page(
                    title=f"AI Insights Summary - {datetime.now().strftime('%Y-%m-%d')}",
                    content=summary_content,
                    database_id=None  # Créer en page standalone
                )
                
                return {
                    "summary_page_created": True,
                    "page_id": notion_page["id"],
                    "insights_processed": len(recent_insights),
                    "url": notion_page.get("url")
                }
            
            return {"summary_page_created": False, "reason": "No recent insights found"}
            
        except Exception as e:
            self.logger.error(f"Error in sync_zep_to_notion: {str(e)}")
            return {"error": str(e)}
    
    async def search_across_both(self, query: str) -> Dict[str, Any]:
        """Recherche unifiée Notion + Zep Memory"""
        try:
            # Recherche parallèle
            zep_task = self.zep_memory.semantic_search_with_context(query, limit=10)
            notion_task = self._search_notion_content(query)
            
            zep_results, notion_results = await asyncio.gather(zep_task, notion_task)
            
            return {
                "query": query,
                "zep_results": zep_results,
                "notion_results": notion_results,
                "total_results": len(zep_results) + len(notion_results),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error in search_across_both: {str(e)}")
            return {"error": str(e)}
    
    async def process(self, enriched_context: Dict[str, Any]) -> Dict[str, Any]:
        """Processing principal du bridge (override BasePersonalAgent)"""
        user_input = enriched_context["user_input"]
        
        # Déterminer l'action à effectuer
        if "sync notion" in user_input.lower():
            return await self.sync_notion_to_zep()
        elif "create summary" in user_input.lower():
            return await self.sync_zep_to_notion(create_summary_page=True)
        elif "search" in user_input.lower():
            query = user_input.replace("search", "").strip()
            return await self.search_across_both(query)
        else:
            return {"message": "Available commands: sync notion, create summary, search [query]"}
    
    # Méthodes privées pour interaction Notion
    async def _get_database_pages(self, database_id: str, limit: int) -> List[Dict]:
        """Récupération pages d'une database Notion"""
        # Implementation récupération pages database
        pass
    
    async def _search_all_pages(self, limit: int) -> List[Dict]:
        """Recherche toutes les pages accessibles"""
        # Implementation recherche pages
        pass
    
    async def _extract_page_content(self, page: Dict) -> Dict[str, Any]:
        """Extraction contenu complet d'une page"""
        # Implementation extraction contenu
        pass
    
    async def _extract_entities_from_page(self, page_content: Dict) -> List[Dict]:
        """Extraction entités d'une page via LLM"""
        # Implementation extraction entités
        pass
    
    async def _generate_insights_summary(self, insights: List[Dict]) -> str:
        """Génération résumé insights pour Notion"""
        # Implementation génération résumé
        pass
    
    async def _create_notion_page(self, title: str, content: str, database_id: Optional[str] = None) -> Dict:
        """Création page Notion"""
        # Implementation création page
        pass
    
    async def _search_notion_content(self, query: str) -> List[Dict]:
        """Recherche dans Notion"""
        # Implementation recherche Notion
        pass
```

### 4. Claude Code Extension (integrations/claude_code/extension.py)

```python
import asyncio
from typing import Dict, List, Any, Optional
from core.agents.orchestrator import PersonalAgentOrchestrator
from core.memory.zep_engine import ZepPersonalMemoryEngine
from integrations.notion.notion_zep_bridge import NotionZepBridge

class ClaudeCodePersonalAgentExtension:
    """Extension Claude Code avec commandes slash personnalisées"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.orchestrator = PersonalAgentOrchestrator(user_id)
        self.zep_memory = ZepPersonalMemoryEngine(user_id)
        self.notion_bridge = NotionZepBridge(user_id, os.getenv("NOTION_TOKEN"))
        
    def register_custom_commands(self) -> Dict[str, callable]:
        """Enregistrement commandes slash personnalisées"""
        return {
            "/memory": self.search_zep_memory,
            "/notion": self.sync_notion_bidirectional,
            "/agents": self.show_agent_network_status,
            "/context": self.assemble_intelligent_context,
            "/pkg": self.navigate_knowledge_graph,
            "/evolve": self.trigger_temporal_evolution
        }
    
    async def search_zep_memory(self, query: str, timeframe: Optional[str] = None) -> str:
        """
        Commande /memory - Recherche intelligente dans mémoire Zep
        Usage: /memory [query] --timeframe [optional]
        """
        try:
            # Parsing timeframe si fourni
            include_temporal = timeframe is not None
            
            results = await self.zep_memory.semantic_search_with_context(
                query=query,
                limit=10,
                include_temporal=include_temporal
            )
            
            if not results:
                return f"🔍 Aucun résultat trouvé pour: {query}"
            
            # Formatage résultats pour Claude Code
            formatted_results = ["🧠 **Résultats mémoire Zep:**\n"]
            
            for i, result in enumerate(results[:5], 1):
                relevance = f"({result['relevance_score']:.2f})"
                timestamp = result['timestamp'].strftime("%Y-%m-%d %H:%M")
                content_preview = result['content'][:100] + "..." if len(result['content']) > 100 else result['content']
                
                formatted_results.append(f"{i}. **{timestamp}** {relevance}")
                formatted_results.append(f"   {content_preview}\n")
                
                if include_temporal and 'temporal_context' in result:
                    formatted_results.append(f"   🕒 Contexte: {result['temporal_context']}\n")
            
            return "\n".join(formatted_results)
            
        except Exception as e:
            return f"❌ Erreur recherche mémoire: {str(e)}"
    
    async def sync_notion_bidirectional(self, action: str = "sync", target: Optional[str] = None) -> str:
        """
        Commande /notion - Sync bidirectionnel Notion ↔ PKG + Zep
        Usage: /notion sync|search|update [target]
        """
        try:
            if action == "sync":
                # Sync Notion → Zep
                sync_result = await self.notion_bridge.sync_notion_to_zep(pages_limit=20)
                
                if "error" in sync_result:
                    return f"❌ Erreur sync Notion: {sync_result['error']}"
                
                return f"""✅ **Sync Notion → Zep terminé:**
📄 Pages traitées: {sync_result['pages_processed']}
🔗 Entités extraites: {sync_result['entities_extracted']}
🧠 Mémoires ajoutées: {sync_result['memories_added']}
⚠️ Erreurs: {len(sync_result.get('errors', []))}"""
                
            elif action == "search" and target:
                # Recherche unifiée
                search_result = await self.notion_bridge.search_across_both(target)
                
                if "error" in search_result:
                    return f"❌ Erreur recherche: {search_result['error']}"
                
                return f"""🔍 **Recherche '{target}':**
🧠 Résultats Zep: {len(search_result['zep_results'])}
📄 Résultats Notion: {len(search_result['notion_results'])}
📊 Total: {search_result['total_results']}"""
                
            elif action == "update":
                # Création résumé insights dans Notion
                update_result = await self.notion_bridge.sync_zep_to_notion(create_summary_page=True)
                
                if update_result.get("summary_page_created"):
                    return f"""✅ **Page résumé créée dans Notion:**
🆔 Page ID: {update_result['page_id']}
📊 Insights traités: {update_result['insights_processed']}
🔗 URL: {update_result.get('url', 'N/A')}"""
                else:
                    return f"ℹ️ Aucune page créée: {update_result.get('reason', 'Raison inconnue')}"
            
            else:
                return """📋 **Commandes /notion disponibles:**
• `/notion sync` - Synchronise Notion → Zep
• `/notion search [query]` - Recherche dans Notion + Zep  
• `/notion update` - Crée résumé insights dans Notion"""
                
        except Exception as e:
            return f"❌ Erreur commande /notion: {str(e)}"
    
    async def show_agent_network_status(self, command: str = "status") -> str:
        """
        Commande /agents - Status et contrôle réseau agents ACP/A2A
        Usage: /agents status|deploy|discover [capability]
        """
        try:
            if command == "status":
                # Status réseau agents
                status = await self.orchestrator.get_network_status()
                
                formatted_status = ["🤖 **Status réseau agents:**\n"]
                
                for agent_type, agents in status.items():
                    formatted_status.append(f"**{agent_type.upper()}:**")
                    for agent_id, agent_status in agents.items():
                        status_icon = "🟢" if agent_status["healthy"] else "🔴"
                        formatted_status.append(f"  {status_icon} {agent_id}: {agent_status['url']}")
                
                return "\n".join(formatted_status)
                
            elif command == "discover":
                # Discovery agents disponibles
                discovered = await self.orchestrator.discover_available_agents()
                return f"🔍 **Agents découverts:** {len(discovered)} agents disponibles"
                
            else:
                return """📋 **Commandes /agents disponibles:**
• `/agents status` - Status réseau agents
• `/agents discover` - Découverte agents disponibles"""
                
        except Exception as e:
            return f"❌ Erreur commande /agents: {str(e)}"
    
    async def assemble_intelligent_context(self, scope: str, depth: str = "shallow") -> str:
        """
        Commande /context - Assembly contexte optimisé Zep
        Usage: /context [scope] --depth [shallow|deep]
        """
        try:
            max_tokens = 1600 if depth == "shallow" else 3200
            
            context_result = await self.zep_memory.assemble_intelligent_context(
                query=scope,
                max_tokens=max_tokens
            )
            
            if "error" in context_result:
                return f"❌ Erreur assembly contexte: {context_result['error']}"
            
            return f"""🧠 **Contexte assemblé pour '{scope}':**
📊 Tokens utilisés: {context_result['tokens_used']}/{max_tokens}
📈 Compression: {context_result['compression_ratio']}
🧠 Mémoires incluses: {context_result['memories_included']}
🔗 Entités graphe: {context_result['graph_entities']}

📝 **Contexte optimisé:**
{context_result['optimized_context'][:500]}..."""
            
        except Exception as e:
            return f"❌ Erreur commande /context: {str(e)}"
    
    async def navigate_knowledge_graph(self, action: str = "explore", entity: Optional[str] = None) -> str:
        """
        Commande /pkg - Navigation Personal Knowledge Graph
        Usage: /pkg explore|search|visualize [entity]
        """
        try:
            if action == "explore":
                # Exploration PKG
                graph_overview = await self.orchestrator.get_pkg_overview()
                
                return f"""🕸️ **Personal Knowledge Graph:**
🔗 Entités totales: {graph_overview['total_entities']}
🤝 Relations totales: {graph_overview['total_relationships']}
⏰ Dernière évolution: {graph_overview['last_evolution']}
🎯 Entités populaires: {', '.join(graph_overview['top_entities'][:5])}"""
                
            elif action == "search" and entity:
                # Recherche entité spécifique
                entity_info = await self.orchestrator.search_pkg_entity(entity)
                
                if entity_info:
                    return f"""🔍 **Entité '{entity}':**
🏷️ Type: {entity_info['type']}
🤝 Relations: {entity_info['relationship_count']}
⏰ Première mention: {entity_info['first_seen']}
📈 Évolutions: {entity_info['evolution_count']}"""
                else:
                    return f"❌ Entité '{entity}' non trouvée dans le PKG"
                    
            else:
                return """📋 **Commandes /pkg disponibles:**
• `/pkg explore` - Vue d'ensemble du graphe
• `/pkg search [entity]` - Recherche entité spécifique"""
                
        except Exception as e:
            return f"❌ Erreur commande /pkg: {str(e)}"
    
    async def trigger_temporal_evolution(self, force: bool = False) -> str:
        """
        Commande /evolve - Déclenche évolution temporelle PKG
        Usage: /evolve [--force]
        """
        try:
            evolution_result = await self.zep_memory.evolve_personal_graph({
                "trigger": "manual_evolution",
                "force": force,
                "timestamp": datetime.now().isoformat()
            })
            
            if "error" in evolution_result:
                return f"❌ Erreur évolution: {evolution_result['error']}"
            
            return f"""🧬 **Évolution temporelle PKG:**
🔗 Entités extraites: {evolution_result['entities_extracted']}
🤝 Relations inférées: {evolution_result['relationships_inferred']}
📈 Résultat évolution: {evolution_result['graph_evolution']}
⏰ Timestamp: {evolution_result['timestamp']}"""
            
        except Exception as e:
            return f"❌ Erreur commande /evolve: {str(e)}"
```

## 📁 Configuration Claude Code (.claude/agent-config.json)

```json
{
  "personal_agent": {
    "version": "1.0.0",
    "memory_provider": "zep",
    "memory_endpoint": "http://localhost:8081",
    "data_sources": ["notion", "local_files", "git", "zep_memory"],
    "agent_network": {
      "protocol": "acp_primary_a2a_fallback",
      "local_discovery": "http://localhost:8080/discovery",
      "remote_registry": "https://your-domain.com/agent-registry",
      "heartbeat_interval": 30
    },
    "ui_mode": "claude_code_primary_with_web_overlay",
    "performance": {
      "memory_token_limit": 1600,
      "cache_ttl": 300,
      "max_concurrent_agents": 5
    }
  },
  "integrations": {
    "zep": {
      "api_key_env": "ZEP_API_KEY",
      "base_url": "https://api.getzep.com",
      "session_management": "automatic",
      "memory_sync": "real_time",
      "enable_temporal_evolution": true
    },
    "notion": {
      "token_env": "NOTION_TOKEN",
      "mcp_enabled": true,
      "auto_sync": true,
      "sync_frequency": "on_change",
      "max_pages_per_sync": 20
    },
    "ollama": {
      "base_url": "http://localhost:11434",
      "model": "llama3.2:latest",
      "enable_edge_processing": true
    }
  },
  "custom_commands": {
    "/memory": {
      "description": "Recherche mémoire Zep avec contexte temporel",
      "usage": "/memory [query] --timeframe [optional]",
      "examples": ["/memory réunion équipe", "/memory projet --timeframe 7d"]
    },
    "/notion": {
      "description": "Sync bidirectionnel Notion ↔ PKG + Zep",
      "usage": "/notion sync|search|update [target]",
      "examples": ["/notion sync", "/notion search Claude Code", "/notion update"]
    },
    "/agents": {
      "description": "Status et contrôle réseau agents ACP/A2A",
      "usage": "/agents status|deploy|discover [capability]",
      "examples": ["/agents status", "/agents discover memory"]
    },
    "/context": {
      "description": "Assembly contexte optimisé Zep (1.6k tokens)",
      "usage": "/context [scope] --depth [shallow|deep]",
      "examples": ["/context projet personnel", "/context --depth deep"]
    },
    "/pkg": {
      "description": "Navigation Personal Knowledge Graph temporel",
      "usage": "/pkg explore|search|visualize [entity]",
      "examples": ["/pkg explore", "/pkg search Claude"]
    },
    "/evolve": {
      "description": "Déclenche évolution temporelle PKG",
      "usage": "/evolve [--force]",
      "examples": ["/evolve", "/evolve --force"]
    }
  },
  "logging": {
    "level": "INFO",
    "format": "structured",
    "outputs": ["console", "file"],
    "agent_telemetry": true
  }
}
```

## 🚀 Plan de développement par phases

### Phase 1: Fondations et POC (Semaines 1-2)

#### Milestone 1.1: Setup UV + Structure modulaire
```bash
# Initialisation projet
uv init personal-agent-pkg
cd personal-agent-pkg
echo "3.12" > .python-version

# Dependencies avec UV (ultra-rapide)
uv add fastapi uvicorn neo4j qdrant-client ollama-python notion-client langchain zep-python
uv add --dev pytest black flake8 mypy

# Structure modulaire
mkdir -p core/{agents,protocols,graph,memory}
mkdir -p integrations/{notion,claude_code,mobile}
mkdir -p edge/{local_processing,sync}
mkdir -p interfaces/{api,web}
mkdir -p config tests docs
```

#### Milestone 1.2: BasePersonalAgent + Zep Memory
- Implémentation `BasePersonalAgent` avec Zep integration native
- Configuration logging structuré et health checks
- Tests unitaires pour mémoire temporelle

#### Milestone 1.3: ZepPersonalMemoryEngine
- Moteur mémoire avec évolution PKG automatique
- Assembly contexte optimisé (1.6k tokens)
- Bi-temporal tracking (event + system timelines)

#### Milestone 1.4: NotionZepBridge
- Sync bidirectionnel Notion ↔ Zep Memory
- Extraction entités et enrichissement PKG
- Recherche unifiée cross-platform

#### Milestone 1.5: Claude Code Extension
- Extension avec commandes slash personnalisées
- Configuration .claude/agent-config.json
- Interface web overlay pour visualisations

**Deliverable Phase 1**: Agent qui lit Notion → mémorise Zep → répond via Claude Code

### Phase 2: Intelligence et Évolution (Semaines 3-4)

#### Milestone 2.1: Auto-évolution PKG temporelle
- Détection patterns comportementaux
- Évolution préférences utilisateur
- Apprentissage continu avec Zep

#### Milestone 2.2: Edge Processing + Mobile Sync
- Agent edge avec Ollama local
- Sync intelligent cloud ↔ edge
- Processing vocal optimisé

#### Milestone 2.3: Multi-agents ACP/A2A
- Communication agents via URLs
- Discovery automatique et orchestration
- Fallback graceful local → remote

#### Milestone 2.4: Performance Optimization
- Optimisation mémoire Zep (90% latence réduite)
- Cache intelligent et compression tokens
- Monitoring et observabilité

**Deliverable Phase 2**: Écosystème agents collaboratifs avec mémoire évolutive

### Phase 3: Interface Unifiée (Semaines 5-6)

#### Milestone 3.1: Claude Code Interface Complète
- Commandes slash opérationnelles
- Web overlay avec visualisations PKG
- Workflow intégré développement + assistance

#### Milestone 3.2: Mobile Companion App
- React Native avec sync Zep temps réel
- Capture rapide (vocal, photo, texte)
- Continuité parfaite desktop ↔ mobile

#### Milestone 3.3: API Orchestration Backend
- FastAPI avec WebSocket temps réel
- Orchestration agents intelligente
- Load balancing et scaling

**Deliverable Phase 3**: Expérience utilisateur unifiée cross-platform

### Phase 4: Production et Déploiement (Semaines 7-8)

#### Milestone 4.1: Infrastructure Production
- Docker-compose complet
- Monitoring et alerting
- Backup et disaster recovery

#### Milestone 4.2: Security by Design
- Chiffrement end-to-end
- Access control granulaire
- Audit logs complets

#### Milestone 4.3: Documentation et Formation
- Documentation utilisateur complète
- Guides développeur et API
- Training matériel

**Deliverable Phase 4**: Solution production-ready avec monitoring complet

## 📊 Métriques de succès et KPIs

### Métriques techniques (mesurables)
- **Performance**: < 200ms réponse agents locaux, < 2s sync mobile/desktop
- **Memory Efficiency**: 90% réduction latence Zep vs traditionnel, 1.6k tokens vs 115k
- **Reliability**: > 99.5% uptime agents + memory layer
- **Speed**: 10-100x improvement avec UV vs Poetry
- **Accuracy**: > 90% précision extraction entités, 100% amélioration vs baseline

### Métriques utilisateur (expérience)
- **Productivity**: 50% réduction temps recherche information
- **Relevance**: 80%+ suggestions contextuelles pertinentes
- **Adoption**: Usage quotidien stable après 2 semaines
- **Satisfaction**: NPS > 8/10 après 1 mois
- **Learning**: Continuité contexte cross-platform parfaite

### Métriques business (ROI)
- **Development Speed**: 3x faster development avec UV + Claude Code
- **Maintenance**: 60% réduction temps debug avec logging structuré
- **Scalability**: Support 100+ agents simultanés
- **Cost**: 40% réduction coûts infrastructure avec edge processing

## 🔧 Environnement de développement

### Variables d'environnement requises
```bash
# Zep Memory
ZEP_API_KEY=your_zep_api_key
ZEP_BASE_URL=https://api.getzep.com

# Notion Integration  
NOTION_TOKEN=your_notion_integration_token

# Neo4j (optionnel pour visualisations avancées)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# Qdrant Vector Store
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Ollama Edge Processing
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:latest

# Logging et Monitoring
LOG_LEVEL=INFO
ENABLE_TELEMETRY=true
```

### Commandes de développement
```bash
# Setup environnement
uv sync
uv run pre-commit install

# Tests
uv run pytest tests/ -v --cov=core
uv run pytest tests/test_memory/ -v

# Linting et formatting
uv run black .
uv run flake8 .
uv run mypy core/

# Démarrage services
uv run uvicorn interfaces.api.main:app --reload --port 8080
uv run python -m core.agents.orchestrator  # Agent principal

# Claude Code
claude  # Lit automatiquement CLAUDE.md + configuration
```

## 🏗️ Architecture de déploiement

### Docker Compose Production
```yaml
version: '3.8'
services:
  personal-agent-api:
    build: .
    environment:
      - ZEP_API_KEY=${ZEP_API_KEY}
      - NOTION_TOKEN=${NOTION_TOKEN}
    ports:
      - "8080:8080"
    depends_on:
      - neo4j
      - qdrant
      - redis
      
  zep-memory-service:
    image: getzep/zep:latest
    environment:
      - ZEP_DATABASE_URL=${ZEP_DATABASE_URL}
    ports:
      - "8081:8000"
      
  neo4j:
    image: neo4j:5.15
    environment:
      - NEO4J_AUTH=neo4j/${NEO4J_PASSWORD}
    ports:
      - "7474:7474"
      - "7687:7687"
    volumes:
      - neo4j_data:/data
      
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage
      
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
      
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./certs:/etc/nginx/certs

volumes:
  neo4j_data:
  qdrant_data:
  redis_data:
```

## 🧪 Stratégie de test

### Tests unitaires
```python
# tests/test_memory/test_zep_engine.py
import pytest
from core.memory.zep_engine import ZepPersonalMemoryEngine

@pytest.mark.asyncio
async def test_zep_memory_search():
    engine = ZepPersonalMemoryEngine("test_user")
    await engine.initialize_session()
    
    results = await engine.semantic_search_with_context("test query")
    assert isinstance(results, list)

@pytest.mark.asyncio 
async def test_pkg_evolution():
    engine = ZepPersonalMemoryEngine("test_user")
    
    result = await engine.evolve_personal_graph({
        "content": "Test interaction for PKG evolution"
    })
    
    assert "entities_extracted" in result
    assert "relationships_inferred" in result
```

### Tests d'intégration
```python
# tests/test_integrations/test_notion_bridge.py
@pytest.mark.asyncio
async def test_notion_zep_sync():
    bridge = NotionZepBridge("test_user", "test_token")
    
    sync_result = await bridge.sync_notion_to_zep(pages_limit=5)
    
    assert sync_result["pages_processed"] >= 0
    assert "errors" in sync_result
```

### Tests performance
```python
# tests/test_performance/test_memory_latency.py
@pytest.mark.performance
async def test_zep_memory_latency():
    start_time = time.time()
    
    results = await zep_engine.semantic_search_with_context("test")
    
    latency = time.time() - start_time
    assert latency < 0.2  # < 200ms requirement
```

---

**Instructions finales pour Claude Code**: 
1. Utilise ce plan comme référence technique complète
2. Implémente selon les phases définies
3. Respecte l'architecture Zep + UV + protocoles A2A/ACP
4. Priorise tests, performance, et modularité
5. Maintiens la compatibilité avec configuration .claude/agent-config.json
6. Documente chaque composant avec exemples d'usage