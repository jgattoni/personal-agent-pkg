"""
Tests unitaires pour BasePersonalAgent
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
import sys
import os

# Ajout du path pour import des modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../packages/core'))

from personal_agent_core.agents.base_agent import (
    BasePersonalAgent,
    AgentCapability,
    AgentState,
    AgentContext,
    AgentMessage,
    AgentResponse,
    create_personal_agent
)


@pytest.fixture
async def mock_zep_client():
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
async def basic_agent(mock_zep_client):
    """Agent basique pour tests"""
    agent = BasePersonalAgent(
        user_id="test_user",
        agent_name="TestAgent",
        zep_client=mock_zep_client,
        enable_a2a=False,
        enable_mcp=False,
        enable_graphiti=False
    )
    return agent


@pytest.fixture
async def initialized_agent(basic_agent):
    """Agent initialisé"""
    await basic_agent.initialize()
    return basic_agent


class TestBasePersonalAgent:
    """Tests pour BasePersonalAgent"""
    
    def test_agent_creation(self):
        """Test création basique d'un agent"""
        agent = BasePersonalAgent(
            user_id="test_user",
            agent_name="TestAgent"
        )
        
        assert agent.user_id == "test_user"
        assert agent.agent_name == "TestAgent"
        assert agent.state == AgentState.INITIALIZING
        assert isinstance(agent.context, AgentContext)
        assert agent.context.user_id == "test_user"
    
    def test_capability_determination(self):
        """Test détermination des capacités"""
        # Agent avec toutes les capacités
        agent_full = BasePersonalAgent(
            user_id="test",
            enable_a2a=True,
            enable_mcp=True,
            enable_graphiti=True
        )
        
        assert AgentCapability.PROTOCOL_A2A in agent_full.context.capabilities
        assert AgentCapability.PROTOCOL_MCP in agent_full.context.capabilities
        assert AgentCapability.KNOWLEDGE_GRAPH in agent_full.context.capabilities
        assert AgentCapability.MEMORY_MANAGEMENT in agent_full.context.capabilities
        
        # Agent minimaliste
        agent_min = BasePersonalAgent(
            user_id="test",
            enable_a2a=False,
            enable_mcp=False,
            enable_graphiti=False
        )
        
        assert AgentCapability.PROTOCOL_A2A not in agent_min.context.capabilities
        assert AgentCapability.MEMORY_MANAGEMENT in agent_min.context.capabilities
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self, basic_agent, mock_zep_client):
        """Test initialisation de l'agent"""
        with patch.object(basic_agent, '_init_memory_engine', new=AsyncMock()):
            with patch.object(basic_agent, '_load_user_context', new=AsyncMock()):
                await basic_agent.initialize()
        
        assert basic_agent.state == AgentState.READY
        assert basic_agent.memory_engine is not None
    
    @pytest.mark.asyncio
    async def test_message_processing(self, initialized_agent):
        """Test traitement d'un message simple"""
        with patch.object(initialized_agent, '_detect_intent', return_value="general_conversation"):
            with patch.object(initialized_agent, '_generate_contextual_response', return_value="Test response"):
                response = await initialized_agent.process_message("Hello, agent!")
        
        assert isinstance(response, AgentResponse)
        assert response.content == "Test response"
        assert "Generated contextual response" in response.actions_taken
        assert initialized_agent.stats["messages_processed"] == 1
    
    @pytest.mark.asyncio
    async def test_agent_message_object(self, initialized_agent):
        """Test traitement avec objet AgentMessage"""
        message = AgentMessage(
            content="Test message",
            source="test_suite",
            priority=8
        )
        
        with patch.object(initialized_agent, '_detect_intent', return_value="general_conversation"):
            with patch.object(initialized_agent, '_generate_contextual_response', return_value="Response"):
                response = await initialized_agent.process_message(message)
        
        assert response.message_id == message.message_id
        assert response.content == "Response"
    
    def test_intent_detection(self, basic_agent):
        """Test détection d'intention"""
        # Task execution
        assert asyncio.run(basic_agent._detect_intent("Please execute this task")) == "task_execution"
        assert asyncio.run(basic_agent._detect_intent("Run the script")) == "task_execution"
        
        # Knowledge query
        assert asyncio.run(basic_agent._detect_intent("Who is John?")) == "knowledge_query"
        assert asyncio.run(basic_agent._detect_intent("Tell me about Python")) == "knowledge_query"
        
        # File operation
        assert asyncio.run(basic_agent._detect_intent("Read the file config.json")) == "file_operation"
        assert asyncio.run(basic_agent._detect_intent("Create a new folder")) == "file_operation"
        
        # Memory query
        assert asyncio.run(basic_agent._detect_intent("What did I say yesterday?")) == "memory_query"
        assert asyncio.run(basic_agent._detect_intent("Remember this for later")) == "memory_query"
        
        # General
        assert asyncio.run(basic_agent._detect_intent("Hello there")) == "general_conversation"
    
    @pytest.mark.asyncio
    async def test_event_handler_registration(self, basic_agent):
        """Test enregistrement et déclenchement d'événements"""
        handler_called = False
        event_data = None
        
        async def test_handler(data):
            nonlocal handler_called, event_data
            handler_called = True
            event_data = data
        
        basic_agent.register_event_handler("test_event", test_handler)
        await basic_agent._trigger_event("test_event", {"test": "data"})
        
        assert handler_called
        assert event_data == {"test": "data"}
    
    @pytest.mark.asyncio
    async def test_learning_from_interaction(self, initialized_agent):
        """Test apprentissage depuis interaction"""
        message = AgentMessage(content="Test message", source="test")
        response = AgentResponse(
            message_id=message.message_id,
            content="Test response",
            metadata={"intent": "general_conversation"}
        )
        
        # Ajout de la capacité d'apprentissage
        initialized_agent.context.capabilities.append(AgentCapability.LEARNING)
        
        with patch.object(initialized_agent.graphiti_engine, 'ingest_episode', new=AsyncMock()) if initialized_agent.graphiti_engine else patch('builtins.print'):
            with patch.object(initialized_agent.memory_engine, 'update_behavior_patterns', new=AsyncMock()) if initialized_agent.memory_engine else patch('builtins.print'):
                await initialized_agent.learn_from_interaction(
                    message, 
                    response, 
                    "Good response"
                )
        
        assert initialized_agent.state == AgentState.READY
    
    @pytest.mark.asyncio
    async def test_stats_tracking(self, initialized_agent):
        """Test suivi des statistiques"""
        # Process a message
        with patch.object(initialized_agent, '_detect_intent', return_value="general_conversation"):
            with patch.object(initialized_agent, '_generate_contextual_response', return_value="Response"):
                await initialized_agent.process_message("Test")
        
        stats = await initialized_agent.get_stats()
        
        assert stats["messages_processed"] == 1
        assert stats["errors"] == 0
        assert "state" in stats
        assert "capabilities" in stats
        assert "uptime" in stats
    
    @pytest.mark.asyncio
    async def test_health_check(self, initialized_agent):
        """Test health check"""
        health = await initialized_agent.health_check()
        
        assert health["status"] == "healthy"
        assert health["agent_state"] == AgentState.READY.value
        assert "components" in health
        assert health["components"]["memory"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_error_handling(self, initialized_agent):
        """Test gestion des erreurs"""
        with patch.object(initialized_agent, '_detect_intent', side_effect=Exception("Test error")):
            response = await initialized_agent.process_message("Cause error")
        
        assert response.confidence == 0.0
        assert "error_handling" in response.actions_taken
        assert initialized_agent.stats["errors"] == 1
    
    @pytest.mark.asyncio
    async def test_message_queue_processing(self, initialized_agent):
        """Test traitement de la queue de messages"""
        # Ajout message à la queue
        message = AgentMessage(content="Queued message", source="test")
        await initialized_agent.message_queue.put(message)
        
        # Attendre un peu pour le traitement
        await asyncio.sleep(0.1)
        
        # Le message devrait être dans le cache des réponses
        # (si le processeur fonctionne)
        # Note: Ce test dépend du processeur async qui tourne en background
    
    @pytest.mark.asyncio
    async def test_shutdown(self, initialized_agent):
        """Test arrêt propre de l'agent"""
        with patch.object(initialized_agent, 'sync_with_cloud', new=AsyncMock()):
            await initialized_agent.shutdown()
        
        assert initialized_agent.state == AgentState.SHUTDOWN
    
    @pytest.mark.asyncio
    async def test_context_update_activity(self, basic_agent):
        """Test mise à jour activité du contexte"""
        initial_activity = basic_agent.context.last_activity
        await asyncio.sleep(0.01)
        basic_agent.context.update_activity()
        
        assert basic_agent.context.last_activity > initial_activity
    
    @pytest.mark.asyncio
    async def test_factory_function(self, mock_zep_client):
        """Test fonction factory pour création d'agent"""
        with patch('personal_agent_core.agents.base_agent.BasePersonalAgent.initialize', new=AsyncMock()):
            agent = await create_personal_agent(
                user_id="factory_test",
                zep_client=mock_zep_client,
                config={"test": "config"}
            )
        
        assert isinstance(agent, BasePersonalAgent)
        assert agent.user_id == "factory_test"
        assert agent.config == {"test": "config"}


class TestAgentProtocolIntegration:
    """Tests d'intégration avec les protocoles"""
    
    @pytest.mark.asyncio
    async def test_a2a_initialization(self):
        """Test initialisation A2A"""
        agent = BasePersonalAgent(
            user_id="test",
            enable_a2a=True,
            enable_mcp=False,
            enable_graphiti=False
        )
        
        with patch('personal_agent_core.agents.base_agent.A2AManager') as MockA2A:
            mock_manager = Mock()
            mock_manager.initialize = AsyncMock()
            mock_manager.register_capability = AsyncMock()
            MockA2A.return_value = mock_manager
            
            await agent._init_a2a()
        
        assert agent.a2a_manager is not None
    
    @pytest.mark.asyncio
    async def test_mcp_initialization(self):
        """Test initialisation MCP"""
        agent = BasePersonalAgent(
            user_id="test",
            enable_mcp=True,
            config={"mcp_servers": ["filesystem"]}
        )
        
        with patch('personal_agent_core.agents.base_agent.MCPManager') as MockMCP:
            mock_manager = Mock()
            mock_manager.connect_filesystem_server = AsyncMock()
            MockMCP.return_value = mock_manager
            
            await agent._init_mcp()
        
        assert agent.mcp_manager is not None
    
    @pytest.mark.asyncio
    async def test_graphiti_initialization(self):
        """Test initialisation Graphiti"""
        agent = BasePersonalAgent(
            user_id="test",
            enable_graphiti=True
        )
        
        with patch('personal_agent_core.graph.graphiti_engine.create_graphiti_engine', new=AsyncMock()):
            await agent._init_graphiti()
        
        assert agent.graphiti_engine is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])