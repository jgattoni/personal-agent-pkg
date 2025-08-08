"""
Tests unitaires pour Claude Code Extension

Tests complets des commandes slash, handlers, configuration, et intégrations
"""

import pytest
import asyncio
import json
import os
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import sys

# Ajout du path pour import des modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../packages/integrations'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../packages/core'))

from personal_agent_integrations.claude_code.extension import (
    ClaudeCodeExtension,
    SlashCommand,
    CommandCategory,
    CommandScope,
    create_claude_extension
)


@pytest.fixture
def mock_agent():
    """Mock agent personnel"""
    agent = Mock()
    agent.state.value = "ready"
    agent.context.capabilities = [Mock(value="memory"), Mock(value="notion")]
    agent.stats = {"messages_processed": 5, "memories_created": 3}
    agent.health_check = AsyncMock(return_value={"status": "healthy"})
    agent.get_stats = AsyncMock(return_value=agent.stats)
    return agent


@pytest.fixture
def mock_memory_engine():
    """Mock moteur mémoire"""
    engine = Mock()
    
    # Mock memory objects
    mock_memory1 = Mock()
    mock_memory1.memory_id = "mem123456"
    mock_memory1.content = "Je suis développeur Python"
    mock_memory1.context.memory_type.value = "semantic"
    mock_memory1.context.importance.value = "medium"
    mock_memory1.context.timestamp = datetime.now()
    
    mock_memory2 = Mock()
    mock_memory2.memory_id = "mem789012"
    mock_memory2.content = "J'aime React pour le frontend"
    mock_memory2.context.memory_type.value = "preference"
    mock_memory2.context.importance.value = "high"
    mock_memory2.context.timestamp = datetime.now()
    
    engine.search_memories = AsyncMock(return_value=[mock_memory1, mock_memory2])
    engine.add_memory = AsyncMock(return_value=mock_memory1)
    engine.get_stats = Mock(return_value={
        "total_memories": 10,
        "total_clusters": 3,
        "memory_types": {"semantic": 5, "preference": 3, "episodic": 2}
    })
    engine.memory_cache = {"mem123456": mock_memory1, "mem789012": mock_memory2}
    engine.cluster_cache = {
        "cluster1": Mock(keywords=["python", "development"], memory_ids=["mem123456"], theme="programming"),
        "cluster2": Mock(keywords=["react", "frontend"], memory_ids=["mem789012"], theme="preferences")
    }
    
    return engine


@pytest.fixture
def mock_notion_bridge():
    """Mock Notion bridge"""
    bridge = Mock()
    
    # Mock sync result
    mock_sync_result = Mock()
    mock_sync_result.status.value = "completed"
    mock_sync_result.pages_processed = 3
    mock_sync_result.entities_extracted = 5
    mock_sync_result.memories_created = 3
    mock_sync_result.duration_seconds = 2.5
    mock_sync_result.errors = []
    
    bridge.sync_notion_to_zep = AsyncMock(return_value=mock_sync_result)
    
    # Mock pages
    mock_page1 = Mock()
    mock_page1.page_id = "page123"
    mock_page1.title = "Projet Python"
    mock_page1.page_type.value = "project"
    mock_page1.content = "Développement d'un agent personnel avec Python et Zep"
    mock_page1.url = "https://notion.so/page123"
    mock_page1.last_edited = datetime.now()
    
    bridge.search_notion_content = AsyncMock(return_value=[mock_page1])
    bridge.get_sync_stats = Mock(return_value={
        "total_syncs": 2,
        "pages_synced": 5,
        "entities_extracted": 8,
        "memories_created": 5
    })
    
    return bridge


@pytest.fixture
def claude_extension(mock_agent, mock_memory_engine, mock_notion_bridge):
    """Extension Claude Code pour tests"""
    config = {
        "enable_history": True,
        "max_history": 10,
        "auto_sync": False
    }
    
    extension = ClaudeCodeExtension(
        agent=mock_agent,
        memory_engine=mock_memory_engine,
        notion_bridge=mock_notion_bridge,
        config=config
    )
    
    return extension


