import sys

# Removes all use of "" from vdata files as it breaks kv3 parser
if __name__ == '__main__':
    print('---', sys.argv[1])

    with open(sys.argv[1], 'r') as f:
        content = f.read()
        # replace '' with ''
        # subclass features in kv3 don't seem to be supported in the keyvalues3 python library
        content = content.replace('subclass:', '')

    with open(sys.argv[1], 'w') as f:
        f.write(content)
