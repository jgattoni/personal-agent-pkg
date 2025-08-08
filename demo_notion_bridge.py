#!/usr/bin/env python3
"""
Demo du NotionZepBridge - Synchronisation Notion ↔ Zep avec extraction d'entités
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'packages/core'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'packages/integrations'))

from personal_agent_integrations.notion.notion_zep_bridge import (
    NotionZepBridge, NotionPage, NotionPageType, create_notion_zep_bridge
)
from personal_agent_core.agents.base_agent import BasePersonalAgent
from personal_agent_core.memory.zep_engine import ZepPersonalMemoryEngine, MemoryType
from personal_agent_core.graph.graphiti_engine import GraphitiEngine


class MockNotionAPI:
    """Mock réaliste de l'API Notion pour demo"""
    
    def __init__(self):
        self.mock_pages = {
            "page_1": {
                "id": "page_1",
                "object": "page", 
                "properties": {"title": {"title": [{"plain_text": "Projet Agent Personnel"}]}},
                "last_edited_time": (datetime.now() - timedelta(days=1)).isoformat(),
                "url": "https://notion.so/projet-agent",
                "blocks": [
                    {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "Développement d'un agent personnel avec Zep Memory et GraphitiEngine."}]}},
                    {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "Équipe: John Doe (tech lead), Marie Curie (data scientist)"}]}},
                    {"type": "to_do", "to_do": {"rich_text": [{"plain_text": "Implémenter NotionZepBridge"}], "checked": True}},
                    {"type": "to_do", "to_do": {"rich_text": [{"plain_text": "Tester l'extraction d'entités"}], "checked": False}},
                    {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "Timeline: Q1 2024. Budget: 50k€. Priorité: HIGH"}]}}
                ]
            },
            "page_2": {
                "id": "page_2",
                "object": "page",
                "properties": {"title": {"title": [{"plain_text": "Réunion équipe du 15/01"}]}},
                "last_edited_time": (datetime.now() - timedelta(hours=3)).isoformat(),
                "url": "https://notion.so/reunion-equipe",
                "blocks": [
                    {"type": "heading_1", "heading_1": {"rich_text": [{"plain_text": "Meeting Notes - Team Sync"}]}},
                    {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "Participants: John, Marie, Pierre, Sophie"}]}},
                    {"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [{"plain_text": "Review du sprint en cours"}]}},
                    {"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [{"plain_text": "Discussion architecture Zep + MCP"}]}},
                    {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "Actions: Pierre finalise les tests, Sophie documente l'API"}]}},
                    {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "Prochaine réunion: 22/01 à 14h"}]}}
                ]
            },
            "page_3": {
                "id": "page_3", 
                "object": "page",
                "properties": {"title": {"title": [{"plain_text": "Contact: Dr. Alan Turing"}]}},
                "last_edited_time": (datetime.now() - timedelta(days=5)).isoformat(),
                "url": "https://notion.so/contact-turing",
                "blocks": [
                    {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "Expert en intelligence artificielle et cryptographie"}]}},
                    {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "Email: alan.turing@cambridge.ac.uk"}]}},
                    {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "Spécialités: Machine Learning, Theoretical CS, Cryptanalysis"}]}},
                    {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "Collaboration potentielle sur le projet d'agent personnel"}]}}
                ]
            }
        }


class MockMCPManager:
    """Mock du MCP Manager avec API Notion simulée"""
    
    def __init__(self):
        self.notion_api = MockNotionAPI()
        self.connected = False
    
    async def connect_notion_server(self, token):
        """Simulation connexion Notion MCP"""
        print(f"🔗 [MCP] Connexion au serveur Notion avec token: {token[:10]}...")
        await asyncio.sleep(0.1)
        self.connected = True
        print("✅ [MCP] Connecté à Notion API via MCP")
    
    async def discover_tools(self, server_name):
        """Simulation découverte des outils MCP"""
        if server_name == "notion":
            return [
                type('Tool', (), {"name": "search"})(),
                type('Tool', (), {"name": "retrieve_page"})(),
                type('Tool', (), {"name": "retrieve_block_children"})(),
                type('Tool', (), {"name": "query_database"})()
            ]
        return []
    
    async def execute_tool(self, server, tool_name, params):
        """Simulation exécution d'outils MCP Notion"""
        if server != "notion" or not self.connected:
            return {}
        
        if tool_name == "search":
            # Retour de toutes les pages mock
            return {
                "results": list(self.notion_api.mock_pages.values())
            }
        
        elif tool_name == "retrieve_page":
            page_id = params.get("page_id")
            return self.notion_api.mock_pages.get(page_id, {})
        
        elif tool_name == "retrieve_block_children":
            block_id = params.get("block_id")
            page = self.notion_api.mock_pages.get(block_id)
            if page:
                return {"results": page["blocks"]}
        
        return {}


