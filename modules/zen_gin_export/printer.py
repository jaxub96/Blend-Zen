"""Output sinks for the archive writer: anything with a print(*parts)
method that receives one line per call (no trailing newline)."""

import os


class Printer:
    def print(self, *content):
        pass


class ConsolePrinter(Printer):
    def print(self, *content):
        print(*content, sep="")


class FilePrinter(Printer):
    """Collects lines in memory and writes them on close().

    Nothing touches the disk until close(), and the file is written to a
    temporary sibling and then moved into place, so a failed export never
    leaves a truncated .ZEN behind (or clobbers the previous good one).
    As a context manager it writes only if the block raised nothing.
    """

    def __init__(self, filepath, encoding="windows-1250"):
        self._filepath = filepath
        self._encoding = encoding
        self._lines = []
        self._closed = False

    def print(self, *content):
        self._lines.append("".join(content))

    def close(self):
        if self._closed:
            return
        self._closed = True
        text = "\n".join(self._lines) + "\n"
        tmp_path = f"{self._filepath}.tmp"
        try:
            with open(tmp_path, "w", encoding=self._encoding, newline="\n") as f:
                f.write(text)
            os.replace(tmp_path, self._filepath)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            self.close()
        else:
            self._closed = True
        return False
