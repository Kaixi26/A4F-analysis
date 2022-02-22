import os
import re
import jpype
import jpype.imports
from jpype.types import *
from ast import AST

jpype.startJVM(classpath=['lib/org.alloytools.alloy.dist.jar'])

from edu.mit.csail.sdg.ast import Command
from edu.mit.csail.sdg.ast import ExprVar
from edu.mit.csail.sdg.ast import ExprList
from edu.mit.csail.sdg.ast import VisitQuery
from edu.mit.csail.sdg.alloy4 import A4Reporter
from edu.mit.csail.sdg.alloy4 import ConstList
from edu.mit.csail.sdg.parser import CompUtil
from edu.mit.csail.sdg.parser import CompModule
from edu.mit.csail.sdg.translator import A4Options
from edu.mit.csail.sdg.translator import A4Solution
from edu.mit.csail.sdg.translator import TranslateAlloyToKodkod


source0 = "var sig File {\n\tvar link : lone File\n}\nvar sig Trash in File {}\nvar sig Protected in File {}\n\npred prop1 {\n\tno Trash\n  \tno Protected\n}\n\npred prop2 { no Protected }\n"
#source1 = "var sig File {\n\tvar link : lone File\n}\nvar sig Trash in File {}\nvar sig Protected in File {}\n\npred prop1 {\n\tno Trash\n  \tno Protected\n}\n\npred prop2 {\n\n}\n\npred prop3 {\n\n}\n\npred prop4 {\n\n}\n\npred prop5 {\n\n}\n\npred prop6 {\n\n}\n\npred prop7 {\n\n}\n\npred prop8 {\n\n}\n\npred prop9 {\n\n}\n\npred prop10 {\n\n}\n\npred prop11 {\n\n}\n\npred prop12 {\n\n}\n\npred prop13 {\n\n}\n\npred prop14 {\n\n}\n\npred prop15 {\n\n}\n\npred prop16 {\n\n}\n\npred prop17 {\n\n}\n\npred prop18 {\n\n}\n\npred prop19 {\n\n}\n\npred prop20 {\n\n}"

def purge_pred(source, pred_name):
  match = re.search(r"pred\s+" + pred_name, source)
  if match is None:
    return source

  begin = match.span(0)[0]
  i = begin
  depth = 0
  while not (source[i] == "}" and depth == 1):
    if source[i] == "{":
      depth += 1
    elif source[i] == "}":
      depth -= 1
    i += 1
  end = i

  return source[0:begin] + source[end+1:]

def pred_list(ret=[]):
  if ret != []:
    return ret
  for i in range(1, 21):
    ret.append("prop" + str(i))
    ret.append("inv" + str(i))
  return ret

def keep_pred(source, pred_name, pred_names):
  for pred in pred_names:
    if pred != pred_name:
      source = purge_pred(source, pred)
  return re.sub(r'\n(?=\n)', '', source, flags=re.DOTALL)

def slice_from_pos(string, pos): # doesn't work too well on sigs
  global i, curx, cury
  i = 0
  curx = 1
  cury = 1

  def step():
    global i, curx, cury
    if string[i] == "\n":
      cury += 1
      curx = 1
    else:
      curx += 1
    i += 1

  while curx != pos.x or cury != pos.y:
    step()
  start = i
  while curx != pos.x2 or cury != pos.y2:
    step()

  return string[start:i+1]

rep = A4Reporter()
absfilepath = "/tmp/tmp.als"
opt = A4Options()
opt.solver = A4Options.SatSolver.SAT4J
opt.originalFilename = absfilepath

def parse(source):
  with open(absfilepath, "w") as f:
    f.write(source)
  return CompUtil.parseEverything_fromFile(rep, None, absfilepath)
  return CompUtil.parseOneModule(source)

def extract_pred(source, pred, prefix=""):
  world = parse(source)
  func = next(expr for expr in world.getAllFunc() if expr.label == "this/" + pred)

  # TODO: find dependencies of func
  # search in the func slice for other func labels
  ret = slice_from_pos(source, func.pos())
  return re.sub(pred, prefix + pred, ret)

def semantic_equals(world, label0, label1):
  
  # find funcs by label (beautiful and pythonic)
  func0 = next((fun for fun in world.getAllFunc() if fun.label == "this/" + label0), None)
  func1 = next((fun for fun in world.getAllFunc() if fun.label == "this/" + label1), None)
  
  expr = func0.call().iff(func1.call()).not_()

  cmd = Command(True, -1, -1, -1, expr)

  check = TranslateAlloyToKodkod.execute_command(A4Reporter.NOP, world.getAllSigs(), cmd, opt)
  return not check.satisfiable()

#def pred_ast_from_source(world):
#
#
#  for func in world.getAllFunc():
#    if not func.isPred:
#      continue
#    if not func.isPred:
#      return
#
#    return AST.from_expr(func.getBody())

pred0 = extract_pred(source0, "prop2", "_")
world = parse(source0 + pred0)
print(semantic_equals(world, "prop1", "prop1"))
print(semantic_equals(world, "prop1", "_prop2"))

#world = parse(source0)
#funcs = world.getAllFunc()
#pred1_0 = slice_from_pos(source0, funcs.get(0).pos())
#pred1_1 = slice_from_pos(source0, funcs.get(1).pos())
#print(pred1_0)
#expr0 = parse_with_module(world, pred1_0)

#world1 = parse(src1)
#print(semantic_equals(world0, world1, "this/prop1", "this/prop1"))
#ast = pred_ast_from_source(src)
#print(ast.toApted())
#print(ast.toGraphviz())
#print(ast.getApted().compute_edit_distance())



#print(world.getAllCommands())
#print(world.getAllAssertions())
#for func in world.getAllFunc():
#  if not func.isPred:
#    continue
#  #print(func)
#  ast = AST.from_expr(func.getBody())
#  #print(ast)
#  #print(ast.toApted())
#
#  #body = func.getBody()
#  #print(body)
#  #print(body.getClass())
#  #print(body.op)
#  #print(body.args)
#  break
#print(world.getAllFunc())

#os.remove(filename)
