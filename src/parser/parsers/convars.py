class ConvarsParser:
    """
    Parses the game-wide convars dump (DumpSource2/convars.txt) into a dict
    keyed by convar name. Each entry is either the bare type-coerced value, or
    a {"value", "description"} object when the convar has a description.

    Each record in the source file spans:
        <name> <value> (<flags>)
            <description>   # tab-indented, may span multiple lines
        <blank line>

    The literal "<no description>" is normalised to an empty string, and the
    trailing "(<flags>)" group is dropped. Values that are quoted in the source
    are kept as strings; unquoted values are coerced to bool/int/float when
    possible, otherwise left as strings.
    """

    NO_DESCRIPTION = '<no description>'

    def __init__(self, convars_file):
        self.convars_file = convars_file

    def run(self):
        with open(self.convars_file, 'r', encoding='utf-8') as f:
            lines = f.read().splitlines()

        convars = {}
        i = 0
        total = len(lines)
        while i < total:
            line = lines[i]

            if line == '' or line[0] in (' ', '\t'):
                i += 1
                continue

            name, value = self._parse_definition(line)

            i += 1
            description_lines = []
            while i < total and lines[i].startswith('\t'):
                description_lines.append(lines[i].strip())
                i += 1

            # Skip debug convars - not useful for the wiki
            if 'debug' in name.lower():
                continue

            # Skip convars with an empty string value (but keep falsy
            # values like 0 and false, which are meaningful)
            if isinstance(value, str) and value == '':
                continue

            description = ' '.join(description_lines).strip()
            if description == self.NO_DESCRIPTION:
                description = ''

            # Only wrap in an object when there's a description to carry;
            # otherwise store the bare value directly under the convar name
            if description:
                convars[name] = {'value': value, 'description': description}
            else:
                convars[name] = value

        return convars

    def _parse_definition(self, line):
        """Split a definition line into (name, coerced_value), dropping flags."""
        name, _, rest = line.partition(' ')

        # Flags are the trailing "(...)" group; drop everything from the last
        # opening paren onward. Descriptions can contain parens, but they live
        # on separate indented lines, so this only ever sees the flags group.
        paren_index = rest.rfind('(')
        if paren_index != -1:
            rest = rest[:paren_index]

        return name, self._coerce(rest.strip())

    def _coerce(self, raw):
        """Coerce an unquoted value to bool/int/float; keep quoted as string."""
        # Explicitly quoted in the dump -> treat as a string (e.g. "value")
        if len(raw) >= 2 and raw[0] == '"' and raw[-1] == '"':
            return raw[1:-1]

        if raw == 'true':
            return True
        if raw == 'false':
            return False

        try:
            return int(raw)
        except ValueError:
            pass

        try:
            return float(raw)
        except ValueError:
            pass

        return raw
