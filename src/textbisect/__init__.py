from io import SEEK_END


class TextBisector:
    def __init__(self, a, x, on_same, key):
        self.a = a
        self.x = x
        self.on_same = on_same
        self.key = key
        self.ref = key(x)

    def get_hi(self, hi):
        """Return hi, or the end position of the file if hi is None."""
        if hi is None:
            self.a.seek(0, SEEK_END)
            hi = self.a.tell() - 1
        return hi

    def get_beginning_of_line(self, pos, lo, hi):
        """Return the beginning of the line containing the position pos.
        On return the file is positioned at the return value."""
        while True:
            if pos == lo:
                return self.a.seek(pos)
            self.a.seek(pos - 1)
            char = self.a.read(1)
            if char == "\n":
                return pos
            pos -= 1

    def get_end_of_line(self, pos, lo, hi):
        """Return the end of the line (the line feed) containing the position
        pos.  On return the file is positioned at the return value."""
        self.a.seek(pos)
        while True:
            if pos > hi:
                raise EOFError("File must end in line feed")
            char = self.a.read(1)
            if char == "\n":
                return self.a.seek(pos)
            pos += 1

    def get_line(self, pos, lo, hi):
        """Return a tuple (line, start, end), where line is the line containing
        the position pos (without the ending line feed), and start and end are
        the positions of the start of the line and of the line feed.  On return
        the file is positioned at the beginning of the next line
        (i.e. end + 1)."""
        end = self.get_end_of_line(pos, lo, hi)
        start = self.get_beginning_of_line(pos, lo, hi)
        line = self.a.read(end - start)
        return (line, start, end)

    def bisect(self, lo, hi):
        # This recursive function ends when hi == lo - 1
        if hi == lo - 1:
            self.a.seek(lo)
            return lo

        # Otherwise, hi must not be less than lo
        assert hi >= lo

        # Bisect the space and decide which way to continue
        (line, start, end) = self.get_line((lo + hi) // 2, lo, hi)
        val = self.key(line)
        if (self.ref < val) or (self.ref == val and self.on_same == "left"):
            return self.bisect(lo, start - 1)
        else:
            return self.bisect(end + 1, hi)


def text_bisect_left(a, x, lo=0, hi=None, key=lambda x: x):
    bisector = TextBisector(a, x, "left", key)
    hi = bisector.get_hi(hi)
    return bisector.bisect(lo, hi)


def text_bisect_right(a, x, lo=0, hi=None, key=lambda x: x):
    bisector = TextBisector(a, x, "right", key)
    hi = bisector.get_hi(hi)
    return bisector.bisect(lo, hi)


text_bisect = text_bisect_right
