#!/usr/bin/env python3
"""
Demo et test pratique de l'agent personnel
Exemple d'utilisation concrète sans dépendances externes
"""

import asyncio
import sys
import os
from datetime import datetime

# Ajouter le path pour imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'packages/core'))

from personal_agent_core.agents.base_agent import BasePersonalAgent, AgentMessage
from personal_agent_core.memory.zep_engine import ZepPersonalMemoryEngine, MemoryType, MemoryImportance


class MockZepClient:
    """Mock simple du client Zep pour le demo"""
    def __init__(self):
        self.memory = MockMemory()
        
class MockMemory:
    """Mock de la mémoire Zep"""
    def __init__(self):
        self.memories = []
        
    async def add_memory(self, session_id, messages, metadata=None):
        print(f"💾 [ZEP] Sauvegarde: {messages[0]['content'][:50]}...")
        self.memories.append({"session": session_id, "content": messages[0]['content']})
        
    async def search_memory(self, session_id, search_payload, limit=10):
        return []  # Retour vide pour simplicité
        
    async def list_sessions(self):
        return []
        
    async def add_session(self, session_id, metadata=None):
        print(f"📁 [ZEP] Création session: {session_id}")


async def demo_agent_conversations():
    """Demo de conversations avec l'agent"""
    print("🤖 === DEMO AGENT PERSONNEL ===\n")
    
    # 1. Création de l'agent avec mock
    print("1️⃣ Création de l'agent personnel...")
    mock_zep = MockZepClient()
    
    agent = BasePersonalAgent(
        user_id="julien",
        agent_name="MonAssistant",
        zep_client=mock_zep,
        enable_a2a=False,  # Désactivé pour demo simple
        enable_mcp=False,  # Désactivé pour demo simple  
        enable_graphiti=False,  # Désactivé pour demo simple
        config={
            "enable_learning": True,
            "enable_preferences": True
        }
    )
    
    await agent.initialize()
    print(f"✅ Agent '{agent.agent_name}' créé avec succès!")
    print(f"📊 État: {agent.state.value}")
    print(f"🎯 Capacités: {[c.value for c in agent.context.capabilities]}\n")
    
    # 2. Conversations de test
    conversations = [
        "Bonjour, je m'appelle Julien et je suis développeur Python",
        "J'aime travailler sur des projets d'IA et machine learning", 
        "Peux-tu m'aider à organiser mes idées sur ce projet d'agent personnel?",
        "Quels sont mes préférences techniques que tu as retenues?",
        "Comment peux-tu m'assister dans mes tâches de développement?"
    ]
    
    print("2️⃣ Série de conversations avec l'agent...\n")
    
    for i, message in enumerate(conversations, 1):
        print(f"👤 [UTILISATEUR] {message}")
        
        # Traitement du message par l'agent
        response = await agent.process_message(message)
        
        print(f"🤖 [AGENT] {response.content}")
        print(f"⚡ Actions: {', '.join(response.actions_taken)}")
        print(f"📈 Confiance: {response.confidence:.1f}")
        print("---")
    
    # 3. Statistiques de l'agent
    print("\n3️⃣ Statistiques de l'agent:")
    stats = await agent.get_stats()
    for key, value in stats.items():
        if not isinstance(value, dict):
            print(f"📊 {key}: {value}")
    
    # 4. Test d'apprentissage
    print("\n4️⃣ Test d'apprentissage avec feedback:")
    message = AgentMessage(content="Rappelle-moi mes préférences", source="user")
    response = await agent.process_message(message)
    print(f"🤖 Réponse: {response.content}")
    
    # Feedback positif
    await agent.learn_from_interaction(message, response, "Très bonne réponse, merci!")
    print("✅ Feedback positif intégré")
    
    # 5. Health check
    print("\n5️⃣ Vérification santé de l'agent:")
    health = await agent.health_check()
    print(f"🏥 État: {health['status']}")
    print(f"🔧 Composants: {health['components']}")
    
    print("\n🎉 Demo terminé avec succès!")


