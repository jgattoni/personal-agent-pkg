"""
Tests unitaires pour NotionZepBridge
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
import sys
import os
import json

# Ajout du path pour import des modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../packages/integrations'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../packages/core'))

from personal_agent_integrations.notion.notion_zep_bridge import (
    NotionZepBridge,
    NotionPage,
    NotionPageType,
    SyncStatus,
    SyncResult,
    create_notion_zep_bridge
)


@pytest.fixture
def mock_zep_memory_engine():
    """Mock du moteur mémoire Zep"""
    engine = Mock()
    engine.add_memory = AsyncMock(return_value=Mock(memory_id="test_memory_123"))
    engine.search_memories = AsyncMock(return_value=[])
    return engine


@pytest.fixture
def mock_graphiti_engine():
    """Mock du moteur Graphiti"""
    engine = Mock()
    
    # Mock episode avec entités extraites
    mock_episode = Mock()
    mock_episode.entities_extracted = [
        Mock(name="John Doe"),
        Mock(name="Python Project"),
        Mock(name="Meeting Notes")
    ]
    
    engine.ingest_episode = AsyncMock(return_value=mock_episode)
    return engine


@pytest.fixture
def mock_mcp_manager():
    """Mock du manager MCP"""
    manager = Mock()
    manager.connect_notion_server = AsyncMock()
    manager.discover_tools = AsyncMock(return_value=[
        Mock(name="search"),
        Mock(name="retrieve_page"),
        Mock(name="query_database")
    ])
    manager.execute_tool = AsyncMock()
    return manager


@pytest.fixture
def notion_bridge(mock_zep_memory_engine, mock_graphiti_engine, mock_mcp_manager):
    """Bridge Notion-Zep pour tests"""
    return NotionZepBridge(
        user_id="test_user",
        notion_token="mock_token",
        zep_memory_engine=mock_zep_memory_engine,
        graphiti_engine=mock_graphiti_engine,
        mcp_manager=mock_mcp_manager,
        config={
            "use_mcp": True,
            "sync_interval_hours": 1,
            "max_pages_per_sync": 10,
            "enable_auto_sync": False  # Désactivé pour les tests
        }
    )


@pytest.fixture
async def initialized_bridge(notion_bridge):
    """Bridge initialisé"""
    await notion_bridge.initialize()
    return notion_bridge


class TestNotionPage:
    """Tests pour NotionPage"""
    
    def test_notion_page_creation(self):
        """Test création d'une page Notion"""
        page = NotionPage(
            page_id="test_page_123",
            title="Test Page",
            content="This is test content",
            page_type=NotionPageType.DOCUMENT
        )
        
        assert page.page_id == "test_page_123"
        assert page.title == "Test Page"
        assert page.content == "This is test content"
        assert page.page_type == NotionPageType.DOCUMENT
        assert isinstance(page.last_edited, datetime)
    
    def test_notion_page_to_dict(self):
        """Test conversion en dictionnaire"""
        page = NotionPage(
            page_id="test_page",
            title="Test",
            content="Content",
            tags=["tag1", "tag2"],
            mentions=["@user1"]
        )
        
        page_dict = page.to_dict()
        
        assert page_dict["page_id"] == "test_page"
        assert page_dict["title"] == "Test"
        assert page_dict["content"] == "Content"
        assert page_dict["tags"] == ["tag1", "tag2"]
        assert page_dict["mentions"] == ["@user1"]
        assert "last_edited" in page_dict


