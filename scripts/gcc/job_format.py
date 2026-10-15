"""Encode and inspect GCCJOB1 with the CCFILES1 filesystem envelope."""
import struct

MAX_JOB = 16*1024*1024


def _path(name, root=False):
    data = name.encode()
    if (len(data) > 4096 or b'\0' in data or name.startswith('/') or
            (not name and not root) or (name and any(p in ('', '.', '..') for p in name.split('/')))):
        raise ValueError('invalid guest path: '+repr(name))
    return data


def pack_job(argv, files):
    if not 1 <= len(argv) <= 256 or not 1 <= len(files) <= 1024:
        raise ValueError('invalid argument or file count')
    arguments = []
    for i, arg in enumerate(argv):
        data = arg.encode()
        if len(data) > 4096 or b'\0' in data or (not i and not data):
            raise ValueError('invalid guest argument')
        arguments.append(struct.pack('<I', len(data))+data)
    roots = sorted({name.rsplit('/', 1)[0] for name in files if '/' in name})
    if len(roots) > 32:
        raise ValueError('too many guest include roots')
    payload = b'\0CCFILES1'+struct.pack('<III', len(files), 0, len(roots))
    for root in roots:
        data = _path(root, True)
        payload += struct.pack('<I', len(data))+data
    for name, data in files.items():
        name = _path(name)
        if len(data) > MAX_JOB:
            raise ValueError('guest file exceeds job limit')
        payload += struct.pack('<II', len(name), len(data))+name+data
    result = b'GCCJOB1\0'+struct.pack('<II', len(argv), len(payload))+b''.join(arguments)+payload
    if len(result) > MAX_JOB:
        raise ValueError('guest job exceeds 16 MiB')
    return result


def unpack_job(data):
    class Reader:
        def __init__(self, blob):
            self.blob, self.at = blob, 0
        def take(self, n):
            if n < 0 or n > len(self.blob)-self.at:
                raise ValueError('truncated guest job')
            result = self.blob[self.at:self.at+n]
            self.at += n
            return result
        def word(self):
            return struct.unpack('<I', self.take(4))[0]
    if not 16 <= len(data) <= MAX_JOB:
        raise ValueError('invalid guest job size')
    r = Reader(data)
    if r.take(8) != b'GCCJOB1\0':
        raise ValueError('invalid GCCJOB1 magic')
    count, size = r.word(), r.word()
    if not 1 <= count <= 256:
        raise ValueError('invalid guest argument count')
    argv = []
    for i in range(count):
        n = r.word()
        if n > 4096 or (not i and not n):
            raise ValueError('invalid guest argument length')
        arg = r.take(n)
        if b'\0' in arg:
            raise ValueError('NUL in guest argument')
        argv.append(arg.decode())
    fs = Reader(r.take(size))
    if r.at != len(data) or fs.take(9) != b'\0CCFILES1':
        raise ValueError('invalid guest filesystem envelope')
    count, primary, roots = fs.word(), fs.word(), fs.word()
    if not 1 <= count <= 1024 or primary >= count or roots > 32:
        raise ValueError('invalid guest filesystem counts')
    for _ in range(roots):
        _path(fs.take(fs.word()).decode(), True)
    files = {}
    for _ in range(count):
        length, n = fs.word(), fs.word()
        name = fs.take(length).decode()
        _path(name)
        if name in files:
            raise ValueError('duplicate guest file')
        files[name] = fs.take(n)
    if fs.at != len(fs.blob):
        raise ValueError('trailing guest filesystem data')
    return argv, files
