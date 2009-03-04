#!/usr/bin/python

# Hacky little script to format names into a html page
# Source data at http://spreadsheets.google.com/feeds/download/spreadsheets/Export?fmcmd=5&gid=0&key=pYkXq3sEXIK3fIX_TWz1FNQ&pli=1

import csv
import collections
import re
import datetime

def GetRows(f):
  clublist = collections.defaultdict(list)

  # Skip to row that looks like header
  lines = []
  in_table = False
  for l in f:
    if re.search(r"Name", l):
      in_table = True
    if re.search(r"^\[", l):
      # Start of footnotes
      in_table = False
    if in_table:
      lines.append(l)
  
  reader = csv.DictReader(lines)
  rows = []
  for row in reader:
    row["Name"] = re.sub(r" (\w)\w+$", r" \1", row["Name"])
    for k, v in row.items():
      if v is None:
        row[k] = ""
    for k, v in row.items():
      row[k.replace(" ", "_")] = v
    rows.append(row)
  return rows


def main_html():
  from django.conf import settings
  settings.configure(DEBUG=True, TEMPLATE_DEBUG=True, TEMPLATE_DIRS=())
  from django.template import Context, Template

  rows = GetRows(open("Tournament 2009.csv"))
  t = Template(open("tourney_names_2009.cst").read())
  c = Context({"row_list": rows, "now": datetime.datetime.now()})
  print t.render(c)


def main_text():
  clublist = GetClubList(open("Tournament 2009.csv"))
  for club in sorted(clublist.keys()):
    players = []
    for name, waiver, dues in sorted(clublist[club]):
      w = waiver and "W" or ""
      d = dues and "D" or ""
      players.append("%s (%s%s)" % (name, w, d))
    print "%s: %s" % (club, ", ".join(players))

def main():
  main_html()

if __name__ == '__main__':
  try:
    import traceplus
    traceplus.RunWithExpandedTrace(main)
  except ImportError:
    main()
