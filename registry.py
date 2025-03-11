# global dictionary to store agent to search_id mappings
agent_registry = {}

def register_agent(agent, search_id):
    """Register an agent with a search_id"""
    agent_registry[id(agent)] = search_id

def get_search_id(agent):
    """Get the search_id for an agent"""
    return agent_registry.get(id(agent))