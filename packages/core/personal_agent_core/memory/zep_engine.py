"""
ZepPersonalMemoryEngine - Moteur de mémoire personnelle avec Zep Cloud
Intégration avec Graphiti pour knowledge graph évolutif
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Union, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import hashlib
from pydantic import BaseModel, Field

# Import conditionnel Zep
try:
    from zep_python import ZepClient, Memory, Message, SearchPayload, SearchType
    HAS_ZEP = True
except ImportError:
    HAS_ZEP = False
    ZepClient = Memory = Message = SearchPayload = SearchType = None


class MemoryType(str, Enum):
    """Types de mémoire"""
    EPISODIC = "episodic"  # Événements spécifiques
    SEMANTIC = "semantic"  # Connaissances générales
    PROCEDURAL = "procedural"  # Comment faire les choses
    WORKING = "working"  # Mémoire de travail courante
    PREFERENCE = "preference"  # Préférences utilisateur
    BEHAVIORAL = "behavioral"  # Patterns comportementaux


class MemoryImportance(str, Enum):
    """Importance des mémoires"""
    CRITICAL = "critical"  # Ne jamais oublier
    HIGH = "high"  # Important à long terme
    MEDIUM = "medium"  # Utile régulièrement
    LOW = "low"  # Peut être oublié
    TRANSIENT = "transient"  # Temporaire


@dataclass
class MemoryContext:
    """Contexte enrichi pour une mémoire"""
    session_id: str
    user_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "direct"
    confidence: float = 1.0
    importance: MemoryImportance = MemoryImportance.MEDIUM
    memory_type: MemoryType = MemoryType.EPISODIC
    entities: List[str] = field(default_factory=list)
    relationships: List[Tuple[str, str, str]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    ttl_hours: Optional[int] = None  # Time to live pour mémoires temporaires


class PersonalMemory(BaseModel):
    """Mémoire personnelle enrichie"""
    memory_id: str = Field(..., description="ID unique de la mémoire")
    content: str = Field(..., description="Contenu de la mémoire")
    context: MemoryContext = Field(..., description="Contexte enrichi")
    embedding: Optional[List[float]] = Field(None, description="Vecteur embedding")
    summary: Optional[str] = Field(None, description="Résumé de la mémoire")
    facts_extracted: List[str] = Field(default_factory=list, description="Faits extraits")
    created_at: datetime = Field(default_factory=datetime.now)
    accessed_count: int = Field(default=0, description="Nombre d'accès")
    last_accessed: Optional[datetime] = Field(None)
    decay_factor: float = Field(default=1.0, description="Facteur de déclin temporel")
    
    def update_access(self):
        """Met à jour les stats d'accès"""
        self.accessed_count += 1
        self.last_accessed = datetime.now()
    
    def calculate_relevance(self, days_old: int) -> float:
        """Calcule la pertinence basée sur l'âge et l'importance"""
        base_decay = 0.95 ** days_old  # Déclin exponentiel
        
        importance_boost = {
            MemoryImportance.CRITICAL: 1.0,  # Pas de déclin
            MemoryImportance.HIGH: 0.9,
            MemoryImportance.MEDIUM: 0.7,
            MemoryImportance.LOW: 0.5,
            MemoryImportance.TRANSIENT: 0.1
        }
        
        boost = importance_boost.get(self.context.importance, 0.5)
        access_boost = min(self.accessed_count * 0.1, 0.5)  # Boost pour accès fréquents
        
        return min(base_decay * boost + access_boost, 1.0)


class MemoryCluster(BaseModel):
    """Cluster de mémoires liées"""
    cluster_id: str = Field(..., description="ID du cluster")
    theme: str = Field(..., description="Thème principal")
    memory_ids: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    last_updated: datetime = Field(default_factory=datetime.now)
    importance_score: float = Field(default=0.5)


