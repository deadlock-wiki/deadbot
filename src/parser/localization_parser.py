import sys
import json

if __name__ == "__main__":
    with open(sys.argv[1], "r") as f:
        lines = f.readlines()
        out = dict()
        for line in lines:
            if line.count('"') >= 4:
                left = line.split('"')[1]

                # Handle cases where there are escaped quotations in the string
                right = "".join(line.split('"')[3:]).strip()
                right = right.replace("\\", '"')

                out[left] = right

        with open(sys.argv[2], "w") as f:
            json.dump(out, f, indent=4)
