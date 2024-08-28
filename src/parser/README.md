# Deadlock Wiki Parser
The parser decompiles the raw game files in order to extract game data for heroes, items, buildings etc.

## Currently Fetched Data
Takes raw source files and exports data to more usable json formats\

**Currently fetches the following**\
Hero\
✅ Base Stats\
❌ Ability Stats\
❌ Description

Items\
❌ Cost+Stats\
❌ Description

Neutral Enemies/Buildings\
❌ Stats\
❌ Descriptions

### Ability File
Prefixes for ability data
Hero abilities - 'citadel', 'ability', 'super', 'trooper', 'rutger', 'gunslinger', 'yakuza', 'thumper', 'signature', 'ultimate', 'hero', 'cadence', 'genericperson', 'mirage', 'slork', 'synth', 'tokamak', 'viscous', 'tech'

npc abilities + stats - 'npc', 'melee', 'targetdummy'

Items - 'upgrade'

Misc - 'tier1', 'tier2', 'tier3', 'tier4', 'armor',  'common', 'invis', 'inherent', 'held'
