import inflection

from pyglet import gl

used = set()

gl.GL_QUADS
content = gl.__dict__
if '_module' in content:
    content = content['_module'].__dict__

for name, value in content.items():

    if name.startswith('GLU_'):
        new_name = name[4:]
    if name.startswith('GLU'):
        new_name = name[3:]
    elif len(name) > 4 and name[3].isupper() and name.startswith('glu'):
        new_name = inflection.underscore(name[3:])

    elif name.startswith('GL_'):
        continue
    elif name.startswith('GL'):
        continue
    elif len(name) > 3 and name[2].isupper() and name.startswith('gl'):
        continue

    elif name.startswith('PFNGL'):
        continue
    else:
        continue

    assert new_name not in used, name
    used.add(new_name)
    globals()[new_name] = value