@pytest.fixture
async def initialized_extension(claude_extension):
    """Extension initialisée"""
    with patch('os.makedirs'), patch('builtins.open', Mock()), patch('json.dump'):
        await claude_extension.initialize()
    return claude_extension


class TestSlashCommand:
    """Tests pour SlashCommand"""
    
    def test_slash_command_creation(self):
        """Test création SlashCommand"""
        handler = Mock()
        
        command = SlashCommand(
            name="test",
            category=CommandCategory.MEMORY,
            description="Test command",
            usage="/test [options]",
            handler=handler,
            aliases=["t", "testing"],
            examples=["/test example"]
        )
        
        assert command.name == "test"
        assert command.category == CommandCategory.MEMORY
        assert command.description == "Test command"
        assert command.usage == "/test [options]"
        assert command.handler == handler
        assert command.aliases == ["t", "testing"]
        assert command.examples == ["/test example"]
        assert command.scope == CommandScope.USER  # default
        assert command.requires_agent == True  # default


class TestClaudeCodeExtension:
    """Tests pour ClaudeCodeExtension"""
    
    def test_extension_creation(self, mock_agent, mock_memory_engine, mock_notion_bridge):
        """Test création extension"""
        extension = ClaudeCodeExtension(
            agent=mock_agent,
            memory_engine=mock_memory_engine,
            notion_bridge=mock_notion_bridge,
            config={"test": True}
        )
        
        assert extension.agent == mock_agent
        assert extension.memory_engine == mock_memory_engine
        assert extension.notion_bridge == mock_notion_bridge
        assert extension.config["test"] == True
        assert not extension.is_initialized
        assert len(extension.commands) > 0  # Commands pré-enregistrées
    
    def test_command_registration(self, claude_extension):
        """Test enregistrement commandes"""
        handler = Mock()
        command = SlashCommand(
            name="custom",
            category=CommandCategory.SYSTEM,
            description="Custom command",
            usage="/custom",
            handler=handler,
            aliases=["c"]
        )
        
        initial_count = len(claude_extension.commands)
        claude_extension.register_command(command)
        
        # Commande + alias enregistrés
        assert len(claude_extension.commands) == initial_count + 2
        assert "custom" in claude_extension.commands
        assert "c" in claude_extension.commands
        assert claude_extension.commands["custom"] == command
        assert claude_extension.commands["c"] == command
    
    @pytest.mark.asyncio
    async def test_extension_initialization(self, claude_extension):
        """Test initialisation extension"""
        with patch('os.makedirs') as mock_mkdir, \
             patch('builtins.open', Mock()) as mock_open, \
             patch('json.dump') as mock_json:
            
            success = await claude_extension.initialize()
            
            assert success
            assert claude_extension.is_initialized
            mock_mkdir.assert_called_once()
            mock_open.assert_called_once()
            mock_json.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_extension_initialization_without_dependencies(self):
        """Test initialisation sans dépendances"""
        extension = ClaudeCodeExtension()
        
        with patch('os.makedirs'), patch('builtins.open', Mock()), patch('json.dump'):
            success = await extension.initialize()
            
            assert success
            assert extension.is_initialized
    
    def test_core_commands_registered(self, claude_extension):
        """Test que les commandes core sont enregistrées"""
        expected_commands = [
            "memory", "memory-add", "memory-stats",
            "notion", "notion-sync",
            "agents", "agent-status", 
            "context",
            "pkg",
            "evolve"
        ]
        
        for cmd_name in expected_commands:
            assert cmd_name in claude_extension.commands
            command = claude_extension.commands[cmd_name]
            assert isinstance(command, SlashCommand)
            assert command.name == cmd_name
            assert callable(command.handler)


