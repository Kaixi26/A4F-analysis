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
    self.world_func_map = None


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

def load_dataset(filename, cmd_i_to_label, oracle):
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
  
  dataset.world_code += "\n/* EMPTY PREDICATES */"

  for i in range(0, 20):
    dataset.world_code += "\n" + "pred id_" + cmd_i_to_label(i) + " {}"

  dataset.world_code += "\n/* STUDENT PREDICATES */"

  for id in dataset.by_id:
    if "code_stripped" in dataset.by_id[id]:
      dataset.world_code += "\n" + dataset.by_id[id]["code_stripped"]
  
  dataset.world_code += "\n/* ORACLE SOLUTIONS */\n" + oracle

  dataset.world = alloy.parse(dataset.world_code)
  dataset.world_func_map = alloy.calculate_world_func_map(dataset.world)

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

def calculate_semantic_graph(dataset, cmd_i, dependency_labels):
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
        if alloy.semantic_equals(self.dataset.world, self.dataset.world_func_map, self.id_to_label(node["ids"][0]), self.id_to_label(id), dependency_labels):
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
      try:
        assert execution["cmd_i"] == cmd_i and "code_stripped" in execution

        g.add_node(execution["_id"])
        g.add_edge(prev, execution["_id"])
      except AssertionError:
        print("assertion failed for id " + execution["_id"], file=sys.stderr)
      except:
        print("failed for id " + execution["_id"], file=sys.stderr)

      prev = execution["_id"]

  return g
    

