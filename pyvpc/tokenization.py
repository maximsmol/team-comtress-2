import re
from pathlib import PureWindowsPath as Path

from utils import Namespace, putter, cf

_spaces = ' \t'
class LineParser:
  def __init__(self, f):
    self.file = f
    self.lines = f.readlines()
    self.num_lines = len(self.lines)
    self.line_idx = 0
    self.line_cache = -1, None

    if self.num_lines > 0 and self.lines[0][0] == '\ufeff':
      # putter.warning(f'Found BOM in {cf.italic(Path(self.file.filename).name)}')
      self.lines[0] = self.lines[0][1:]

  # TODO(maximsmol): allow reporting column number
  def die(self, msg, *args, **kwargs):
    p = Path(self.file.name)
    # putter.error(f'{cf.bold(str(self.line_cache[0])+":")} {self.lines[self.line_cache[0]-1].strip()}')
    putter.error(self.line_cache[1].rstrip()) # righthand whitespace will not be visible anyway
    putter.die(f'{cf.italic(p.name)}:{str(self.line_cache[0]+1)+":"} {msg}', *args, **kwargs)

  # TODO(maximsmol): save this logic somewhere and rm this
  # def _read_line(self):
  #   while True:
  #     if self.line_idx >= self.num_lines:
  #       return None

  #     res = self.lines[self.line_idx]
  #     res = res.strip()

  #     if res == '' or res.startswith('//'):
  #       self.line_idx += 1
  #       continue

  #     inline_comment_start = res.find('//')
  #     if inline_comment_start != -1:
  #       res = res[:inline_comment_start]
  #       res = res.strip()

  #     if res[-1] == '\\':
  #       res = res[:-1]
  #       # if we strip here, we lose the whitespace separating
  #       # strings (which are expected to unify as if we are using the C preprocessor)
  #       # res = res.strip()

  #       # go to next line and read more
  #       # we will cache at the line after the compound line ends
  #       self.line_idx += 1

  #       cont = self._read_line()
  #       if cont is None:
  #         self.die('Unexpected EOF after line continuation.')
  #       res += cont

  #     break

  #   self.line_cache = self.line_idx, res
  #   return res

  def _read_line(self):
    if self.line_idx >= self.num_lines:
      return None
    return self.lines[self.line_idx]

  @property
  def line(self):
    if self.line_cache[0] == self.line_idx:
      return self.line_cache[1]

    res = self._read_line()
    self.line_cache = self.line_idx, res
    return res

  def next_line(self):
    self.line_idx += 1

  def consume_line(self):
    res = self.line
    self.next_line()
    return res

# we want die, consume_line, BOM handling
class VPCTokenizer(LineParser):
  def __init__(self, f):
    super().__init__(f)
    self.nesting_level = 0
    self._tokens = []

  def _tokenize_line(self):
    try:
      tokens_pushed = 0
      def push_token(x):
        nonlocal tokens_pushed
        self._tokens.append(x)
        tokens_pushed += 1

      while True:
        if self.line_idx >= self.num_lines:
          # success if pushed anything
          return tokens_pushed > 0

        # TODO(maximsmol): unify pre-processing parsing with the real deal
        cur_res = Namespace(type='parts', parts=[])
        cur = self.consume_line()
        cur = cur.lstrip() # keep whitespace in comments after the line
        if cur == '':
          # if we found an empty line, just read the next one
          continue

        if cur.startswith('//'):
          push_token(Namespace(type='comment', comment=cur[2:]))
          return True

        def line_end_processing():
          nonlocal cur
          if cur[-1] == '\n':
            # ugh... windows...
            cur = cur[:-1]
          # TODO(maximsmol): we strip here, so if there was a "\ " we think
          #                  it is just a continuation
          cur = cur.rstrip()
        line_end_processing()

        if cur == '':
          # if we found an empty line, just read the next one
          continue

        comment = ''
        part = ''
        in_str = False
        in_cond = False
        got_one_slash = False
        in_comment = False
        def finish_cur_res():
          nonlocal cur_res
          assert not in_cond
          assert not in_str

          if part != '':
            cur_res.parts.append(Namespace(type='raw', x=part))

          # do not push empty tokens
          if len(cur_res.parts) == 0 and 'comment' not in cur_res:
            return

          push_token(cur_res)
          cur_res = Namespace(type='parts', parts=[])
        def flush_part(type):
          nonlocal part
          assert part != ''
          cur_res.parts.append(Namespace(type=type, x=part))
          part = ''

        # cannot use an iterator because we replace cur midway through
        # if we find a continuation
        i = -1
        while True:
          i += 1
          if i >= len(cur):
            break
          x = cur[i]

          if in_comment:
            # once entered a comment, go forever
            comment += x
            continue

          if not in_cond and x == '"':
            if in_str:
              in_str = False
              flush_part('str')
            else:
              in_str = True
            continue
          if in_str:
            part += x
            continue

          if x == '\\':
            # TODO(maximsmol): make sure the line is empty past this
            cur = self.consume_line()
            i = 0
            line_end_processing()
            continue

          if got_one_slash:
            if x == '/':
              in_comment = True
              got_one_slash = False
              continue
            else:
              got_one_slash = False
              # add the slash that we skipped (most often occurs in paths)
              part += '/'
          elif x == '/':
            got_one_slash = True
            continue

          if x == '[':
            assert not in_cond
            in_cond = True
            continue
          if x == ']':
            assert in_cond
            in_cond = False
            flush_part('cond')
            continue
          if in_cond:
            if x == '"':
              self.die('Condition cannot have quotes.')
            # cond does not need spaces
            if x in _spaces:
              continue
            part += x
            continue

          if x == '}':
            # this is a body end (possibly inline)
            finish_cur_res()
            push_token(Namespace(type='}'))

            assert self.nesting_level > 0
            self.nesting_level -= 1

            continue
          if x == '{':
            # this is a body start (possibly inline)
            finish_cur_res()
            push_token(Namespace(type='{'))

            self.nesting_level += 1

            continue

          if x in '"\\[]{}':
            self.die(f'Special character {x} in raw token.')
          if x in _spaces:
            if part != '':
              flush_part('raw')
            continue
          part += x

        finish_cur_res()

        assert tokens_pushed > 0 # we must have found at least something
        if comment == '':
          # the comment belongs to the last token in the line
          self._tokens[-1].comment = comment
        break
      return True
    except BaseException as e:
      self.die(str(e), exception=e)

  @property
  def tokens(self):
    # TODO(maximsmol): cache tokenization failure?
    if len(self._tokens) == 0 and not self._tokenize_line():
      if self.nesting_level != 0:
        # TODO(maximsmol): improve error message
        self.die('Unexpected EOF: unbalanced {')
      return None

    assert len(self._tokens) != 0
    return self._tokens

  @property
  def token(self):
    # TODO(maximsmol): invert this list so pop is O(1)?
    if self.tokens is None:
      return None
    return self.tokens[0]

  def consume_token(self):
    if self.tokens is None:
      return None
    return self.tokens.pop(0)