class TestCommandExecution:
    """Tests d'exécution des commandes"""
    
    @pytest.mark.asyncio
    async def test_execute_command_invalid_format(self, initialized_extension):
        """Test commande invalide"""
        result = await initialized_extension.execute_command("invalid")
        
        assert result["status"] == "error"
        assert "Invalid command format" in result["message"]
    
    @pytest.mark.asyncio
    async def test_execute_command_unknown(self, initialized_extension):
        """Test commande inconnue"""
        result = await initialized_extension.execute_command("/unknown-command")
        
        assert result["status"] == "error"
        assert "Unknown command" in result["message"]
        assert "unknown-command" in result["message"]
    
    @pytest.mark.asyncio
    async def test_execute_command_requires_agent(self):
        """Test commande nécessitant un agent"""
        extension = ClaudeCodeExtension(agent=None)  # Pas d'agent
        with patch('os.makedirs'), patch('builtins.open', Mock()), patch('json.dump'):
            await extension.initialize()
        
        result = await extension.execute_command("/agent-status")
        
        assert result["status"] == "error"
        assert "requires an active agent" in result["message"]
    
    @pytest.mark.asyncio
    async def test_command_execution_history(self, initialized_extension):
        """Test historique des commandes"""
        initial_history_len = len(initialized_extension.command_history)
        
        await initialized_extension.execute_command("/memory-stats")
        
        assert len(initialized_extension.command_history) == initial_history_len + 1
        
        history_entry = initialized_extension.command_history[-1]
        assert history_entry["command"] == "/memory-stats"
        assert "result" in history_entry
        assert "timestamp" in history_entry


class TestMemoryCommands:
    """Tests des commandes mémoire"""
    
    @pytest.mark.asyncio
    async def test_memory_search_command(self, initialized_extension):
        """Test commande /memory"""
        result = await initialized_extension.execute_command("/memory python --limit=5")
        
        assert result["status"] == "success"
        assert result["query"] == "python"
        assert "results_count" in result
        assert "memories" in result
        assert len(result["memories"]) > 0
        
        memory = result["memories"][0]
        assert "id" in memory
        assert "content" in memory
        assert "type" in memory
        assert "importance" in memory
    
    @pytest.mark.asyncio
    async def test_memory_search_no_query(self, initialized_extension):
        """Test /memory sans query"""
        result = await initialized_extension.execute_command("/memory")
        
        assert result["status"] == "error"
        assert "Query required" in result["message"]
    
    @pytest.mark.asyncio
    async def test_memory_add_command(self, initialized_extension):
        """Test commande /memory-add"""
        # Patch imports Zep dans la fonction handler
        with patch('personal_agent_integrations.claude_code.extension.MemoryType', create=True) as mock_memory_type, \
             patch('personal_agent_integrations.claude_code.extension.MemoryImportance', create=True) as mock_importance:
            
            # Mock enum attributes
            mock_memory_type.PREFERENCE = Mock()
            mock_importance.MEDIUM = Mock()
            
            result = await initialized_extension.execute_command(
                "/memory-add \"J'aime le café\" --type=preference --importance=medium"
            )
            
            assert result["status"] == "success"
            assert result["content"] == "J'aime le café"
            assert result["type"] == "preference" 
            assert result["importance"] == "medium"
            assert "memory_id" in result
    
    @pytest.mark.asyncio
    async def test_memory_add_no_content(self, initialized_extension):
        """Test /memory-add sans contenu"""
        result = await initialized_extension.execute_command("/memory-add")
        
        assert result["status"] == "error"
        assert "Content required" in result["message"]
    
    @pytest.mark.asyncio
    async def test_memory_stats_command(self, initialized_extension):
        """Test commande /memory-stats"""
        result = await initialized_extension.execute_command("/memory-stats")
        
        assert result["status"] == "success"
        assert "stats" in result
        stats = result["stats"]
        assert "total_memories" in stats
        assert "total_clusters" in stats
    
    @pytest.mark.asyncio
    async def test_memory_stats_detailed(self, initialized_extension):
        """Test /memory-stats --detailed"""
        result = await initialized_extension.execute_command("/memory-stats --detailed")
        
        assert result["status"] == "success"
        assert "type_distribution" in result
        assert "top_clusters" in result
        assert len(result["top_clusters"]) > 0
        
        cluster = result["top_clusters"][0]
        assert "id" in cluster
        assert "keywords" in cluster
        assert "memories_count" in cluster
        assert "theme" in cluster
    
    @pytest.mark.asyncio
    async def test_memory_commands_without_engine(self):
        """Test commandes mémoire sans moteur"""
        extension = ClaudeCodeExtension(memory_engine=None)
        with patch('os.makedirs'), patch('builtins.open', Mock()), patch('json.dump'):
            await extension.initialize()
        
        result = await extension.execute_command("/memory-stats")
        
        assert result["status"] == "error"
        assert "Memory engine not available" in result["message"]


