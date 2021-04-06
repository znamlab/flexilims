import pytest
import datetime
import mcms
from resources.secret_password import mcms_passwords

username = 'ab8'
password = mcms_passwords[username]


def test_download_mouse():
    mcms.download_mouse_info(username=username, mouse_name='PZAJ2.1c')
