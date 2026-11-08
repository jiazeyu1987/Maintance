"""Bounded readiness for one already verified control process and one GET."""
import errno
import json
import time
import urllib.error


def wait_http_json(opener,request,verify_process,validate,*,timeout=15):
    if not (0<timeout<=15):
        raise ValueError('CONTROL_HTTP_READINESS_BUDGET_INVALID')
    deadline=time.monotonic()+timeout
    while True:
        verify_process()
        remaining=deadline-time.monotonic()
        if remaining<=0:
            raise ValueError('CONTROL_HTTP_NOT_READY')
        try:
            with opener.open(request,timeout=min(remaining,5)) as response:
                if response.status!=200:
                    raise ValueError('CONTROL_HTTP_UNEXPECTED_STATUS')
                value=json.load(response)
            verify_process()
            validate(value)
            return value
        except urllib.error.URLError as error:
            # HTTPError is also URLError: only an actual refused connection to
            # this exact process's socket is eligible for startup waiting.
            reason=error.reason
            if isinstance(error,urllib.error.HTTPError) or not isinstance(reason,OSError) or reason.errno not in (errno.ECONNREFUSED,10061):
                raise
            remaining=deadline-time.monotonic()
            if remaining<=0:
                raise ValueError('CONTROL_HTTP_NOT_READY') from error
            time.sleep(min(.1,remaining))
