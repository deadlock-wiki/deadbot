from python_mermaid.diagram import MermaidDiagram, Node, Link


class ItemComponentTree:
    """Interface for creating a mermaid diagram for item component dependencies"""

    def __init__(self, localizations):
        self.localizations = localizations
        self.nodes = []
        self.links = []
        self.chart = MermaidDiagram(title='Items', nodes=self.nodes, links=self.links)

    def add_component(self, parent_name: str, components: dict):
        self._add_children_to_tree(parent_name, components)

    def get_chart(self):
        return self.chart

    def _add_children_to_tree(self, parent_key, child_keys):
        """Add items to mermaid tree"""
        for child_key in child_keys:
            self.links.append(Link(Node(self.localizations.get(child_key)), Node(parent_key)))