class TestNotionCommands:
    """Tests des commandes Notion"""
    
    @pytest.mark.asyncio
    async def test_notion_sync_command(self, initialized_extension):
        """Test commande /notion-sync"""
        result = await initialized_extension.execute_command("/notion-sync --full")
        
        assert result["status"] == "success"
        assert result["sync_status"] == "completed"
        assert result["pages_processed"] == 3
        assert result["entities_extracted"] == 5
        assert result["memories_created"] == 3
        assert "duration" in result
    
    @pytest.mark.asyncio
    async def test_notion_search_command(self, initialized_extension):
        """Test commande /notion search"""
        result = await initialized_extension.execute_command("/notion search projet")
        
        assert result["status"] == "success"
        assert result["query"] == "projet"
        assert "results_count" in result
        assert "pages" in result
        assert len(result["pages"]) > 0
        
        page = result["pages"][0]
        assert "id" in page
        assert "title" in page
        assert "type" in page
        assert "content_preview" in page
    
    @pytest.mark.asyncio
    async def test_notion_search_no_query(self, initialized_extension):
        """Test /notion search sans query"""
        result = await initialized_extension.execute_command("/notion search")
        
        assert result["status"] == "error"
        assert "Search query required" in result["message"]
    
    @pytest.mark.asyncio
    async def test_notion_stats_command(self, initialized_extension):
        """Test commande /notion stats"""
        result = await initialized_extension.execute_command("/notion stats")
        
        assert result["status"] == "success"
        assert "stats" in result
        stats = result["stats"]
        assert "pages_synced" in stats
        assert "total_syncs" in stats
    
    @pytest.mark.asyncio
    async def test_notion_unknown_subcommand(self, initialized_extension):
        """Test /notion avec sous-commande inconnue"""
        result = await initialized_extension.execute_command("/notion unknown")
        
        assert result["status"] == "error"
        assert "Unknown notion subcommand" in result["message"]
    
    @pytest.mark.asyncio
    async def test_notion_commands_without_bridge(self):
        """Test commandes Notion sans bridge"""
        extension = ClaudeCodeExtension(notion_bridge=None)
        with patch('os.makedirs'), patch('builtins.open', Mock()), patch('json.dump'):
            await extension.initialize()
        
        result = await extension.execute_command("/notion-sync")
        
        assert result["status"] == "error"
        assert "Notion bridge not available" in result["message"]


class TestAgentCommands:
    """Tests des commandes agent"""
    
    @pytest.mark.asyncio
    async def test_agent_status_command(self, initialized_extension):
        """Test commande /agent-status"""
        result = await initialized_extension.execute_command("/agent-status")
        
        assert result["status"] == "success"
        assert result["agent_status"] == "ready"
        assert "health" in result
        assert "stats" in result
    
    @pytest.mark.asyncio
    async def test_agent_status_detailed(self, initialized_extension):
        """Test /agent-status --detailed"""
        result = await initialized_extension.execute_command("/agent-status --detailed")
        
        assert result["status"] == "success"
        assert "capabilities" in result
        assert "integrations" in result
        assert "uptime" in result
        
        integrations = result["integrations"]
        assert "memory_engine" in integrations
        assert "notion_bridge" in integrations
    
    @pytest.mark.asyncio
    async def test_agents_list_command(self, initialized_extension):
        """Test commande /agents list"""
        result = await initialized_extension.execute_command("/agents list")
        
        assert result["status"] == "success"
        assert "agents" in result
        assert "count" in result
        assert len(result["agents"]) > 0
        
        agent = result["agents"][0]
        assert agent["name"] == "Personal Agent"
        assert agent["type"] == "local"
        assert agent["status"] == "ready"
    
    @pytest.mark.asyncio
    async def test_agents_discover_without_a2a(self, initialized_extension):
        """Test /agents discover sans A2A manager"""
        result = await initialized_extension.execute_command("/agents discover")
        
        assert result["status"] == "error"
        assert "A2A manager not available" in result["message"]


