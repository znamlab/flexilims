from flexiznam.config.config_tools import get_password
from flexilims import main
import pytest
import yaml

BASE_URL = "https://flexylims.thecrick.org/flexilims/api/"
USERNAME = "blota"
password = get_password(USERNAME, "flexilims")
PROJECT_ID = "606df1ac08df4d77c72c9aa4"  # <- test_api project
MOUSE_ID = "6094f7212597df357fa24a8c"
JSON_FILE = "/Volumes/lab-znamenskiyp/home/shared/projects/hey2_3d-vision_foodres_20220101/flexlims_json_version.yml"


@pytest.mark.slow
def test_download_database(tmp_path):
    from flexilims.offline import download_database

    flm_sess = main.Flexilims(USERNAME, password, PROJECT_ID)
    json_data = download_database(flm_sess, root_datatypes=("mouse",), verbose=True)
    assert isinstance(json_data, dict)
    assert len(json_data) == 1
    assert next(iter(json_data)) == "test_mouse"
    ts = json_data["test_mouse"]["children"]["test_session"]
    assert "test_recording" in ts["children"]

    with open(tmp_path / "test.json", "w") as f:
        yaml.dump(json_data, f)

    reloaded_data = yaml.load(open(tmp_path / "test.json"), Loader=yaml.SafeLoader)
    assert reloaded_data == json_data

    def test_origin(parent):
        for child in parent["children"].values():
            assert child["origin_id"] == parent["id"]
            test_origin(child)

    test_origin(json_data["test_mouse"])


def test_format_df():
    import pandas as pd
    from flexilims.offline import OffFlexilims

    sess = OffFlexilims(JSON_FILE)
    assert isinstance(sess._dataframe, pd.DataFrame)
