import os
from .s3 import S3


class DataTransfer:
    def __init__(self, data_dir, bucket_name, aws_access_key_id, aws_secret_access_key):
        self.DATA_DIR = data_dir
        self.s3 = S3(bucket_name, aws_access_key_id, aws_secret_access_key)

    def import_data(self, version=None):
        """Import decompiled game data from an S3 bucket into the local data directory

        Args:
            version (str, optional): Build number to retrieve game files for. Defaults to None.
        """
        # get latest version if none is specified
        if not version:
            versions = self._get_versions()
            version = max(versions)

        files = self.s3.list_files(version)
        if files is None:
            raise Exception(f'No data found for version {version}')

        for obj in files:
            key = obj['Key']

            # Skip any folder keys (keys ending with a "/")
            if key.endswith('/'):
                continue

            # Build local path from the S3 key, excluding the version prefix
            relative_path = key[len(version) :]
            local_file_path = self.DATA_DIR + '/' + relative_path
            local_file_dir = os.path.dirname(local_file_path)

            if not os.path.exists(local_file_dir):
                os.makedirs(local_file_dir)

            self.s3.download(key, local_file_path)

    def export_data(self):
        """Export local decompiled game data to an S3 bucket"""
        version = self._get_current_version()
        if version in self._get_versions():
            print(f'Version {version} already exists on s3')
            return

        print(f'Exporting data for patch version {version}...')

        self.s3.write(version, self.DATA_DIR)

    def _get_current_version(self):
        version_text = open(self.DATA_DIR + '/version.txt', 'r').read()
        keyvalue_pairs = version_text.split('\n')

        version_data = {}
        for pair in keyvalue_pairs:
            if pair == '':
                continue
            [key, value] = pair.split('=')
            version_data[key] = value

        return version_data['ClientVersion']

    def _get_versions(self):
        return self.s3.get_folders()
