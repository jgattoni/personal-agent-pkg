"""
NotionZepBridge - Pont bidirectionnel Notion ↔ Zep avec extraction d'entités
Utilise MCP Notion server + GraphitiEngine pour synchronisation intelligente
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import hashlib
from pydantic import BaseModel, Field

# Import conditionnel Notion
try:
    from notion_client import Client as NotionClient
    HAS_NOTION = True
except ImportError:
    HAS_NOTION = False
    NotionClient = None


class SyncStatus(str, Enum):
    """Statuts de synchronisation"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class NotionPageType(str, Enum):
    """Types de pages Notion détectés"""
    DATABASE_ENTRY = "database_entry"
    DOCUMENT = "document"
    TASK = "task"
    MEETING_NOTES = "meeting_notes"
    PROJECT = "project"
    PERSON = "person"
    RESOURCE = "resource"
    UNKNOWN = "unknown"


@dataclass
class NotionPage:
    """Représentation d'une page Notion"""
    page_id: str
    title: str
    content: str
    page_type: NotionPageType = NotionPageType.UNKNOWN
    last_edited: datetime = field(default_factory=datetime.now)
    properties: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    mentions: List[str] = field(default_factory=list)
    database_id: Optional[str] = None
    parent_id: Optional[str] = None
    url: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Conversion en dictionnaire"""
        return {
            "page_id": self.page_id,
            "title": self.title,
            "content": self.content,
            "page_type": self.page_type.value,
            "last_edited": self.last_edited.isoformat(),
            "properties": self.properties,
            "tags": self.tags,
            "mentions": self.mentions,
            "database_id": self.database_id,
            "parent_id": self.parent_id,
            "url": self.url
        }


class SyncResult(BaseModel):
    """Résultat d'une synchronisation"""
    status: SyncStatus = Field(..., description="Statut de la sync")
    pages_processed: int = Field(default=0, description="Nombre de pages traitées")
    entities_extracted: int = Field(default=0, description="Entités extraites")
    memories_created: int = Field(default=0, description="Mémoires créées")
    errors: List[str] = Field(default_factory=list, description="Erreurs rencontrées")
    duration_seconds: float = Field(default=0.0, description="Durée de la sync")
    last_sync: datetime = Field(default_factory=datetime.now, description="Timestamp de sync")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Métadonnées additionnelles")


