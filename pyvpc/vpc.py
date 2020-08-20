from pathlib import PureWindowsPath as Path
from contextlib import contextmanager
from collections import deque

from utils import Namespace, putter, cf
from tokenization import VPCTokenizer
from vpc_utils import strip_quotes, raw_string, string_like, merge_command_data

class CondParser:
  def __init__(self, x):
    assert x.type == 'cond'
    self.x = x.x
    self.i = 0
    self.l = len(self.x)

  @property
  def cur(self):
    if self.i >= self.l:
      putter.die(f'Ran out of input in {cf.bold(self.x)}')

    return self.x[self.i]

  def skip_spaces(self):
    while self.i < self.l and self.cur in ' \t':
      self.i += 1

  def parse_id(self):
    value = True
    if self.cur == '!':
      value = False
      self.i += 1
      self.skip_spaces()

    if self.cur != '$':
      putter.die(f'$ does not preceed macro name in {cf.bold(self.x)}.')
    self.i += 1

    res = ''
    while self.i < self.l and self.cur not in ' \t)&|':
      if self.cur == '(':
        putter.die(f'Unexpected ( in macro name in {cf.bold(self.x)}.')
      res += self.cur
      self.i += 1

    self.skip_spaces()
    return Namespace(type='macro',
                     name=res,
                     setto=value)

  def parse_parens(self):
    if self.cur != '(':
      return self.parse_id()

    self.i += 1
    self.skip_spaces()

    res = self.parse_expr()

    assert self.cur == ')'
    self.i += 1

    self.skip_spaces()
    return res

  def parse_and(self):
    res = []
    while self.i < self.l:
      res.append(self.parse_parens())
      if self.i >= self.l:
        break
      if self.cur == '&' and self.cur == '&':
        self.i += 2
      else:
        break
      self.skip_spaces()

    if len(res) == 1:
      return res[0]
    return Namespace(type='and',
                     conds=res)

  def parse_or(self):
    res = []
    while self.i < self.l:
      res.append(self.parse_and())
      if self.i >= self.l:
        break
      if self.cur == '|' and self.cur == '|':
        self.i += 2
      else:
        break
      self.skip_spaces()

    if len(res) == 1:
      return res[0]
    return Namespace(type='or',
                     conds=res)

  def parse_expr(self):
    return self.parse_or()

  def parse(self):
    self.skip_spaces()
    return self.parse_expr()
def parse_cond(x):
  p = CondParser(x)
  return p.parse()

