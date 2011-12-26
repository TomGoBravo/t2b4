#!/usr/bin/python2.5

# Includes locals in the stacktrace when a failure occurs.
#
# Example use:
#
# if __name__ == '__main__':
#   try:
#     import traceplusunittest
#   except ImportError:
#     unittest.main()
#   else:
#     traceplusunittest.main()

import unittest
import traceplus
import traceback
import inspect


class TextBigStackTestRunner(unittest.TextTestRunner):
  def _makeResult(self):
    return TextBigStackTestResult(self.stream, self.descriptions, self.verbosity)


class TextBigStackTestResult(unittest._TextTestResult):
  def _exc_info_to_string(self, err, test):
    """Converts a sys.exc_info()-style tuple of values into a string."""
    exctype, value, tb = err
    # Skip test runner traceback levels
    while tb and self._is_relevant_tb_level(tb):
      tb = tb.tb_next
    if exctype is test.failureException:
      # Skip assert*() traceback levels
      length = self._count_relevant_tb_levels(tb)
      return ''.join(FormatException(exctype, value, tb, length))
    return ''.join(FormatException(exctype, value, tb))


def FormatException(exctype, value, tb, length=None):
  frame_records = inspect.getinnerframes(tb, 3)

  dump = []
  if length is None:
    dump.extend(traceplus.MakeExpandedTrace(frame_records))
  else:
    dump.extend(traceplus.MakeExpandedTrace(frame_records[:length]))
  dump.extend(traceback.format_exception_only(exctype, value))
  return ''.join(dump)


def main():
  unittest.main(testRunner=TextBigStackTestRunner())

