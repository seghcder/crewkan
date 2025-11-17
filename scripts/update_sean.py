#!/usr/bin/env python3
"""Update sean to be human agent."""
from crewkan.utils import load_yaml, save_yaml
from pathlib import Path

agents_path = Path('boards/crewkanteam/agents/agents.yaml')
agents = load_yaml(agents_path)
sean = next((a for a in agents['agents'] if a['id'] == 'sean'), None)
if sean:
    sean['kind'] = 'human'
    sean['name'] = 'Sean'
    save_yaml(agents_path, agents)
    print('Updated sean to human')




