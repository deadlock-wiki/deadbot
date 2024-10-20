import boto3
import glob


class S3:
    def __init__(self, bucket_name, aws_access_key_id, aws_secret_access_key):
        self.client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
        )

        self.bucket_name = bucket_name

    def list_files(self, folder):
        return self.client.list_objects_v2(Bucket=self.bucket_name, Prefix=folder).get('Contents')

    def download(self, key, path):
        return self.client.download_file(self.bucket_name, key, path)

    def write(self, export_folder, data_directory):
        # get all files in data directory
        files = glob.iglob(data_directory + '/**/*.*', recursive=True)
        for file in files:
            # get path after the root folder
            key = file.replace(data_directory, '')
            key = f'{export_folder}{key}'

            # keys must use forward slashes to create folders
            key = key.replace('\\', '/')
            self.client.upload_file(file, self.bucket_name, key)

    # returns the list of top-level folder names
    def get_folders(self):
        paginator = self.client.get_paginator('list_objects')
        result = paginator.paginate(Bucket=self.bucket_name, Delimiter='/')

        folders = []
        for prefix in result.search('CommonPrefixes'):
            version = prefix.get('Prefix')
            # remove "/" suffix
            folders.append(version.replace('/', ''))

        return folders
