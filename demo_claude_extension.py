#!/usr/bin/env python3
"""
Demo Claude Code Extension - Test des commandes slash personnalisées

Montre l'utilisation de l'extension Claude Code avec toutes les commandes slash
implémentées pour l'agent personnel.
"""

import asyncio
import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'packages/core'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'packages/integrations'))

from personal_agent_core.agents.base_agent import BasePersonalAgent
from personal_agent_core.memory.zep_engine import ZepPersonalMemoryEngine, MemoryType
from personal_agent_integrations.notion.notion_zep_bridge import create_notion_zep_bridge
from personal_agent_integrations.claude_code.extension import create_claude_extension


async def demo_extension_setup():
    """Demo setup de l'extension Claude Code"""
    print("🔧 === SETUP CLAUDE CODE EXTENSION ===\n")
    
    # 1. Création des composants
    print("1️⃣ Initialisation des composants...")
    
    # Agent personnel
    agent = BasePersonalAgent(
        user_id="claude_demo_user",
        agent_name="ClaudeDemoAgent",
        zep_client=None,  # Mode local
        enable_a2a=False,
        enable_mcp=False,
        enable_graphiti=False,
        config={"enable_learning": True}
    )
    await agent.initialize()
    print("✅ BasePersonalAgent initialisé")
    
    # Memory engine
    memory_engine = ZepPersonalMemoryEngine(
        user_id="claude_demo_user",
        zep_client=None,
        config={"enable_clustering": True, "auto_summarize": True}
    )
    await memory_engine.initialize()
    print("✅ ZepPersonalMemoryEngine initialisé")
    
    # Notion bridge (mock mode)
    notion_bridge = await create_notion_zep_bridge(
        user_id="claude_demo_user",
        notion_token="demo_token",
        zep_memory_engine=memory_engine,
        config={"use_mcp": False, "enable_auto_sync": False}
    )
    print("✅ NotionZepBridge initialisé")
    
    # 2. Extension Claude Code
    print("\n2️⃣ Création de l'extension Claude Code...")
    
    extension = await create_claude_extension(
        agent=agent,
        memory_engine=memory_engine,
        notion_bridge=notion_bridge,
        config={
            "enable_history": True,
            "max_history": 50,
            "auto_sync": True,
            "memory_cache_size": 1000,
            "enable_a2a": False
        }
    )
    
    print(f"✅ Extension Claude Code créée avec {len(set(extension.commands.keys()))} commandes uniques")
    
    # 3. Vérification configuration
    print("\n3️⃣ Vérification de la configuration...")
    
    config_file = ".claude/agent-config.json"
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            config = json.load(f)
        print(f"✅ Configuration sauvée: {len(config['commands'])} commandes configurées")
        print(f"   • Intégrations: Zep={config['integrations']['zep_memory']['enabled']}, "
              f"Notion={config['integrations']['notion_sync']['enabled']}")
    else:
        print("❌ Fichier de configuration non créé")
    
    return extension, agent, memory_engine, notion_bridge