#for filename in ["trash.json"]: #["bNCCf9FMRZoxqobfX.json", "dkZH6HJNQNLLDX6Aj.json", "PSqwzYAfW9dFAa9im.json", "QxGnrFQnXPGh2Lh8C.json"]:
def main():
  oracle_trash = ""
  oracle_bNCCf9FMRZoxqobfX = "pred inv1o {\n\tWorker = Human + Robot\n}\npred inv2o {\n\tworkers in Workstation one -> some Worker\n}\npred inv3o {\n\tall c : Component | one c.workstation\n}\npred inv4o {\n\tall c : Component | some c.parts\n\tall m : Material | no m.parts\n\n}\npred inv5o {\n\tall c : Workstation | no (c.workers & Human) or no (c.workers & Robot)\n}\npred inv6o {\n\tno c : Component | c in c.^parts\n}\npred inv7o {\n\tall c : Component | some c.parts & Dangerous implies c in Dangerous\n}\npred inv8o {\n\tall c : Component & Dangerous | no c.workstation.workers & Human\n}\npred inv9o {\n\tall w : Workstation - end | one w.succ\n\tno end.succ\n\tWorkstation in begin.*succ\n}\npred inv10o {\n\tall c : Component, p : c.parts | p.workstation in ^succ.(c.workstation)\n}\n"
  oracle_dkZH6HJNQNLLDX6Aj = "pred inv1o {\n\tall p : Photo | one posts.p\n}\npred inv2o {\n\tall p : User | p not in p.follows\n}\npred inv3o {\n\tall p : User | p.sees - Ad in p.follows.posts\n}\npred inv4o {\n\t\tall u : posts.Ad | u.posts in Ad\n}\npred inv5o {\n\tall i : Influencer | follows.i = User - i\n}\npred inv6o {\n\tall i : Influencer, d : Day | some i.posts & date.d\n}\npred inv7o {\n\tall u : User | u.suggested = u.follows.follows - u.follows - u\n}\npred inv8o {\n\tall u : User, p : u.sees & Ad | p in u.(follows+suggested).posts\n}\n"
  oracle_PSqwzYAfW9dFAa9im = "pred inv1o {\n\tenrolled in Student -> Course\n}\npred inv2o {\n\tteaches in Professor -> Course\n}\npred inv3o {\n\tteaches in Person some -> Course\n}\npred inv4o {\n\tall p : Project | one (Course <: projects).p\n}\npred inv5o {\n\tall p : Project | some (Person <: projects).p\n\tall p : Project | (Person <: projects).p in Student\n}\npred inv6o {\n\tall p : Person | p.projects in p.enrolled.projects\n}\npred inv7o {\n\tall p : Person, c : Course | lone p.projects & c.projects\n}\npred inv8o {\n\t(all p : Person | no p.teaches & p.enrolled)\n}\npred inv9o {\n\tall p : Person | no (p.teaches.~teaches - p) & p.teaches.~enrolled\n}\npred inv10o {\n\tCourse.grades.Grade in Student\n}\npred inv11o {\n\tall c : Course | c.grades.Grade in enrolled.c\n}\npred inv12o {\n\tall p : Person, c : Course | lone p.(c.grades)\n}\npred inv13o {\n\tall c : Course, p : Person | last in p.(c.grades) implies some p.projects & c.projects\n}\npred inv14o {\n\tall p : Person, disj x,y : p.projects | no ((Person <: projects).x & projects.y) - p\n}\npred inv15o {\n\tall c : Course, p : c.projects, disj x,y : (Person <: projects).p | some c.grades[x] and some c.grades[y] implies c.grades[x] in c.grades[y].(prev+iden+next)\n}\n"
  oracle_QxGnrFQnXPGh2Lh8C = "pred inv1o {\n\tsome Entry\n\tsome Exit\n}\npred inv2o {\n\tall s : Signal | one signals.s\n}\npred inv3o {\n\tall t : Track | t in Exit iff no t.succs\n}\npred inv4o {\n\tall t : Track | t in Entry iff no succs.t\n}\npred inv5o {\n\tall t : Track | t not in Junction iff lone succs.t\n}\npred inv6o {\n\tall t : Entry | some t.signals & Speed\n}\npred inv7o {\n\tno t : Track | t in t.^succs\n}\npred inv8o {\n\tall e : Entry, x : Exit | x in e.*succs\n}\npred inv9o {\n\tall t : Track | no t.succs & Junction implies no t.signals & Semaphore\n}\npred inv10o {\n\tall j : Junction, t : succs.j | some t.signals & Semaphore\n}\n"
  class Input():
    def __init__(self, filename, range_, label_from_cmd_i, oracle="", oracle_deps_from_cmd_i=lambda x: [], outfile=None):
      self.filename = filename
      self.range = range_
      self.label_from_cmd_i = label_from_cmd_i
      self.oracle = oracle
      self.oracle_deps_from_cmd_i = oracle_deps_from_cmd_i
      if outfile != None:
        self.outfile = outfile
      else:
        self.outfile = "/tmp/" + self.filename

  default_prop_fun = lambda cmd_i: "prop" + str(cmd_i+1)
  default_inv_fun = lambda cmd_i: "inv" + str(cmd_i+1)
  default_inv_oracle_deps_fun = lambda cmd_i: list(map(lambda i: "inv" + str(i+1) + "o", list(range(cmd_i))))

  input_trash             = Input("trash.json", range(1,5), default_prop_fun, oracle_trash, lambda x: [])
  input_bNCCf9FMRZoxqobfX = Input("bNCCf9FMRZoxqobfX.json", range(0,10), default_inv_fun, oracle_bNCCf9FMRZoxqobfX, default_inv_oracle_deps_fun, "/tmp/bNCCf9FMRZoxqobfX_full.json")
  input_dkZH6HJNQNLLDX6Aj = Input("dkZH6HJNQNLLDX6Aj.json", range(0, 8), default_inv_fun, oracle_dkZH6HJNQNLLDX6Aj, default_inv_oracle_deps_fun, "/tmp/dkZH6HJNQNLLDX6Aj_full.json")
  input_PSqwzYAfW9dFAa9im = Input("PSqwzYAfW9dFAa9im.json", range(0,15), default_inv_fun, oracle_PSqwzYAfW9dFAa9im, default_inv_oracle_deps_fun, "/tmp/PSqwzYAfW9dFAa9im_full.json")
  input_QxGnrFQnXPGh2Lh8C = Input("QxGnrFQnXPGh2Lh8C.json", range(0,10), default_inv_fun, oracle_QxGnrFQnXPGh2Lh8C, default_inv_oracle_deps_fun, "/tmp/QxGnrFQnXPGh2Lh8C_full.json")

  inputs = [
    #input_trash,
    #input_bNCCf9FMRZoxqobfX,
    #input_dkZH6HJNQNLLDX6Aj,
    #input_PSqwzYAfW9dFAa9im,
    input_QxGnrFQnXPGh2Lh8C,
  ]

  for input in inputs:
    print("Loading " + input.filename, file=sys.stderr)
    print("Saving in " + input.outfile, file=sys.stderr)
    dataset = load_dataset("datasets/" + input.filename, input.label_from_cmd_i, input.oracle)
    obj = {}

    obj["execution_info"] = {}
    for id in dataset.by_id:
      if "code_stripped" in dataset.by_id[id]:
        obj["execution_info"][id] = { 
          "code_stripped" : dataset.by_id[id]["code_stripped"],
          "sat": dataset.by_id[id]["sat"]
          }

    obj["cmds"] = {}
    for cmd_i in input.range:
      print("calculating for cmd " + str(cmd_i), file=sys.stderr)
      #try:
      g = calculate_semantic_graph(dataset, cmd_i, input.oracle_deps_from_cmd_i(cmd_i))
      obj["cmds"][input.label_from_cmd_i(cmd_i)] = { "nodes": g.nodes, "edges": g.edges }
      #except:
      #  print("failed for cmd " + str(cmd_i), file=sys.stderr)

      with open(input.outfile, "w") as fp:
        fp.write(json.dumps(obj))

main()


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
