#!/usr/bin/env python3
import json
import re
import alloy
import ast
import d3
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


def strip_comments(code):
  return re.sub(r'(/\*\*.+\*\*/)|(//.+?\n)', '', code, flags=re.DOTALL)


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


def load_dataset(filename):
  dataset = Dataset()
  with open(filename, "r") as dataset_file:
    for line in dataset_file:
      line_json = json.loads(line)
      if "code" in line_json:
        line_json["code"] = strip_comments(line_json["code"])

      dataset.by_id[line_json["_id"]] = line_json
      if "derivationOf" in line_json:
        dataset.by_derivation[line_json["derivationOf"]] = line_json
  build_execution_traces(dataset)
  return dataset


dataset = load_dataset("datasets/trash.json")

def calculate_sat_ast(dataset, cmd_i):
  prop_name = "prop" + str(cmd_i+1)

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
  for cmd_i in range(9,10):
    graph = d3.D3()
    codes = {"{true}": "initial state"}
    sat_asts = calculate_sat_ast(dataset, cmd_i)
    ast_dists = {}

    for execution_key in dataset.execution_traces.keys():
      if cmd_i not in dataset.execution_traces[execution_key].subtraces_by_cmd:
        continue

      prev = "{true}"
      graph.add_visit(prev)
      graph.add_group(prev, 1)
      prop_name = "prop" + str(cmd_i+1)

      for execution in dataset.execution_traces[execution_key].subtraces_by_cmd[cmd_i]:
        assert execution["cmd_i"] == cmd_i

        source = alloy.keep_pred(execution["code"], prop_name, alloy.pred_list())
        try:
          ast = alloy.pred_ast_from_source(source)
        except Exception as e:
          continue
        curr = ast.toApted()
        ast_dists[curr] = calculate_closest_sat_ast(ast, sat_asts)

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

#calculate_graphs(dataset)
print(re.escape(json.dumps(calculate_graphs(dataset))))

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