negatable_cmds = ['file']
class VPCParser(VPCTokenizer):
  @contextmanager
  def need_body(self):
    assert self.consume_token().type == '{'
    yield
    assert self.consume_token().type == '}'

  def need_command(self, parts, lowercase=True):
    def die_no_command():
      self.die(f'Line does not contain command {cf.bold(str(parts))}.')

    if len(parts) == 0:
      die_no_command()

    # TODO(maximsmol): separate the negation logic from the command name logic?
    cmd_part = parts[0]
    assert cmd_part.type == 'raw'
    cmd = cmd_part.x

    if cmd[0] == '-':
      if cmd[1] != '$':
        die_no_command()

      cmd = cmd[2:]
      if lowercase:
        cmd = cmd.lower()

      if cmd not in negatable_cmds:
        self.die(f'Cannot negate {cf.bold(cmd)}.')
      return '-' + cmd

    if cmd[0] != '$':
        die_no_command()

    if lowercase:
      return cmd[1:].lower()
    return cmd[1:]

  def parse_body(self, merge_strings=False):
    with self.need_body():
      while True:
        if self.token is None:
          self.die(f'Unexpected end of file for {cf.bold("$"+cmd)}.')
        if self.token.type == '}':
          break
        yield self.parse_command_parts(merge_strings=merge_strings)

  def parse_body_commands(self, merge_strings=False, lowercase=True):
    for body_parts in self.parse_body(merge_strings=merge_strings):
      yield self.need_command(body_parts, lowercase=lowercase), body_parts

  def parse_command_parts(self, merge_strings=False):
    tok = self.consume_token()
    if tok is None:
      self.die('Unexpected EOF: missing command parts.')
    assert tok.type == 'parts'

    l = len(tok.parts)
    res = Namespace(parts=[])

    strs_to_merge = []
    def push_merged_str():
      if len(strs_to_merge) == 0:
        return
      res.parts.append(Namespace(type='str', x=''.join([x.x for x in strs_to_merge])))

    for i, x in enumerate(tok.parts):
      if x.type == 'str':
        if not merge_strings:
          res.parts.append(x)
          continue
        strs_to_merge.append(x)
        continue

      push_merged_str()

      if x.type == 'raw':
        res.parts.append(x)
        continue
      if x.type == 'cond':
        assert i == l-1
        res.parts.append(x)
        continue
      self.die(f'Unknown token "{cf.bold(x.type)}".')

    if 'comment' in tok:
      res.comment = tok.comment

    # TODO(maximsmol): handle comments properly
    if 'comment' in res:
      pass
    return res.parts

  # def parse_command_parts(self):
  #   parts = []

  #   i = 0
  #   l = len(self.line)

  #   def skip_whitespace():
  #     nonlocal i
  #     while i < l:
  #       if self.line[i] not in ' \t':
  #         break
  #       i += 1
  #   def read_word():
  #     nonlocal i
  #     res = ''

  #     in_str = self.line[i] == '"'
  #     if in_str:
  #       res += '"'
  #       i += 1

  #     in_cond = self.line[i] == '['
  #     while i < l:
  #       if not in_cond and not in_str:
  #         if self.line[i] in ' \t':
  #           break
  #       res += self.line[i]
  #       if in_str and self.line[i] == '"':
  #         i += 1
  #         break
  #       if in_cond and self.line[i] == ']':
  #         i += 1
  #         break
  #       i += 1
  #     return res

  #   skip_whitespace()
  #   while i < l:
  #     parts.append(read_word())
  #     skip_whitespace()

  #   self.next_line()

  #   return parts

  @property
  def token(self):
    while True:
      res = super().token
      if res is None:
        return None
      if res.type != 'comment':
        return res
      super().consume_token()

  def consume_token(self):
    while True:
      res = super().consume_token()
      if res is None:
        return None
      if res.type != 'comment':
        return res

  def parse(self, *args, **kwargs):
    try:
      return self._parse(*args, **kwargs)
    except BaseException as e:
      self.die(repr(e), exception=e)

class ManifestParser(VPCParser):
  def parse_command(self, res):
    parts = self.parse_command_parts()
    cmd = self.need_command(parts)
    if cmd == 'include':
      assert len(parts) == 2
      res.includes.append(strip_quotes(parts[1]))
    elif cmd == 'games':
      assert len(parts) == 1
      for body_parts in self.parse_body():
        assert len(body_parts) == 1
        res.games.append(strip_quotes(body_parts[0]).lower())
    elif cmd == 'group':
      assert len(parts) >= 1
      projects = []
      for body_parts in self.parse_body():
        assert len(body_parts) == 1
        projects.append(strip_quotes(body_parts[0]))

      for g_name in parts[1:]:
        g_name = strip_quotes(g_name)
        group = res.groups.setdefault(g_name, Namespace())
        group.setdefault('projects', []).extend(projects)
    elif cmd == 'project':
      assert len(parts) == 2

      name = strip_quotes(parts[1])
      if name in res.projects:
        self.die(f'Duplicate project {cf.bold(name)}.')

      proj = res.projects.setdefault(name, Namespace())
      paths = proj.setdefault('paths', [])

      for body_parts in self.parse_body():
        path = strip_quotes(body_parts[0])
        if len(body_parts) == 2:
          cond = parse_cond(body_parts[1])

          paths.append(Namespace(path=path,
                                 cond=cond))
        else:
          assert len(body_parts) == 1
          paths.append(Namespace(path=path))
    else:
      print(parts)
      self.die(f'Unknown command {cf.bold(cmd)}.')

  def _parse(self):
    res = Namespace(projects=Namespace(),
                    groups=Namespace(),
                    games=[],
                    includes=[])
    while self.token is not None:
      self.parse_command(res)
    return res

