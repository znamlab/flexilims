# Flexilims repository

Flexilims is a laboratory database software written and maintained by the database team of the Crick. Flexilims web interface can be accessed at https://flexylims.thecrick.org/flexilims/. Mike Gavrielides wrote an API. His initial documentations can be found in the `docs` folder.

This repository is defining python wrappers to use the API.

# flexilims

This package contains a class with generic wrapper to the flexilims get/put/post request. It should not depend on particular local schema.

## Basic use

### Authentication
First you can create a `Flexilims` object that will handle the authentication. It can also have a default project to avoid re-entering the id at every request.

```
import flexilims.main as flm

session = flm.Flexilims(username='MyUserName', password='Password', project_id='hexcode000000000')
```

If the password is not provided, it will attempt to load it from `secret_password.py`. If this file exists it must contain a dictionnary of username/password pairs called `password_dict`

### Reading data: Get request
The `session` can then be use to get data of any type:

```
# Get request:
results = session.get(datatype='mouse')
```

`results` will be a list of dictionnary with each element being one `mouse` in that case. You can specify the `project_id` in the call to get if you didn't set it at session creation (or if you want to access a different project for this request). It is not possible for now to query a selection of the datatype.

TODO: ask for query exactly identical to the put request

### Updating data: put request

Similarly one can update existing elements. For now you can update them all at once:

```
rep = sess.put(datatype='session', update_key='test_attribute', update_value='new_value')
```
This should print something like:
```
'updated successfully 5 items of type session with test_attribute=new_value'
```
That's obviously dangerous as you rarely want to have the same `new_value` for everyone. You can select which element to update by using the `query_key`/`query_value` pair but that can query only attributes for now.

```
rep = sess.put(datatype='session', query_key='test_uniq', query_value='unique',
                   update_key='test_uniq', update_value='unique')
```

TODO: bother Mike to update a single entry by filtering on name

## Add new data: post request

New entries can be created with the post request. Once again, it's a simple call of a session method:

```
now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    sess.post(datatype='mouse', name='test_ran_on_%s' % now, attributes=dict(age=12))
```
