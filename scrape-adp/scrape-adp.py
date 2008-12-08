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
# Crappy little scraper I wrote to download the pdf statements on ADP's
# website. Extracting the numbers out of the pdfs is another chore which I
# didn't make so much progress on. This could be used as an example scraper
# using cookies and BeautifulSoup.



# http://www.voidspace.org.uk/python/articles/authentication.shtml

import urllib
import urllib2
import urlparse
import cgi
import cookielib
import re
import optparse
import os.path
from BeautifulSoup import BeautifulSoup
from StringIO import StringIO


parser = optparse.OptionParser()
parser.add_option('-u', '--username', dest='username')
parser.add_option('-p', '--password', dest='password')

(options, args) = parser.parse_args()


passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
passman.add_password("iPay AG User", "https://ipay.adp.com/iPay/private/", options.username, options.password)
authhandler = urllib2.HTTPBasicAuthHandler(passman)
cj = cookielib.LWPCookieJar()
opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj), authhandler)
opener.addheaders = [("User-agent", "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9b4pre) Gecko/2008030305 Minefield/3.0b4pre")]


class LoggingOpener:
  def __init__(self, opener):
    self._opener = opener

  def open(self, req):
    if isinstance(req, basestring):
      req = urllib2.Request(req)
    print req.header_items()
    print req.get_data()
    try:
      resp = self._opener.open(req)
      content = resp.read()
      print resp.geturl()
      print resp.info().items()
      print content
      return StringIO(content)
    except urllib2.HTTPError, e:
      print "urllib2.HTTPError"
      print e
      print e.hdrs
      print e.filename
      print e.fp.read()
      raise


opener = LoggingOpener(opener)


def GetYearRequest(listDoc):
  """Return a list of Request objects."""
  soup = BeautifulSoup(listDoc.read())
  for yearnum in range(1, 10):
    atag = soup.find(attrs={"id": "statement:year%d" % yearnum})
    if atag is not None:
      print atag
      args = {"statement": "statement",
              "statement:changeStatementsType": "1",
              "statement:_idcl": "statement:year%d" % yearnum}
      yield urllib2.Request(url="https://ipay.adp.com/iPay/private/listDoc.jsf",
                            data=urllib.urlencode(args))
    else:
      print "year %d not found" % (yearnum)



def GetCheckRequest(year_list_req, year_list_resp):
  soup = BeautifulSoup(year_list_resp.read())
  yearnum_match = re.search(r"(year\d+)", year_list_req.get_data())
  yearnum = yearnum_match.group(1)
  for checknum in range(0, 40):
    atag = soup.find(attrs={"id": "statement:checks:%d:view" % checknum})
    if atag is not None:
      print atag
      args = {"statement:changeYear": yearnum,
              "statement:_idcl": "statement:checks:%d:view" % checknum,
              "statement": "statement"}
      yield urllib2.Request(url="https://ipay.adp.com/iPay/private/listDoc.jsf",
                            data=urllib.urlencode(args))
    else:
      print "%s check %d not found" % (yearnum, checknum)

def GetNewFilename(slashdate):
  date_m = re.match(r"(\d+)/(\d+)/(\d+)", slashdate)
  dashdate = "%s-%s-%s" % (date_m.group(3), date_m.group(1), date_m.group(2))
  filename = "%s.pdf" % (dashdate)
  if not os.path.exists(filename):
    return filename
  
  for i in "abcdefgh":
    filename = "%s.%s.pdf" % (dashdate, i)
    if not os.path.exists(filename):
      return filename
  raise Exception("Can't find unique name for %s" % dashdate)


# Login and set cookies
indexurl = "https://ipay.adp.com/iPay/private/index.jsf"
opener.open(indexurl).read()

#data="statement%3AchangeYear=year1&statement=statement&statement%3A_idcl="
url = "https://ipay.adp.com/iPay/private/listDoc.jsf"
req = urllib2.Request(url, headers={"Referer": "https://ipay.adp.com/iPay/private/listDoc.jsf"})
list_resp = opener.open(req)
for req in GetYearRequest(list_resp):
  year_list_resp = opener.open(req)
  for req in GetCheckRequest(req, year_list_resp):
    check_list_resp = opener.open(req)
    check_wrapper_soup = BeautifulSoup(check_list_resp.read())
    paydate_span = check_wrapper_soup.find(attrs={"class": "ADPUI-PageHead_Red"})
    if paydate_span is None:
      print "Couldn't find ADPUI-PageHead_Red"
      continue
    filename = GetNewFilename(paydate_span.string)
    iframe_tag = check_wrapper_soup.find(name="iframe")
    pdf_url = urlparse.urljoin(req.get_full_url(), iframe_tag['src'])
    pdf_resp = opener.open(pdf_url)
    pdf_parsed_query = cgi.parse_qs(urlparse.urlsplit(pdf_url)[3])
    open(filename, "w").write(pdf_resp.read())
