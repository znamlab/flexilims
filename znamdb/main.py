import pandas as pd
import numpy as np
import flexilims as flm
import mcms
import resources.parameters as prm


def add_mouse(mouse_name, project_id, mcms_animal_name=None, flexilims_username=None, mcms_username=None):
    """Check if a mouse is already in the database and add it if it isn't"""

    if flexilims_username is None:
        flexilims_username = prm.FLEXILIMS_USERNAME
    session = flm.Flexilims(username=flexilims_username, project_id=project_id)
    mice_df = get_mice(session=session)
    if mouse_name in mice_df.index:
        return mice_df.loc[mouse_name]

    if mcms_username is None:
        mcms_username = prm.MCMS_USERNAME
    if mcms_animal_name is None:
        mcms_animal_name = mouse_name
    mouse_info = mcms.get_mouse_df(mouse_name=mcms_animal_name, username=mcms_username)

    # add the data in flexilims, which requires a directory
    mouse_info = dict(mouse_info)
    for k, v in mouse_info.items():
        if type(v) != str:
            mouse_info[k] = float(v)
        else:
            mouse_info[k] = v.strip()
    resp = session.post(datatype='mouse', name=mouse_name, attributes=dict(mouse_info))
    return resp


def get_mice(project_id=None, username=None, session=None):
    """Get mouse info and format it"""

    assert (project_id is not None) or (session is not None)

    if session is None:
        if username is None:
            username = prm.FLEXILIMS_USERNAME
        session = flm.Flexilims(username)

    mice = session.get(datatype='mouse', project_id=project_id)
    # make into a nice df
    reserved_keywords = ['id', 'type', 'name', 'incrementalId']
    for mouse in mice:
        for attr_name, attr_value in mouse['attributes'].items():
            assert attr_name not in reserved_keywords
            mouse[attr_name] = attr_value
        mouse.pop('attributes')
    mice = pd.DataFrame(mice)
    if len(mice):
        mice.set_index('name', drop=False, inplace=True)
    return mice


if __name__ == '__main__':
    proj_id = '606df5af08df4d77c72c9b05'
    mdf = add_mouse(project_id=proj_id, mouse_name='PZAH4.1c')
    print('done')