class TestContextCommands:
    """Tests des commandes contexte"""
    
    @pytest.mark.asyncio
    async def test_context_analyze_command(self, initialized_extension):
        """Test commande /context analyze"""
        result = await initialized_extension.execute_command("/context analyze python")
        
        assert result["status"] == "success"
        assert result["query"] == "python"
        assert "context" in result
        
        context = result["context"]
        assert "memories" in context
        assert "notion_pages" in context
        assert "entities" in context
        assert "themes" in context
    
    @pytest.mark.asyncio
    async def test_context_graph_command(self, initialized_extension):
        """Test commande /context graph"""
        result = await initialized_extension.execute_command("/context graph")
        
        assert result["status"] == "info"
        assert "not yet implemented" in result["message"]
    
    @pytest.mark.asyncio
    async def test_context_timeline_command(self, initialized_extension):
        """Test commande /context timeline"""
        result = await initialized_extension.execute_command("/context timeline --days=30")
        
        assert result["status"] == "info"
        assert "not yet implemented" in result["message"]


class TestSystemCommands:
    """Tests des commandes système"""
    
    @pytest.mark.asyncio
    async def test_pkg_command(self, initialized_extension):
        """Test commande /pkg"""
        result = await initialized_extension.execute_command("/pkg status")
        
        assert result["status"] == "info"
        assert "not yet implemented" in result["message"]
    
    @pytest.mark.asyncio
    async def test_evolve_command(self, initialized_extension):
        """Test commande /evolve"""
        result = await initialized_extension.execute_command("/evolve status")
        
        assert result["status"] == "info"
        assert "not yet implemented" in result["message"]


class TestHelpSystem:
    """Tests du système d'aide"""
    
    def test_get_command_help_general(self, claude_extension):
        """Test aide générale"""
        help_result = claude_extension.get_command_help()
        
        assert help_result["status"] == "success"
        assert "categories" in help_result
        assert "total_commands" in help_result
        assert help_result["total_commands"] > 0
        
        categories = help_result["categories"]
        assert len(categories) > 0
        
        # Vérifier qu'on a les catégories attendues
        expected_categories = ["memory", "notion", "agents", "context", "pkg", "system"]
        for category in expected_categories:
            if category in categories:
                assert len(categories[category]) > 0
                for cmd in categories[category]:
                    assert "name" in cmd
                    assert "description" in cmd
                    assert "usage" in cmd
    
    def test_get_command_help_specific(self, claude_extension):
        """Test aide pour commande spécifique"""
        help_result = claude_extension.get_command_help("memory")
        
        assert help_result["status"] == "success"
        assert "command" in help_result
        
        cmd_info = help_result["command"]
        assert cmd_info["name"] == "memory"
        assert cmd_info["category"] == "memory"
        assert "description" in cmd_info
        assert "usage" in cmd_info
        assert "examples" in cmd_info
    
    def test_get_command_help_unknown(self, claude_extension):
        """Test aide pour commande inconnue"""
        help_result = claude_extension.get_command_help("unknown")
        
        assert help_result["status"] == "error"
        assert "Unknown command" in help_result["message"]


