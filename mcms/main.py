import os
import time
import pandas as pd
from webbot import Browser
from resources import parameters as prm

BASE_URL = 'https://crick.colonymanagement.org/mouse/'


def download_mouse_info(mouse_name, username, password=None, suffix='autodownloaded'):
    """Log in to MCMS using webbot and download csv about all alive mice"""
    if password is None:
        try:
            from resources.secret_password import mcms_passwords
        except ImportError:
            print('Cannot load flexilims.secret_password')
            return
        password = mcms_passwords[username]

    web = Browser()
    web.go_to('%sstandard_user_home.do' % BASE_URL)
    web.click('Sign in')
    web.type(username, into='Username')
    web.click('NEXT', tag='span')
    web.type(password, into='Password', id='passwordFieldId')  # specific selection
    web.click('Sign in', tag='span')
    print("Log in Successful")

    request = 'RepAllMice'
    web.go_to('%scustom_query.do?queryUid=%s' % (BASE_URL, request))
    web.click(xpath="/html/body/div[3]/form/div[3]/div/div/div/div/button")
    time.sleep(0.5)  # seconds
    web.click('Animal Name')
    # web.click(xpath="/html/body/div[3]/form/div[2]/div/div/div[3]/table/tbody/tr/td[2]/span/select")
    time.sleep(0.5)  # seconds
    web.type(mouse_name)
    time.sleep(0.1)  # seconds
    web.click('Run Live', tag='span')
    # long sleep timer to allow it to run
    print('Running query')
    time.sleep(5)  # seconds

    # Checks to see if required button exists
    exists = web.exists(xpath="/html/body/div[3]/div[4]/div/div/div/div[2]/div[3]/div[4]/button")
    assert exists
    web.click(xpath="/html/body/div[3]/div[4]/div/div/div/div[2]/div[3]/div[4]/button")
    time.sleep(1)  # seconds
    # Change target file name
    assert web.exists(xpath="/html/body/div[8]/div[3]/div[1]/input")
    web.click(xpath="/html/body/div[8]/div[3]/div[1]/input")
    web.type('\b' * 100 + mouse_name + '_' + suffix)
    # Checks to see if required button exists
    assert web.exists(xpath="/html/body/div[8]/div[3]/div[1]/span")
    web.click(id="customQueryDt_downloadToFile")
    # sleep timer to allow for download
    time.sleep(5)  # seconds
    print("Mouse info downloaded")


def get_mouse_df(mouse_name, username, password=None):
    """Load mouse info from mcms in a dataframe"""
    download_mouse_info(mouse_name, username, password, suffix='get_mouse_df_file')
    fnames = [s for s in os.listdir(prm.DOWNLOAD_FOLDER) if s.startswith(mouse_name + '_get_mouse_df_file')]
    if len(fnames) > 1:
        raise IOError('Multiple file found. Please remove old downloads with similar name '
                      '(i.e. starting with %s' % (mouse_name + '_get_mouse_df_file'))

    # read this file and delete it
    mcms_file = os.path.join(prm.DOWNLOAD_FOLDER, fnames[0])
    mouse_data = pd.read_csv(mcms_file)
    os.remove(mcms_file)
    # reformat columns name to valid flexilims attribute
    cols = []
    replace_map = {' ': '_', '.': '_', '(': '', ')': ''}
    for col in mouse_data.columns:
        for char in replace_map.keys():
            if char in col:
                col = col.replace(char, replace_map[char])
        cols.append(col.lower())
    mouse_data.columns = cols
    mouse_data.set_index('animal_name', drop=False, inplace=True)

    return mouse_data.loc[mouse_name]


if __name__ == '__main__':
    df = get_mouse_df(username='ab8', mouse_name='PZAJ2.1c')
    print('done')