async def demo_notion_bridge_full():
    """Demo complet du NotionZepBridge"""
    print("🌉 === DEMO NOTION-ZEP BRIDGE ===\n")
    
    # 1. Création des composants
    print("1️⃣ Initialisation des composants...")
    
    # Mock Zep Memory Engine
    memory_engine = ZepPersonalMemoryEngine(
        user_id="demo_user",
        zep_client=None,  # Mode local
        config={"enable_clustering": True, "auto_summarize": True}
    )
    await memory_engine.initialize()
    print("✅ ZepMemoryEngine initialisé")
    
    # Mock Graphiti Engine
    graphiti_engine = GraphitiEngine(user_id="demo_user")
    print("✅ GraphitiEngine initialisé")
    
    # Mock MCP Manager
    mcp_manager = MockMCPManager()
    print("✅ MCPManager mocké initialisé")
    
    # NotionZepBridge
    bridge = await create_notion_zep_bridge(
        user_id="demo_user",
        notion_token="mock_token_abcd1234567890",
        zep_memory_engine=memory_engine,
        graphiti_engine=graphiti_engine,
        mcp_manager=mcp_manager,
        config={
            "use_mcp": True,
            "max_pages_per_sync": 10,
            "enable_auto_sync": False,
            "sync_filters": {
                "min_content_length": 20,
                "include_pages": True,
                "skip_archived": True
            }
        }
    )
    print("✅ NotionZepBridge initialisé\n")
    
    # 2. Synchronisation Notion → Zep
    print("2️⃣ Synchronisation Notion → Zep Memory...")
    sync_result = await bridge.sync_notion_to_zep(force_full_sync=True)
    
    print(f"📊 Résultat de la sync:")
    print(f"   Status: {sync_result.status.value}")
    print(f"   Pages traitées: {sync_result.pages_processed}")
    print(f"   Entités extraites: {sync_result.entities_extracted}")
    print(f"   Mémoires créées: {sync_result.memories_created}")
    print(f"   Durée: {sync_result.duration_seconds:.2f}s")
    if sync_result.errors:
        print(f"   Erreurs: {sync_result.errors}")
    print()
    
    # 3. Exploration du cache des pages
    print("3️⃣ Exploration des pages Notion synchronisées...")
    for page_id, page in bridge.pages_cache.items():
        print(f"📄 {page.title} ({page.page_type.value})")
        print(f"   ID: {page_id}")
        print(f"   Contenu: {page.content[:100]}...")
        print(f"   Dernière modif: {page.last_edited.strftime('%Y-%m-%d %H:%M')}")
        print(f"   Tags: {page.tags}")
        print(f"   Mentions: {page.mentions}")
        print()
    
    # 4. Test de recherche dans les pages
    print("4️⃣ Test de recherche dans les pages Notion...")
    search_queries = ["projet", "réunion", "Alan", "tests"]
    
    for query in search_queries:
        results = await bridge.search_notion_content(query, limit=3)
        print(f"🔍 Recherche '{query}': {len(results)} résultat(s)")
        for result in results:
            print(f"   📄 {result.title} ({result.page_type.value})")
    print()
    
    # 5. Vérification de la mémoire Zep
    print("5️⃣ Vérification des mémoires créées dans Zep...")
    all_memories = []
    for memory_id, memory in memory_engine.memory_cache.items():
        if "notion_bridge" in memory.context.metadata.get("source", ""):
            all_memories.append(memory)
    
    print(f"🧠 {len(all_memories)} mémoires Notion dans Zep:")
    for memory in all_memories:
        print(f"   💾 {memory.memory_id[:8]}: {memory.content[:60]}...")
        print(f"      Type: {memory.context.memory_type.value}")
        print(f"      Importance: {memory.context.importance.value}")
        print(f"      Entités: {memory.context.metadata.get('entities', [])}")
        print()
    
    # 6. Test de recherche dans la mémoire
    print("6️⃣ Test de recherche dans la mémoire Zep...")
    memory_searches = ["John Doe", "agent personnel", "réunion", "Pierre"]
    
    for search_term in memory_searches:
        memory_results = await memory_engine.search_memories(search_term, limit=2)
        print(f"🔎 Recherche mémoire '{search_term}': {len(memory_results)} résultat(s)")
        for result in memory_results:
            print(f"   🧠 {result.content[:80]}...")
    print()
    
    # 7. Stats et export
    print("7️⃣ Statistiques et export...")
    stats = bridge.get_sync_stats()
    print(f"📈 Stats du bridge:")
    print(f"   Syncs totales: {stats['total_syncs']}")
    print(f"   Pages synchronisées: {stats['pages_synced']}")  
    print(f"   Entités extraites: {stats['entities_extracted']}")
    print(f"   Pages en cache: {stats['pages_cached']}")
    print(f"   Utilise MCP: {stats['use_mcp']}")
    
    # Export des données
    export_data = await bridge.export_notion_cache(format="dict")
    print(f"\n📤 Export: {export_data['total_pages']} pages exportées")
    
    return bridge, memory_engine, graphiti_engine


