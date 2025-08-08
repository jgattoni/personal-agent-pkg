"""
Tests unitaires pour ZepPersonalMemoryEngine
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
import sys
import os
import json

# Ajout du path pour import des modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../packages/core'))

from personal_agent_core.memory.zep_engine import (
    ZepPersonalMemoryEngine,
    MemoryType,
    MemoryImportance,
    MemoryContext,
    PersonalMemory,
    MemoryCluster,
    create_memory_engine
)


@pytest.fixture
def mock_zep_client():
    """Mock du client Zep"""
    client = Mock()
    client.memory = Mock()
    client.memory.add_memory = AsyncMock()
    client.memory.get_memory = AsyncMock(return_value=[])
    client.memory.list_sessions = AsyncMock(return_value=[])
    client.memory.add_session = AsyncMock()
    client.memory.search_memory = AsyncMock(return_value=[])
    return client


@pytest.fixture
def mock_graphiti_engine():
    """Mock du moteur Graphiti"""
    engine = Mock()
    engine.ingest_episode = AsyncMock(return_value=Mock(
        entities_extracted=[],
        relationships_inferred=[]
    ))
    return engine


@pytest.fixture
def memory_engine(mock_zep_client, mock_graphiti_engine):
    """Moteur de mémoire pour tests"""
    return ZepPersonalMemoryEngine(
        user_id="test_user",
        zep_client=mock_zep_client,
        graphiti_engine=mock_graphiti_engine,
        config={
            "max_working_memory": 5,
            "auto_summarize": True,
            "enable_clustering": True
        }
    )


@pytest.fixture
async def initialized_memory_engine(memory_engine):
    """Moteur de mémoire initialisé"""
    await memory_engine.initialize()
    return memory_engine


class TestMemoryContext:
    """Tests pour MemoryContext"""
    
    def test_memory_context_creation(self):
        """Test création d'un contexte mémoire"""
        context = MemoryContext(
            session_id="test_session",
            user_id="test_user"
        )
        
        assert context.session_id == "test_session"
        assert context.user_id == "test_user"
        assert context.importance == MemoryImportance.MEDIUM
        assert context.memory_type == MemoryType.EPISODIC
        assert isinstance(context.timestamp, datetime)


class TestPersonalMemory:
    """Tests pour PersonalMemory"""
    
    def test_personal_memory_creation(self):
        """Test création d'une mémoire personnelle"""
        context = MemoryContext(
            session_id="test_session",
            user_id="test_user"
        )
        
        memory = PersonalMemory(
            memory_id="test_memory",
            content="Test content",
            context=context
        )
        
        assert memory.memory_id == "test_memory"
        assert memory.content == "Test content"
        assert memory.context == context
        assert memory.accessed_count == 0
    
    def test_memory_access_update(self):
        """Test mise à jour des accès"""
        context = MemoryContext(session_id="test", user_id="test")
        memory = PersonalMemory(
            memory_id="test",
            content="Test",
            context=context
        )
        
        initial_count = memory.accessed_count
        memory.update_access()
        
        assert memory.accessed_count == initial_count + 1
        assert memory.last_accessed is not None
    
    def test_relevance_calculation(self):
        """Test calcul de pertinence"""
        # Mémoire critique
        context_critical = MemoryContext(
            session_id="test",
            user_id="test",
            importance=MemoryImportance.CRITICAL
        )
        memory_critical = PersonalMemory(
            memory_id="critical",
            content="Critical info",
            context=context_critical
        )
        
        relevance = memory_critical.calculate_relevance(30)  # 30 jours
        assert relevance > 0.8  # Mémoire critique reste pertinente
        
        # Mémoire transitoire
        context_transient = MemoryContext(
            session_id="test",
            user_id="test",
            importance=MemoryImportance.TRANSIENT
        )
        memory_transient = PersonalMemory(
            memory_id="transient",
            content="Transient info",
            context=context_transient
        )
        
        relevance = memory_transient.calculate_relevance(30)
        assert relevance < 0.2  # Mémoire transitoire perd vite en pertinence