class TestNotionZepBridge:
    """Tests pour NotionZepBridge"""
    
    def test_bridge_creation(self, mock_zep_memory_engine, mock_graphiti_engine):
        """Test création du bridge"""
        bridge = NotionZepBridge(
            user_id="test_user",
            notion_token="test_token",
            zep_memory_engine=mock_zep_memory_engine,
            graphiti_engine=mock_graphiti_engine
        )
        
        assert bridge.user_id == "test_user"
        assert bridge.notion_token == "test_token"
        assert bridge.zep_memory_engine == mock_zep_memory_engine
        assert bridge.graphiti_engine == mock_graphiti_engine
        assert not bridge.is_initialized
    
    @pytest.mark.asyncio
    async def test_bridge_initialization(self, notion_bridge, mock_mcp_manager):
        """Test initialisation du bridge"""
        success = await notion_bridge.initialize()
        
        assert success
        assert notion_bridge.is_initialized
        mock_mcp_manager.connect_notion_server.assert_called_once()
    
    def test_page_type_classification(self, notion_bridge):
        """Test classification des types de pages"""
        # Page de tâche
        task_page = NotionPage(
            page_id="task1",
            title="Todo List",
            content="Task 1: Complete project\nTask 2: Review code\nDeadline: Friday"
        )
        assert notion_bridge._classify_page_type(task_page) == NotionPageType.TASK
        
        # Page de réunion
        meeting_page = NotionPage(
            page_id="meeting1",
            title="Team Meeting Notes",
            content="Meeting agenda: 1. Project status 2. Action items\nParticipants: John, Mary"
        )
        assert notion_bridge._classify_page_type(meeting_page) == NotionPageType.MEETING_NOTES
        
        # Page de projet
        project_page = NotionPage(
            page_id="project1",
            title="New Website Project",
            content="Project roadmap and milestones\nTimeline: Q1 2024\nDeliverables listed below"
        )
        assert notion_bridge._classify_page_type(project_page) == NotionPageType.PROJECT
        
        # Page générique
        doc_page = NotionPage(
            page_id="doc1",
            title="Random Notes",
            content="Some random thoughts and ideas here"
        )
        assert notion_bridge._classify_page_type(doc_page) == NotionPageType.DOCUMENT
    
    def test_extract_text_from_blocks(self, notion_bridge):
        """Test extraction de texte des blocs Notion"""
        blocks = [
            {
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"plain_text": "This is a paragraph."}]
                }
            },
            {
                "type": "heading_1", 
                "heading_1": {
                    "rich_text": [{"plain_text": "Main Title"}]
                }
            },
            {
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"plain_text": "Bullet point"}]
                }
            },
            {
                "type": "to_do",
                "to_do": {
                    "rich_text": [{"plain_text": "Todo item"}],
                    "checked": True
                }
            }
        ]
        
        text = notion_bridge._extract_text_from_blocks(blocks)
        expected = "This is a paragraph.\nMain Title\n• Bullet point\n☑ Todo item"
        
        assert text == expected
    
    def test_calculate_page_importance(self, notion_bridge):
        """Test calcul d'importance des pages"""
        from personal_agent_core.memory.zep_engine import MemoryImportance
        
        # Page récente et longue
        recent_page = NotionPage(
            page_id="recent",
            title="Recent Important Page",
            content="A" * 1500,  # Long contenu
            page_type=NotionPageType.PROJECT,
            last_edited=datetime.now() - timedelta(hours=2),
            mentions=["@user1", "@user2"],
            tags=["important", "urgent"]
        )
        
        importance = notion_bridge._calculate_page_importance(recent_page)
        assert importance == MemoryImportance.HIGH
        
        # Page ancienne et courte
        old_page = NotionPage(
            page_id="old",
            title="Old Page", 
            content="Short content",
            last_edited=datetime.now() - timedelta(days=60)
        )
        
        importance = notion_bridge._calculate_page_importance(old_page)
        assert importance == MemoryImportance.LOW
    
    @pytest.mark.asyncio
    async def test_sync_notion_to_zep_mock_mode(self, initialized_bridge):
        """Test sync en mode mock"""
        # Le bridge utilisera les pages mock car pas de vrai client Notion
        result = await initialized_bridge.sync_notion_to_zep(force_full_sync=True)
        
        assert isinstance(result, SyncResult)
        assert result.status in [SyncStatus.COMPLETED, SyncStatus.PARTIAL]
        assert result.pages_processed >= 0
        assert result.duration_seconds > 0
    
    @pytest.mark.asyncio
    async def test_sync_with_mcp(self, initialized_bridge, mock_mcp_manager):
        """Test sync utilisant MCP"""
        # Configuration des mocks MCP
        mock_search_result = {
            "results": [
                {
                    "id": "page_123",
                    "object": "page",
                    "properties": {"title": {"title": [{"plain_text": "Test Page"}]}},
                    "last_edited_time": datetime.now().isoformat(),
                    "url": "https://notion.so/test123"
                }
            ]
        }
        
        mock_blocks_result = {
            "results": [
                {
                    "type": "paragraph",
                    "paragraph": {"rich_text": [{"plain_text": "Test content for MCP sync"}]}
                }
            ]
        }
        
        # Configuration des retours MCP
        def mock_execute_tool(server, tool_name, params):
            if tool_name == "search":
                return asyncio.create_task(asyncio.coroutine(lambda: mock_search_result)())
            elif tool_name == "retrieve_block_children":
                return asyncio.create_task(asyncio.coroutine(lambda: mock_blocks_result)())
            return asyncio.create_task(asyncio.coroutine(lambda: {})())
        
        mock_mcp_manager.execute_tool.side_effect = mock_execute_tool
        
        result = await initialized_bridge.sync_notion_to_zep(force_full_sync=True)
        
        assert result.status in [SyncStatus.COMPLETED, SyncStatus.PARTIAL]
        assert mock_mcp_manager.execute_tool.called
    
    @pytest.mark.asyncio
    async def test_search_notion_content(self, initialized_bridge):
        """Test recherche dans le contenu Notion"""
        # Ajout de pages au cache pour le test
        test_pages = [
            NotionPage(
                page_id="search1",
                title="Python Development",
                content="Working on Python projects and Django applications",
                page_type=NotionPageType.PROJECT
            ),
            NotionPage(
                page_id="search2", 
                title="Meeting Notes",
                content="Discussed React frontend improvements",
                page_type=NotionPageType.MEETING_NOTES
            )
        ]
        
        for page in test_pages:
            initialized_bridge.pages_cache[page.page_id] = page
        
        # Recherche générale
        results = await initialized_bridge.search_notion_content("Python")
        assert len(results) == 1
        assert results[0].title == "Python Development"
        
        # Recherche avec filtrage par type
        meeting_results = await initialized_bridge.search_notion_content(
            "React", 
            page_types=[NotionPageType.MEETING_NOTES]
        )
        assert len(meeting_results) == 1
        assert meeting_results[0].page_type == NotionPageType.MEETING_NOTES
        
        # Recherche sans résultats
        no_results = await initialized_bridge.search_notion_content("nonexistent")
        assert len(no_results) == 0
    
    def test_get_sync_stats(self, initialized_bridge):
        """Test récupération des statistiques"""
        stats = initialized_bridge.get_sync_stats()
        
        assert "total_syncs" in stats
        assert "pages_synced" in stats
        assert "entities_extracted" in stats
        assert "memories_created" in stats
        assert "is_initialized" in stats
        assert "sync_in_progress" in stats
        assert "use_mcp" in stats
        
        assert stats["is_initialized"] == True
        assert stats["sync_in_progress"] == False
    
    @pytest.mark.asyncio
    async def test_export_notion_cache(self, initialized_bridge):
        """Test export du cache Notion"""
        # Ajout d'une page au cache
        test_page = NotionPage(
            page_id="export_test",
            title="Export Test Page",
            content="Content for export test"
        )
        initialized_bridge.pages_cache["export_test"] = test_page
        
        # Export JSON
        json_export = await initialized_bridge.export_notion_cache(format="json")
        assert isinstance(json_export, str)
        
        # Vérification du contenu
        export_data = json.loads(json_export)
        assert export_data["user_id"] == "test_user"
        assert export_data["total_pages"] == 1
        assert len(export_data["pages"]) == 1
        assert export_data["pages"][0]["title"] == "Export Test Page"
        
        # Export dict
        dict_export = await initialized_bridge.export_notion_cache(format="dict")
        assert isinstance(dict_export, dict)
        assert dict_export["total_pages"] == 1
    
    @pytest.mark.asyncio
    async def test_sync_error_handling(self, initialized_bridge, mock_mcp_manager):
        """Test gestion des erreurs pendant la sync"""
        # Configuration pour générer une erreur
        mock_mcp_manager.execute_tool.side_effect = Exception("MCP connection error")
        
        result = await initialized_bridge.sync_notion_to_zep()
        
        assert result.status == SyncStatus.FAILED
        assert len(result.errors) > 0
        assert "error" in result.errors[0].lower()
    
    def test_memory_type_conversion(self, notion_bridge):
        """Test conversion types Notion → types mémoire"""
        from personal_agent_core.memory.zep_engine import MemoryType
        
        # Mapping des conversions
        conversions = [
            (NotionPageType.TASK, MemoryType.WORKING),
            (NotionPageType.MEETING_NOTES, MemoryType.EPISODIC),
            (NotionPageType.PROJECT, MemoryType.WORKING),
            (NotionPageType.PERSON, MemoryType.SEMANTIC),
            (NotionPageType.DOCUMENT, MemoryType.SEMANTIC),
            (NotionPageType.UNKNOWN, MemoryType.EPISODIC)
        ]
        
        for notion_type, expected_memory_type in conversions:
            result = notion_bridge._notion_type_to_memory_type(notion_type)
            assert result == expected_memory_type


