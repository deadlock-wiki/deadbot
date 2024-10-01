import os
import boto3
import glob

class S3:
    def __init__(self, data_dir, bucket_name, aws_access_key_id, aws_secret_access_key):
        self.client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
        )

        self.bucket_name = bucket_name
        self.DATA_DIR = data_dir

    def read(self):
        return self.client.list_objects_v2(Bucket=self.bucket_name).get('Contents')

    def write(self):
        version = self._get_current_version()
        if version in self.versions():
            print(f'Version {version} already exists on s3')
            return

        print(f'Uploading data for patch version {version}...')

        # get all files in data directory
        files = glob.iglob(self.DATA_DIR + '/**/*.*', recursive=True)
        for file in files:
            # get path after the root folder
            key = file.replace(self.DATA_DIR, '')
            key = f'{version}{key}'

            # keys must use forward slashes to create folders
            key = key.replace('\\', '/')
            self.client.upload_file(file, self.bucket_name, key)

        print('Done!')

    # returns the list of client patch numbers stored on the s3 bucket
    def versions(self):
        paginator = self.client.get_paginator('list_objects')
        result = paginator.paginate(Bucket=self.bucket_name, Delimiter='/')

        versions = []
        for prefix in result.search('CommonPrefixes'):
            version = prefix.get('Prefix')
            # remove "/" suffix
            versions.append(version.replace('/', ''))

        return versions

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


if __name__ == '__main__':
    S3('deadlock-game-files').write()
