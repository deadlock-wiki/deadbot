import keyvalues3 as kv3
import json

class Parser:
    def __init__(self):
        self.data = kv3.read('./decompiled-data/scripts/heroes.vdata')

    def run(self): 
        self.parse_heroes()

    def parse_heroes(self):
        hero_keys = self.data.keys()
        base_hero_stats = self.data['hero_base']['m_mapStartingStats']

        all_hero_stats = dict()

        for hero_key in hero_keys:
            if hero_key.startswith('hero') and hero_key != 'hero_base':
                merged_stats = dict()
                hero_stats = self.data[hero_key]['m_mapStartingStats']
                merged_stats.update(base_hero_stats)
                merged_stats.update(hero_stats)

                hero_name = hero_key.replace('hero_', '')
                all_hero_stats[hero_name] = merged_stats

        self.write('output/hero-data.json', all_hero_stats) 


    def write(self, path, data):
        with open(path, "w") as outfile:
            json.dump(data, outfile, indent=4)


if __name__ == "__main__":
    parser = Parser() 
    parser.run()  
