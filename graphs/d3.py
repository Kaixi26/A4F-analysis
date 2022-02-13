import json

class D3:

  def __init__(self):
    self.next_i = 0
    self.nodes = {}
    self.links = {}
    self.groups = {}
    self.visits = {}

  def add_visit(self, node_name):
    self.visits[node_name] = self.visits.get(node_name, 0) + 1

  def add_group(self, node_name, group):
    self.groups[node_name] = group

  def add_node(self, node):
    if node not in self.nodes:
      self.nodes[node] = {"id": self.next_i, "name": node}
      self.next_i += 1

  def add_link(self, source, target):
    self.add_node(source)
    self.add_node(target)
    source_link = self.links.get(source, {})
    source_link[target] = source_link.get(target, 0) + 1
    self.links[source] = source_link

    #self.links.append({"source": self.nodes[source]["id"], "target": self.nodes[target]["id"]})
  
  def to_dict(self):
    edges = []
    for source in self.links:
      for target in self.links[source]:
        edges.append({
          "source":self.nodes[source]["id"],
          "target":self.nodes[target]["id"],
          "value":self.links[source][target]
        })
    nodes = []
    for node in self.nodes.values():
      nodes.append({
        "name": node["name"],
        "grp": self.groups[node["name"]],
        "n": self.visits.get(node["name"], 0),
        "id": node["id"]
      })
    return { "nodes": nodes, "edges": edges }
