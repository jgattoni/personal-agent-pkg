"""
Graphiti Integration Engine pour Personal Knowledge Graph avec Zep
Basé sur l'architecture Graphiti open-source de Zep
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json
from pydantic import BaseModel, Field


class EntityType(str, Enum):
    """Types d'entités personnalisés pour l'agent personnel"""
    PERSON = "person"
    PROJECT = "project"
    TASK = "task"
    MEETING = "meeting"
    DOCUMENT = "document"
    CONCEPT = "concept"
    PREFERENCE = "preference"
    SKILL = "skill"
    GOAL = "goal"
    LOCATION = "location"
    ORGANIZATION = "organization"
    TOOL = "tool"


class RelationType(str, Enum):
    """Types de relations personnalisés"""
    WORKS_ON = "works_on"
    COLLABORATES_WITH = "collaborates_with"
    DEPENDS_ON = "depends_on"
    RELATES_TO = "relates_to"
    OWNS = "owns"
    PREFERS = "prefers"
    LOCATED_AT = "located_at"
    USES = "uses"
    LEARNS = "learns"
    CREATES = "creates"
    MENTIONS = "mentions"
    TEMPORAL_FOLLOWS = "temporal_follows"


@dataclass
class TemporalEdge:
    """Edge avec métadonnées temporelles (Graphiti style)"""
    source_id: str
    target_id: str
    relation_type: RelationType
    weight: float = 1.0
    valid_from: datetime = None
    valid_to: Optional[datetime] = None
    created_at: datetime = None
    episode_ids: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.valid_from is None:
            self.valid_from = self.created_at
        if self.episode_ids is None:
            self.episode_ids = []
        if self.metadata is None:
            self.metadata = {}


class GraphitiEntity(BaseModel):
    """Entité Graphiti avec custom types pour agent personnel"""
    entity_id: str = Field(..., description="ID unique de l'entité")
    entity_type: EntityType = Field(..., description="Type d'entité personnalisé")
    name: str = Field(..., description="Nom de l'entité")
    description: Optional[str] = Field(None, description="Description")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Propriétés additionnelles")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    first_seen: datetime = Field(default_factory=datetime.now)
    last_seen: datetime = Field(default_factory=datetime.now)
    confidence_score: float = Field(default=1.0, description="Score de confiance 0-1")
    episode_ids: List[str] = Field(default_factory=list, description="Episodes qui mentionnent cette entité")
    
    class Config:
        use_enum_values = True


class GraphitiEpisode(BaseModel):
    """Episode d'informations pour ingestion dans Graphiti"""
    episode_id: str = Field(..., description="ID unique de l'épisode")
    content: str = Field(..., description="Contenu textuel")
    source: str = Field(..., description="Source (notion, conversation, etc.)")
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    entities_extracted: List[GraphitiEntity] = Field(default_factory=list)
    relationships_inferred: List[TemporalEdge] = Field(default_factory=list)
    processed: bool = Field(default=False)


