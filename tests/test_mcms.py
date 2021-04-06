import pytest
import datetime
import mcms
from resources.secret_password import mcms_passwords

username = 'blota'
password = mcms_passwords['blota']


def test_download_mouse():
    mcms.download_mouse_info(username=username, mouse_name='PZAJ2.1c')