async def demo_memory_engine():
    """Demo du moteur de mémoire en isolation"""
    print("\n🧠 === DEMO MOTEUR MÉMOIRE ===\n")
    
    # Création moteur mémoire
    memory_engine = ZepPersonalMemoryEngine(
        user_id="julien",
        zep_client=MockZepClient(),
        config={
            "auto_summarize": True,
            "enable_clustering": True,
            "max_working_memory": 5
        }
    )
    
    await memory_engine.initialize()
    print("✅ Moteur mémoire initialisé\n")
    
    # Test des différents types de mémoire
    memories = [
        ("J'ai rencontré Sarah lors du meetup Python", MemoryType.EPISODIC, MemoryImportance.HIGH),
        ("React est un framework JavaScript", MemoryType.SEMANTIC, MemoryImportance.MEDIUM),
        ("Je préfère VS Code à Vim", MemoryType.PREFERENCE, MemoryImportance.MEDIUM),
        ("Pour déployer: git push origin main", MemoryType.PROCEDURAL, MemoryImportance.HIGH),
        ("L'utilisateur pose souvent des questions sur l'architecture", MemoryType.BEHAVIORAL, MemoryImportance.LOW)
    ]
    
    print("1️⃣ Ajout de différents types de mémoire:")
    for content, mem_type, importance in memories:
        memory = await memory_engine.add_memory(content, memory_type=mem_type, importance=importance)
        print(f"💾 {mem_type.value}: {content[:40]}... [ID: {memory.memory_id[:8]}]")
    
    # Recherche dans la mémoire
    print("\n2️⃣ Recherche dans la mémoire:")
    search_queries = ["Python", "Sarah", "préférences", "déployer"]
    
    for query in search_queries:
        results = await memory_engine.search_memories(query, limit=2)
        print(f"🔍 '{query}' → {len(results)} résultat(s)")
        for result in results:
            print(f"   📄 {result.content[:50]}...")
    
    # Export des mémoires
    print("\n3️⃣ Export des mémoires:")
    json_export = await memory_engine.export_memories(format="json")
    print(f"📊 Export JSON: {len(json_export)} caractères")
    
    # Statistiques
    stats = memory_engine.get_stats()
    print(f"\n4️⃣ Statistiques mémoire:")
    print(f"📈 Mémoires créées: {stats['memories_created']}")
    print(f"🧠 Cache size: {stats['cache_size']}")
    print(f"🔗 Clusters: {stats['clusters']}")


async def interactive_test():
    """Test interactif avec l'utilisateur"""
    print("\n💬 === TEST INTERACTIF ===")
    print("Tapez vos messages pour l'agent (ou 'quit' pour sortir)")
    
    agent = BasePersonalAgent(
        user_id="user_test",
        zep_client=MockZepClient(),
        enable_a2a=False,
        enable_mcp=False,
        enable_graphiti=False
    )
    await agent.initialize()
    
    while True:
        user_input = input("\n👤 Vous: ").strip()
        if user_input.lower() in ['quit', 'exit', 'stop']:
            break
            
        if user_input:
            response = await agent.process_message(user_input)
            print(f"🤖 Agent: {response.content}")
            
            # Possibilité de feedback
            feedback = input("👍/👎 (feedback optionnel): ").strip()
            if feedback:
                await agent.learn_from_interaction(
                    AgentMessage(content=user_input, source="user"), 
                    response, 
                    feedback
                )
    
    print("👋 Session terminée!")


async def main():
    """Point d'entrée principal"""
    print("🚀 Tests de l'Agent Personnel - Milestone 1.2\n")
    
    print("Choisissez un test:")
    print("1 - Demo conversations automatiques")
    print("2 - Demo moteur mémoire") 
    print("3 - Test interactif")
    print("4 - Tous les tests")
    
    choice = input("\nVotre choix (1-4): ").strip()
    
    if choice == "1":
        await demo_agent_conversations()
    elif choice == "2":
        await demo_memory_engine()
    elif choice == "3":
        await interactive_test()
    elif choice == "4":
        await demo_agent_conversations()
        await demo_memory_engine()
        await interactive_test()
    else:
        print("❌ Choix invalide")
        return
    
    print("\n✨ Tests terminés!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Arrêt demandé par l'utilisateur")
    except Exception as e:
        print(f"❌ Erreur: {str(e)}")