class ZepPersonalMemoryEngine:
    """
    Moteur de mémoire personnelle avec Zep Cloud
    Gère la persistence, recherche et évolution temporelle des mémoires
    """
    
    def __init__(
        self,
        user_id: str,
        zep_client=None,
        graphiti_engine=None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialise le moteur de mémoire
        
        Args:
            user_id: ID utilisateur
            zep_client: Client Zep pour persistence cloud
            graphiti_engine: Moteur Graphiti pour knowledge graph
            config: Configuration additionnelle
        """
        self.user_id = user_id
        self.zep_client = zep_client
        self.graphiti_engine = graphiti_engine
        self.config = config or {}
        self.logger = logging.getLogger(f"memory.{user_id}")
        
        # Sessions Zep
        self.primary_session_id = f"user_{user_id}_primary"
        self.working_session_id = f"user_{user_id}_working"
        
        # Caches locaux pour performance
        self.memory_cache: Dict[str, PersonalMemory] = {}
        self.cluster_cache: Dict[str, MemoryCluster] = {}
        self.preference_cache: Dict[str, Any] = {}
        
        # Configuration mémoire
        self.max_working_memory = config.get("max_working_memory", 10) if config else 10
        self.cache_ttl_minutes = config.get("cache_ttl_minutes", 15) if config else 15
        self.auto_summarize = config.get("auto_summarize", True) if config else True
        self.enable_clustering = config.get("enable_clustering", True) if config else True
        
        # Stats
        self.stats = {
            "memories_created": 0,
            "memories_retrieved": 0,
            "searches_performed": 0,
            "clusters_formed": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
        
        # Temporal evolution
        self.last_consolidation = datetime.now()
        self.consolidation_interval_hours = config.get("consolidation_hours", 24) if config else 24
    
    async def initialize(self) -> None:
        """Initialise le moteur de mémoire et les sessions Zep"""
        try:
            self.logger.info(f"Initializing memory engine for user {self.user_id}")
            
            if not HAS_ZEP:
                self.logger.warning("Zep client not available, running in local mode")
                return
            
            if self.zep_client:
                # Création des sessions Zep si nécessaire
                await self._ensure_sessions_exist()
                
                # Chargement des préférences utilisateur
                await self._load_user_preferences()
                
                # Chargement mémoire de travail récente
                await self._load_working_memory()
            
            # Démarrage processus de consolidation périodique
            asyncio.create_task(self._periodic_memory_consolidation())
            
            self.logger.info("Memory engine initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize memory engine: {str(e)}")
            raise
    
    async def _ensure_sessions_exist(self) -> None:
        """S'assure que les sessions Zep existent"""
        if not self.zep_client:
            return
        
        try:
            # Session primaire pour mémoire long terme
            sessions = await self.zep_client.memory.list_sessions()
            if self.primary_session_id not in [s.session_id for s in sessions]:
                await self.zep_client.memory.add_session(
                    session_id=self.primary_session_id,
                    metadata={
                        "user_id": self.user_id,
                        "type": "primary",
                        "created_at": datetime.now().isoformat()
                    }
                )
            
            # Session working pour mémoire de travail
            if self.working_session_id not in [s.session_id for s in sessions]:
                await self.zep_client.memory.add_session(
                    session_id=self.working_session_id,
                    metadata={
                        "user_id": self.user_id,
                        "type": "working",
                        "created_at": datetime.now().isoformat()
                    }
                )
            
        except Exception as e:
            self.logger.error(f"Error ensuring sessions exist: {str(e)}")
    
    async def _load_user_preferences(self) -> None:
        """Charge les préférences utilisateur depuis Zep"""
        try:
            if not self.zep_client:
                return
            
            # Recherche mémoires de type préférence
            search_result = await self.zep_client.memory.search_memory(
                session_id=self.primary_session_id,
                search_payload=SearchPayload(
                    text="preferences settings configuration",
                    search_type=SearchType.similarity,
                    search_scope="metadata"
                ),
                limit=20
            )
            
            for result in search_result:
                if result.metadata and result.metadata.get("memory_type") == MemoryType.PREFERENCE.value:
                    pref_key = result.metadata.get("preference_key")
                    pref_value = result.metadata.get("preference_value")
                    if pref_key:
                        self.preference_cache[pref_key] = pref_value
            
            self.logger.info(f"Loaded {len(self.preference_cache)} user preferences")
            
        except Exception as e:
            self.logger.warning(f"Could not load preferences: {str(e)}")
    
    async def _load_working_memory(self) -> None:
        """Charge la mémoire de travail récente"""
        try:
            if not self.zep_client:
                return
            
            # Récupération des dernières mémoires de la session working
            memories = await self.zep_client.memory.get_memory(
                session_id=self.working_session_id,
                limit=self.max_working_memory
            )
            
            for memory in memories:
                memory_id = memory.metadata.get("memory_id") if memory.metadata else None
                if memory_id:
                    # Conversion en PersonalMemory pour le cache
                    personal_memory = self._zep_to_personal_memory(memory)
                    self.memory_cache[memory_id] = personal_memory
            
            self.logger.info(f"Loaded {len(self.memory_cache)} working memories")
            
        except Exception as e:
            self.logger.warning(f"Could not load working memory: {str(e)}")
    
    def _zep_to_personal_memory(self, zep_memory: Any) -> PersonalMemory:
        """Convertit une mémoire Zep en PersonalMemory"""
        metadata = zep_memory.metadata or {}
        
        context = MemoryContext(
            session_id=metadata.get("session_id", self.primary_session_id),
            user_id=self.user_id,
            timestamp=datetime.fromisoformat(metadata.get("timestamp", datetime.now().isoformat())),
            source=metadata.get("source", "zep"),
            confidence=metadata.get("confidence", 1.0),
            importance=MemoryImportance(metadata.get("importance", MemoryImportance.MEDIUM.value)),
            memory_type=MemoryType(metadata.get("memory_type", MemoryType.EPISODIC.value)),
            entities=metadata.get("entities", []),
            relationships=metadata.get("relationships", []),
            metadata=metadata
        )
        
        return PersonalMemory(
            memory_id=metadata.get("memory_id", self._generate_memory_id(zep_memory.content)),
            content=zep_memory.content,
            context=context,
            summary=metadata.get("summary"),
            facts_extracted=metadata.get("facts", []),
            created_at=datetime.fromisoformat(metadata.get("created_at", datetime.now().isoformat())),
            accessed_count=metadata.get("accessed_count", 0)
        )
    
    def _generate_memory_id(self, content: str) -> str:
        """Génère un ID unique pour une mémoire"""
        hash_input = f"{self.user_id}_{content}_{datetime.now().isoformat()}"
        return hashlib.md5(hash_input.encode()).hexdigest()[:12]
    
    async def add_memory(
        self,
        content: str,
        response: Optional[str] = None,
        memory_type: MemoryType = MemoryType.EPISODIC,
        importance: MemoryImportance = MemoryImportance.MEDIUM,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PersonalMemory:
        """
        Ajoute une nouvelle mémoire
        
        Args:
            content: Contenu de la mémoire
            response: Réponse associée (optionnel)
            memory_type: Type de mémoire
            importance: Importance de la mémoire
            metadata: Métadonnées additionnelles
            
        Returns:
            PersonalMemory créée
        """
        try:
            memory_id = self._generate_memory_id(content)
            
            # Extraction d'entités via Graphiti si disponible
            entities = []
            relationships = []
            facts = []
            
            if self.graphiti_engine:
                episode = await self.graphiti_engine.ingest_episode(
                    content=content,
                    source="memory_engine",
                    metadata=metadata or {}
                )
                entities = [e.name for e in episode.entities_extracted]
                relationships = [
                    (r.source_id, r.relation_type.value, r.target_id) 
                    for r in episode.relationships_inferred
                ]
            
            # Extraction de faits (version simple)
            if self.auto_summarize:
                facts = self._extract_facts(content)
            
            # Création contexte
            context = MemoryContext(
                session_id=self.primary_session_id if importance in [MemoryImportance.CRITICAL, MemoryImportance.HIGH] else self.working_session_id,
                user_id=self.user_id,
                source=metadata.get("source", "direct") if metadata else "direct",
                confidence=metadata.get("confidence", 1.0) if metadata else 1.0,
                importance=importance,
                memory_type=memory_type,
                entities=entities,
                relationships=relationships,
                metadata=metadata or {},
                ttl_hours=24 if importance == MemoryImportance.TRANSIENT else None
            )
            
            # Création mémoire
            memory = PersonalMemory(
                memory_id=memory_id,
                content=content,
                context=context,
                summary=self._generate_summary(content) if self.auto_summarize else None,
                facts_extracted=facts
            )
            
            # Sauvegarde dans Zep
            if self.zep_client:
                zep_metadata = {
                    "memory_id": memory_id,
                    "memory_type": memory_type.value,
                    "importance": importance.value,
                    "entities": entities,
                    "relationships": relationships,
                    "facts": facts,
                    "created_at": memory.created_at.isoformat(),
                    "user_id": self.user_id,
                    **context.metadata
                }
                
                # Message pour Zep
                messages = [
                    {"role": "user", "content": content}
                ]
                if response:
                    messages.append({"role": "assistant", "content": response})
                
                await self.zep_client.memory.add_memory(
                    session_id=context.session_id,
                    messages=messages,
                    metadata=zep_metadata
                )
            
            # Cache local
            self.memory_cache[memory_id] = memory
            
            # Clustering si activé
            if self.enable_clustering:
                await self._update_clusters(memory)
            
            self.stats["memories_created"] += 1
            self.logger.info(f"Created memory {memory_id} with {len(entities)} entities")
            
            return memory
            
        except Exception as e:
            self.logger.error(f"Error adding memory: {str(e)}")
            raise
    
    def _extract_facts(self, content: str) -> List[str]:
        """Extrait des faits du contenu (version simple)"""
        facts = []
        
        # Extraction simple basée sur patterns
        sentences = content.split('.')
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 10 and len(sentence) < 200:
                # Patterns de faits
                if any(pattern in sentence.lower() for pattern in [
                    "is", "are", "was", "were", "has", "have", "can", "will",
                    "prefers", "likes", "works", "lives", "knows"
                ]):
                    facts.append(sentence)
        
        return facts[:5]  # Limiter à 5 faits
    
    def _generate_summary(self, content: str) -> str:
        """Génère un résumé du contenu (version simple)"""
        # Version simple: première phrase ou premiers 100 caractères
        if len(content) <= 100:
            return content
        
        first_sentence = content.split('.')[0]
        if len(first_sentence) > 20:
            return first_sentence + "."
        
        return content[:100] + "..."
    
    async def _update_clusters(self, memory: PersonalMemory) -> None:
        """Met à jour les clusters de mémoires"""
        try:
            # Recherche cluster existant basé sur les entités
            found_cluster = None
            for cluster in self.cluster_cache.values():
                # Vérification overlap d'entités
                common_entities = set(memory.context.entities) & set(cluster.keywords)
                if len(common_entities) > 0:
                    found_cluster = cluster
                    break
            
            if found_cluster:
                # Ajout au cluster existant
                found_cluster.memory_ids.append(memory.memory_id)
                found_cluster.keywords.extend(memory.context.entities)
                found_cluster.keywords = list(set(found_cluster.keywords))  # Dédupliquer
                found_cluster.last_updated = datetime.now()
            else:
                # Création nouveau cluster
                cluster = MemoryCluster(
                    cluster_id=f"cluster_{len(self.cluster_cache)}",
                    theme=memory.context.memory_type.value,
                    memory_ids=[memory.memory_id],
                    keywords=memory.context.entities,
                    importance_score=0.5 if memory.context.importance == MemoryImportance.MEDIUM else 0.8
                )
                self.cluster_cache[cluster.cluster_id] = cluster
                self.stats["clusters_formed"] += 1
            
        except Exception as e:
            self.logger.warning(f"Could not update clusters: {str(e)}")
    
    async def search_memories(
        self,
        query: str,
        memory_types: Optional[List[MemoryType]] = None,
        limit: int = 10,
        min_confidence: float = 0.5
    ) -> List[PersonalMemory]:
        """
        Recherche dans les mémoires
        
        Args:
            query: Requête de recherche
            memory_types: Types de mémoire à chercher
            limit: Nombre max de résultats
            min_confidence: Confiance minimale
            
        Returns:
            Liste de mémoires pertinentes
        """
        try:
            self.stats["searches_performed"] += 1
            
            # Recherche dans le cache local d'abord
            cached_results = self._search_cache(query, memory_types, limit)
            if cached_results:
                self.stats["cache_hits"] += 1
                return cached_results
            
            self.stats["cache_misses"] += 1
            
            # Recherche Zep si disponible
            if self.zep_client:
                results = []
                
                # Recherche dans les deux sessions
                for session_id in [self.primary_session_id, self.working_session_id]:
                    search_result = await self.zep_client.memory.search_memory(
                        session_id=session_id,
                        search_payload=SearchPayload(
                            text=query,
                            search_type=SearchType.similarity
                        ),
                        limit=limit
                    )
                    
                    for result in search_result:
                        if result.score >= min_confidence:
                            memory = self._zep_to_personal_memory(result.message)
                            
                            # Filtrage par type si spécifié
                            if memory_types and memory.context.memory_type not in memory_types:
                                continue
                            
                            memory.update_access()
                            results.append(memory)
                
                # Tri par pertinence
                results.sort(key=lambda m: m.calculate_relevance(0), reverse=True)
                
                # Mise en cache
                for memory in results[:limit]:
                    self.memory_cache[memory.memory_id] = memory
                
                self.stats["memories_retrieved"] += len(results)
                return results[:limit]
            
            return []
            
        except Exception as e:
            self.logger.error(f"Error searching memories: {str(e)}")
            return []
    
    def _search_cache(
        self,
        query: str,
        memory_types: Optional[List[MemoryType]],
        limit: int
    ) -> List[PersonalMemory]:
        """Recherche dans le cache local"""
        results = []
        query_lower = query.lower()
        
        for memory in self.memory_cache.values():
            # Filtrage par type
            if memory_types and memory.context.memory_type not in memory_types:
                continue
            
            # Recherche simple dans le contenu
            if query_lower in memory.content.lower():
                results.append(memory)
                continue
            
            # Recherche dans les entités
            for entity in memory.context.entities:
                if query_lower in entity.lower():
                    results.append(memory)
                    break
        
        # Tri par pertinence
        results.sort(key=lambda m: m.calculate_relevance(0), reverse=True)
        
        return results[:limit]
    
    async def get_user_preferences(self) -> Dict[str, Any]:
        """Récupère les préférences utilisateur"""
        return self.preference_cache.copy()
    
    async def update_preference(
        self,
        key: str,
        value: Any,
        category: Optional[str] = None
    ) -> None:
        """Met à jour une préférence utilisateur"""
        try:
            # Mise à jour cache
            self.preference_cache[key] = value
            
            # Sauvegarde comme mémoire de type préférence
            await self.add_memory(
                content=f"User preference: {key} = {value}",
                memory_type=MemoryType.PREFERENCE,
                importance=MemoryImportance.HIGH,
                metadata={
                    "preference_key": key,
                    "preference_value": value,
                    "category": category or "general"
                }
            )
            
            self.logger.info(f"Updated preference: {key} = {value}")
            
        except Exception as e:
            self.logger.error(f"Error updating preference: {str(e)}")
    
    async def update_behavior_patterns(self, pattern_data: Dict[str, Any]) -> None:
        """Met à jour les patterns comportementaux"""
        try:
            await self.add_memory(
                content=f"Behavioral pattern: {json.dumps(pattern_data)}",
                memory_type=MemoryType.BEHAVIORAL,
                importance=MemoryImportance.MEDIUM,
                metadata=pattern_data
            )
            
        except Exception as e:
            self.logger.error(f"Error updating behavior patterns: {str(e)}")
    
    async def consolidate_memories(self) -> None:
        """
        Consolide les mémoires: working → primary, clustering, nettoyage
        """
        try:
            self.logger.info("Starting memory consolidation")
            
            if not self.zep_client:
                return
            
            # 1. Promotion des mémoires importantes de working → primary
            working_memories = await self.zep_client.memory.get_memory(
                session_id=self.working_session_id,
                limit=50
            )
            
            promoted_count = 0
            for memory in working_memories:
                metadata = memory.metadata or {}
                importance = MemoryImportance(metadata.get("importance", MemoryImportance.LOW.value))
                
                # Promotion si importante ou accédée fréquemment
                if importance in [MemoryImportance.HIGH, MemoryImportance.CRITICAL]:
                    await self.zep_client.memory.add_memory(
                        session_id=self.primary_session_id,
                        messages=[{"role": "user", "content": memory.content}],
                        metadata=metadata
                    )
                    promoted_count += 1
            
            # 2. Nettoyage mémoires transitoires expirées
            expired_count = 0
            for memory_id, memory in list(self.memory_cache.items()):
                if memory.context.ttl_hours:
                    age_hours = (datetime.now() - memory.created_at).total_seconds() / 3600
                    if age_hours > memory.context.ttl_hours:
                        del self.memory_cache[memory_id]
                        expired_count += 1
            
            # 3. Mise à jour clusters
            if self.enable_clustering:
                for cluster in self.cluster_cache.values():
                    # Recalcul importance basé sur l'activité
                    cluster.importance_score = min(
                        len(cluster.memory_ids) * 0.1,
                        1.0
                    )
            
            self.last_consolidation = datetime.now()
            self.logger.info(f"Consolidation complete: {promoted_count} promoted, {expired_count} expired")
            
        except Exception as e:
            self.logger.error(f"Error during consolidation: {str(e)}")
    
    async def _periodic_memory_consolidation(self) -> None:
        """Processus périodique de consolidation"""
        while True:
            try:
                await asyncio.sleep(self.consolidation_interval_hours * 3600)
                await self.consolidate_memories()
            except Exception as e:
                self.logger.error(f"Error in periodic consolidation: {str(e)}")
    
    async def sync_to_cloud(self) -> None:
        """Synchronise l'état local avec Zep Cloud"""
        try:
            if not self.zep_client:
                return
            
            # Sync des mémoires cachées non synchronisées
            for memory in self.memory_cache.values():
                # Vérification si déjà dans Zep (simplifiée)
                # En production, utiliser un flag de sync
                pass
            
            # Sync des stats
            await self.zep_client.memory.add_memory(
                session_id=f"stats_{self.user_id}",
                messages=[{
                    "role": "system",
                    "content": f"Memory engine stats: {json.dumps(self.stats)}",
                    "metadata": {
                        "timestamp": datetime.now().isoformat(),
                        "type": "stats"
                    }
                }]
            )
            
            self.logger.info("Cloud sync completed")
            
        except Exception as e:
            self.logger.error(f"Error during cloud sync: {str(e)}")
    
    async def get_memory_timeline(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        memory_types: Optional[List[MemoryType]] = None
    ) -> List[PersonalMemory]:
        """
        Récupère les mémoires dans une période temporelle
        
        Args:
            start_date: Date de début
            end_date: Date de fin
            memory_types: Types de mémoire à inclure
            
        Returns:
            Liste de mémoires dans la période
        """
        memories = []
        
        for memory in self.memory_cache.values():
            # Filtrage temporel
            if start_date and memory.created_at < start_date:
                continue
            if end_date and memory.created_at > end_date:
                continue
            
            # Filtrage par type
            if memory_types and memory.context.memory_type not in memory_types:
                continue
            
            memories.append(memory)
        
        # Tri chronologique
        memories.sort(key=lambda m: m.created_at)
        
        return memories
    
    async def export_memories(
        self,
        format: str = "json",
        include_embeddings: bool = False
    ) -> Union[str, Dict[str, Any]]:
        """
        Exporte les mémoires dans différents formats
        
        Args:
            format: Format d'export (json, markdown)
            include_embeddings: Inclure les embeddings
            
        Returns:
            Mémoires exportées
        """
        memories_data = []
        
        for memory in self.memory_cache.values():
            memory_dict = {
                "id": memory.memory_id,
                "content": memory.content,
                "type": memory.context.memory_type.value,
                "importance": memory.context.importance.value,
                "created": memory.created_at.isoformat(),
                "entities": memory.context.entities,
                "facts": memory.facts_extracted
            }
            
            if include_embeddings and memory.embedding:
                memory_dict["embedding"] = memory.embedding
            
            memories_data.append(memory_dict)
        
        if format == "json":
            return json.dumps(memories_data, indent=2)
        elif format == "markdown":
            md = "# Personal Memories Export\n\n"
            for mem in memories_data:
                md += f"## {mem['created']}\n"
                md += f"**Type**: {mem['type']} | **Importance**: {mem['importance']}\n\n"
                md += f"{mem['content']}\n\n"
                if mem['entities']:
                    md += f"**Entities**: {', '.join(mem['entities'])}\n"
                if mem['facts']:
                    md += f"**Facts**:\n"
                    for fact in mem['facts']:
                        md += f"- {fact}\n"
                md += "\n---\n\n"
            return md
        else:
            return {"memories": memories_data}
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du moteur de mémoire"""
        return {
            **self.stats,
            "cache_size": len(self.memory_cache),
            "clusters": len(self.cluster_cache),
            "preferences": len(self.preference_cache),
            "last_consolidation": self.last_consolidation.isoformat() if self.last_consolidation else None
        }


# Factory function pour création simplifiée
async def create_memory_engine(
    user_id: str,
    zep_client=None,
    graphiti_engine=None,
    config: Optional[Dict[str, Any]] = None
) -> ZepPersonalMemoryEngine:
    """
    Factory function pour créer et initialiser un moteur de mémoire
    
    Args:
        user_id: ID utilisateur
        zep_client: Client Zep
        graphiti_engine: Moteur Graphiti
        config: Configuration
        
    Returns:
        Moteur de mémoire initialisé
    """
    engine = ZepPersonalMemoryEngine(
        user_id=user_id,
        zep_client=zep_client,
        graphiti_engine=graphiti_engine,
        config=config or {}
    )
    
    await engine.initialize()
    
    return engine