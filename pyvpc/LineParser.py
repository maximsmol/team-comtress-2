from pathlib import PureWindowsPath as Path

from utils import Namespace, putter, cf

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

  def die(self, msg, *args, **kwargs):
    p = Path(self.file.name)
    # putter.error(f'{cf.bold(str(self.line_cache[0])+":")} {self.lines[self.line_cache[0]-1].strip()}')
    putter.error(self.line_cache[1])
    putter.die(f'{cf.italic(p.name)}:{str(self.line_cache[0])+":"} {msg}', *args, **kwargs)

  def _read_line_at(self):
    while True:
      if self.line_idx >= self.num_lines:
        return None

      res = self.lines[self.line_idx]
      res = res.strip()

      if res == '' or res.startswith('//'):
        self.line_idx += 1
        continue

      inline_comment_start = res.find('//')
      if inline_comment_start != -1:
        res = res[:inline_comment_start]
        res = res.strip()

      if res[-1] == '\\':
        res = res[:-1]
        # if we strip here, we lose the whitespace separating
        # strings (which are expected to unify as if we are using the C preprocessor)
        # res = res.strip()

        # go to next line and read more
        # we will cache at the line after the compound line ends
        self.line_idx += 1

        cont = self._read_line_at()
        if cont is None:
          self.die('Unexpected EOF after line continuation.')
        res += cont

      break

    self.line_cache = self.line_idx, res
    return res

  @property
  def line(self):
    if self.line_cache[0] == self.line_idx:
      return self.line_cache[1]

    return self._read_line_at()

  def next_line(self):
    self.line_idx += 1

  def consume_line(self):
    res = self.line
    self.next_line()
    return res
