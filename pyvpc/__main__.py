import sys
import re
from pathlib import PureWindowsPath as Path
from collections import deque
import sys
import ntpath

import args
from vpc_utils import render_cond, merge_command_data
from utils import Namespace, putter, print, cf
from vpc import read_manifest, read_project, parse_cond
import vpc

parsed_args = args.parser.parse_args()

# TODO(maximsmol): parse this on-demand
mainlist = read_manifest(Path('vpc_scripts') / 'default.vgc')
to_include = deque(mainlist.includes)
while len(to_include) > 0:
  incl_path = to_include.popleft()
  included = read_manifest(Path(incl_path))

  if parsed_args.log_includes:
    print(f'Included "{cf.bold(incl_path)}".')

  merge_command_data(mainlist.projects, included.projects)
  merge_command_data(mainlist.games, included.games)
  merge_command_data(mainlist.groups, included.groups, allow_duplicates=True)

  to_include.extend(included.includes)

macro_state = Namespace()

def cond_suffix(x):
  if 'cond' not in x:
    return ''
  return f' {render_cond(x.cond, macro_state)}'

def render_macro_value(x):
  stripped = x.strip()
  if stripped != x or stripped == '':
    return cf.bold(f'"{x}"')
  return cf.bold(x)

def err_dump_macro_state():
  have_non_bool_macros = False
  bool_macro_strs = []
  for k, v in macro_state.items():
    if not isinstance(v, bool):
      have_non_bool_macros = True
      continue
    if v is True:
      bool_macro_strs.append(f'${k}')
    else:
      bool_macro_strs.append(f'!${k}')

  if not have_non_bool_macros:
    putter.error('Macros: ' + putter.render_list(bool_macro_strs))
  else:
    putter.error('Macros:')

  with putter.indent():
    for k, v in macro_state.items():
      if v is True:
        continue
      putter.error(f'{cf.bold("$"+k)} = {render_macro_value(v)}')

def die(msg, *args, linefeed_before=True, **kwargs):
  if linefeed_before:
    putter.newline()
  err_dump_macro_state()
  putter.newline()
  putter.die(msg, *args, **kwargs)

uppercase_re = re.compile(r'[A-Z]')
uppercase_alphanum_re = re.compile(r'[A-Z0-9_]')
def expand_macros_in_string(x):
  i = 0
  l = len(x)

  res = ''

  in_macro = False
  macro_name = ''
  def commit_macro():
    nonlocal in_macro, macro_name, res

    if macro_name not in macro_state:
      # TODO(maximsmol): is this fine?
      # die(f'Macro {cf.bold(macro_name)} is undefined.')
      val = "0"
    else:
      val = macro_state[macro_name]

    if not isinstance(val, str):
      # TODO(maximsmol): is this fine?
      # die(f'Macro {cf.bold(macro_name)} is not a string.')
      if not isinstance(val, bool):
        die(f'Macro {cf.bold(macro_name)} has invalid type.')
      val = "1" if val is True else "0"
    res += val

    in_macro = False
    macro_name = ''

  while i < l:
    if x[i] == '$':
      if in_macro:
        commit_macro()
      in_macro = True
      i += 1
      continue

    if macro_name != '' and uppercase_alphanum_re.fullmatch(x[i]) is None:
      commit_macro()

    if in_macro:
      if macro_name == '' and uppercase_re.fullmatch(x[i]) is None:
        die(f'Macro {macro_name} starts with an invalid symbol.')
      macro_name += x[i]
    else:
      res += x[i]

    i += 1
  if in_macro:
    commit_macro()
  assert not in_macro

  return res

def eval_cond(x):
  if x.type == 'or':
    for c in x.conds:
      if not eval_cond(c):
        continue
      return True
    return False
  elif x.type == 'and':
    for c in x.conds:
      if eval_cond(c):
        continue
      return False
    return True
  elif x.type == 'macro':
    if x.name not in macro_state:
      # putter.die(f'Macro {x.name} is not defined.')
      return False == x.setto

    state = macro_state[x.name]
    if isinstance(state, bool):
      return state == x.setto
    if not isinstance(state, str):
      self.die(f'Cond {state} has invalid type.')

    print(state, x.name)
    assert False

    expr = expand_macros_in_string(state)
    return eval_cond(parse_cond(Namespace(type='cond', x=expr))) == x.setto
  else:
    putter.die(f'Unknown condition type: {cf.bold(x.type)}')

