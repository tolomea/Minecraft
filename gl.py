import inflection

from pyglet import gl

used = set()

gl.GL_QUADS
content = gl.__dict__
if '_module' in content:
    content = content['_module'].__dict__

for name, value in content.items():

    if name.startswith('GLU_'):
        continue
    if name.startswith('GLU'):
        continue
    elif len(name) > 4 and name[3].isupper() and name.startswith('glu'):
        continue

    elif name.startswith('GL_'):
        new_name = name[3:]
    elif name.startswith('GL'):
        new_name = name[2:]
    elif len(name) > 3 and name[2].isupper() and name.startswith('gl'):
        new_name = inflection.underscore(name[2:])

    elif name.startswith('PFNGL'):
        continue
    else:
        continue

    assert new_name not in used, name
    used.add(new_name)
    globals()[new_name] = value
