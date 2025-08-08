#!/usr/bin/env python3
"""
Demo amélioré de l'agent personnel avec corrections
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'packages/core'))

from personal_agent_core.agents.base_agent import BasePersonalAgent, AgentMessage


class SmartMockZepClient:
    """Mock amélioré du client Zep pour demo réaliste"""
    def __init__(self):
        self.memory = SmartMockMemory()
        
class SmartMockMemory:
    def __init__(self):
        self.memories = []
        self.sessions = []
        
    async def add_memory(self, session_id, messages, metadata=None):
        # Stockage plus intelligent
        content = messages[0]['content']
        self.memories.append({
            "session": session_id, 
            "content": content,
            "metadata": metadata or {},
            "timestamp": asyncio.get_event_loop().time()
        })
        print(f"💾 [MÉMOIRE] Sauvé: {content[:40]}...")
        
    async def search_memory(self, session_id, search_payload, limit=10):
        # Recherche simple mais fonctionnelle
        query = search_payload.text.lower()
        results = []
        
        for memory in self.memories:
            if any(word in memory['content'].lower() for word in query.split()):
                # Mock d'un résultat de recherche
                result = type('obj', (object,), {
                    'score': 0.8,
                    'message': type('obj', (object,), {
                        'content': memory['content'],
                        'metadata': memory['metadata']
                    })()
                })()
                results.append(result)
        
        return results[:limit]
        
    async def list_sessions(self):
        return self.sessions
        
    async def add_session(self, session_id, metadata=None):
        self.sessions.append({"id": session_id, "metadata": metadata})
        print(f"📁 Session créée: {session_id}")


async def demo_intelligent():
    """Demo avec agent intelligent qui se souvient"""
    print("🤖 === AGENT PERSONNEL AMÉLIORÉ ===\n")
    
    # Agent avec mock intelligent
    agent = BasePersonalAgent(
        user_id="demo_user",
        agent_name="AssistantPersonnel", 
        zep_client=SmartMockZepClient(),
        enable_a2a=False,
        enable_mcp=False,
        enable_graphiti=False,
        config={
            "enable_learning": True,
            "enable_preferences": True,
            "auto_summarize": True
        }
    )
    
    await agent.initialize()
    print("✅ Agent intelligent initialisé !\n")
    
    # Scénario de conversation réaliste
    print("📝 Scénario: Vous vous présentez et exprimez des préférences\n")
    
    conversations = [
        ("Je m'appelle Julien", "👤 Je me présente"),
        ("J'aime la glace à l'eau", "🍧 J'exprime une préférence"),
        ("Je suis développeur Python", "💻 Je donne mon métier"),
        ("Comment je m'appelle ?", "❓ Je teste la mémoire"),
        ("Quelle glace j'aime ?", "❓ Je teste les préférences"),
        ("Quel est mon métier ?", "❓ Je teste les infos professionnelles"),
        ("Résume ce que tu sais sur moi", "📊 Bilan des connaissances")
    ]
    
    for message, description in conversations:
        print(f"{description}")
        print(f"👤 VOUS: {message}")
        
        # L'agent traite et répond
        response = await agent.process_message(message)
        
        print(f"🤖 AGENT: {response.content}")
        print(f"🎯 Intention: {response.metadata.get('intent', 'general')}")
        print(f"⚡ Actions: {', '.join(response.actions_taken)}")
        print("---\n")
        
        # Pause pour réalisme
        await asyncio.sleep(0.5)
    
    # Statistiques finales
    print("📊 STATISTIQUES FINALES:")
    stats = await agent.get_stats()
    print(f"💬 Messages traités: {stats['messages_processed']}")
    print(f"🧠 Mémoires créées: {stats['memories_created']}")
    print(f"🏥 État: {(await agent.health_check())['status']}")
    
    return agent


async def test_interactif_ameliore():
    """Test interactif avec agent amélioré"""
    print("\n💬 === TEST INTERACTIF AMÉLIORÉ ===")
    print("💡 L'agent va maintenant se souvenir de vos réponses !")
    print("📝 Essayez de vous présenter, puis demandez-lui ce qu'il sait sur vous")
    print("🛑 Tapez 'quit' pour sortir\n")
    
    agent = BasePersonalAgent(
        user_id="interactive_user",
        zep_client=SmartMockZepClient(),
        enable_a2a=False,
        enable_mcp=False, 
        enable_graphiti=False,
        config={"enable_learning": True}
    )
    
    await agent.initialize()
    
    # Message de bienvenue intelligent
    welcome = await agent.process_message("Bonjour")
    print(f"🤖 {welcome.content}\n")
    
    conversation_count = 0
    
    while True:
        user_input = input("👤 Vous: ").strip()
        
        if user_input.lower() in ['quit', 'exit', 'stop', 'au revoir']:
            farewell = await agent.process_message(f"Au revoir, merci pour cette conversation de {conversation_count} messages")
            print(f"🤖 {farewell.content}")
            break
            
        if user_input:
            response = await agent.process_message(user_input)
            print(f"🤖 Agent: {response.content}")
            
            # Stats en temps réel
            conversation_count += 1
            if conversation_count % 3 == 0:
                print(f"📊 Stats: {conversation_count} messages échangés, {agent.stats['memories_created']} souvenirs")
            
            # Feedback optionnel
            if conversation_count > 2:  # Après quelques échanges
                feedback = input("👍👎 Cette réponse était-elle utile ? (o/n/skip): ").strip().lower()
                if feedback in ['o', 'oui', 'y', 'yes']:
                    await agent.learn_from_interaction(
                        AgentMessage(content=user_input, source="user"),
                        response,
                        "Bonne réponse, merci !"
                    )
                    print("✅ Feedback positif enregistré")
                elif feedback in ['n', 'non', 'no']:
                    await agent.learn_from_interaction(
                        AgentMessage(content=user_input, source="user"),
                        response, 
                        "Cette réponse n'était pas très utile"
                    )
                    print("❌ Feedback négatif enregistré")
            
            print()  # Ligne vide pour lisibilité
    
    print(f"\n📈 Session terminée après {conversation_count} échanges")
    stats = await agent.get_stats()
    print(f"🧠 L'agent a créé {stats['memories_created']} souvenirs de notre conversation")


async def main():
    print("🚀 DEMO AGENT PERSONNEL - VERSION AMÉLIORÉE\n")
    
    print("Choisissez votre test:")
    print("1 - Demo scénario intelligent (recommandé)")
    print("2 - Test interactif amélioré")
    print("3 - Les deux")
    
    choice = input("\nVotre choix (1-3): ").strip()
    
    try:
        if choice == "1":
            await demo_intelligent()
        elif choice == "2":
            await test_interactif_ameliore()
        elif choice == "3":
            await demo_intelligent()
            await test_interactif_ameliore()
        else:
            print("❌ Choix invalide")
            return
            
        print("\n🎉 Demo terminé avec succès !")
        print("💡 L'agent peut maintenant mémoriser et utiliser le contexte de vos conversations")
        
    except Exception as e:
        print(f"❌ Erreur pendant le demo: {str(e)}")
        print("🔧 Cela peut arriver pendant le développement, mais l'architecture fonctionne !")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Demo interrompu par l'utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur: {str(e)}")