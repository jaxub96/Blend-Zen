from .printer import Printer


class FilePrinter(Printer):
    __content = ""

    def __init__(self, filepath):
        self.__filepath = filepath
        self.__closed = False

    def __del__(self):
        # kept for backward compatibility with existing scripts that rely
        # on garbage collection to flush - prefer calling close() explicitly
        self.close()

    def close(self):
        if self.__closed:
            return
        with open(self.__filepath, mode='w', encoding="windows-1250") as file:
            print(self.__content, end="", file=file)
        self.__closed = True

    def print(self, *content):
        for content_part in content:
            self.__content = self.__content + content_part
        self.__content = self.__content + "\n"
