import os
# Default values

FLEXILIMS_USERNAME = 'blota'
MCMS_USERNAME = 'ab8'


# Config
DOWNLOAD_FOLDER = os.path.join(os.path.expanduser('~'), 'Downloads')
assert os.path.isdir(DOWNLOAD_FOLDER)