class GraphitiEngine:
    """
    Moteur Graphiti pour Personal Knowledge Graph évolutif
    Intégration avec Zep Cloud pour persistence et recherche
    """
    
    def __init__(self, user_id: str, zep_client=None):
        self.user_id = user_id
        self.zep_client = zep_client
        self.logger = logging.getLogger(f"graphiti.{user_id}")
        
        # En-memory graph pour traitement local
        self.entities: Dict[str, GraphitiEntity] = {}
        self.edges: List[TemporalEdge] = []
        self.episodes: Dict[str, GraphitiEpisode] = {}
        
        # Configuration custom entity types pour l'agent personnel
        self.entity_schemas = self._setup_custom_entity_schemas()
        
        # Cache pour optimisation des requêtes
        self._entity_cache: Dict[str, datetime] = {}
        self._search_cache: Dict[str, Any] = {}
    
    def _setup_custom_entity_schemas(self) -> Dict[EntityType, Dict[str, Any]]:
        """Configuration des schemas d'entités personnalisés"""
        return {
            EntityType.PERSON: {
                "required_fields": ["name"],
                "optional_fields": ["role", "email", "company", "skills", "relationship_type"],
                "extraction_patterns": [
                    r"(?i)\b([A-Z][a-z]+ [A-Z][a-z]+)\b",  # Nom Prénom
                    r"(?i)@([a-zA-Z0-9_.+-]+)",  # Mentions
                ]
            },
            EntityType.PROJECT: {
                "required_fields": ["name"],
                "optional_fields": ["status", "deadline", "priority", "team_members", "description"],
                "extraction_patterns": [
                    r"(?i)projet\s+([^,.\n]+)",
                    r"(?i)working on\s+([^,.\n]+)"
                ]
            },
            EntityType.TASK: {
                "required_fields": ["name"],
                "optional_fields": ["priority", "status", "due_date", "assignee", "project"],
                "extraction_patterns": [
                    r"(?i)(?:task|tâche|todo)\s*:?\s*([^,.\n]+)",
                    r"(?i)need to\s+([^,.\n]+)"
                ]
            },
            EntityType.MEETING: {
                "required_fields": ["name"],
                "optional_fields": ["date", "participants", "location", "duration", "action_items"],
                "extraction_patterns": [
                    r"(?i)(?:meeting|réunion)\s+(?:with|avec)?\s*([^,.\n]+)",
                    r"(?i)(?:call|appel)\s+(?:with|avec)?\s*([^,.\n]+)"
                ]
            },
            EntityType.CONCEPT: {
                "required_fields": ["name"],
                "optional_fields": ["definition", "category", "related_concepts", "importance"],
                "extraction_patterns": [
                    r"(?i)concept\s+(?:of|de)?\s*([^,.\n]+)",
                    r"(?i)learning about\s+([^,.\n]+)"
                ]
            },
            EntityType.PREFERENCE: {
                "required_fields": ["name", "value"],
                "optional_fields": ["category", "strength", "context", "changed_at"],
                "extraction_patterns": [
                    r"(?i)(?:prefer|préfère|like|aime)\s+([^,.\n]+)",
                    r"(?i)(?:don't like|n'aime pas)\s+([^,.\n]+)"
                ]
            }
        }
    
    async def ingest_episode(
        self, 
        content: str, 
        source: str = "unknown",
        metadata: Optional[Dict[str, Any]] = None
    ) -> GraphitiEpisode:
        """
        Ingestion d'un episode d'information avec extraction entités et relations
        Style Graphiti avec processing temporel
        """
        try:
            episode_id = f"ep_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{source}"
            
            episode = GraphitiEpisode(
                episode_id=episode_id,
                content=content,
                source=source,
                metadata=metadata or {}
            )
            
            self.logger.info(f"Processing episode {episode_id} from {source}")
            
            # 1. Extraction d'entités avec custom types
            entities = await self._extract_entities_with_types(content, episode_id)
            episode.entities_extracted = entities
            
            # 2. Inférence de relations temporelles
            relationships = await self._infer_temporal_relationships(entities, content, episode_id)
            episode.relationships_inferred = relationships
            
            # 3. Mise à jour du graphe local
            await self._update_local_graph(entities, relationships)
            
            # 4. Sync avec Zep pour persistence
            if self.zep_client:
                await self._sync_episode_to_zep(episode)
            
            # 5. Stockage épisode
            self.episodes[episode_id] = episode
            episode.processed = True
            
            self.logger.info(f"Episode {episode_id} processed: {len(entities)} entities, {len(relationships)} relations")
            
            return episode
            
        except Exception as e:
            self.logger.error(f"Error processing episode: {str(e)}")
            raise
    
    async def _extract_entities_with_types(
        self, 
        content: str, 
        episode_id: str
    ) -> List[GraphitiEntity]:
        """Extraction d'entités avec types personnalisés"""
        entities = []
        
        try:
            # Pour chaque type d'entité configuré
            for entity_type, schema in self.entity_schemas.items():
                # Extraction via patterns regex (simple version)
                for pattern in schema["extraction_patterns"]:
                    import re
                    matches = re.findall(pattern, content)
                    
                    for match in matches:
                        if isinstance(match, tuple):
                            match = match[0]
                        
                        # Nettoyage et validation
                        entity_name = match.strip()
                        if len(entity_name) < 2 or len(entity_name) > 100:
                            continue
                        
                        # Génération ID unique
                        entity_id = f"{entity_type.value}_{hash(entity_name.lower()) % 10000}"
                        
                        # Vérification si entité existe déjà
                        existing_entity = self.entities.get(entity_id)
                        
                        if existing_entity:
                            # Mise à jour entité existante
                            existing_entity.last_seen = datetime.now()
                            existing_entity.episode_ids.append(episode_id)
                            entities.append(existing_entity)
                        else:
                            # Création nouvelle entité
                            entity = GraphitiEntity(
                                entity_id=entity_id,
                                entity_type=entity_type,
                                name=entity_name,
                                episode_ids=[episode_id],
                                properties=self._extract_entity_properties(
                                    entity_name, content, entity_type
                                )
                            )
                            entities.append(entity)
            
            # En production, utiliser un LLM pour extraction plus sophistiquée
            # entities.extend(await self._llm_extract_entities(content, episode_id))
            
            return entities
            
        except Exception as e:
            self.logger.error(f"Error extracting entities: {str(e)}")
            return []
    
    def _extract_entity_properties(
        self, 
        entity_name: str, 
        content: str, 
        entity_type: EntityType
    ) -> Dict[str, Any]:
        """Extraction de propriétés spécifiques selon le type d'entité"""
        properties = {}
        
        # Propriétés basiques communes
        properties["extraction_context"] = content[:200]
        properties["entity_type"] = entity_type.value
        
        # Propriétés spécifiques par type
        if entity_type == EntityType.PERSON:
            # Extraction email, rôle, etc.
            import re
            email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', content)
            if email_match:
                properties["email"] = email_match.group()
        
        elif entity_type == EntityType.PROJECT:
            # Extraction status, priorité, etc.
            if "urgent" in content.lower():
                properties["priority"] = "high"
            if "completed" in content.lower():
                properties["status"] = "completed"
        
        elif entity_type == EntityType.PREFERENCE:
            # Extraction force de préférence
            if any(word in content.lower() for word in ["love", "adore", "favorite"]):
                properties["strength"] = "strong"
            elif any(word in content.lower() for word in ["hate", "dislike"]):
                properties["strength"] = "strong_negative"
            else:
                properties["strength"] = "moderate"
        
        return properties
    
    async def _infer_temporal_relationships(
        self, 
        entities: List[GraphitiEntity], 
        content: str, 
        episode_id: str
    ) -> List[TemporalEdge]:
        """Inférence de relations temporelles entre entités"""
        relationships = []
        
        try:
            # Relations basées sur co-occurrence dans le même épisode
            for i, entity1 in enumerate(entities):
                for entity2 in entities[i+1:]:
                    
                    # Inférence du type de relation basé sur les types d'entités
                    relation_type = self._infer_relation_type(entity1, entity2, content)
                    
                    if relation_type:
                        # Calcul du poids basé sur la proximité dans le texte
                        weight = self._calculate_relation_weight(entity1, entity2, content)
                        
                        edge = TemporalEdge(
                            source_id=entity1.entity_id,
                            target_id=entity2.entity_id,
                            relation_type=relation_type,
                            weight=weight,
                            episode_ids=[episode_id],
                            metadata={
                                "context": content[:100],
                                "confidence": weight,
                                "inferred_from": "co_occurrence"
                            }
                        )
                        
                        relationships.append(edge)
            
            # Relations temporelles (succession d'events)
            relationships.extend(self._infer_temporal_sequence_relations(entities, episode_id))
            
            return relationships
            
        except Exception as e:
            self.logger.error(f"Error inferring relationships: {str(e)}")
            return []
    
    def _infer_relation_type(
        self, 
        entity1: GraphitiEntity, 
        entity2: GraphitiEntity, 
        content: str
    ) -> Optional[RelationType]:
        """Inférence du type de relation entre deux entités"""
        
        # Règles basées sur les types d'entités
        type_pair = (entity1.entity_type, entity2.entity_type)
        
        relation_rules = {
            (EntityType.PERSON, EntityType.PROJECT): RelationType.WORKS_ON,
            (EntityType.PERSON, EntityType.PERSON): RelationType.COLLABORATES_WITH,
            (EntityType.TASK, EntityType.PROJECT): RelationType.DEPENDS_ON,
            (EntityType.PERSON, EntityType.SKILL): RelationType.LEARNS,
            (EntityType.PERSON, EntityType.PREFERENCE): RelationType.PREFERS,
            (EntityType.PERSON, EntityType.TOOL): RelationType.USES,
            (EntityType.MEETING, EntityType.PERSON): RelationType.RELATES_TO,
            (EntityType.DOCUMENT, EntityType.PROJECT): RelationType.RELATES_TO,
        }
        
        # Relation directe basée sur les types
        if type_pair in relation_rules:
            return relation_rules[type_pair]
        
        # Relation inverse
        reverse_pair = (entity2.entity_type, entity1.entity_type)
        if reverse_pair in relation_rules:
            return relation_rules[reverse_pair]
        
        # Relation générique
        return RelationType.RELATES_TO
    
    def _calculate_relation_weight(
        self, 
        entity1: GraphitiEntity, 
        entity2: GraphitiEntity, 
        content: str
    ) -> float:
        """Calcul du poids d'une relation basé sur le contexte"""
        
        # Distance dans le texte
        pos1 = content.lower().find(entity1.name.lower())
        pos2 = content.lower().find(entity2.name.lower())
        
        if pos1 == -1 or pos2 == -1:
            return 0.5  # Poids par défaut
        
        # Plus les entités sont proches, plus le poids est élevé
        distance = abs(pos1 - pos2)
        max_distance = len(content)
        
        # Normalisation inverse de la distance (0.1 à 1.0)
        weight = max(0.1, 1.0 - (distance / max_distance))
        
        return round(weight, 2)
    
    def _infer_temporal_sequence_relations(
        self, 
        entities: List[GraphitiEntity], 
        episode_id: str
    ) -> List[TemporalEdge]:
        """Inférence de relations de séquence temporelle"""
        temporal_relations = []
        
        # Si plusieurs entités du même type, créer des relations temporelles
        entities_by_type = {}
        for entity in entities:
            if entity.entity_type not in entities_by_type:
                entities_by_type[entity.entity_type] = []
            entities_by_type[entity.entity_type].append(entity)
        
        # Création de chaînes temporelles pour certains types
        temporal_types = [EntityType.TASK, EntityType.MEETING, EntityType.PROJECT]
        
        for entity_type in temporal_types:
            if entity_type in entities_by_type and len(entities_by_type[entity_type]) > 1:
                type_entities = entities_by_type[entity_type]
                
                # Tri par ordre d'apparition dans le texte (approximation)
                # type_entities.sort(key=lambda e: e.first_seen)
                
                # Création relations TEMPORAL_FOLLOWS
                for i in range(len(type_entities) - 1):
                    edge = TemporalEdge(
                        source_id=type_entities[i].entity_id,
                        target_id=type_entities[i+1].entity_id,
                        relation_type=RelationType.TEMPORAL_FOLLOWS,
                        weight=0.8,
                        episode_ids=[episode_id],
                        metadata={
                            "inferred_from": "temporal_sequence",
                            "sequence_position": i
                        }
                    )
                    temporal_relations.append(edge)
        
        return temporal_relations
    
    async def _update_local_graph(
        self, 
        entities: List[GraphitiEntity], 
        relationships: List[TemporalEdge]
    ) -> None:
        """Mise à jour du graphe local en mémoire"""
        
        # Mise à jour entités
        for entity in entities:
            if entity.entity_id in self.entities:
                # Fusion avec entité existante
                existing = self.entities[entity.entity_id]
                existing.last_seen = entity.last_seen
                existing.episode_ids.extend(entity.episode_ids)
                existing.properties.update(entity.properties)
            else:
                # Nouvelle entité
                self.entities[entity.entity_id] = entity
        
        # Mise à jour relations
        self.edges.extend(relationships)
        
        # Nettoyage du cache
        self._search_cache.clear()
        
        self.logger.info(f"Updated local graph: {len(self.entities)} entities, {len(self.edges)} edges")
    
    async def _sync_episode_to_zep(self, episode: GraphitiEpisode) -> None:
        """Synchronisation épisode vers Zep Memory pour persistence"""
        try:
            if not self.zep_client:
                return
            
            # Préparation métadonnées enrichies pour Zep
            zep_metadata = {
                "episode_id": episode.episode_id,
                "source": episode.source,
                "entities_count": len(episode.entities_extracted), 
                "relationships_count": len(episode.relationships_inferred),
                "graphiti_processed": True,
                "custom_entity_types": list(set([
                    e.entity_type for e in episode.entities_extracted
                ])),
                **episode.metadata
            }
            
            # Ajout à Zep Memory avec enrichissement Graphiti
            await self.zep_client.memory.add_memory(
                session_id=f"graphiti_session_{self.user_id}",
                messages=[{
                    "role": "system",
                    "content": f"Graphiti Episode: {episode.content}",
                    "metadata": zep_metadata
                }]
            )
            
            self.logger.info(f"Synced episode {episode.episode_id} to Zep")
            
        except Exception as e:
            self.logger.error(f"Error syncing episode to Zep: {str(e)}")
    
    async def search_entities_by_type(
        self, 
        entity_type: EntityType, 
        limit: int = 10
    ) -> List[GraphitiEntity]:
        """Recherche d'entités par type"""
        entities = [
            entity for entity in self.entities.values()
            if entity.entity_type == entity_type
        ]
        
        # Tri par dernière observation
        entities.sort(key=lambda e: e.last_seen, reverse=True)
        
        return entities[:limit]
    
    async def find_related_entities(
        self, 
        entity_id: str, 
        max_depth: int = 2
    ) -> Dict[str, Any]:
        """Recherche d'entités liées avec traversée du graphe"""
        if entity_id not in self.entities:
            return {"error": f"Entity {entity_id} not found"}
        
        related = {"direct": [], "indirect": []}
        visited = set()
        
        # Recherche directe (profondeur 1)
        for edge in self.edges:
            if edge.source_id == entity_id and edge.target_id not in visited:
                target_entity = self.entities.get(edge.target_id)
                if target_entity:
                    related["direct"].append({
                        "entity": target_entity,
                        "relation": edge.relation_type,
                        "weight": edge.weight
                    })
                    visited.add(edge.target_id)
        
        # Recherche indirecte (profondeur 2+) si demandé
        if max_depth > 1:
            for direct_rel in related["direct"]:
                entity_id_2 = direct_rel["entity"].entity_id
                for edge in self.edges:
                    if edge.source_id == entity_id_2 and edge.target_id not in visited:
                        target_entity = self.entities.get(edge.target_id)
                        if target_entity:
                            related["indirect"].append({
                                "entity": target_entity,
                                "relation": edge.relation_type,
                                "weight": edge.weight,
                                "via": entity_id_2
                            })
                            visited.add(edge.target_id)
        
        return related
    
    async def get_graph_stats(self) -> Dict[str, Any]:
        """Statistiques du graphe Graphiti"""
        
        # Stats par type d'entité
        entity_stats = {}
        for entity_type in EntityType:
            count = sum(1 for e in self.entities.values() if e.entity_type == entity_type)
            entity_stats[entity_type.value] = count
        
        # Stats par type de relation
        relation_stats = {}
        for relation_type in RelationType:
            count = sum(1 for r in self.edges if r.relation_type == relation_type)
            relation_stats[relation_type.value] = count
        
        return {
            "total_entities": len(self.entities),
            "total_relationships": len(self.edges),
            "total_episodes": len(self.episodes),
            "entity_types": entity_stats,
            "relation_types": relation_stats,
            "last_update": max([e.updated_at for e in self.entities.values()]) if self.entities else None,
            "user_id": self.user_id
        }


# Factory function pour création simplifiée
async def create_graphiti_engine(user_id: str, zep_client=None) -> GraphitiEngine:
    """Factory function pour créer un GraphitiEngine"""
    engine = GraphitiEngine(user_id, zep_client)
    return engine