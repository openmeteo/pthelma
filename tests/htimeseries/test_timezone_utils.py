from __future__ import annotations

import datetime as dt
from unittest import TestCase

from htimeseries import TzinfoFromString


class TzinfoFromStringTestCase(TestCase):
    def test_simple(self) -> None:
        atzinfo = TzinfoFromString("+0130")
        self.assertEqual(atzinfo.offset, dt.timedelta(hours=1, minutes=30))

    def test_brackets(self) -> None:
        atzinfo = TzinfoFromString("DUMMY (+0240)")
        self.assertEqual(atzinfo.offset, dt.timedelta(hours=2, minutes=40))

    def test_brackets_with_utc(self) -> None:
        atzinfo = TzinfoFromString("DUMMY (UTC+0350)")
        self.assertEqual(atzinfo.offset, dt.timedelta(hours=3, minutes=50))

    def test_negative(self) -> None:
        atzinfo = TzinfoFromString("DUMMY (UTC-0420)")
        self.assertEqual(atzinfo.offset, -dt.timedelta(hours=4, minutes=20))

    def test_zero(self) -> None:
        atzinfo = TzinfoFromString("DUMMY (UTC-0000)")
        self.assertEqual(atzinfo.offset, dt.timedelta(hours=0, minutes=0))

    def test_wrong_input(self) -> None:
        for s in ("DUMMY (GMT+0350)", "0150", "+01500"):
            self.assertRaises(ValueError, TzinfoFromString, s)
