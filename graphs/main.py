#!/usr/bin/env python3
import json
import re
import alloy
import ast
import d3
import sys
from apted import APTED, Config

class ExecutionTrace:
  def __init__(self):
    self.full = []
    self.subtraces = []
    self.subtraces_by_cmd = {}


class Dataset:
  def __init__(self):
    self.by_id = {}
    self.by_derivation = {}
    self.execution_traces = {}
    self.cmd_i_to_label = None
    self.world_code = ""
    self.world = None


def validate_dataset(dataset):
  total = len(list(filter(lambda e: "cmd_i" in e, dataset.by_id.values())))
  total_by_traces = 0
  total_by_subtraces = 0
  total_by_subtraces_cmd = 0
  for execution_trace_key in dataset.execution_traces:
    execution_trace = dataset.execution_traces[execution_trace_key]
    total_by_traces += len(execution_trace.full)
    for subtrace in execution_trace.subtraces:
      total_by_subtraces += len(subtrace)
    for subtrace in execution_trace.subtraces_by_cmd.values():
      total_by_subtraces_cmd += len(subtrace)
  #print(total)
  #print(total_by_traces)
  #print(total_by_subtraces)
  #print(total_by_subtraces_cmd)
  assert total > total_by_traces and total_by_traces == total_by_subtraces == total_by_subtraces_cmd

def build_execution_trace(dataset, initial_id):
  execution_trace = ExecutionTrace()
  execution_trace.full.append(dataset.by_id[initial_id])
  dataset.execution_traces[initial_id] = execution_trace

  curr_execution_id = initial_id
  next_execution = dataset.by_derivation.get(curr_execution_id)
  while next_execution != None:
    execution_trace.full.append(next_execution)
    curr_execution_id = next_execution["_id"]
    next_execution = dataset.by_derivation.get(curr_execution_id, None)

  execution_trace.full = list(
      filter(lambda e: "cmd_i" in e, execution_trace.full))
  if len(execution_trace.full) == 0:
    del dataset.execution_traces[initial_id]
    return

  execution_trace.subtraces = [[execution_trace.full[0]]]
  for i in range(1, len(execution_trace.full)):
    if execution_trace.full[i]["cmd_i"] == execution_trace.full[i-1]["cmd_i"]:
      execution_trace.subtraces[-1].append(execution_trace.full[i])
    else:
      execution_trace.subtraces.append([execution_trace.full[i]])

  for execution in execution_trace.full:
      subtrace = execution_trace.subtraces_by_cmd.get(execution["cmd_i"], [])
      subtrace.append(execution)
      execution_trace.subtraces_by_cmd[execution["cmd_i"]] = subtrace


def build_execution_traces(dataset):
  for execution_id in dataset.by_id:
    if dataset.by_id[execution_id]["derivationOf"] == dataset.by_id[execution_id]["original"]:
      build_execution_trace(dataset, execution_id)

def load_dataset(filename, cmd_i_to_label):
  loaded_n = 0
  stripped_n = 0
  dataset = Dataset()
  dataset.cmd_i_to_label = cmd_i_to_label

  with open(filename, "r") as dataset_file:
    for line in dataset_file:
      line_json = json.loads(line)
      if "code" in line_json:
        line_json["code"] = alloy.strip_comments(line_json["code"])
        try:
          # some have the comments bugged (see _id: 'F4P7B9ALZD2fD492k')
          if line_json["sat"] != -1:
            line_json["code_stripped"] = alloy.extract_pred(line_json["code"], cmd_i_to_label(line_json["cmd_i"]), "id" + line_json["_id"] + "_")
            stripped_n += 1
        except:
          pass

      dataset.by_id[line_json["_id"]] = line_json
      if "derivationOf" in line_json:
        dataset.by_derivation[line_json["derivationOf"]] = line_json

      loaded_n += 1
      if loaded_n % 500 == 0:
        print("Loaded " + str(loaded_n) + " lines.", file=sys.stderr)
  
  print("Dataset loaded, " + str(loaded_n) + " lines, " + str(stripped_n) + " valid command and stripped lines.", file=sys.stderr)

  build_execution_traces(dataset)

  # build the full model
  for id in dataset.by_id:
    if dataset.by_id[id].get("sat", None) == 0:
      dataset.world_code += alloy.remove_funcs(dataset.by_id[id]["code"])
      break
  
  for i in range(0, 20):
    dataset.world_code += "\n" + "pred id_" + cmd_i_to_label(i) + " {}"

  for id in dataset.by_id:
    if "code_stripped" in dataset.by_id[id]:
      dataset.world_code += "\n" + dataset.by_id[id]["code_stripped"]

  #print(dataset.world_code)
  dataset.world = alloy.parse(dataset.world_code)

  print("Everything parsed. :)", file=sys.stderr)

  return dataset



def prop_name_from_cmdi(cmd_i):
  return "inv" + str(cmd_i+1)

def calculate_sat_ast(dataset, cmd_i):
  prop_name = prop_name_from_cmdi(cmd_i)

  ret = {}
  for execution_key in dataset.execution_traces.keys():
    if cmd_i not in dataset.execution_traces[execution_key].subtraces_by_cmd:
      continue
    
    for execution in dataset.execution_traces[execution_key].subtraces_by_cmd[cmd_i]:
      assert execution["cmd_i"] == cmd_i
      if execution["sat"] != 0:
        continue

      source = alloy.keep_pred(execution["code"], prop_name, alloy.pred_list())
      ast = alloy.pred_ast_from_source(source)
      ret[ast.toApted()] = { "source": source, "ast": ast }

  return ret