class TestSyncIntegration:
    """Tests d'intégration pour la synchronisation"""
    
    @pytest.mark.asyncio
    async def test_full_sync_workflow(self, mock_zep_memory_engine, mock_graphiti_engine):
        """Test workflow complet de synchronisation"""
        bridge = NotionZepBridge(
            user_id="integration_test",
            zep_memory_engine=mock_zep_memory_engine,
            graphiti_engine=mock_graphiti_engine,
            config={"enable_auto_sync": False}
        )
        
        await bridge.initialize()
        
        # Exécution d'une sync complète
        result = await bridge.sync_notion_to_zep(force_full_sync=True)
        
        # Vérifications
        assert result.status in [SyncStatus.COMPLETED, SyncStatus.PARTIAL]
        assert result.pages_processed >= 0
        assert result.duration_seconds > 0
        
        # Vérifications des appels aux dépendances
        if result.pages_processed > 0:
            assert mock_graphiti_engine.ingest_episode.called
            assert mock_zep_memory_engine.add_memory.called
        
        # Vérifications des stats
        stats = bridge.get_sync_stats()
        assert stats["total_syncs"] >= 1


class TestFactoryFunction:
    """Tests pour la fonction factory"""
    
    @pytest.mark.asyncio
    async def test_create_notion_zep_bridge(self, mock_zep_memory_engine, mock_graphiti_engine):
        """Test fonction factory"""
        with patch.object(NotionZepBridge, 'initialize', new=AsyncMock(return_value=True)):
            bridge = await create_notion_zep_bridge(
                user_id="factory_test",
                notion_token="test_token",
                zep_memory_engine=mock_zep_memory_engine,
                graphiti_engine=mock_graphiti_engine,
                config={"test": "config"}
            )
        
        assert isinstance(bridge, NotionZepBridge)
        assert bridge.user_id == "factory_test"
        assert bridge.notion_token == "test_token"


