from webbot import Browser
import time

BASE_URL = 'https://crick.colonymanagement.org/mouse/'


def download_alive_mice(username, password=None):
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

    request = 'RepAllMice&queryInstanceIndex=0&bypassForm=false&action=retrieveFromSession'
    web.go_to('%scustom_query.do?queryUid=%s' % (BASE_URL, request))
    web.click(xpath="/html/body/div[3]/form/div[2]/div/div/div[3]/table/tbody/tr/td[2]/span/select")
    time.sleep(2)  # seconds
    web.click('PZ license - alive', tag='span')
    time.sleep(2)  # seconds
    web.click('recall', tag='span')
    time.sleep(2)  # seconds
    web.click('Run Live', tag='span')
    # long sleep timer to allow it to run
    print('Running query')
    time.sleep(10)  # seconds

    # Checks to see if required button exists
    exists = web.exists(xpath="/html/body/div[3]/div[4]/div/div/div/div[2]/div[3]/div[4]/button")
    print(exists)
    web.click(xpath="/html/body/div[3]/div[4]/div/div/div/div[2]/div[3]/div[4]/button")
    time.sleep(5)  # seconds

    # Checks to see if required button exists
    exists2 = web.exists(xpath="/html/body/div[8]/div[3]/div[1]/span")
    print(exists2)
    web.click(id="customQueryDt_downloadToFile")
    # sleep timer to allow for download
    time.sleep(20)  # seconds
    print("Alive mice downloaded")


if __name__ == '__main__':
    download_alive_mice('ab8')
