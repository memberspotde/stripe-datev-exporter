import json


def json_print(printable):
  print(json.dumps(printable, indent=4, sort_keys=True, default=str))


def print_json(printable):
  print(json.dumps(printable, indent=4, sort_keys=True, default=str))
