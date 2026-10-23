"""Explicit NAS authentication; never use stored Windows credentials implicitly."""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path, PureWindowsPath


def connection_parameters(nas_path, credentials_file):
    path = PureWindowsPath(nas_path)
    parts = path.drive.split('\\')
    if len(parts) != 4 or parts[:2] != ['', ''] or not all(parts[2:]):
        raise ValueError('NAS destination must be an explicit UNC share path')
    if '..' in path.parts:
        raise ValueError('NAS destination must not contain parent traversal')
    if not credentials_file or not Path(credentials_file).is_absolute():
        raise ValueError('An absolute private NAS credentials file is required')
    credentials = json.loads(Path(credentials_file).read_text('utf-8-sig'))
    server, share = parts[2:]
    if (credentials.get('server', '').casefold(), credentials.get('share', '').casefold()) != (server.casefold(), share.casefold()):
        raise ValueError('NAS credentials are not bound to the configured server/share')
    if not all(isinstance(credentials.get(key), str) and credentials[key] for key in ('username', 'password')):
        raise ValueError('NAS username and password are required in the private credentials file')
    username = credentials['username']
    domain = credentials.get('domain', '')
    if domain:
        if '\\' in username or '@' in username:
            raise ValueError('Use a plain NAS username when a separate domain is configured')
        username = domain+'\\'+username
    return '\\\\'+server+'\\'+share, username, credentials['password']


def connect_nas(nas_path, credentials_file):
    """Authenticate without an interactive prompt or persisted Windows password.

    A conflicting existing SMB identity fails; no unrelated connection is removed.
    Windows establishes the SMB session, using credentials supplied on every call.
    """
    remote, username, password = connection_parameters(nas_path, credentials_file)
    if os.name != 'nt':
        raise RuntimeError('This NAS publisher requires the configured Windows executor')

    class NetResource(ctypes.Structure):
        _fields_ = [('scope', wintypes.DWORD), ('type', wintypes.DWORD),
                    ('displayType', wintypes.DWORD), ('usage', wintypes.DWORD),
                    ('localName', wintypes.LPWSTR), ('remoteName', wintypes.LPWSTR),
                    ('comment', wintypes.LPWSTR), ('provider', wintypes.LPWSTR)]

    resource = NetResource(type=1, remoteName=remote)
    connect = ctypes.WinDLL('mpr', use_last_error=True).WNetAddConnection2W
    connect.argtypes = [ctypes.POINTER(NetResource), wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD]
    connect.restype = wintypes.DWORD
    # CONNECT_TEMPORARY: do not persist the password or map a drive letter.
    code = connect(ctypes.byref(resource), password, username, 4)
    if code:
        detail = 'existing SMB identity conflicts; no connection was removed' if code == 1219 else 'explicit NAS authentication failed'
        raise RuntimeError('NAS connection error '+str(code)+': '+detail)
    # The application release root can be created by the first publication.
    if not Path(remote).is_dir():
        raise RuntimeError('Authenticated NAS share is unavailable')
    return remote
