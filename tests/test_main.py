"""Unit tests for the main flexilims wrappers"""

import pytest
import flexilims.main as flm

username = 'blota'
password = 'blota'

tok = flm.get_token(username, password)