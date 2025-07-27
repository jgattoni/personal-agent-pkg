# Agent Personnel avec PKG et Protocols Edge

## Vision
Je développe un agent personnel intelligent avec Notion, mobile/desktop, utilisant Zep Memory (state-of-the-art), protocoles A2A/ACP/MCP, et Claude Code comme interface principale.

## Stack technologique
- **Package**: UV (10-100x plus rapide que Poetry)
- **Memory**: Zep Cloud (+100% précision, -90% latence)  
- **Interface Desktop**: Claude Code + extensions personnalisées
- **Interface Mobile**: React Native + sync Zep
- **Knowledge Graph**: Zep + Neo4j + Qdrant
- **Protocols**: MCP (tools), ACP (local), A2A (remote)

## Architecture agents
```
# Local (ACP - performance max)
localhost:8080  # Agent principal Claude Code
localhost:8081  # Zep Memory service  
localhost:8082  # Notion Bridge
localhost:8083  # Mobile Edge sync

# Remote (A2A - intégrations)
api.notion.com/mcp
claude-code.anthropic.com/a2a
```

## Initialisation
```bash
uv init personal-agent-pkg && cd personal-agent-pkg
echo "3.12" > .python-version
uv add fastapi uvicorn neo4j qdrant-client ollama-python notion-client langchain zep-python
uv add --dev pytest black flake8 mypy
```

## Documentation de référence
- **[DEVELOPMENT_PLAN.md](./DEVELOPMENT_PLAN.md)** - Architecture technique complète et code examples
- **[TASKS.md](./TASKS.md)** - Statut phases, todos, et métriques de progression

## Configuration Claude Code
Commandes slash personnalisées : `/memory`, `/notion`, `/agents`, `/context`, `/pkg`
Configuration complète dans `.claude/agent-config.json`

## Composants core à implémenter
1. **BasePersonalAgent** avec Zep Memory integration
2. **ZepPersonalMemoryEngine** avec temporal evolution  
3. **NotionZepBridge** pour sync bidirectionnel
4. **ClaudeCodeExtension** avec commandes personnalisées
5. **AgentOrchestrator** pour communication ACP/A2A

## Phase actuelle
Voir **[TASKS.md](./TASKS.md)** pour le statut détaillé et prochaines actions.

## Métriques cibles
- Performance: < 200ms requêtes, 90% latence réduite
- Précision: > 90% extraction entités  
- UX: 50% temps recherche réduit, continuité cross-platform

---
**Instructions pour Claude Code**: Consulte DEVELOPMENT_PLAN.md pour l'architecture détaillée et TASKS.md pour les tâches courantes. Respecte l'architecture Zep + UV + protocoles A2A/ACP. Priorise performance, modularité, et tests.