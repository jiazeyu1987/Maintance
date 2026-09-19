import platform


def _disable_broken_wmi_query(*_args, **_kwargs):
    raise OSError("WMI query disabled for release verifier process")


platform._wmi_query = _disable_broken_wmi_query