async def demo_commands_execution(extension):
    """Demo d'exécution des commandes slash"""
    print("\n🎯 === DEMO COMMANDES SLASH ===\n")
    
    # Ajout de données test pour les demos
    print("📝 Préparation des données test...")
    
    # Ajout mémoires test
    await extension.memory_engine.add_memory(
        "Je suis développeur Python spécialisé en IA",
        memory_type=MemoryType.SEMANTIC
    )
    await extension.memory_engine.add_memory(
        "J'aime travailler sur des projets d'agents intelligents",
        memory_type=MemoryType.PREFERENCE
    )
    await extension.memory_engine.add_memory(
        "Réunion équipe projet agent personnel prévue vendredi",
        memory_type=MemoryType.EPISODIC
    )
    
    # Sync Notion mock
    await extension.notion_bridge.sync_notion_to_zep(force_full_sync=True)
    
    print("✅ Données test créées\n")
    
    # Test des commandes
    commands_to_test = [
        # MEMORY
        "/memory-stats --detailed",
        "/memory python --limit=3",
        "/memory-add \"J'utilise VS Code comme IDE\" --type=preference",
        
        # NOTION
        "/notion-sync --full",
        "/notion search projet",
        "/notion stats",
        
        # AGENTS
        "/agent-status --detailed",
        "/agents list",
        
        # CONTEXT
        "/context analyze python",
        "/context graph",
        
        # SYSTEM
        "/pkg status",
        "/evolve status"
    ]
    
    print("🚀 Exécution des commandes test:\n")
    
    results = []
    for cmd in commands_to_test:
        print(f"🔸 Commande: {cmd}")
        
        try:
            result = await extension.execute_command(cmd)
            
            # Affichage résultat
            status_emoji = "✅" if result["status"] == "success" else "⚠️" if result["status"] == "info" else "❌"
            print(f"   {status_emoji} Status: {result['status']}")
            print(f"   📄 Message: {result['message']}")
            
            if result["status"] == "success" and "execution_time" in result:
                print(f"   ⚡ Temps: {result['execution_time']:.3f}s")
            
            # Détails spécifiques selon le type de commande
            if "/memory" in cmd and result["status"] == "success":
                if "memories" in result:
                    print(f"   🧠 Mémoires trouvées: {result['results_count']}")
                elif "stats" in result:
                    stats = result["stats"]
                    print(f"   📊 Stats: {stats.get('total_memories', 0)} mémoires, {stats.get('total_clusters', 0)} clusters")
            
            elif "/notion" in cmd and result["status"] == "success":
                if "pages_processed" in result:
                    print(f"   📄 Pages: {result['pages_processed']}, Mémoires: {result['memories_created']}")
                elif "pages" in result:
                    print(f"   📄 Pages trouvées: {result['results_count']}")
            
            elif "/agent" in cmd and result["status"] == "success":
                if "agent_status" in result:
                    print(f"   🤖 État: {result['agent_status']}")
                    if "stats" in result:
                        stats = result["stats"]
                        print(f"   📊 Messages: {stats.get('messages_processed', 0)}, Mémoires: {stats.get('memories_created', 0)}")
            
            results.append({"command": cmd, "result": result})
            
        except Exception as e:
            print(f"   ❌ Erreur: {str(e)}")
            results.append({"command": cmd, "error": str(e)})
        
        print()  # Ligne vide
    
    return results


async def demo_help_system(extension):
    """Demo du système d'aide"""
    print("📚 === SYSTÈME D'AIDE ===\n")
    
    # Aide générale
    print("📖 Aide générale:")
    help_result = extension.get_command_help()
    
    if help_result["status"] == "success":
        categories = help_result["categories"]
        print(f"✅ {help_result['total_commands']} commandes dans {len(categories)} catégories:\n")
        
        for category, commands in categories.items():
            print(f"🔹 {category.upper()}:")
            for cmd in commands[:3]:  # Limite à 3 par catégorie pour demo
                print(f"   /{cmd['name']} - {cmd['description']}")
            if len(commands) > 3:
                print(f"   ... et {len(commands)-3} autres commandes")
            print()
    
    # Aide spécifique
    print("📖 Aide spécifique pour /memory:")
    memory_help = extension.get_command_help("memory")
    
    if memory_help["status"] == "success":
        cmd_info = memory_help["command"]
        print(f"✅ /{cmd_info['name']} ({cmd_info['category']})")
        print(f"   📝 Description: {cmd_info['description']}")
        print(f"   💡 Usage: {cmd_info['usage']}")
        if cmd_info["examples"]:
            print("   📚 Exemples:")
            for example in cmd_info["examples"][:2]:
                print(f"      {example}")
        if cmd_info["aliases"]:
            print(f"   🔗 Alias: {', '.join(cmd_info['aliases'])}")