def calculate_closest_sat_ast(ast, sat_asts):
  min_dist = None
  min_ast = None
  for sat_ast in sat_asts:
    sat_ast = sat_asts[sat_ast]["ast"]
    dist = APTED(ast, sat_ast, Config()).compute_edit_distance()
    if min_dist == None or dist < min_dist:
      min_dist = dist
      min_ast = sat_ast

  return { "dist": min_dist, "ast": min_ast.toApted() }


def calculate_graphs(dataset):
  graphs = {}
  for cmd_i in range(0,20):
    print("calculating cmd_i " + str(cmd_i), file=sys.stderr)
    graph = d3.D3()
    codes = {"{true}": "initial state"}
    sat_asts = {} #calculate_sat_ast(dataset, cmd_i)
    ast_dists = {}

    for execution_key in dataset.execution_traces.keys():
      if cmd_i not in dataset.execution_traces[execution_key].subtraces_by_cmd:
        continue

      prev = "{true}"
      graph.add_visit(prev)
      graph.add_group(prev, 1)
      prop_name = prop_name_from_cmdi(cmd_i)

      for execution in dataset.execution_traces[execution_key].subtraces_by_cmd[cmd_i]:
        if execution["sat"] == -1:
          continue
        assert execution["cmd_i"] == cmd_i

        try:
          source = alloy.keep_pred(execution["code"], prop_name, alloy.pred_list())
          ast = alloy.pred_ast_from_source(source)
        except:
            continue

        curr = ast.toApted()
        #ast_dists[curr] = calculate_closest_sat_ast(ast, sat_asts)

        codes[curr] = source
        graph.add_link(prev, curr)
        graph.add_group(curr, execution["sat"])
        graph.add_visit(curr)

        prev = curr

        if execution["sat"] == 0:
          break

    graph_dict = graph.to_dict()
    graph_dict["codes"] = codes
    #graph_dict["sat_asts"] = list(map(lambda x: x.toApted(), sat_asts))
    graph_dict["dists"] = ast_dists
    graphs[prop_name] = graph_dict

  return graphs

def calculate_semantic_graph(dataset, cmd_i):
  class Graph():
    def __init__(self, dataset, id_to_label):
      self.nodes = []
      self.edges = {}
      self.id_to_label = id_to_label
      self.dataset = dataset
    
    def find_node(self, id):
      for i in range(len(self.nodes)):
        for id_ in self.nodes[i]["ids"]:
          if id == id_:
            return i

    def add_node(self, id):
      for node in self.nodes:
        if alloy.semantic_equals(self.dataset.world, self.id_to_label(node["ids"][0]), self.id_to_label(id)):
          node["ids"].append(id)
          return
      self.nodes.append({"ids": [id]})
    
    def add_edge(self, id_from, id_to):
      from_ = self.find_node(id_from)
      to_ = self.find_node(id_to)
      edge_from = self.edges.get(from_, {})
      edge_to = edge_from.get(to_, { "ids": [] })
      edge_to["ids"].append({ "from": id_from, "to": id_to })
      edge_from[to_] = edge_to
      self.edges[from_] = edge_from
    
    

  base = dataset.cmd_i_to_label(cmd_i)
  g = Graph(dataset, lambda id: "id" + id + "_" + base)

  for execution_key in dataset.execution_traces.keys():
    if cmd_i not in dataset.execution_traces[execution_key].subtraces_by_cmd:
      continue
    
    prev = ""
    g.add_node("")

    for execution in dataset.execution_traces[execution_key].subtraces_by_cmd[cmd_i]:
      if execution["sat"] == -1:
        continue
      assert execution["cmd_i"] == cmd_i and "code_stripped" in execution

      g.add_node(execution["_id"])
      g.add_edge(prev, execution["_id"])

      prev = execution["_id"]

  return g
    

for f in ["trash.json"]:
  label_from_cmd_i = lambda cmd_i: "prop" + str(cmd_i+1)
  dataset = load_dataset("datasets/" + f, label_from_cmd_i)
  obj = {}
  for cmd_i in range(1):
    print("calculating for cmd " + str(cmd_i), file=sys.stderr)
    g = calculate_semantic_graph(dataset, cmd_i)
    obj[label_from_cmd_i(cmd_i)] = { "nodes": g.nodes, "edges": g.edges }

  obj["execution_info"] = {}
  for id in dataset.by_id:
    if "code_stripped" in dataset.by_id[id]:
      obj["execution_info"][id] = { "code_stripped" : dataset.by_id[id]["code_stripped"] }

  print(json.dumps(obj))


#calculate_graphs(dataset)
#dataset = load_dataset("datasets/bNCCf9FMRZoxqobfX.json")
#validate_dataset(dataset)

#total = 0
#solved = 0
#for execution_trace_id in dataset.execution_traces:
#  execution_trace = dataset.execution_traces[execution_trace_id]
#  for cmd_i in execution_trace.subtraces_by_cmd:
#    total += 1
#    for execution in execution_trace.subtraces_by_cmd[cmd_i]:
#      if execution["sat"] == 0:
#        solved += 1
#        break
#    pass
#
#print("total: " + str(total))
#print("solved: " + str(solved))
#print("solved/total: " + str(solved/total))

#for i in range(20):
#  total = 0
#  solved = 0
#  for execution_trace_id in dataset.execution_traces:
#    if i in dataset.execution_traces[execution_trace_id].subtraces_by_cmd:
#      total += 1
#      for execution in dataset.execution_traces[execution_trace_id].subtraces_by_cmd[i]:
#        if execution["sat"] == 0:
#          solved += 1
#          break
#  print("prop" + str(i+1), end="\t")
#  print("total: " + str(total), end="\t")
#  print("solved: " + str(solved), end="\t")
#  print("diff: " + str(solved/total))
#  print("solved/total: " + str(solved/total))
