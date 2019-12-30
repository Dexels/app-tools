import os


class IndentedWriter(object):
    def __init__(self, path: os.PathLike, indent: int = 0):
        self.path = path
        self.indent = indent
        self.indentation = " " * indent

    def __enter__(self):
        self.fp = open(self.path, "w")

        return self

    def __exit__(self, *args):
        self.fp.close()

    def indented(self, indent: int = 4):
        writer = IndentedWriter(self.path, self.indent + indent)
        writer.fp = self.fp

        return writer

    def newline(self, count: int = 1):
        for _ in range(count):
            self.fp.write("\n")

    def writeln(self, text: str):
        self.fp.write(f"{self.indentation}{text}\n")

    def write(self, text: str):
        self.fp.write(f"{self.indentation}{text}")

    def appendln(self, text: str):
        self.append(text)
        self.newline()

    def append(self, text: str):
        self.fp.write(text)
