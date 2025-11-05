import textwrap
from io import StringIO
from typing import Any, Union
from unittest import TestCase

from textbisect import text_bisect, text_bisect_left, text_bisect_right

testtext = textwrap.dedent(
    """\
    alpha
    bravo
    charlie
    delta
    echo
    foxtrot
    golf
    hotel
    india
    juillet
    kilo
    lima
    mike
    november
    oscar
    papa
    quebec
    romeo
    sierra
    tango
    uniform
    victor
    whiskey
    x-ray
    yankee
    zulu
    """
)

# These are the positions in which each of the line of the above string start:
#
# alpha    0
# bravo    6
# charlie  12
# delta    20
# echo     26
# foxtrot  31
# golf     39
# hotel    44
# india    50
# juillet  56
# kilo     64
# lima     69
# mike     74
# november 79
# oscar    88
# papa     94
# quebec   99
# romeo    106
# sierra   112
# tango    119
# uniform  125
# victor   133
# whiskey  140
# x-ray    148
# yankee   154
# zulu     161
#          166 (length of file, or position of next character to be appended)


testtext2 = textwrap.dedent(
    """\
    1
    003
    fivey
    seven07
    ninenine9
    eleven00011
    """
)

# These are the positions in which each of the line of the above string start:
#
# 1           0
# 003         2
# fivey       6
# seven07     12
# ninenine9   20
# eleven00011 30
#             42 (length of file, or position of next character to be appended)


class TextBisectTestCaseBase(TestCase):
    f: StringIO

    @staticmethod
    def KEY(x: str) -> str:
        return x

    def _do_test(
        self,
        search_term: str,
        expected_result: int,
        direction: str = "",
        lo: int = 0,
        hi: Union[int, None] = None,
    ):
        function = {
            "left": text_bisect_left,
            "right": text_bisect_right,
            "": text_bisect,
        }[direction]
        pos = function(self.f, search_term, lo=lo, hi=hi, key=self.__class__.KEY)
        self.assertEqual(pos, expected_result)
        self.assertEqual(pos, self.f.tell())


IRRELEVANT = -1


class TextBisectWithoutKeyTestCase(TextBisectTestCaseBase):
    @staticmethod
    def KEY(x: str) -> Any:
        return x

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.f = StringIO(testtext)

    def test_beginning_of_file(self):
        self._do_test("alice", 0)

    def test_end_of_file(self):
        self._do_test("zuzu", 166)

    def test_somewhere_in_file(self):
        self._do_test("somewhere", 119)

    def test_bisect_left(self):
        self._do_test("lima", 69, direction="left")

    def test_bisect_right(self):
        self._do_test("lima", 74, direction="right")

    def test_in_file_part_for_something_in_the_beginning_of_that_part(self):
        self._do_test("bob", 106, lo=106)

    def test_when_file_part_starts_in_middle_of_line_and_result_starts_before(self):
        self._do_test("bob", 108, lo=108)

    def test_when_file_part_starts_in_middle_of_line(self):
        self._do_test("nick", 112, lo=108)

    def test_when_file_part_starts_in_end_of_line(self):
        self._do_test("bob", 112, lo=111)

    def test_when_file_part_starts_at_end_of_file(self):
        self._do_test("bob", 166, lo=166)

    def test_when_file_part_starts_at_last_character_of_file(self):
        self._do_test("bob", 166, lo=165)

    def test_in_file_part_for_something_after_end_of_that_part(self):
        self._do_test("nick", 74, hi=73)

    def test_when_file_part_ends_in_middle_of_line(self):
        with self.assertRaises(EOFError):
            self._do_test("nick", IRRELEVANT, hi=71)

    def test_searching_in_file_part_specified_by_both_lo_and_hi(self):
        self._do_test("nick", 79, lo=64, hi=93)

    def test_beginning_of_file_part_specified_by_both_lo_and_hi(self):
        self._do_test("george", 64, lo=64, hi=93)

    def test_end_of_file_part_specified_by_both_lo_and_hi(self):
        self._do_test("tango", 94, lo=64, hi=93)

    def test_bisect_left_at_beginning_of_file_part_specified_by_both_lo_and_hi(self):
        self._do_test("kilo", 64, direction="left", lo=64, hi=93)

    def test_bisect_right_at_beginning_of_file_part_specified_by_both_lo_and_hi(self):
        self._do_test("kilo", 69, direction="right", lo=64, hi=93)

    def test_bisect_left_at_middle_of_file_part_specified_by_both_lo_and_hi(self):
        self._do_test("oscar", 88, direction="left", lo=64, hi=93)

    def test_bisect_right_at_middle_of_file_part_specified_by_both_lo_and_hi(self):
        self._do_test("oscar", 94, direction="right", lo=64, hi=93)

    def test_bisect_right_at_end_of_file_part_specified_by_both_lo_and_hi(self):
        self._do_test("papa", 94, direction="right", lo=64, hi=93)


