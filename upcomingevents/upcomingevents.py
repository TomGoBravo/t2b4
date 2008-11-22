#!/usr/bin/python2.5
#
#   Copyright 2008 Tom Brown
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
#
# To run this on your local machine fetch
# the latest gdata Python library from
# http://code.google.com/p/gdata-python-client/ and create symlinks similar to
# these in this directory:
# atom -> /usr/local/src/gdata.py-1.2.2/src/atom
# gdata -> /usr/local/src/gdata.py-1.2.2/src/gdata
# See this post and comments:
# http://googledataapis.blogspot.com/2008/04/release-hounds-support-for-app-engine.html
#
# You also need the appengine SDK:
# http://code.google.com/appengine/downloads.html
#
# Then change into this directory and run
# /usr/local/src/google_appengine/dev_appserver.py


import gdata.calendar.service
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from datetime import date
from datetime import timedelta
import re

import gdata.urlfetch
# Use urlfetch instead of httplib
# http://googledataapis.blogspot.com/2008/04/release-hounds-support-for-app-engine.html
gdata.service.http_request_handler = gdata.urlfetch


def GetCalendarService():
  return gdata.calendar.service.CalendarService()


def IsoToDate(iso_format):
  m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", iso_format)
  if not m:
    raise ValueError("all day events only")
  return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))


def FormatDateRange(start_date, end_date):
  """Return pretty version of range of dates."""
  if start_date == end_date:
    return "%s %d" % (
        start_date.strftime("%a, %B"),
        start_date.month)  # no strftime for day of month without zero padding
  elif start_date.month == end_date.month:
    return "%s - %s, %s %d - %d" % (
        start_date.strftime("%a"),
        end_date.strftime("%a"),
        start_date.strftime("%B"),
        start_date.day,  # no strftime for day of month without zero padding
        end_date.day)
  else:
    return "%s -%s, %s %d - %s %d" % (
        start_date.strftime("%a"),
        end_date.strftime("%a"),
        start_date.strftime("%B"),
        start_date.month,  # no strftime for day of month without zero padding
        end_date.strftime("%B"),
        end_date.month)  # no strftime for day of month without zero padding


def EventStartEnd(calendar_service, cal, start_date, end_date, max_results=None):
  """Return list of Events"""
  query = gdata.calendar.service.CalendarEventQuery(cal, 'public', 'full')
  query.start_min = start_date.isoformat()
  query.start_max = end_date.isoformat()
  query.orderby = 'starttime'
  query.sortorder = 'ascend'
  if max_results:
    query.max_results = max_results
  feed = calendar_service.CalendarQuery(query)
  rv = []
  for i, an_event in enumerate(feed.entry):
    for a_when in an_event.when:
      try:
        start_time = IsoToDate(a_when.start_time)
        # Subtract one from the end date
        # http://groups.google.com/group/google-calendar-help-dataapi/browse_thread/thread/60f83f8eedac5485
        end_time = IsoToDate(a_when.end_time) - timedelta(days=1)
        rv.append(Event(title=an_event.title.text, start_date=start_time,
                        end_date=end_time, url=an_event.GetHtmlLink().href))
      except ValueError:
        pass  # Don't handle non-allday events
  return rv


class Event(object):
  def __init__(self, **kwargs):
    self.__dict__.update(kwargs)

  def __getitem__(self, key):
    if key in self.__dict__:
      return self.__dict__[key]
    if key == "dates":
      return FormatDateRange(self.start_date, self.end_date)


def FormatHtml(events):
  rv = []
  rv.append('<div class="rss-box">')
  rv.append('<ul class="rss-items">')
  for event in events:
    rv.append('<li class="rss-item">'
              '%(dates)s<br />'
              '<a class="rss-item" href="%(url)s" target="_self">%(title)s'
              '</a><br />' % event)
    rv.append('</li>')
  rv.append('</ul></div>')
  return rv


def FormatText(events):
  rv = []
  for event in events:
    rv.append(event["dates"])
    rv.append("  " + event["title"])
  return rv


def JsEscape(html):
  return re.sub(r"""(['"\\])""", r"""\\\1""", html)


def FormatJs(events):
  rv = []
  for html_line in FormatHtml(events):
    rv.append('document.write(\'' + JsEscape(html_line) + '\');')
  return rv


def PrintJs(events):
  print 'Content-Type: application/x-javascript'
  print ''
  for line in FormatJs(events):
    print line


class WebInterface(webapp.RequestHandler):
  def get(self):
    src = self.request.get("src")
    if not re.match(r"^\w{1,50}@[\w.]{0,50}\.google\.com$", src):
      raise ValueError("Invalid src")
    output = self.request.get("output", "js")
    if not re.match(r"^text|js$", output):
      raise ValueError("Invalid output")
    max_future_days = int(self.request.get("max-future-days", 90))
    max_results = int(self.request.get("max-results", 5))

    calendar_service = GetCalendarService()
    events = EventStartEnd(calendar_service,
                           src, date.today(),
                           date.today() + timedelta(days=max_future_days),
                           max_results)

    if output == "js":
      self.response.headers["Content-Type"] = "application/x-javascript"
      self.response.out.write("\n".join(FormatJs(events)))
    else:
      self.response.headers["Content-Type"] = "text/plain"
      self.response.out.write("\n".join(FormatText(events)))


application = webapp.WSGIApplication([('/upcomingevents', WebInterface)], debug=True)

def main():
  run_wsgi_app(application)

  #calendar_service = GetCalendarService()
  #events = EventStartEnd(calendar_service, "pt4s3b5b4ls13c6t9fjmm281no@group.calendar.google.com",
  #               date.today(), date.today() + timedelta(days=90))

  #PrintText(events)


if __name__ == '__main__':
  try:
    import traceplus
    traceplus.RunWithExpandedTrace(main)
  except ImportError:
    main()