async def demo_interactive_mode(extension):
    """Demo mode interactif avec l'extension"""
    print("\n💬 === MODE INTERACTIF ===")
    print("💡 Tapez des commandes slash pour interagir avec l'agent")
    print("🛑 Tapez 'quit', 'exit' ou 'stop' pour sortir")
    print("❓ Tapez 'help' pour l'aide\n")
    
    command_count = 0
    
    while True:
        try:
            user_input = input("🔸 claude> ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'stop', 'q']:
                print("👋 Mode interactif terminé")
                break
            
            if user_input.lower() in ['help', 'h', '?']:
                help_result = extension.get_command_help()
                print(f"\n📚 {help_result['total_commands']} commandes disponibles:")
                for category, commands in help_result["categories"].items():
                    cmd_names = [f'/{cmd["name"]}' for cmd in commands]
                print(f"  🔹 {category}: {', '.join(cmd_names)}")
                print()
                continue
            
            if not user_input:
                continue
            
            # Assurer que la commande commence par /
            if not user_input.startswith('/'):
                user_input = '/' + user_input
            
            # Exécution
            result = await extension.execute_command(user_input)
            
            # Affichage résultat
            status_emoji = "✅" if result["status"] == "success" else "⚠️" if result["status"] == "info" else "❌"
            print(f"{status_emoji} {result['message']}")
            
            # Détails pour certaines commandes
            if result["status"] == "success":
                if "memories" in result:
                    for i, memory in enumerate(result["memories"][:3], 1):
                        print(f"  {i}. [{memory['type']}] {memory['content']}")
                elif "pages" in result:
                    for i, page in enumerate(result["pages"][:3], 1):
                        print(f"  {i}. [{page['type']}] {page['title']}: {page['content_preview']}")
                elif "agents" in result:
                    for i, agent in enumerate(result["agents"], 1):
                        print(f"  {i}. {agent['name']} ({agent['type']}) - {agent['status']}")
            
            command_count += 1
            
            if result["status"] == "error":
                print("💡 Tapez 'help' pour voir les commandes disponibles")
            
            print()
            
        except KeyboardInterrupt:
            print("\n👋 Interruption clavier - au revoir !")
            break
        except Exception as e:
            print(f"❌ Erreur: {str(e)}\n")
    
    print(f"📊 Session terminée: {command_count} commandes exécutées")


async def demo_configuration_details():
    """Affiche les détails de configuration Claude Code"""
    print("\n⚙️ === DÉTAILS CONFIGURATION ===\n")
    
    config_file = ".claude/agent-config.json"
    
    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        print("📄 Configuration Claude Code générée:")
        print(f"   📋 Nom: {config['name']}")
        print(f"   📝 Version: {config['version']}")
        print(f"   📄 Description: {config['description']}")
        print(f"   🔧 Commandes: {len(config['commands'])}")
        
        print("\n🔹 Intégrations configurées:")
        for integration, details in config['integrations'].items():
            status = "✅ Activée" if details['enabled'] else "❌ Désactivée"
            print(f"   • {integration}: {status}")
        
        print("\n🔹 Paramètres:")
        for setting, value in config['settings'].items():
            print(f"   • {setting}: {value}")
        
        print(f"\n💾 Fichier: {config_file}")
        print(f"📊 Taille: {os.path.getsize(config_file)} bytes")
        
    else:
        print("❌ Fichier de configuration non trouvé")


async def main():
    """Demo principal de l'extension Claude Code"""
    print("🚀 DEMO CLAUDE CODE EXTENSION - Milestone 1.4\n")
    
    print("🎯 Cette demo montre:")
    print("• Setup complet de l'extension Claude Code")  
    print("• Configuration automatique .claude/agent-config.json")
    print("• Commandes slash: /memory, /notion, /agents, /context, /pkg")
    print("• Intégration avec BaseAgent, ZepMemory, NotionBridge")
    print("• Mode interactif pour tests\n")
    
    try:
        # 1. Setup extension
        extension, agent, memory_engine, notion_bridge = await demo_extension_setup()
        
        # 2. Test commandes
        results = await demo_commands_execution(extension)
        
        # 3. Système d'aide
        await demo_help_system(extension)
        
        # 4. Configuration
        await demo_configuration_details()
        
        # 5. Mode interactif (optionnel)
        print("\n" + "="*50)
        interactive = input("🎮 Voulez-vous tester le mode interactif? (o/n): ").strip().lower()
        
        if interactive in ['o', 'oui', 'y', 'yes']:
            await demo_interactive_mode(extension)
        
        # 6. Résumé
        print("\n🎉 === RÉSUMÉ DEMO ===")
        
        successful_commands = sum(1 for r in results if r.get("result", {}).get("status") == "success")
        total_commands = len(results)
        
        print(f"✅ Extension Claude Code opérationnelle")
        print(f"🔧 Configuration: .claude/agent-config.json créé")
        print(f"🎯 Commandes testées: {successful_commands}/{total_commands} succès")
        print(f"🧠 Mémoires: {memory_engine.get_stats().get('total_memories', 0)} en cache")
        print(f"📄 Notion: {notion_bridge.get_sync_stats()['pages_synced']} pages synchronisées")
        print(f"📊 Agent: {(await agent.get_stats())['messages_processed']} messages traités")
        
        print("\n💡 L'extension est prête pour Claude Code !")
        print("   Utilisez les commandes slash dans votre workflow de développement")
        
    except Exception as e:
        print(f"❌ Erreur demo: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Demo interrompu")
    except Exception as e:
        print(f"\n❌ Erreur: {str(e)}")