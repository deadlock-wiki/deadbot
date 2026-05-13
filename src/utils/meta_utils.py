def get_deadbot_version():
    try:
        # TODO - fix versioning
        return '1.10.0'
    except Exception as e:
        raise Exception('Deadbot package version not found') from e