class TestEdgeCases:
    """Tests pour les cas limites"""
    
    @pytest.mark.asyncio
    async def test_bridge_without_dependencies(self):
        """Test bridge sans dépendances"""
        bridge = NotionZepBridge(
            user_id="minimal_test",
            notion_token=None,
            zep_memory_engine=None,
            graphiti_engine=None,
            mcp_manager=None
        )
        
        success = await bridge.initialize()
        assert success  # Devrait réussir en mode dégradé
        
        # Sync devrait fonctionner en mode mock
        result = await bridge.sync_notion_to_zep()
        assert result.status in [SyncStatus.COMPLETED, SyncStatus.FAILED]
    
    def test_empty_content_filtering(self, notion_bridge):
        """Test filtrage du contenu vide"""
        # Configuration pour filtrer le contenu court
        notion_bridge.sync_filters["min_content_length"] = 100
        
        # Page avec contenu court
        short_page_info = {
            "id": "short_page",
            "properties": {"title": {"title": [{"plain_text": "Short"}]}},
            "last_edited_time": datetime.now().isoformat()
        }
        
        # Test avec contenu mock court
        with patch.object(notion_bridge, '_extract_text_from_blocks', return_value="Short"):
            result = asyncio.run(notion_bridge._extract_page_content(short_page_info))
            assert result is None  # Devrait être filtré
    
    @pytest.mark.asyncio
    async def test_concurrent_sync_prevention(self, initialized_bridge):
        """Test prévention de syncs concurrentes"""
        # Première sync (simule une sync longue)
        with patch.object(initialized_bridge, '_discover_pages_to_sync', 
                         new=AsyncMock(return_value=[])) as mock_discover:
            
            # Démarrage première sync
            task1 = asyncio.create_task(initialized_bridge.sync_notion_to_zep())
            
            # Tentative de deuxième sync pendant que la première est en cours
            initialized_bridge.sync_in_progress = True
            result2 = await initialized_bridge.sync_notion_to_zep()
            
            # La deuxième sync devrait être rejetée
            assert result2.status == SyncStatus.FAILED
            assert "already in progress" in result2.errors[0]
            
            # Attendre la fin de la première sync
            initialized_bridge.sync_in_progress = False
            await task1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])