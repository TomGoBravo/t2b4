#!/usr/bin/python2.5

# Example use:
# def main():
#   ...
#
# if __name__ == '__main__':
#   try:
#     import traceplus
#   except ImportError:
#     main()
#   else:
#     traceplus.RunWithExpandedTrace(main)


def MakeExpandedTrace(frame_records):
  """Return a list of text lines for the given list of frame records."""
  dump = []
  for (frame_obj, filename, line_num, fun_name, context_lines,
       context_index) in frame_records:
    dump.append('File "%s", line %d, in %s\n' % (filename, line_num,
                                                 fun_name))
    if context_lines:
      for (i, line) in enumerate(context_lines):
        if i == context_index:
          dump.append(' --> %s' % line)
        else:
          dump.append('     %s' % line)
    for local_name, local_val in frame_obj.f_locals.items():
      try:
        truncated_val = repr(local_val)[0:500]
      except Exception, e:
        dump.append('    Exception in str(%s): %s\n' % (local_name, e))
      else:
        if len(truncated_val) >= 500:
          truncated_val = '%s...' % truncated_val[0:499]
        dump.append('    %s = %s\n' % (local_name, truncated_val))
    dump.append('\n')
  return dump


def RunWithExpandedTrace(closure):
  try:
    return closure()
  except (SystemExit, KeyboardInterrupt):
    raise
  except:
    import inspect
    import sys
    import traceback

    # Save trace and exception now. This call looks at the most recently
    # raised exception. The code that makes the report might trigger other
    # exceptions.
    exc_type, exc_value, tb = sys.exc_info()
    frame_records = inspect.getinnerframes(tb, 3)[1:]
    formatted_exception = traceback.format_exception_only(exc_type, exc_value)

    dashes = '%s\n' % ('-' * 60)
    dump = []
    dump.append(dashes)
    dump.extend(MakeExpandedTrace(frame_records))


    dump.append(''.join(formatted_exception))

    print ''.join(dump)
    print
    print dashes
    sys.exit(127)
