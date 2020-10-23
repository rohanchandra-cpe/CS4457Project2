#!/usr/bin/env python3
import os
class FileReader:

    def __init__(self):
        pass

    def get(self, filepath, cookies):
        print('GET ACKED')
        if not os.path.exists(filepath):
            return None
        file_contents = open(filepath,'rb').read()
        return file_contents

    def head(self, filepath, cookies):
        print('HEAD ACKED')
        if not os.path.exists(filepath):
            return None
        return os.stat(filepath).st_size