class TextBisectWithKeyTestCase(TextBisectTestCaseBase):
    @staticmethod
    def KEY(x: str) -> Any:
        return len(x)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.f = StringIO(testtext2)

    def test_beginning_of_file(self):
        self._do_test("", 0)

    def test_end_of_file(self):
        self._do_test("twelvetwelve", 42)

    def test_somewhere_in_file(self):
        self._do_test("sixsix", 12)

    def test_bisect_left(self):
        self._do_test("fiver", 6, direction="left")

    def test_bisect_right(self):
        self._do_test("fiver", 12, direction="right")

    def test_in_file_part_for_something_in_the_beginning_of_that_part(self):
        self._do_test("02", 12, lo=12)

    def test_when_file_part_starts_in_middle_of_line_and_result_starts_before(self):
        self._do_test("02", 8, lo=8)

    def test_when_file_part_starts_in_middle_of_line(self):
        self._do_test("four", 12, lo=8)

    def test_when_file_part_starts_in_end_of_line(self):
        self._do_test("02", 6, lo=5)

    def test_when_file_part_starts_at_end_of_file(self):
        self._do_test("any", 42, lo=41)

    def test_when_file_part_starts_at_last_character_of_file(self):
        self._do_test("any", 42, lo=40)

    def test_in_file_part_for_something_after_end_of_that_part(self):
        self._do_test("ten=ten=10", 12, hi=11)

    def test_when_file_part_ends_in_middle_of_line(self):
        with self.assertRaises(EOFError):
            self._do_test("eleven=0011", IRRELEVANT, hi=32)

    def test_beginning_of_file_part_specified_by_both_lo_and_hi(self):
        self._do_test("four", 6, lo=6, hi=29)

    def test_searching_in_file_part_specified_by_both_lo_and_hi(self):
        self._do_test("eight008", 20, lo=6, hi=29)

    def test_end_of_file_part_specified_by_both_lo_and_hi(self):
        self._do_test("twelvetwelve", 30, lo=6, hi=29)

    def test_bisect_left_at_beginning_of_file_part_specified_by_both_lo_and_hi(self):
        self._do_test("fiver", 6, direction="left", lo=6, hi=29)

    def test_bisect_right_at_beginning_of_file_part_specified_by_both_lo_and_hi(self):
        self._do_test("fiver", 12, direction="right", lo=6, hi=29)

    def test_bisect_left_at_middle_of_file_part_specified_by_both_lo_and_hi(self):
        self._do_test("nine=nine", 20, direction="left", lo=6, hi=29)

    def test_bisect_right_at_middle_of_file_part_specified_by_both_lo_and_hi(self):
        self._do_test("nine=nine", 30, direction="right", lo=6, hi=29)

    def test_bisect_right_at_end_of_file_part_specified_by_both_lo_and_hi(self):
        self._do_test("twelvetwelve", 30, direction="right", lo=6, hi=29)


class TextBisectOnlyOneLineTestCase(TextBisectTestCaseBase):
    @staticmethod
    def KEY(x: str) -> str:
        return x

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.f = StringIO("bravo\n")

    def test_before(self):
        self._do_test("alpha", 0)

    def test_after(self):
        self._do_test("charlie", 6)

    def test_left(self):
        self._do_test("bravo", 0, direction="left")

    def test_right(self):
        self._do_test("bravo", 6, direction="right")