class TestZepPersonalMemoryEngine:
    """Tests pour ZepPersonalMemoryEngine"""
    
    def test_engine_creation(self, mock_zep_client, mock_graphiti_engine):
        """Test création du moteur"""
        engine = ZepPersonalMemoryEngine(
            user_id="test_user",
            zep_client=mock_zep_client,
            graphiti_engine=mock_graphiti_engine
        )
        
        assert engine.user_id == "test_user"
        assert engine.zep_client == mock_zep_client
        assert engine.graphiti_engine == mock_graphiti_engine
        assert engine.primary_session_id == "user_test_user_primary"
        assert engine.working_session_id == "user_test_user_working"
    
    @pytest.mark.asyncio
    async def test_engine_initialization(self, memory_engine, mock_zep_client):
        """Test initialisation du moteur"""
        # Mock des sessions existantes
        mock_zep_client.memory.list_sessions.return_value = []
        
        await memory_engine.initialize()
        
        # Vérification création des sessions
        assert mock_zep_client.memory.add_session.call_count == 2
    
    @pytest.mark.asyncio
    async def test_add_memory_basic(self, initialized_memory_engine):
        """Test ajout d'une mémoire basique"""
        memory = await initialized_memory_engine.add_memory(
            content="Test memory content",
            memory_type=MemoryType.EPISODIC,
            importance=MemoryImportance.MEDIUM
        )
        
        assert isinstance(memory, PersonalMemory)
        assert memory.content == "Test memory content"
        assert memory.context.memory_type == MemoryType.EPISODIC
        assert memory.context.importance == MemoryImportance.MEDIUM
        assert memory.memory_id in initialized_memory_engine.memory_cache
    
    @pytest.mark.asyncio
    async def test_add_memory_with_response(self, initialized_memory_engine, mock_zep_client):
        """Test ajout mémoire avec réponse"""
        memory = await initialized_memory_engine.add_memory(
            content="User question",
            response="Agent response",
            importance=MemoryImportance.HIGH
        )
        
        assert memory is not None
        # Vérification que Zep a été appelé avec les bons messages
        mock_zep_client.memory.add_memory.assert_called()
    
    @pytest.mark.asyncio
    async def test_memory_with_graphiti_integration(self, initialized_memory_engine, mock_graphiti_engine):
        """Test intégration avec Graphiti"""
        # Configuration du mock Graphiti
        mock_episode = Mock()
        mock_episode.entities_extracted = [
            Mock(name="John Doe"),
            Mock(name="Python Project")
        ]
        mock_episode.relationships_inferred = [
            Mock(source_id="john", relation_type=Mock(value="works_on"), target_id="python")
        ]
        mock_graphiti_engine.ingest_episode.return_value = mock_episode
        
        memory = await initialized_memory_engine.add_memory(
            content="John Doe is working on a Python project"
        )
        
        # Vérification appel Graphiti
        mock_graphiti_engine.ingest_episode.assert_called_once()
        assert len(memory.context.entities) == 2
        assert len(memory.context.relationships) == 1
    
    def test_memory_id_generation(self, memory_engine):
        """Test génération d'ID de mémoire"""
        id1 = memory_engine._generate_memory_id("test content")
        id2 = memory_engine._generate_memory_id("test content")
        
        # Les IDs doivent être différents (timestamp inclus)
        assert id1 != id2
        assert len(id1) == 12
    
    def test_fact_extraction(self, memory_engine):
        """Test extraction de faits"""
        content = "John is a developer. He works at Google. He likes Python programming."
        facts = memory_engine._extract_facts(content)
        
        assert len(facts) > 0
        assert any("developer" in fact for fact in facts)
    
    def test_summary_generation(self, memory_engine):
        """Test génération de résumé"""
        short_content = "This is short."
        summary = memory_engine._generate_summary(short_content)
        assert summary == short_content
        
        long_content = "This is a very long content that should be summarized because it exceeds the normal length limit for content display."
        summary = memory_engine._generate_summary(long_content)
        assert len(summary) < len(long_content)
    
    @pytest.mark.asyncio
    async def test_clustering(self, initialized_memory_engine):
        """Test clustering des mémoires"""
        # Ajout de mémoires liées
        memory1 = await initialized_memory_engine.add_memory(
            content="Working on Python project with John",
            metadata={"entities": ["John", "Python"]}
        )
        
        memory2 = await initialized_memory_engine.add_memory(
            content="John sent code review for Python module",
            metadata={"entities": ["John", "Python", "code_review"]}
        )
        
        # Vérification clustering
        assert len(initialized_memory_engine.cluster_cache) > 0
    
    @pytest.mark.asyncio
    async def test_search_memories_cache(self, initialized_memory_engine):
        """Test recherche dans le cache"""
        # Ajout d'une mémoire
        await initialized_memory_engine.add_memory(
            content="Python programming tutorial",
            memory_type=MemoryType.SEMANTIC
        )
        
        # Recherche
        results = await initialized_memory_engine.search_memories(
            query="Python",
            memory_types=[MemoryType.SEMANTIC]
        )
        
        assert len(results) == 1
        assert "Python" in results[0].content
        assert initialized_memory_engine.stats["cache_hits"] == 1
    
    @pytest.mark.asyncio
    async def test_search_memories_zep(self, initialized_memory_engine, mock_zep_client):
        """Test recherche via Zep"""
        # Configuration du mock
        mock_result = Mock()
        mock_result.score = 0.8
        mock_result.message = Mock()
        mock_result.message.content = "Test content"
        mock_result.message.metadata = {
            "memory_id": "test123",
            "memory_type": MemoryType.EPISODIC.value,
            "timestamp": datetime.now().isoformat()
        }
        
        mock_zep_client.memory.search_memory.return_value = [mock_result]
        
        # Recherche (cache vide)
        initialized_memory_engine.memory_cache.clear()
        results = await initialized_memory_engine.search_memories("test query")
        
        assert len(results) == 1
        assert initialized_memory_engine.stats["cache_misses"] == 1
    
    @pytest.mark.asyncio
    async def test_preference_management(self, initialized_memory_engine):
        """Test gestion des préférences"""
        await initialized_memory_engine.update_preference(
            key="theme",
            value="dark",
            category="ui"
        )
        
        preferences = await initialized_memory_engine.get_user_preferences()
        assert preferences["theme"] == "dark"
    
    @pytest.mark.asyncio
    async def test_behavior_patterns(self, initialized_memory_engine):
        """Test mise à jour patterns comportementaux"""
        pattern_data = {
            "intent": "task_execution",
            "success": True,
            "timestamp": datetime.now().isoformat()
        }
        
        await initialized_memory_engine.update_behavior_patterns(pattern_data)
        
        # Vérification qu'une mémoire comportementale a été créée
        behavioral_memories = [
            m for m in initialized_memory_engine.memory_cache.values()
            if m.context.memory_type == MemoryType.BEHAVIORAL
        ]
        assert len(behavioral_memories) == 1
    
    @pytest.mark.asyncio
    async def test_memory_consolidation(self, initialized_memory_engine, mock_zep_client):
        """Test consolidation des mémoires"""
        # Configuration du mock
        mock_memory = Mock()
        mock_memory.content = "Test content"
        mock_memory.metadata = {
            "importance": MemoryImportance.HIGH.value,
            "memory_type": MemoryType.EPISODIC.value
        }
        mock_zep_client.memory.get_memory.return_value = [mock_memory]
        
        await initialized_memory_engine.consolidate_memories()
        
        # Vérification des appels
        mock_zep_client.memory.get_memory.assert_called()
    
    def test_memory_timeline(self, initialized_memory_engine):
        """Test timeline des mémoires"""
        # Ajout de mémoires avec différentes dates
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        
        # Simulation de mémoires dans le cache
        memory1 = PersonalMemory(
            memory_id="mem1",
            content="Today's memory",
            context=MemoryContext(session_id="test", user_id="test"),
            created_at=now
        )
        memory2 = PersonalMemory(
            memory_id="mem2",
            content="Yesterday's memory",
            context=MemoryContext(session_id="test", user_id="test"),
            created_at=yesterday
        )
        
        initialized_memory_engine.memory_cache["mem1"] = memory1
        initialized_memory_engine.memory_cache["mem2"] = memory2
        
        # Test timeline
        timeline = asyncio.run(initialized_memory_engine.get_memory_timeline(
            start_date=yesterday,
            end_date=now
        ))
        
        assert len(timeline) == 2
        assert timeline[0].created_at < timeline[1].created_at  # Tri chronologique
    
    @pytest.mark.asyncio
    async def test_memory_export_json(self, initialized_memory_engine):
        """Test export mémoires en JSON"""
        # Ajout d'une mémoire
        await initialized_memory_engine.add_memory("Test export content")
        
        export = await initialized_memory_engine.export_memories(format="json")
        
        assert isinstance(export, str)
        data = json.loads(export)
        assert len(data) == 1
        assert data[0]["content"] == "Test export content"
    
    @pytest.mark.asyncio
    async def test_memory_export_markdown(self, initialized_memory_engine):
        """Test export mémoires en Markdown"""
        await initialized_memory_engine.add_memory("Test markdown export")
        
        export = await initialized_memory_engine.export_memories(format="markdown")
        
        assert isinstance(export, str)
        assert "# Personal Memories Export" in export
        assert "Test markdown export" in export
    
    def test_stats_tracking(self, initialized_memory_engine):
        """Test suivi des statistiques"""
        stats = initialized_memory_engine.get_stats()
        
        assert "memories_created" in stats
        assert "memories_retrieved" in stats
        assert "cache_size" in stats
        assert "clusters" in stats
        assert "preferences" in stats
    
    @pytest.mark.asyncio
    async def test_ttl_memory_expiration(self, initialized_memory_engine):
        """Test expiration des mémoires TTL"""
        # Création mémoire transitoire avec TTL
        past_time = datetime.now() - timedelta(hours=2)
        
        memory = PersonalMemory(
            memory_id="ttl_test",
            content="TTL memory",
            context=MemoryContext(
                session_id="test",
                user_id="test",
                ttl_hours=1  # Expire après 1h
            ),
            created_at=past_time
        )
        
        initialized_memory_engine.memory_cache["ttl_test"] = memory
        
        await initialized_memory_engine.consolidate_memories()
        
        # La mémoire devrait être supprimée
        assert "ttl_test" not in initialized_memory_engine.memory_cache
    
    @pytest.mark.asyncio
    async def test_cloud_sync(self, initialized_memory_engine, mock_zep_client):
        """Test synchronisation cloud"""
        await initialized_memory_engine.sync_to_cloud()
        
        # Vérification que les stats ont été sauvegardées
        mock_zep_client.memory.add_memory.assert_called()


