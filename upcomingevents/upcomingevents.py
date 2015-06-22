#!/usr/bin/python2.7
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
# https://github.com/google/gdata-python-client and create symlinks similar to
# these in this directory:
# atom -> gdata-python-client/src/atom
# gdata -> gdata-python-client/src/gdata
#
# You also need the appengine SDK:
# http://code.google.com/appengine/downloads.html
#
# The dev_appserver doesn't have an API key for server applications
# so it can't run this application. Instead run it locally
# in a console by getting the key for public access from
# https://console.developers.google.com/project/tombapps/apiui/credential and
# then run
# PYTHONPATH=../traceplus:~/Downloads/google_appengine:~/Downloads/google_appengine/lib/webob-1.2.3 ./upcomingevents.py <key>
#
# To run on appengine remotely
# mkdir lib
# pip install -t lib  google-api-python-client
# PYTHONPATH=~/Downloads/google_appengine/lib/oauth2client ~/Downloads/google_appengine/appcfg.py -A tombapps-hdr update .


from apiclient.discovery import build
from google.appengine.api import memcache
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta
from oauth2client.appengine import AppAssertionCredentials
import httplib2
import re
import sys



def GetCalendarService(developerKey=None):
  if developerKey:
    return build('calendar', 'v3', developerKey=developerKey)
  else:
    credentials = AppAssertionCredentials(scope='https://www.googleapis.com/auth/calendar.readonly')
    http = credentials.authorize(httplib2.Http(memcache))
    return build('calendar', 'v3', http=http)


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
        start_date.day)  # no strftime for day of month without zero padding
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
        start_date.day,  # no strftime for day of month without zero padding
        end_date.strftime("%B"),
        end_date.day)  # no strftime for day of month without zero padding


def EventStartEnd(calendar_service, cal, max_future_days, max_results=None):
  """Return list of Events"""
  # The Calendar API v3 seems to return a "400 Bad Request" error if timeMin or
  # timeMax don't include a timezone offset. Because it is okay to show events
  # which recently passed I'll simply append 'Z' for UTC time and start display
  # at yesterday so an event on date X in the US remains when the UTC date is
  # X + 1 day. See:
  # http://stackoverflow.com/questions/17133777/google-calendar-api-400-error
  # https://code.google.com/p/google-apis-explorer/issues/detail?id=24
  # https://developers.google.com/google-apps/calendar/quickstart/python
  start_date = datetime.combine(date.today() - timedelta(days=1), time.min)
  end_date = datetime.combine(date.today() + timedelta(days=max_future_days), time.min)
  events = calendar_service.events().list(
      calendarId=cal,
      singleEvents=True,  # Needed for orderBy
      orderBy='startTime',
      maxResults=max_results,
      timeMin=start_date.isoformat() + 'Z',
      timeMax=end_date.isoformat() + 'Z'
      ).execute()
  rv = []
  for i, an_event in enumerate(events['items']):
    if 'dateTime' in an_event['start']:
      continue
    try:
      start_time = IsoToDate(an_event['start']['date'])
      # End date is exclusive according to
      # https://developers.google.com/google-apps/calendar/v3/reference/events
      end_time = IsoToDate(an_event['end']['date']) - timedelta(days=1)
      rv.append(Event(title=an_event['summary'], start_date=start_time,
                      end_date=end_time, url=an_event['htmlLink']))
    except ValueError:
      pass  # Don't handle non-allday events
    except AttributeError:
      pass  # Don't handle baddly formed events
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


class WebInterface(webapp.RequestHandler):
  def get(self):
    src = self.request.get("src")
    if not re.match(r"^\w{1,50}@[\w.]{0,50}\.google\.com$", src):
      raise ValueError("Invalid src")
    output = self.request.get("output", "js")
    if not re.match(r"^text|js$", output):
      raise ValueError("Invalid output")
    max_future_days = int(self.request.get("max-future-days", 210))
    max_results = int(self.request.get("max-results", 5))

    calendar_service = GetCalendarService()
    events = EventStartEnd(calendar_service,
                           src, max_future_days,
                           max_results)

    if output == "js":
      self.response.headers["Content-Type"] = "application/x-javascript"
      self.response.out.write("\n".join(FormatJs(events)))
    else:
      self.response.headers["Content-Type"] = "text/plain"
      self.response.out.write("\n".join(FormatText(events)))


app = webapp.WSGIApplication([('/upcomingevents', WebInterface)], debug=True)

def main():
  if len(sys.argv) == 2:
    calendar_service = GetCalendarService(sys.argv[1])
    events = EventStartEnd(calendar_service, "pt4s3b5b4ls13c6t9fjmm281no@group.calendar.google.com",
                   210)

    print "\n".join(FormatText(events))
  else:
    run_wsgi_app(app)



if __name__ == '__main__':
  try:
    import traceplus
    traceplus.RunWithExpandedTrace(main)
  except ImportError:
    main()
