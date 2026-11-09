from .printer import Printer


class ZenGinDataPrinter:
    """Generic ZenGin ASCII syntax: `[type1 type2 version objectIndex]` ...
    `[]` blocks and `name=type:value` properties, tab-indented by depth."""

    def __init__(self, printer: Printer):
        self._printer = printer
        self._indent = ""

    def start_object_block(self, type_1="%", type_2="%", triangles_limit=0, object_index=0):
        # `triangles_limit` is the class version number in the block header.
        self._printer.print(f"{self._indent}[{type_1} {type_2} {triangles_limit} {object_index}]")
        self._indent += "\t"

    def end_object_block(self):
        self._indent = self._indent[:-1]
        self._printer.print(f"{self._indent}[]")

    def print_property(self, name, data_type, value):
        self._printer.print(f"{self._indent}{name}={data_type}:{value}")

    def print_vec3_property(self, name, value_vector):
        self.print_property(name, "vec3", value_vector)

    def print_raw_rotation_property(self, name, value_quaternion):
        self.print_property(name, "raw", value_quaternion)

    def print_raw_float_property(self, name, value):
        self.print_property(name, "rawFloat", value)

    def print_float_property(self, name, value_float):
        self.print_property(name, "float", value_float)

    def print_enum_property(self, name, value_enum_ordinal):
        self.print_property(name, "enum", value_enum_ordinal)

    def print_bool_property(self, name, value_bool):
        self.print_property(name, "bool", 1 if value_bool else 0)

    def print_int_property(self, name, value_int):
        self.print_property(name, "int", value_int)

    def print_string_property(self, name, value_string):
        self.print_property(name, "string", value_string)

    def print_color_property(self, name, value_color):
        self.print_property(name, "color", value_color)