class TestConfigurationGeneration:
    """Tests génération configuration Claude Code"""
    
    @pytest.mark.asyncio
    async def test_claude_config_generation(self, claude_extension):
        """Test génération configuration .claude/agent-config.json"""
        from unittest.mock import mock_open
        
        with patch('os.makedirs') as mock_mkdir, \
             patch('builtins.open', mock_open()) as mock_open_patch, \
             patch('json.dump') as mock_json:
            
            await claude_extension.initialize()
            
            # Vérifications
            mock_mkdir.assert_called_once_with(".claude", exist_ok=True)
            mock_open_patch.assert_called_once_with(".claude/agent-config.json", 'w', encoding='utf-8')
            mock_json.assert_called_once()
            
            # Vérifier structure config passée à json.dump
            config_written = mock_json.call_args[0][0]  # Premier argument
            
            assert config_written["name"] == "Personal Agent Extension"
            assert "version" in config_written
            assert "description" in config_written
            assert "commands" in config_written
            assert "settings" in config_written
            assert "integrations" in config_written
            
            # Vérifier intégrations
            integrations = config_written["integrations"]
            assert "zep_memory" in integrations
            assert "notion_sync" in integrations
            assert "a2a_protocol" in integrations
            
            # Vérifier commandes
            commands = config_written["commands"]
            assert len(commands) > 0
            
            for cmd_name, cmd_info in commands.items():
                assert "name" in cmd_info
                assert "category" in cmd_info
                assert "description" in cmd_info
                assert "usage" in cmd_info


class TestFactoryFunction:
    """Tests de la fonction factory"""
    
    @pytest.mark.asyncio
    async def test_create_claude_extension(self, mock_agent, mock_memory_engine, mock_notion_bridge):
        """Test fonction factory create_claude_extension"""
        config = {"test": True}
        
        with patch.object(ClaudeCodeExtension, 'initialize', new=AsyncMock(return_value=True)):
            extension = await create_claude_extension(
                agent=mock_agent,
                memory_engine=mock_memory_engine,
                notion_bridge=mock_notion_bridge,
                config=config
            )
        
        assert isinstance(extension, ClaudeCodeExtension)
        assert extension.agent == mock_agent
        assert extension.memory_engine == mock_memory_engine
        assert extension.notion_bridge == mock_notion_bridge
        assert extension.config["test"] == True


class TestEdgeCases:
    """Tests des cas limites"""
    
    @pytest.mark.asyncio
    async def test_extension_without_any_components(self):
        """Test extension sans aucun composant"""
        extension = ClaudeCodeExtension()
        
        with patch('os.makedirs'), patch('builtins.open', Mock()), patch('json.dump'):
            success = await extension.initialize()
            
            assert success
            assert extension.is_initialized
    
    @pytest.mark.asyncio
    async def test_command_execution_exception(self, initialized_extension):
        """Test gestion d'exception pendant exécution commande"""
        # Mock handler qui lève une exception
        def failing_handler(args):
            raise Exception("Test exception")
        
        command = SlashCommand(
            name="fail",
            category=CommandCategory.SYSTEM,
            description="Failing command",
            usage="/fail",
            handler=failing_handler
        )
        
        initialized_extension.register_command(command)
        
        result = await initialized_extension.execute_command("/fail")
        
        assert result["status"] == "error"
        assert "Command execution failed" in result["message"]
        assert "Test exception" in result["message"]
    
    @pytest.mark.asyncio
    async def test_command_history_limit(self, initialized_extension):
        """Test limite historique commandes"""
        initialized_extension.max_history = 2
        
        # Exécuter 3 commandes
        await initialized_extension.execute_command("/memory-stats")
        await initialized_extension.execute_command("/agent-status")
        await initialized_extension.execute_command("/notion stats")
        
        # Vérifier que seulement les 2 dernières sont gardées
        assert len(initialized_extension.command_history) == 2
        assert initialized_extension.command_history[-1]["command"] == "/notion stats"
        assert initialized_extension.command_history[-2]["command"] == "/agent-status"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])