def read_manifest(path):
  with open(str(path)) as f:
    p = ManifestParser(f)
    res = p.parse()
    return res

configuration_commands = Namespace(
  Compiler=Namespace(pythonized='compiler'),
  General=Namespace(pythonized='general'),
  Linker=Namespace(pythonized='linker'),
  Debugging=Namespace(pythonized='debugging'),
  ManifestTool=Namespace(pythonized='manifest_tool'),
  XMLDocumentGenerator=Namespace(pythonized='xml_document_generator'),
  BrowseInformation=Namespace(pythonized='browse_information'),
  Resources=Namespace(pythonized='resources'),
  CustomBuildStep=Namespace(pythonized='custom_build_step'),
  PreBuildEvent=Namespace(pythonized='pre_build_event'),
  PreLinkEvent=Namespace(pythonized='pre_link_event'),
  PostBuildEvent=Namespace(pythonized='post_build_event'),
  PostLinkEvent=Namespace(pythonized='post_link_event'))
class ProjectParser(VPCParser):
  def parse_configuration_comamnd(self, res, parts):
    inst = Namespace(type='configuration')
    res.instructions.append(inst)

    if len(parts) == 2:
      inst.name = strip_quotes(parts[1])
    else:
      assert len(parts) == 1

    def generic_prop_group(name, body_parts):
      group = Namespace()
      inst.setdefault(name, []).append(group)

      if len(body_parts) == 2:
        group.cond = parse_cond(body_parts[1])
      else:
        assert len(body_parts) == 1

      for cmd, body_parts in self.parse_body_commands(lowercase=False):
        group.setdefault(cmd, []).append(body_parts[1:])

    for cmd, body_parts in self.parse_body_commands(lowercase=False):
      if cmd not in configuration_commands:
        self.die(f'Unknown configuration command {cf.bold(cmd)}.')

      generic_prop_group(configuration_commands[cmd].pythonized, body_parts)

  def parse_folder_command(self, res, parts):
    assert len(parts) >= 2
    name = strip_quotes(parts[1])

    if name not in res.folders:
      res.folders[name] = Namespace(files=[],
                                    libs=[],
                                    folders=Namespace())
    # TODO(maximsmol): we lose definition order information here so something might break
    folder = res.folders[name]

    if len(parts) == 3:
      folder.cond = parse_cond(parts[2])
    else:
      assert len(parts) == 2

    for cmd, body_parts in self.parse_body_commands():
      if cmd == 'folder':
        self.parse_folder_command(folder, body_parts)
      elif cmd in ['file', '-file']:
        file = Namespace(paths=[],
                         instructions=[])
        folder.files.append(file)

        if body_parts[-1].type == 'cond':
          file.cond = parse_cond(body_parts[-1])
          body_parts = body_parts[:-1]

        for p in body_parts[1:]:
          file.paths.append(strip_quotes(p))

        if self.token.type == '{':
          for cmd, body_parts in self.parse_body_commands():
            if cmd == 'configuration':
              self.parse_configuration_comamnd(file, body_parts)
            else:
              self.die(f'Unknown file command {cf.bold(cmd)}.')
      elif cmd in ['libexternal']:
        lib = Namespace(paths=string_like(body_parts[1]))
        folder.libs.append(lib)

        if len(body_parts) == 3:
          lib.cond = parse_cond(body_parts[2])
        else:
          assert len(body_parts) == 2
      else:
        self.die(f'Unknown folder command {cf.bold(cmd)}.')

  def parse_command(self, res):
    parts = self.parse_command_parts()
    cmd = self.need_command(parts, lowercase=False)
    if cmd == 'Macro':
      name = string_like(parts[1])
      # TODO(maximsmol): weird unquoted macro values are allowed
      #                  and we skip the spaces in them + this parsing
      #                  is all around weird
      value = string_like(parts[2])

      cond = None
      if len(parts) > 3:
        # TODO(maximsmol): check that weird unquoted macros are unquoted
        value_parts = [value]
        i = 3
        for p in parts[3:]:
          if p.type == 'cond':
            cond = parse_cond(parts[3])
            assert i == len(parts)-1
            break

          value_parts.append(raw_string(p))
          i += 1
        # TODO(maximsmol): this actually loses some whitespaces
        value = ' '.join(value_parts)
      else:
        assert len(parts) == 3

      inst = Namespace(type='macro')
      inst.name = name
      inst.value = value
      if cond is not None:
        inst.cond = cond
      res.instructions.append(inst)
    elif cmd == 'Conditional':
      name = parts[1]
      assert name[0] != '"' and name[-1] != '"'

      inst = Namespace(type='conditional')
      res.instructions.append(inst)

      inst.name = name
      inst.value = strip_quotes(parts[2])

      cond = None
      if len(parts) == 4:
        inst.cond = parse_cond(parts[3])
      else:
        assert len(parts) == 3
    elif cmd == 'MacroRequired':
      inst = Namespace(type='macro_required')

      if len(parts) == 3:
        inst.default = strip_quotes(parts[2])
      else:
        assert len(parts) == 2

      inst.name = strip_quotes(parts[1])
      inst.allow_empty = False
    elif cmd == 'MacroRequiredAllowEmpty':
      inst = Namespace(type='macro_required')

      if len(parts) == 3:
        inst.default = strip_quotes(parts[2])
      else:
        assert len(parts) == 2

      inst.name = strip_quotes(parts[1])
      inst.allow_empty = True
    elif cmd == 'LoadAddressMacro':
      inst = Namespace(type='address_macro')
      res.instructions.append(inst)

      assert len(parts) == 2

      inst.name = parts[1]
      assert inst.name[0] != '"' and inst.name[-1] != '"'

      for body_parts in self.parse_body():
        # TODO(maximsmol): parse this
        # this is only used on XBOX afaik
        pass
    elif cmd == 'LoadAddressMacroAuto':
      inst = Namespace(type='address_macro_auto')
      res.instructions.append(inst)

      assert len(parts) == 4

      inst.name = parts[1]
      assert inst.name[0] != '"' and inst.name[-1] != '"'

      inst.addr = int(parts[2], 16)
      inst.cond = parse_cond(parts[3])

      for body_parts in self.parse_body():
        # TODO(maximsmol): parse this
        # this is only used on XBOX afaik
        pass
    elif cmd == 'IgnoreRedundancyWarning':
      inst = Namespace(type='ignore_redundancy_warning')
      assert len(parts) == 2

      inst.value = strip_quotes(parts[1]).lower()
    elif cmd in ['Include', 'include']: # Valve, why do you insist on mixing case
      path = strip_quotes(parts[1])
      cond = None
      if len(parts) == 3:
        cond = parse_cond(parts[2])
      else:
        assert len(parts) == 2

      inst = Namespace(type='include')
      inst.path = path
      if cond is not None:
        inst.cond = cond
      res.instructions.append(inst)
    elif cmd == 'Configuration':
      self.parse_configuration_comamnd(res, parts)
    elif cmd == 'Project':
      proj = Namespace(type='project',
                       folders=Namespace())
      res.instructions.append(proj)

      if len(parts) == 2:
        name = strip_quotes(parts[1])
      else:
        assert len(parts) == 1

      for cmd, body_parts in self.parse_body_commands():
        if cmd == 'folder':
          self.parse_folder_command(proj, body_parts)
        else:
          self.die(f'Unknown project command {cf.bold(cmd)}.')
    else:
      self.die(f'Unknown command {cf.bold(cmd)}.')

  def _parse(self):
    res = Namespace(instructions=[])
    while self.token is not None:
      self.parse_command(res)
    return res

def read_project(path):
  with open(str(path)) as f:
    p = ProjectParser(f)
    res = p.parse()
    return res