async def demo_agent_with_notion():
    """Demo agent personnel avec accès Notion via bridge"""
    print("\n🤖 === AGENT AVEC NOTION INTÉGRÉ ===\n")
    
    # Récupération des composants du demo précédent
    bridge, memory_engine, graphiti_engine = await demo_notion_bridge_full()
    
    # Création agent avec accès Notion
    agent = BasePersonalAgent(
        user_id="demo_user",
        agent_name="NotionAgent",
        zep_client=None,
        enable_a2a=False,
        enable_mcp=False,
        enable_graphiti=False,
        config={
            "enable_learning": True,
            "notion_bridge": bridge
        }
    )
    
    # Injection du bridge dans l'agent (simulation)
    agent.notion_bridge = bridge
    agent.memory_engine = memory_engine
    
    await agent.initialize()
    print("✅ Agent avec Notion bridge initialisé\n")
    
    # Conversations test
    conversations = [
        ("Qui travaille sur le projet agent personnel ?", "👥 Question sur l'équipe"),
        ("Quand est la prochaine réunion ?", "📅 Question planning"),
        ("Qui est Alan Turing dans mes contacts ?", "👤 Question contact"),
        ("Quelles sont les tâches en cours ?", "✅ Question tâches"),
        ("Résume mes dernières notes Notion", "📝 Demande de résumé")
    ]
    
    print("💬 Conversations avec l'agent (accès aux données Notion):")
    
    for message, description in conversations:
        print(f"\n{description}")
        print(f"👤 VOUS: {message}")
        
        # L'agent peut maintenant répondre avec les données Notion
        response = await agent.process_message(message)
        print(f"🤖 AGENT: {response.content}")
        print(f"🎯 Confiance: {response.confidence:.1f}")
        
        await asyncio.sleep(0.5)
    
    # Stats finales
    print(f"\n📊 STATS FINALES:")
    agent_stats = await agent.get_stats()
    bridge_stats = bridge.get_sync_stats()
    
    print(f"🤖 Agent: {agent_stats['messages_processed']} messages traités")
    print(f"🌉 Bridge: {bridge_stats['pages_synced']} pages Notion synchronisées")
    print(f"🧠 Mémoire: {len(memory_engine.memory_cache)} mémoires en cache")
    
    return agent


async def demo_realtime_sync():
    """Demo synchronisation temps réel"""
    print("\n⚡ === DEMO SYNC TEMPS RÉEL ===\n")
    
    # Simulation d'une nouvelle page Notion ajoutée
    print("📝 Simulation: Nouvelle page ajoutée dans Notion...")
    
    bridge = await create_notion_zep_bridge(
        user_id="realtime_user",
        notion_token="realtime_token",
        mcp_manager=MockMCPManager(),
        config={"enable_auto_sync": False}
    )
    
    # Première sync
    print("1️⃣ Sync initiale...")
    result1 = await bridge.sync_notion_to_zep()
    print(f"   Pages: {result1.pages_processed}, Durée: {result1.duration_seconds:.2f}s")
    
    # Simulation ajout de contenu
    await asyncio.sleep(0.1)
    print("\n2️⃣ Ajout simulé de nouvelles pages...")
    
    # Deuxième sync (mode incrémental)
    result2 = await bridge.sync_notion_to_zep(force_full_sync=False)
    print(f"   Sync incrémentale - Pages: {result2.pages_processed}")
    
    # Historique des syncs
    history = bridge.get_recent_sync_results(limit=5)
    print(f"\n📚 Historique des {len(history)} dernières syncs:")
    for i, sync in enumerate(history, 1):
        print(f"   {i}. {sync.status.value} - {sync.pages_processed} pages - {sync.duration_seconds:.2f}s")


async def main():
    """Menu principal"""
    print("🚀 DEMO NOTION-ZEP BRIDGE - Milestone 1.3\n")
    
    print("Choisissez votre demo:")
    print("1 - Bridge Notion-Zep complet")
    print("2 - Agent avec intégration Notion")
    print("3 - Synchronisation temps réel")
    print("4 - Tous les demos")
    
    choice = input("\nVotre choix (1-4): ").strip()
    
    try:
        if choice == "1":
            await demo_notion_bridge_full()
        elif choice == "2":
            await demo_agent_with_notion()
        elif choice == "3":
            await demo_realtime_sync()
        elif choice == "4":
            await demo_notion_bridge_full()
            await demo_agent_with_notion() 
            await demo_realtime_sync()
        else:
            print("❌ Choix invalide")
            return
        
        print("\n🎉 Demo terminé avec succès !")
        print("💡 Le bridge Notion-Zep permet à votre agent de comprendre et utiliser vos notes Notion !")
        
    except Exception as e:
        print(f"❌ Erreur: {str(e)}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Demo interrompu")
    except Exception as e:
        print(f"\n❌ Erreur: {str(e)}")