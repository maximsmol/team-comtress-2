import sys
from contextlib import contextmanager

# TODO(maximsmol): make optional
import colorful as cf

class Namespace(dict):
  def __getattr__(self, x):
    if x in self:
      return self[x]

    raise AttributeError(x)

  def __setattr__(self, k, v):
    self[k] = v

_print = print
class _Putter:
  def __init__(self):
    self.indent_level = 0

  def newline(self):
    _print()

  def warning(self, msg, *args, **kwargs):
    self.print(cf.yellow(msg, *args, **kwargs))

  def error(self, msg, *args, **kwargs):
    self.print(cf.red(msg, *args, **kwargs))

  def die(self, msg, *args, exception=None, **kwargs):
    self.error(msg, *args, **kwargs)

    if exception is not None:
      raise exception
    else:
      raise ValueError(msg)
    sys.exit(1)

  def group(self, msg, *args, **kwargs):
    self.print(cf.cornflowerBlue(msg)+':', *args, **kwargs)
    return self.indent()

  def print(self, msg=''):
    _print('  ' * self.indent_level + str(msg))

  @contextmanager
  def indent(self):
    self.indent_level += 1
    yield
    self.indent_level -= 1

  def render_list(self, xs, separator=', '):
    return separator.join([str(cf.bold(x)) for x in xs])

putter = _Putter()

def print(*args, **kwargs):
  return putter.print(*args, **kwargs)
