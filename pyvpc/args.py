from argparse import ArgumentParser

def add_common_arguments(parser):
  parser.add_argument(
    '--log-includes',
    action='store_true',
    default=False)
  parser.add_argument(
    '--debug',
    action='store_true',
    default=False)

parser = ArgumentParser()
add_common_arguments(parser)
subparser = parser.add_subparsers()

build_parser = subparser.add_parser('build')
add_common_arguments(build_parser)
build_parser.add_argument(
  'group',
  type=str,
  nargs='?') # TODO(maximsmol): support building many groups?
 # TODO(maximsmol): support building single projects?
build_parser.add_argument(
  '-D',
  '--define',
  action='append',
  type=str,
  default=[])


dump_parser = subparser.add_parser('dump')
add_common_arguments(dump_parser)
dump_subparser = dump_parser.add_subparsers()

dump_group_parser = dump_subparser.add_parser('group')
add_common_arguments(dump_group_parser)
dump_group_parser.add_argument(
  'group',
  type=str,
  nargs='?') # TODO(maximsmol): support dumping many groups?

dump_project_parser = dump_subparser.add_parser('project')
add_common_arguments(dump_project_parser)
dump_project_parser.add_argument(
  'project',
  type=str,
  nargs='?') # TODO(maximsmol): support dumping many projects?
dump_project_parser.add_argument(
  '-D',
  '--define',
  action='append',
  type=str,
  default=[])

dump_project_manifest_parser = dump_subparser.add_parser('project-manifest')
add_common_arguments(dump_project_manifest_parser)
dump_project_manifest_parser.add_argument(
  'project',
  type=str,
  nargs='?') # TODO(maximsmol): support dumping many projects' manifests?
dump_project_manifest_parser.add_argument(
  '-D',
  '--define',
  action='append',
  type=str,
  default=[])
