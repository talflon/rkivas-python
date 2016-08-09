# rkivas file backupper
# Copyright (C) 2016  Daniel Getz
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import hashlib
import os
import os.path
import shutil
from base64 import b32encode


def hash_file(digest, fp, buffer_size=4096):
    buf = bytearray(buffer_size)
    while True:
        bytes_read = fp.readinto(buf)
        if not bytes_read:
            return digest.digest()
        digest.update(buf[:bytes_read])


def encode_hash(hash_bytes, length):
    length_bits = length * 5
    length_bytes = length_bits // 8
    if length_bits % 8 != 0:
        length_bytes += 1
    return b32encode(hash_bytes[:length_bytes])[:length].lower()


class Archiver:

    def __init__(self, cfg):
        self.cfg = cfg

    def archive_all(self):
        for dir, source in self.cfg['sources'].items():
            for path in os.listdir(dir):
                if os.path.isfile(path):
                    self.archive_file(source, path)

    def archive_file(self, source, path):
        ext = self.get_ext(path)
        timestamp = self.get_timestamp(ext, path)
        if timestamp is not None:
            format_cfg = self.cfg['backup']
        else:
            format_cfg = self.cfg['backup-no-timestamp']
        hashed = self.get_hash(format_cfg, path)
        out_path = format_cfg['filename-format'].format(
            source=source, timestamp=timestamp, hash=hashed) + '.' + ext
        self.copy_to(path, out_path)

    def get_ext(self, path):
        ext = os.path.splitext(path)[1][1:]
        return self.cfg['extension-map'].get(ext, ext)

    def copy_to(self, path, out_path):
        if not os.path.lexists(out_path):
            dir = os.path.split(out_path)
            if not os.path.isdir(dir):
                os.makedirs(dir)
            shutil.copy2(path, out_path)

    def get_timestamp(self, ext, path):
        return None

    def get_hash(self, format_cfg, path):
        algorithm = format_cfg['hash-algorithm']
        length = format_cfg['hash-length']
        if algorithm == 'md5':
            digest = hashlib.md5
        elif algorithm == 'sha1':
            digest = hashlib.sha1
        elif algorithm == 'sha2':
            length_bits = length * 5
            for i in [224, 256, 384]:
                if i >= length_bits:
                    digest = getattr(hashlib, 'sha%i' % i)
                    break
            else:  # didn't break
                digest = hashlib.sha512
        else:
            raise ValueError('Invalid algorithm: %r' % algorithm)
        with open(path, 'rb') as f:
            return encode_hash(hash_file(digest(), f), length)
