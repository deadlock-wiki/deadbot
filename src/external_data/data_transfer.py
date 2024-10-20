from .s3 import S3


class DataTransfer:
    def __init__(self, data_dir, bucket_name, aws_access_key_id, aws_secret_access_key):
        self.DATA_DIR = data_dir
        self.s3 = S3(bucket_name, aws_access_key_id, aws_secret_access_key)

    def import_data(self, version='current'):
        data = self.s3.read(version)
        print(data)
        if ~data:
            raise Exception(f'No data found for version {version}')

        return data

    def export_data(self):
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
