#!/usr/bin/env python3
"""
Exemple simple d'utilisation de l'agent personnel
Montre les concepts clés sans complexité
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'packages/core'))

from personal_agent_core.agents.base_agent import create_personal_agent


async def exemple_simple():
    """Exemple ultra-simple d'usage"""
    
    print("🤖 Création d'un agent personnel simple...\n")
    
    # 1. Création de l'agent (sans Zep pour simplicité)
    agent = await create_personal_agent(
        user_id="demo_user",
        zep_client=None,  # Mode local seulement
        config={
            "enable_learning": True,
            "auto_summarize": False  # Plus simple
        }
    )
    
    print("✅ Agent créé !")
    
    # 2. Quelques interactions basiques
    messages_test = [
        "Bonjour ! Je suis développeur Python",
        "J'aime faire du code propre et des tests",
        "Peux-tu m'aider à organiser mes projets ?",
        "Quelles sont mes préférences que tu as notées ?",
    ]
    
    for message in messages_test:
        print(f"\n👤 USER: {message}")
        
        # L'agent traite le message
        response = await agent.process_message(message)
        
        print(f"🤖 AGENT: {response.content}")
        print(f"🎯 Intent détecté: {response.metadata.get('intent', 'N/A')}")
    
    # 3. Vérification que l'agent a bien mémorisé
    print(f"\n📊 L'agent a traité {agent.stats['messages_processed']} messages")
    print(f"💾 Et créé {agent.stats['memories_created']} mémoires")
    
    # 4. État de santé
    health = await agent.health_check()
    print(f"🏥 Santé de l'agent: {health['status']}")
    
    return agent


if __name__ == "__main__":
    asyncio.run(exemple_simple())