def resolve_project_path(name, do_not_crash=False):
  proj = mainlist.projects[name]

  # TODO(maximsmol): shortcircuit path search if not debugging
  path = None
  for p in proj.paths:
    if 'cond' not in p:
      if path is not None:
        putter.die(f'Multiple paths apply: {cf.bold(path)} and {cf.bold(p.path)}.')
      path = p.path
      continue

    if eval_cond(p.cond):
      if path is not None:
        putter.die(f'Multiple paths apply: {cf.bold(path)} and {cf.bold(p.path)}.')
      path = p.path
  if path is None:
    if do_not_crash:
      return None

    # TODO(maximsmol): display why each condition failed
    err_dump_macro_state()
    putter.newline()
    putter.error(f'Found no applicable paths after trying the following:')
    with putter.indent():
      for p in proj.paths:
        putter.error(f'{cf.italic(p.path)}{cond_suffix(p)}')
    putter.newline()

  return Path(path)

no_strings = ['no', 'off', 'false', 'not set', 'disabled', '0']
yes_strings = ['yes', 'on', 'true', 'set', 'enabled', '1']
def build_project(name):
  project_data = Namespace(
    configuration=Namespace(compiler=Namespace()))

  root_path = None
  def build_data(path):
    data = read_project(path)
    for inst in data.instructions:
      if inst.type == 'conditional':
        if 'cond' not in inst or eval_cond(inst.cond):
          val = expand_macros_in_string(inst.value)
          if val == '1':
            val = True
          if val == '0':
            val = False

          if val in no_strings or val in yes_strings:
            putter.warning(f'Found yes/no stringbut refusing to convert it: {render_macro_value(val)}')

          print(f'{cf.magenta("Set conditional")} {cf.bold("$"+inst.name)} = {render_macro_value(val)}{cond_suffix(inst)}')
          if inst.name in macro_state:
            with putter.indent():
              putter.warning(f'Overriding old value of {render_macro_value(macro_state[inst.name])}')
          macro_state[inst.name] = val
        else:
          print(f'Not setting conditional {cf.bold("$"+inst.name)} = {render_macro_value(val)}{cond_suffix(inst)} due to the false condition')
      elif inst.type == 'macro':
        if 'cond' not in inst or eval_cond(inst.cond):
          val = expand_macros_in_string(inst.value)
          if val == '1':
            val = True
          if val == '0':
            val = False

          if val in no_strings or val in yes_strings:
            putter.warning(f'Found yes/no stringbut refusing to convert it: {render_macro_value(val)}')

          print(f'{cf.magenta("Set")} {cf.bold("$"+inst.name)} = {render_macro_value(val)}{cond_suffix(inst)}')
          if inst.name in macro_state:
            with putter.indent():
              putter.warning(f'Overriding old value of {render_macro_value(macro_state[inst.name])}')
          macro_state[inst.name] = val
        else:
          print(f'Not setting {cf.bold("$"+inst.name)} = {render_macro_value(val)}{cond_suffix(inst)} due to the false condition')
      elif inst.type == 'include':
        if 'cond' not in inst or eval_cond(inst.cond):
          print(f'{cf.magenta("Including")} {cf.italic(inst.path)}{cond_suffix(inst)}')
          with putter.indent():
            include_path = expand_macros_in_string(inst.path)
            resolved_path = Path(ntpath.normpath(str(root_path.parent / include_path)))
            print(f'{cf.magenta("Resolved to")} {cf.italic(resolved_path)}')
            build_data(resolved_path)
        else:
          print(f'Not including {cf.italic(Path(inst.path).name)}{cond_suffix(inst)} due to the false condition')
      elif inst.type == 'configuration':
        def print_generic_dict(x_name):
          x_key = vpc.configuration_commands[x_name].pythonized
          if x_key not in inst:
            return

          # TODO(maximsmol): print the merging process
          merged = Namespace()
          for x in inst[x_key]:
            if 'cond' not in x or eval_cond(x.cond):
              merge_command_data(merged, x)

          with putter.group(x_name):
            for k, v in merged.items():
                print(f'{cf.bold(k)} = {cf.bold(v)}')

        suffix = ''
        if 'name' in inst:
          suffix = f' "{inst.name}"'
        with putter.group(f'Configuration{suffix}'):
          for generic_group in vpc.configuration_commands:
            print_generic_dict(generic_group)
      elif inst.type == 'macro_required':
        invalid_value = macro_state.get(inst.name) == '' and not inst.allow_empty
        if inst.name not in macro_state or invalid_value:
          if 'default' not in inst:
            if inst.name not in macro_state:
              die(f'Macro {cf.bold("$"+inst.name)} is required, but not defined.')
            if not inst.allow_empty:
              die(f'Macro {cf.bold("$"+inst.name)} is required, but is set to an empty string.')
          with putter.indent():
            print(f'{cf.magenta("Defaulted")} {cf.bold("$"+inst.name)} = {render_macro_value(inst.default)}')
            macro_state[inst.name] = inst.default
        else:
          print(f'{cf.magenta("Found required")} {cf.bold("$"+inst.name)}')
      else:
        putter.warning(f'Skipped instruction {cf.bold(inst.type)}.')

  root_path = resolve_project_path(name)
  print(f'Resolved project to {cf.italic(root_path)}')
  print()
  try:
    build_data(root_path)
  except (ValueError, AssertionError):
    putter.newline()
    putter.error(f'Root path is: {cf.italic(root_path)}')
    die('Could not parse file.', linefeed_before=False)
    raise
  except FileNotFoundError as e:
    putter.newline()
    putter.error(f'Root path is: {cf.italic(root_path)}')
    die(f'File not found: {cf.italic(e.filename)}.', linefeed_before=False)
    raise

