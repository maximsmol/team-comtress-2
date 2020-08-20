from utils import cf

def merge_command_data(to, from_, allow_duplicates=False):
  if isinstance(from_, dict):
    for k, v in from_.items():
      if k not in to:
        to[k] = v
        continue
      if not isinstance(to[k], list) and not allow_duplicates:
        raise ValueError(f'Duplicate at key "{k}".')
      if type(to[k]) is not type(v):
        raise ValueError(f'Incompatible types at key "{k}".')
      merge_command_data(to[k], v)
    return
  if isinstance(from_, list):
    # TODO(maximsmol): check for duplicates. especially important when conditions vary on the items
    to.extend(from_)
    return
  raise ValueError('Unsure how to merge.')

def raw_string(x):
  assert x.type == 'raw'
  return x.x

def string_like(x):
  assert x.type == 'str' or x.type == 'raw'
  return x.x

def strip_quotes(x):
  # this looks weird because we did not have a proper
  # tokenizer in the past and this actually tore quotes
  # off of raw strings like '"value"'
  assert x.type == 'str'
  return x.x

def render_cond(x, macro_state):
  def render(x, enclosing_type):
    if x.type == 'or':
      res = [render(x, 'or') for x in x.conds]
      if enclosing_type != 'and':
        return '||'.join(res)
      return f'({"||".join(res)})'
    if x.type == 'and':
      res = [render(x, 'and') for x in x.conds]
      return f'{"&&".join(res)}'
    if x.type == 'macro':
      res = f'{"" if x.setto else "!"}${x.name}'
      if macro_state.get(x.name, False) == x.setto:
        return str(cf.bold(res))
      return res
    raise ValueError(f'Unknown cond type "{x.type}"')

  return f'[{render(x, None)}]'
