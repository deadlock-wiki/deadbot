from importlib.metadata import version


def get_deadbot_version():
    try:
        return version('Deadbot')
    except Exception as e:
        raise Exception('Deadbot package version not found') from e
