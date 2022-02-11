import os
import re
import jpype
import jpype.imports
from jpype.types import *
from ast import AST

jpype.startJVM(classpath=['lib/alloy6.jar'])

from edu.mit.csail.sdg.ast import Command
from edu.mit.csail.sdg.ast import VisitQuery
from edu.mit.csail.sdg.alloy4 import A4Reporter
from edu.mit.csail.sdg.parser import CompUtil
from edu.mit.csail.sdg.parser import CompModule
from edu.mit.csail.sdg.translator import A4Options
from edu.mit.csail.sdg.translator import A4Solution


source = "\nvar sig File {\n\tvar link : lone File\n}\nvar sig Trash in File {}\nvar sig Protected in File {}\n\npred prop1 {\n\tno Trash\n  \tno Protected\n}\n\npred prop2 {\n\n}\n\npred prop3 {\n\n}\n\npred prop4 {\n\n}\n\npred prop5 {\n\n}\n\npred prop6 {\n\n}\n\npred prop7 {\n\n}\n\npred prop8 {\n\n}\n\npred prop9 {\n\n}\n\npred prop10 {\n\n}\n\npred prop11 {\n\n}\n\npred prop12 {\n\n}\n\npred prop13 {\n\n}\n\npred prop14 {\n\n}\n\npred prop15 {\n\n}\n\npred prop16 {\n\n}\n\npred prop17 {\n\n}\n\npred prop18 {\n\n}\n\npred prop19 {\n\n}\n\npred prop20 {\n\n}"

def purge_pred(source, pred_name):
  match = re.search(r"pred\s+" + pred_name, source)
  if match is None:
    return

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

def pred_list():
  return list(map(lambda x: "prop" + str(x), range(1,21)))

def keep_pred(source, pred_name, pred_names):
  for pred in pred_names:
    if pred != pred_name:
      source = purge_pred(source, pred)
  return re.sub(r'\n(?=\n)', '', source, flags=re.DOTALL)


def pred_ast_from_source(source):
  absfilepath = "/tmp/tmp.als"
  fp = open(absfilepath, "w")
  fp.write(source)
  fp.close()

  rep = A4Reporter()
  world = CompUtil.parseEverything_fromFile(rep, None, absfilepath)
  opt = A4Options()
  opt.originalFilename = absfilepath
  opt.solver = A4Options.SatSolver.SAT4J

  for func in world.getAllFunc():
    if not func.isPred:
      continue
    if not func.isPred:
      return

    return AST.from_expr(func.getBody())

#src = keep_pred(source, "prop1", pred_list())
#ast = pred_ast_from_source(src)
#print(src)
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
