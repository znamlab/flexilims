# Flexilims repository

Flexilims is a laboratory database software written and maintained by the database team of the Crick. Flexilims web interface can be accessed at https://flexylims.thecrick.org/flexilims/. Mike Gavrielides wrote an API. The documentation is here https://flexylims.thecrick.org/flexilims/api/docs.
This repository is defining python wrappers to use the API.

# flexilims

This package contains a class with generic wrapper to the flexilims get/put/post request. It should not depend on particular local schema.

## Valid data types

Data is sent via http requests containing a json-formatted body. All valid json should 
work, with some caveat for empty structures.  

### Valid type (uploaded as is)

Most basic datatype work as expected. This includes:

- `str` including empty strings.
- Numbers, `int` or `float`.
- `list` containing at least one element.
- `dict` containing at least one element.
- Nested structures of the above.

### Converted types

Some types can be uploaded but will converted when uploaded to the database, and come 
back as a different type when using a `get` request.

- A `tuple` becomes a `list`.
- Empty `dict` are uploaded as `null` .
- Empty `list` are uploaded as `null`.

**Warning**: the reply from flexilims after a `post` request is sent before uploading the 
database, empty list and dictionaries are still present as such in this reply. 

### Invalid types

Trying to upload these types will raise an error.

- `complex`
- `set`/`frozenset`
- `bytes`
- `range`
- Almost any other non built-in types (`np.array`, `pd.DataFrame`...)

## Basic use

### Authentication

To connect to flexilims you must be on the Crick network (or vpn to it). Your flexilims username and password can be used to get a token than must then be provided in the headers of any subsequent request. 

The simplest way to do that is to create a `Flexilims` object that will handle the authentication. It can also have a default project to avoid re-entering the id at every request.

```
import flexilims.main as flm

session = flm.Flexilims(username='MyUserName', password='Password', project_id='hexcode000000000')
```


### Reading data: Get request

The `session` can then be use to get data of any type:

```
# Get request:
results = session.get(datatype='mouse')
```

`results` will be a list of dictionnary with each element being one `mouse` in that case. You can specify the `project_id` in the call to get if you didn't set it at session creation (or if you want to access a different project for this request). It is possible to query a selection of the datatype, see docstring for documentation.

The database is hierachical, each entity has an origin. The list of children from one entity can get obtained using `get_children`:

```
# Get the database entries for all children of one entity
children = session.get_children(id='hexcode000000000')
```

## Add new data: post request

New entries can be created with the post request. Once again, it's a simple call of a session method:

```
now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
session.post(datatype='mouse', name='test_ran_on_%s' % now, attributes=dict(age=12))
```

The parent of the entity can be specified using the `origin_id` keyword. See docstring for more information.

### Updating data: put request

Similarly one can update existing elements. You can update one entry using `update_one`:

```
rep = session.update_one(id=entity_id, datatype='recording', strict_validation=False)
```

Entities can only be identify by hexadecimal id. Name, origin_id or attributes can be changed. See docstring for more details

You can also update multiple entries all at once:

```
rep = session.update_many(datatype='session', update_key='test_attribute', update_value='new_value')
```

This should print something like:
```
'updated successfully 5 items of type session with test_attribute=new_value'
```
That's obviously dangerous as you rarely want to have the same `new_value` for everyone. You can select which element to update by using the `query_key`/`query_value` pair but that can query only attributes.

```
rep = session.update_many(datatype='session', query_key='test_uniq', query_value='unique',
                          update_key='test_uniq', update_value='unique')
```

### Utilities

Other request are provided:

#### Get children

Returns all children from an entity

#### Get project info

List existing projects and their attributes