class TestMemoryCluster:
    """Tests pour MemoryCluster"""
    
    def test_cluster_creation(self):
        """Test création d'un cluster"""
        cluster = MemoryCluster(
            cluster_id="test_cluster",
            theme="work",
            keywords=["python", "development"]
        )
        
        assert cluster.cluster_id == "test_cluster"
        assert cluster.theme == "work"
        assert "python" in cluster.keywords
        assert isinstance(cluster.created_at, datetime)


class TestFactoryFunction:
    """Tests pour la fonction factory"""
    
    @pytest.mark.asyncio
    async def test_create_memory_engine(self, mock_zep_client, mock_graphiti_engine):
        """Test fonction factory"""
        with patch.object(ZepPersonalMemoryEngine, 'initialize', new=AsyncMock()):
            engine = await create_memory_engine(
                user_id="factory_test",
                zep_client=mock_zep_client,
                graphiti_engine=mock_graphiti_engine,
                config={"test": "config"}
            )
        
        assert isinstance(engine, ZepPersonalMemoryEngine)
        assert engine.user_id == "factory_test"
        assert engine.config == {"test": "config"}


class TestEdgeCases:
    """Tests pour les cas limites"""
    
    @pytest.mark.asyncio
    async def test_memory_engine_without_zep(self, mock_graphiti_engine):
        """Test moteur sans client Zep"""
        engine = ZepPersonalMemoryEngine(
            user_id="no_zep_test",
            zep_client=None,
            graphiti_engine=mock_graphiti_engine
        )
        
        await engine.initialize()
        
        # Devrait fonctionner en mode local
        memory = await engine.add_memory("Local only memory")
        assert memory is not None
        assert memory.memory_id in engine.memory_cache
    
    @pytest.mark.asyncio
    async def test_search_with_no_zep_client(self, mock_graphiti_engine):
        """Test recherche sans client Zep"""
        engine = ZepPersonalMemoryEngine(
            user_id="no_zep",
            zep_client=None,
            graphiti_engine=mock_graphiti_engine
        )
        
        await engine.initialize()
        await engine.add_memory("Searchable content")
        
        results = await engine.search_memories("Searchable")
        assert len(results) == 1
        assert "Searchable" in results[0].content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])