def dump_project(data):
  def print_folder(name, folder_data):
    with putter.group(f'{name}/'):
      for k, v in folder_data.folders.items():
        print_folder(k, v)

      for f in folder_data.files:
        print(f'{cf.bold(f.path)}{cond_suffix(f)}')
        with putter.indent():
          for inst in f.instructions:
            print_inst(inst)
    # TODO(maximsmol): only print this when there was a lot of output?
    print(cf.gray(f'--- {name} ---'))

  def print_inst(inst):
    if inst.type == 'macro':
      print(f'{cf.bold("$"+inst.name)} = {cf.bold(inst.value)}{cond_suffix(inst)}')
    elif inst.type == 'include':
      print(f'include {cf.italic(inst.path)}{cond_suffix(inst)}')
    elif inst.type == 'configuration':
      with putter.group('configuration'):
        if 'compiler' in inst:
          with putter.group('compiler'):
            for k, v in inst.compiler.items():
              print(f'{cf.bold(k)} = {cf.bold(v)}')
    elif inst.type == 'project':
      with putter.group('project'):
        for k, v in inst.folders.items():
          print_folder(k, v)
    else:
      print(inst)

  for inst in data.instructions:
    print_inst(inst)

def dump_project_manifest(name):
  data = mainlist.projects[name]
  with putter.group(f'{name}'):
    for path in data.paths:
      print(f'{cf.italic(path.path)}{cond_suffix(path)}')

def dump_group(name):
  data = mainlist.groups[name]
  with putter.group(f'{name}'):
    for project in data.projects:
        print(f'{project}')

macro_re = re.compile(r'[A-Z][A-Z0-9]*')
def apply_define_args(args):
  for x in args.define:
    if macro_re.fullmatch(x) is None:
      putter.die(f'Macro name {cf.bold(x)} is invalid.')
    macro_state[x] = True

def cmd_dump_group(args):
  if len(mainlist.groups) == 0:
    putter.error('No groups available.')
    return

  if args.group is None:
    with putter.group('Groups'):
      for name in mainlist.groups:
        dump_group(name)
    return

  dump_group(args.group)

def cmd_dump_project(args):
  if len(mainlist.projects) == 0:
    putter.error('No projects available.')
    return

  apply_define_args(args)

  if args.project is None:
    with putter.group('Projects'):
      for name in mainlist.projects:
        path = resolve_project_path(name, do_not_crash=True)
        if path is None:
          putter.warning(f'No path allowed by conditions for {cf.bold(name)}.')
          continue
        try:
          data = read_project(path)
          dump_project(data)
        except (ValueError, AssertionError):
          putter.error('Could not parse file.')
        except FileNotFoundError:
          putter.error(f'File not found: {cf.underlined(path)}.')
    return

  try:
    data = read_project(resolve_project_path(args.project))
    dump_project(data)
  except (ValueError, AssertionError):
    putter.error('Could not parse file.')
    raise
  except FileNotFoundError:
    putter.error(f'File not found: {cf.underlined(path)}.')
    raise

def cmd_dump_project_manifest(args):
  if len(mainlist.projects) == 0:
    putter.error('No projects available.')
    return

  apply_define_args(args)

  if args.project is None:
    with putter.group('Projects'):
      for name in mainlist.projects:
          dump_project_manifest(name)
    return

  dump_project_manifest(args.project)

def cmd_build(args):
  if args.group is None:
    putter.error('Specify a group to build.')
    print()
    with putter.group('Available groups'):
      print(putter.render_list(mainlist.groups.keys()))
    return

  apply_define_args(args)
  build_project('client')

args.build_parser.set_defaults(func=cmd_build)

args.dump_group_parser.set_defaults(func=cmd_dump_group)
args.dump_project_parser.set_defaults(func=cmd_dump_project)
args.dump_project_manifest_parser.set_defaults(func=cmd_dump_project_manifest)

parsed_args = args.parser.parse_args()
if 'func' not in parsed_args:
  args.parser.print_help()
  sys.exit(1)

try:
  parsed_args.func(parsed_args)
except:
  if parsed_args.debug:
    raise