class NotionZepBridge:
    """
    Pont intelligent entre Notion et Zep Memory
    
    Fonctionnalités:
    - Extraction automatique du contenu Notion
    - Classification intelligente des pages
    - Extraction d'entités avec GraphitiEngine  
    - Synchronisation bidirectionnelle Notion ↔ Zep
    - Monitoring et statistiques
    """
    
    def __init__(
        self,
        user_id: str,
        notion_token: Optional[str] = None,
        zep_memory_engine=None,
        graphiti_engine=None,
        mcp_manager=None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialise le bridge Notion-Zep
        
        Args:
            user_id: Identifiant utilisateur
            notion_token: Token API Notion (optionnel si MCP utilisé)
            zep_memory_engine: Moteur mémoire Zep
            graphiti_engine: Moteur GraphitiEngine pour extraction entités
            mcp_manager: Manager MCP pour accès Notion
            config: Configuration additionnelle
        """
        self.user_id = user_id
        self.notion_token = notion_token
        self.zep_memory_engine = zep_memory_engine
        self.graphiti_engine = graphiti_engine
        self.mcp_manager = mcp_manager
        self.config = config or {}
        self.logger = logging.getLogger(f"notion_bridge.{user_id}")
        
        # État du bridge
        self.is_initialized = False
        self.last_sync = None
        self.sync_in_progress = False
        
        # Client Notion (direct ou via MCP)
        self.notion_client = None
        self.use_mcp = self.config.get("use_mcp", True) and mcp_manager is not None
        
        # Cache des pages
        self.pages_cache: Dict[str, NotionPage] = {}
        self.sync_history: List[SyncResult] = []
        
        # Configuration sync
        self.sync_interval_hours = config.get("sync_interval_hours", 24)
        self.max_pages_per_sync = config.get("max_pages_per_sync", 50)
        self.enable_auto_sync = config.get("enable_auto_sync", True)
        self.sync_filters = config.get("sync_filters", {
            "include_databases": True,
            "include_pages": True,
            "skip_archived": True,
            "min_content_length": 50
        })
        
        # Patterns de détection de type de page
        self.page_type_patterns = {
            NotionPageType.TASK: [
                "todo", "task", "tâche", "à faire", "deadline", "due",
                "assignee", "priority", "status", "done", "completed"
            ],
            NotionPageType.MEETING_NOTES: [
                "meeting", "réunion", "notes", "agenda", "participants",
                "action items", "decisions", "minutes"  
            ],
            NotionPageType.PROJECT: [
                "project", "projet", "roadmap", "milestone", "sprint",
                "timeline", "deliverable", "scope"
            ],
            NotionPageType.PERSON: [
                "contact", "person", "personne", "team member", "profile",
                "role", "email", "phone", "skills"
            ],
            NotionPageType.RESOURCE: [
                "resource", "link", "reference", "documentation", "guide",
                "tutorial", "bookmark", "tools"
            ]
        }
        
        # Stats
        self.stats = {
            "total_syncs": 0,
            "pages_synced": 0,
            "entities_extracted": 0,
            "memories_created": 0,
            "sync_errors": 0,
            "last_sync_duration": 0.0
        }
    
    async def initialize(self) -> bool:
        """Initialise le bridge"""
        try:
            self.logger.info(f"Initializing Notion-Zep bridge for user {self.user_id}")
            
            # Initialisation client Notion
            if self.use_mcp and self.mcp_manager:
                # Via MCP
                await self._init_notion_via_mcp()
            elif self.notion_token and HAS_NOTION:
                # Direct
                self.notion_client = NotionClient(auth=self.notion_token)
            else:
                self.logger.warning("No Notion access method available, running in mock mode")
            
            # Vérification des dépendances
            if not self.zep_memory_engine:
                self.logger.warning("No Zep memory engine provided")
            
            if not self.graphiti_engine:
                self.logger.warning("No Graphiti engine provided")
            
            # Démarrage sync automatique si activé
            if self.enable_auto_sync:
                asyncio.create_task(self._periodic_sync())
            
            self.is_initialized = True
            self.logger.info("Notion-Zep bridge initialized successfully")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize bridge: {str(e)}")
            return False
    
    async def _init_notion_via_mcp(self) -> None:
        """Initialise l'accès Notion via MCP"""
        try:
            # Connexion au serveur MCP Notion
            await self.mcp_manager.connect_notion_server(self.notion_token)
            
            # Vérification des outils disponibles
            notion_tools = await self.mcp_manager.discover_tools("notion")
            self.logger.info(f"Notion MCP tools available: {[tool.name for tool in notion_tools]}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Notion MCP: {str(e)}")
            self.use_mcp = False
    
    async def sync_notion_to_zep(
        self, 
        database_ids: Optional[List[str]] = None,
        page_ids: Optional[List[str]] = None,
        force_full_sync: bool = False
    ) -> SyncResult:
        """
        Synchronise le contenu Notion vers Zep Memory
        
        Args:
            database_ids: IDs des databases à synchroniser (optionnel)
            page_ids: IDs des pages spécifiques à synchroniser (optionnel)  
            force_full_sync: Force une sync complète même si récente
            
        Returns:
            SyncResult avec les détails de la synchronisation
        """
        if self.sync_in_progress:
            return SyncResult(
                status=SyncStatus.FAILED,
                errors=["Sync already in progress"]
            )
        
        self.sync_in_progress = True
        start_time = datetime.now()
        
        try:
            self.logger.info("Starting Notion → Zep synchronization")
            
            # 1. Découverte des pages à synchroniser
            pages_to_sync = await self._discover_pages_to_sync(
                database_ids, page_ids, force_full_sync
            )
            
            self.logger.info(f"Found {len(pages_to_sync)} pages to sync")
            
            # 2. Extraction et traitement des pages
            sync_result = SyncResult(status=SyncStatus.IN_PROGRESS)
            
            for page_info in pages_to_sync[:self.max_pages_per_sync]:
                try:
                    # Extraction du contenu
                    page = await self._extract_page_content(page_info)
                    if not page:
                        continue
                    
                    # Classification du type de page
                    page.page_type = self._classify_page_type(page)
                    
                    # Extraction d'entités avec Graphiti
                    entities = []
                    if self.graphiti_engine:
                        episode = await self.graphiti_engine.ingest_episode(
                            content=f"Notion: {page.title}\n\n{page.content}",
                            source="notion",
                            metadata={
                                "page_id": page.page_id,
                                "page_type": page.page_type.value,
                                "url": page.url,
                                "properties": page.properties
                            }
                        )
                        entities = episode.entities_extracted
                        sync_result.entities_extracted += len(entities)
                    
                    # Création mémoire Zep
                    if self.zep_memory_engine:
                        memory = await self.zep_memory_engine.add_memory(
                            content=f"[{page.page_type.value.upper()}] {page.title}: {page.content}",
                            response=f"Page Notion '{page.title}' synchronisée avec {len(entities)} entités extraites",
                            memory_type=self._notion_type_to_memory_type(page.page_type),
                            importance=self._calculate_page_importance(page),
                            metadata={
                                "source": "notion_bridge",
                                "page_id": page.page_id,
                                "page_type": page.page_type.value,
                                "url": page.url,
                                "entities": [e.name for e in entities] if entities else [],
                                "properties": page.properties,
                                "last_edited": page.last_edited.isoformat()
                            }
                        )
                        sync_result.memories_created += 1
                    
                    # Mise en cache
                    self.pages_cache[page.page_id] = page
                    sync_result.pages_processed += 1
                    
                    self.logger.debug(f"Synced page: {page.title} ({page.page_type.value})")
                    
                except Exception as e:
                    error_msg = f"Error processing page {page_info.get('id', 'unknown')}: {str(e)}"
                    self.logger.error(error_msg)
                    sync_result.errors.append(error_msg)
            
            # 3. Finalisation
            end_time = datetime.now()
            sync_result.duration_seconds = (end_time - start_time).total_seconds()
            sync_result.last_sync = end_time
            
            if sync_result.errors:
                sync_result.status = SyncStatus.PARTIAL if sync_result.pages_processed > 0 else SyncStatus.FAILED
            else:
                sync_result.status = SyncStatus.COMPLETED
            
            # 4. Mise à jour stats
            self.stats["total_syncs"] += 1
            self.stats["pages_synced"] += sync_result.pages_processed
            self.stats["entities_extracted"] += sync_result.entities_extracted
            self.stats["memories_created"] += sync_result.memories_created
            self.stats["last_sync_duration"] = sync_result.duration_seconds
            if sync_result.errors:
                self.stats["sync_errors"] += len(sync_result.errors)
            
            self.last_sync = end_time
            self.sync_history.append(sync_result)
            
            # Garder seulement les 10 derniers historiques
            if len(self.sync_history) > 10:
                self.sync_history = self.sync_history[-10:]
            
            self.logger.info(
                f"Sync completed: {sync_result.pages_processed} pages, "
                f"{sync_result.entities_extracted} entities, "
                f"{sync_result.memories_created} memories, "
                f"{len(sync_result.errors)} errors in {sync_result.duration_seconds:.1f}s"
            )
            
            return sync_result
            
        except Exception as e:
            error_msg = f"Sync failed: {str(e)}"
            self.logger.error(error_msg)
            
            return SyncResult(
                status=SyncStatus.FAILED,
                errors=[error_msg],
                duration_seconds=(datetime.now() - start_time).total_seconds()
            )
        
        finally:
            self.sync_in_progress = False
    
    async def _discover_pages_to_sync(
        self,
        database_ids: Optional[List[str]],
        page_ids: Optional[List[str]],
        force_full_sync: bool
    ) -> List[Dict[str, Any]]:
        """Découvre les pages Notion à synchroniser"""
        pages_to_sync = []
        
        try:
            if self.use_mcp and self.mcp_manager:
                # Via MCP
                if database_ids:
                    for db_id in database_ids:
                        db_pages = await self.mcp_manager.execute_tool(
                            "notion",
                            "query_database",
                            {"database_id": db_id}
                        )
                        if db_pages and "results" in db_pages:
                            pages_to_sync.extend(db_pages["results"])
                
                if page_ids:
                    for page_id in page_ids:
                        page_info = await self.mcp_manager.execute_tool(
                            "notion",
                            "retrieve_page",
                            {"page_id": page_id}
                        )
                        if page_info:
                            pages_to_sync.append(page_info)
                
                # Si aucun ID spécifié, recherche globale
                if not database_ids and not page_ids:
                    search_result = await self.mcp_manager.execute_tool(
                        "notion",
                        "search",
                        {
                            "query": "",
                            "sort": {"direction": "descending", "timestamp": "last_edited_time"},
                            "page_size": self.max_pages_per_sync
                        }
                    )
                    if search_result and "results" in search_result:
                        pages_to_sync = search_result["results"]
            
            elif self.notion_client:
                # Client direct Notion
                if database_ids:
                    for db_id in database_ids:
                        response = self.notion_client.databases.query(database_id=db_id)
                        pages_to_sync.extend(response.get("results", []))
                
                if page_ids:
                    for page_id in page_ids:
                        page = self.notion_client.pages.retrieve(page_id=page_id)
                        pages_to_sync.append(page)
                
                # Recherche globale
                if not database_ids and not page_ids:
                    response = self.notion_client.search(
                        query="",
                        sort={"direction": "descending", "timestamp": "last_edited_time"},
                        page_size=self.max_pages_per_sync
                    )
                    pages_to_sync = response.get("results", [])
            
            else:
                # Mode mock pour développement
                pages_to_sync = [
                    {
                        "id": "mock-page-1",
                        "object": "page",
                        "properties": {"title": {"title": [{"plain_text": "Page de test 1"}]}},
                        "last_edited_time": datetime.now().isoformat(),
                        "url": "https://notion.so/mock1"
                    },
                    {
                        "id": "mock-page-2", 
                        "object": "page",
                        "properties": {"title": {"title": [{"plain_text": "Réunion équipe"}]}},
                        "last_edited_time": datetime.now().isoformat(),
                        "url": "https://notion.so/mock2"
                    }
                ]
                self.logger.warning("Using mock pages for development")
            
            # Filtrage selon configuration
            if not force_full_sync and self.last_sync:
                cutoff_time = self.last_sync - timedelta(hours=1)  # Buffer d'1h
                pages_to_sync = [
                    page for page in pages_to_sync
                    if datetime.fromisoformat(page.get("last_edited_time", "1970-01-01").replace("Z", "+00:00")) > cutoff_time
                ]
            
            # Filtrage par type et taille
            filtered_pages = []
            for page in pages_to_sync:
                # Skip pages archivées
                if self.sync_filters["skip_archived"] and page.get("archived", False):
                    continue
                
                # Include selon type
                if page.get("object") == "database" and not self.sync_filters["include_databases"]:
                    continue
                if page.get("object") == "page" and not self.sync_filters["include_pages"]:
                    continue
                
                filtered_pages.append(page)
            
            return filtered_pages
            
        except Exception as e:
            self.logger.error(f"Error discovering pages: {str(e)}")
            return []
    
    async def _extract_page_content(self, page_info: Dict[str, Any]) -> Optional[NotionPage]:
        """Extrait le contenu d'une page Notion"""
        try:
            page_id = page_info["id"]
            
            # Extraction titre
            title = "Untitled"
            if "properties" in page_info:
                # Recherche propriété titre
                for prop_name, prop_value in page_info["properties"].items():
                    if prop_value.get("type") == "title" and prop_value.get("title"):
                        title = prop_value["title"][0]["plain_text"]
                        break
            
            # Extraction contenu
            content = ""
            if self.use_mcp and self.mcp_manager:
                # Via MCP
                blocks_result = await self.mcp_manager.execute_tool(
                    "notion",
                    "retrieve_block_children", 
                    {"block_id": page_id}
                )
                if blocks_result and "results" in blocks_result:
                    content = self._extract_text_from_blocks(blocks_result["results"])
            
            elif self.notion_client:
                # Client direct
                blocks = self.notion_client.blocks.children.list(block_id=page_id)
                content = self._extract_text_from_blocks(blocks.get("results", []))
            
            else:
                # Mode mock
                content = f"Contenu mock pour {title}. Ceci est un exemple de contenu Notion avec des informations sur le projet, les tâches, et les personnes impliquées."
            
            # Filtrage par taille minimale
            if len(content) < self.sync_filters["min_content_length"]:
                return None
            
            # Création objet NotionPage
            page = NotionPage(
                page_id=page_id,
                title=title,
                content=content,
                last_edited=datetime.fromisoformat(
                    page_info.get("last_edited_time", datetime.now().isoformat()).replace("Z", "+00:00")
                ),
                properties=page_info.get("properties", {}),
                url=page_info.get("url"),
                parent_id=page_info.get("parent", {}).get("database_id") or page_info.get("parent", {}).get("page_id")
            )
            
            return page
            
        except Exception as e:
            self.logger.error(f"Error extracting page content for {page_info.get('id')}: {str(e)}")
            return None
    
    def _extract_text_from_blocks(self, blocks: List[Dict[str, Any]]) -> str:
        """Extrait le texte des blocs Notion"""
        text_parts = []
        
        for block in blocks:
            block_type = block.get("type")
            
            if block_type in ["paragraph", "heading_1", "heading_2", "heading_3"]:
                rich_text = block.get(block_type, {}).get("rich_text", [])
                for text_obj in rich_text:
                    text_parts.append(text_obj.get("plain_text", ""))
            
            elif block_type == "bulleted_list_item":
                rich_text = block.get("bulleted_list_item", {}).get("rich_text", [])
                bullet_text = "".join([text_obj.get("plain_text", "") for text_obj in rich_text])
                text_parts.append(f"• {bullet_text}")
            
            elif block_type == "numbered_list_item":
                rich_text = block.get("numbered_list_item", {}).get("rich_text", [])
                number_text = "".join([text_obj.get("plain_text", "") for text_obj in rich_text])
                text_parts.append(f"1. {number_text}")
            
            elif block_type == "to_do":
                rich_text = block.get("to_do", {}).get("rich_text", [])
                checked = block.get("to_do", {}).get("checked", False)
                todo_text = "".join([text_obj.get("plain_text", "") for text_obj in rich_text])
                checkbox = "☑" if checked else "☐"
                text_parts.append(f"{checkbox} {todo_text}")
        
        return "\n".join(text_parts)
    
    def _classify_page_type(self, page: NotionPage) -> NotionPageType:
        """Classifie le type d'une page selon son contenu"""
        content_lower = f"{page.title} {page.content}".lower()
        
        # Score par type
        type_scores = {}
        
        for page_type, patterns in self.page_type_patterns.items():
            score = sum(1 for pattern in patterns if pattern in content_lower)
            if score > 0:
                type_scores[page_type] = score
        
        if type_scores:
            # Retourne le type avec le meilleur score
            return max(type_scores.items(), key=lambda x: x[1])[0]
        
        return NotionPageType.DOCUMENT  # Par défaut
    
    def _notion_type_to_memory_type(self, notion_type: NotionPageType):
        """Convertit un type de page Notion en type mémoire Zep"""
        from ...core.personal_agent_core.memory.zep_engine import MemoryType
        
        mapping = {
            NotionPageType.TASK: MemoryType.WORKING,
            NotionPageType.MEETING_NOTES: MemoryType.EPISODIC,
            NotionPageType.PROJECT: MemoryType.WORKING,
            NotionPageType.PERSON: MemoryType.SEMANTIC,
            NotionPageType.RESOURCE: MemoryType.SEMANTIC,
            NotionPageType.DOCUMENT: MemoryType.SEMANTIC,
            NotionPageType.DATABASE_ENTRY: MemoryType.SEMANTIC,
            NotionPageType.UNKNOWN: MemoryType.EPISODIC
        }
        
        return mapping.get(notion_type, MemoryType.EPISODIC)
    
    def _calculate_page_importance(self, page: NotionPage):
        """Calcule l'importance d'une page"""
        from ...core.personal_agent_core.memory.zep_engine import MemoryImportance
        
        # Facteurs d'importance
        importance_score = 0
        
        # Récence
        days_old = (datetime.now() - page.last_edited).days
        if days_old < 1:
            importance_score += 3
        elif days_old < 7:
            importance_score += 2
        elif days_old < 30:
            importance_score += 1
        
        # Longueur du contenu
        if len(page.content) > 1000:
            importance_score += 2
        elif len(page.content) > 500:
            importance_score += 1
        
        # Type de page
        if page.page_type in [NotionPageType.TASK, NotionPageType.PROJECT]:
            importance_score += 2
        elif page.page_type == NotionPageType.MEETING_NOTES:
            importance_score += 1
        
        # Mentions et tags
        importance_score += len(page.mentions) * 0.5
        importance_score += len(page.tags) * 0.3
        
        # Classification
        if importance_score >= 5:
            return MemoryImportance.HIGH
        elif importance_score >= 3:
            return MemoryImportance.MEDIUM
        else:
            return MemoryImportance.LOW
    
    async def _periodic_sync(self) -> None:
        """Synchronisation périodique automatique"""
        while self.enable_auto_sync:
            try:
                await asyncio.sleep(self.sync_interval_hours * 3600)
                
                if not self.sync_in_progress:
                    self.logger.info("Starting periodic sync")
                    result = await self.sync_notion_to_zep()
                    self.logger.info(f"Periodic sync completed: {result.status.value}")
                
            except Exception as e:
                self.logger.error(f"Error in periodic sync: {str(e)}")
    
    async def search_notion_content(
        self,
        query: str,
        page_types: Optional[List[NotionPageType]] = None,
        limit: int = 10
    ) -> List[NotionPage]:
        """Recherche dans le contenu Notion mis en cache"""
        results = []
        query_lower = query.lower()
        
        for page in self.pages_cache.values():
            # Filtrage par type si spécifié
            if page_types and page.page_type not in page_types:
                continue
            
            # Recherche dans titre et contenu
            if (query_lower in page.title.lower() or 
                query_lower in page.content.lower()):
                results.append(page)
        
        # Tri par pertinence (titre d'abord, puis récence)
        results.sort(key=lambda p: (
            query_lower in p.title.lower(),
            p.last_edited
        ), reverse=True)
        
        return results[:limit]
    
    def get_sync_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de synchronisation"""
        return {
            **self.stats,
            "is_initialized": self.is_initialized,
            "sync_in_progress": self.sync_in_progress,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "pages_cached": len(self.pages_cache),
            "sync_history_count": len(self.sync_history),
            "use_mcp": self.use_mcp,
            "auto_sync_enabled": self.enable_auto_sync
        }
    
    def get_recent_sync_results(self, limit: int = 5) -> List[SyncResult]:
        """Retourne les résultats de sync récents"""
        return self.sync_history[-limit:] if self.sync_history else []
    
    async def export_notion_cache(self, format: str = "json") -> Union[str, Dict[str, Any]]:
        """Exporte le cache des pages Notion"""
        cache_data = {
            "export_date": datetime.now().isoformat(),
            "user_id": self.user_id,
            "total_pages": len(self.pages_cache),
            "pages": [page.to_dict() for page in self.pages_cache.values()]
        }
        
        if format == "json":
            return json.dumps(cache_data, indent=2, ensure_ascii=False)
        else:
            return cache_data


# Factory function pour création simplifiée
async def create_notion_zep_bridge(
    user_id: str,
    notion_token: Optional[str] = None,
    zep_memory_engine=None,
    graphiti_engine=None,
    mcp_manager=None,
    config: Optional[Dict[str, Any]] = None
) -> NotionZepBridge:
    """
    Factory function pour créer et initialiser le bridge
    
    Args:
        user_id: ID utilisateur
        notion_token: Token Notion API
        zep_memory_engine: Moteur mémoire Zep
        graphiti_engine: Moteur Graphiti
        mcp_manager: Manager MCP
        config: Configuration
        
    Returns:
        Bridge Notion-Zep initialisé
    """
    bridge = NotionZepBridge(
        user_id=user_id,
        notion_token=notion_token,
        zep_memory_engine=zep_memory_engine,
        graphiti_engine=graphiti_engine,
        mcp_manager=mcp_manager,
        config=config or {}
    )
    
    await bridge.initialize()
    
    return bridge