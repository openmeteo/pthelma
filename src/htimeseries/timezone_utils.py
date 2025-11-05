from __future__ import annotations

import datetime as dt
from typing import Optional


class TzinfoFromString(dt.tzinfo):
    def __init__(self, string: Optional[str]) -> None:
        self.offset: Optional[dt.timedelta] = None
        self.name = ""
        if not string:
            return

        # If string contains brackets, set tzname to whatever is before the
        # brackets and retrieve the part inside the brackets.
        i = string.find("(")
        if i > 0:
            self.name = string[:i].strip()
        start = i + 1
        s = string[start:]
        i = s.find(")")
        i = len(s) if i < 0 else i
        s = s[:i]

        # Remove any preceeding 'UTC' (as in "UTC+0200")
        s = s[3:] if s.startswith("UTC") else s

        # s should be in +0000 format
        try:
            if len(s) != 5:
                raise ValueError()
            sign = {"+": 1, "-": -1}[s[0]]
            hours = int(s[1:3])
            minutes = int(s[3:5])
        except (ValueError, IndexError):
            raise ValueError("Time zone {} is invalid".format(string))

        self.offset = sign * dt.timedelta(hours=hours, minutes=minutes)

    def utcoffset(self, adatetime: Optional[dt.datetime]) -> Optional[dt.timedelta]:
        return self.offset

    def dst(self, adatetime: Optional[dt.datetime]) -> dt.timedelta:
        return dt.timedelta(0)

    def tzname(self, adatetime: Optional[dt.datetime]) -> str:
        return self.name
