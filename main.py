from __future__ import division

import math
import time
from collections import deque

import gl
import glu

import pyglet
from pyglet import image
from pyglet.graphics import TextureGroup
from pyglet.window import key, mouse

from gatesym import core


TICKS_PER_SEC = 60

FLYING_SPEED = 10


def cube_vertices(p, n):
    """ Return the vertices of the cube at position x, y, z with size 2*n.

    """
    offset = [n, n, n]
    return box_vertices(sub(p, offset), add(p, offset))


def box_vertices(p1, p2):
    x1, y1, z1 = p1
    x2, y2, z2 = p2
    return [
        x1, y2, z1, x1, y2, z2, x2, y2, z2, x2, y2, z1,  # top
        x1, y1, z1, x2, y1, z1, x2, y1, z2, x1, y1, z2,  # bottom
        x2, y1, z2, x2, y1, z1, x2, y2, z1, x2, y2, z2,  # right
        x1, y1, z1, x1, y1, z2, x1, y2, z2, x1, y2, z1,  # left
        x1, y1, z2, x2, y1, z2, x2, y2, z2, x1, y2, z2,  # front
        x2, y1, z1, x1, y1, z1, x1, y2, z1, x2, y2, z1,  # back
    ]


def tex_coord(x, y, n=4):
    """ Return the bounding vertices of the texture square.

    """
    m = 1.0 / n
    dx = x * m
    dy = y * m
    return dx, dy, dx + m, dy, dx + m, dy + m, dx, dy + m


def tex_coords(coord):
    """ Return a list of the texture squares for the top, bottom and side.

    """
    face = tex_coord(*coord)
    return face * 6


TEXTURE_PATH = 'texture.png'

# GRASS = tex_coords((1, 0), (0, 1), (0, 0))

CLOCK, WIRE, GATE = 'clock', 'wire', 'gate'

TEXTURES = {
    CLOCK: tex_coords((1, 1)),
    WIRE: tex_coords((2, 0)),
    GATE: tex_coords((2, 1)),
}

FACES = [
    (0, 1, 0),
    (0, -1, 0),
    (-1, 0, 0),
    (1, 0, 0),
    (0, 0, 1),
    (0, 0, -1),
]

UNCONNECTED = -1

UP, DOWN, LEFT, RIGHT, FRONT, BACK = range(6)

FACE_NAMES = [
    'up',
    'down',
    'right',
    'left',
    'front',
    'back',
]


def add(va, vb):
    return tuple(a + b for a, b in zip(va, vb))


def mul(va, s):
    return tuple(a * s for a in va)


def sub(va, vb):
    return tuple(a - b for a, b in zip(va, vb))


def div(va, s):
    return tuple(a / s for a in va)


def normalize(position):
    """ Accepts `position` of arbitrary precision and returns the block
    containing that position.

    Parameters
    ----------
    position : tuple of len 3

    Returns
    -------
    block_position : tuple of ints of len 3

    """
    x, y, z = position
    x, y, z = (int(round(x)), int(round(y)), int(round(z)))
    return (x, y, z)


class Model(object):

    def __init__(self):

        # A Batch is a collection of vertex lists for batched rendering.
        self.batch = pyglet.graphics.Batch()

        # A TextureGroup manages an OpenGL texture.
        self.group = TextureGroup(image.load(TEXTURE_PATH).get_texture())

        # A mapping from position to the texture of the block at that position.
        # This defines all the blocks that are currently in the world.
        self.world = {}

        # Same mapping as `world` but contains block orientations
        self.orientation = {}

        # Same mapping as `world` but contains core network ids
        self.line = {}

        # Mapping from position to a pyglet `VertextList` for all shown blocks.
        self._shown = {}

        self.network = core.Network()

        self._initialize()

    def _initialize(self):
        """ Initialize the world by placing all the blocks.

        """
        position = (0, 0, -5)
        self.add_block(position, CLOCK)
        self.clock_index = self.line[position]

    def hit_test(self, position, vector, max_distance=8):
        """ Line of sight search from current position. If a block is
        intersected it is returned, along with the block previously in the line
        of sight. If no block is found, return None, None.

        Parameters
        ----------
        position : tuple of len 3
            The (x, y, z) position to check visibility from.
        vector : tuple of len 3
            The line of sight vector.
        max_distance : int
            How many blocks away to search for a hit.

        """
        m = 8
        key = None
        previous = None
        for _ in range(max_distance * m):
            new = normalize(position)
            if new != key:
                previous = key
                key = new
                if key in self.world:
                    break
            position = add(position, div(vector, m))
        return key, previous

    def add_block(self, position, block, orientation=DOWN):  # GDW remove default orientation
        """ Add a block with the given `texture` and `position` to the world.

        Parameters
        ----------
        position : tuple of len 3
            The (x, y, z) position of the block to add.
        texture : list of len 3
            The coordinates of the texture squares. Use `tex_coords()` to
            generate.

        """
        if position in self.world:
            self.remove_block(position)
        self.world[position] = block
        self.orientation[position] = orientation
        if block == GATE:
            self.line[position] = self.network.add_gate(core.NOR)
        elif block == CLOCK:
            self.line[position] = self.network.add_gate(core.SWITCH)
        elif block == WIRE:
            source = add(position, FACES[orientation])
            self.line[position] = self.line[source] if source in self.world else UNCONNECTED
        else:
            assert False
        self.show_block(position)

    def remove_block(self, position):
        """ Remove the block at the given `position`.

        Parameters
        ----------
        position : tuple of len 3
            The (x, y, z) position of the block to remove.

        """
        del self.world[position]
        del self.orientation[position]
        del self.line[position]
        self.hide_block(position)

    def show_block(self, position):
        """ Show the block at the given `position`. This method assumes the
        block has already been added with add_block()

        Parameters
        ----------
        position : tuple of len 3
            The (x, y, z) position of the block to show.

        """
        type_ = self.world[position]
        texture = TEXTURES[type_]
        orientation = self.orientation[position]

        if type_ == WIRE:
            extension = add(position, mul(FACES[orientation], 0.5))
            vertex_data = cube_vertices(position, 0.25) + cube_vertices(extension, 0.25)
            texture_data = list(texture * 2)
        else:
            vertex_data = cube_vertices(position, 0.5)
            texture_data = list(texture)

        # create vertex list
        # FIXME Maybe `add_indexed()` should be used instead
        assert len(vertex_data) == len(texture_data) / 2 * 3
        self._shown[position] = self.batch.add(
            len(vertex_data) // 3, gl.QUADS, self.group,
            ('v3f/static', vertex_data),
            ('t2f/static', texture_data),
        )

    def hide_block(self, position):
        """ Hide the block at the given `position`. Hiding does not remove the
        block from the world.

        Parameters
        ----------
        position : tuple of len 3
            The (x, y, z) position of the block to hide.
        """
        self._shown.pop(position).delete()


class Window(pyglet.window.Window):

    def __init__(self, *args, **kwargs):
        super(Window, self).__init__(*args, **kwargs)

        # Whether or not the window exclusively captures the mouse.
        self.exclusive = False

        # Strafing is moving lateral to the direction you are facing,
        # e.g. moving to the left or right while continuing to face forward.
        #
        # First element is -1 when moving forward, 1 when moving back, and 0
        # otherwise. The second element is -1 when moving down, 1 when moving
        # up, and 0 otherwise. The second element is -1 when moving left,
        # 1 when moving right, and 0 otherwise.
        self.strafe = [0, 0, 0]

        # Current (x, y, z) position in the world, specified with floats. Note
        # that, perhaps unlike in math class, the y-axis is the vertical axis.
        self.position = (0, 0, 0)

        # First element is rotation of the player in the x-z plane (ground
        # plane) measured from the z-axis down. The second is the rotation
        # angle from the ground plane up. Rotation is in degrees.
        #
        # The vertical plane rotation ranges from -90 (looking straight down) to
        # 90 (looking straight up). The horizontal rotation range is unbounded.
        self.rotation = (0, 0)
        self.rotation_new = (0, 0)

        # The crosshairs at the center of the screen.
        self.reticle = None

        # A list of blocks the player can place. Hit num keys to cycle.
        self.inventory = [WIRE, GATE]

        # The current block the user can place. Hit num keys to cycle.
        self.block = self.inventory[0]

        # Convenience list of num keys.
        self.num_keys = [
            key._1, key._2, key._3, key._4, key._5,
            key._6, key._7, key._8, key._9, key._0]

        # Instance of the model that handles the world.
        self.model = Model()

        # The label that is displayed in the top left of the canvas.
        self.label = pyglet.text.Label(
            '',
            font_name='Arial',
            font_size=18,
            x=10,
            y=self.height - 10,
            anchor_x='left',
            anchor_y='top',
            color=(0, 0, 0, 255),
        )
        self.label2 = pyglet.text.Label(
            '',
            font_name='Arial',
            font_size=18,
            x=10,
            y=self.height - 30,
            anchor_x='left',
            anchor_y='top',
            color=(0, 0, 0, 255),
        )

        # This call schedules the `update()` method to be called
        # TICKS_PER_SEC. This is the main game event loop.
        pyglet.clock.schedule_interval(self.update, 1.0 / TICKS_PER_SEC)

    def set_exclusive_mouse(self, exclusive):
        """ If `exclusive` is True, the game will capture the mouse, if False
        the game will ignore the mouse.

        """
        super(Window, self).set_exclusive_mouse(exclusive)
        self.exclusive = exclusive

    def get_sight_vector(self):
        """ Returns the current line of sight vector indicating the direction
        the player is looking.

        """
        x, y = self.rotation
        # y ranges from -90 to 90, or -pi/2 to pi/2, so m ranges from 0 to 1 and
        # is 1 when looking ahead parallel to the ground and 0 when looking
        # straight up or down.
        m = math.cos(math.radians(y))
        # dy ranges from -1 to 1 and is -1 when looking straight down and 1 when
        # looking straight up.
        dy = math.sin(math.radians(y))
        dx = math.cos(math.radians(x - 90)) * m
        dz = math.sin(math.radians(x - 90)) * m
        return (dx, dy, dz)

    def get_motion_vector(self):
        """ Returns the current motion vector indicating the velocity of the
        player.

        Returns
        -------
        vector : tuple of len 3
            Tuple containing the velocity in x, y, and z respectively.

        """
        if self.strafe[0] or self.strafe[2]:
            x, y = self.rotation
            strafe = math.degrees(math.atan2(self.strafe[0], self.strafe[2]))
            y_angle = math.radians(y)
            x_angle = math.radians(x + strafe)

            m = math.cos(y_angle)
            dy = math.sin(y_angle)
            if self.strafe[2]:
                # Moving left or right.
                dy = 0.0
                m = 1
            if self.strafe[0] > 0:
                # Moving backwards.
                dy *= -1
            # When you are flying up or down, you have less left and right
            # motion.
            dx = math.cos(x_angle) * m
            dz = math.sin(x_angle) * m
        else:
            dy = 0.0
            dx = 0.0
            dz = 0.0

        dy += self.strafe[1]

        return (dx, dy, dz)

    def update(self, dt):
        """ This method is scheduled to be called repeatedly by the pyglet
        clock.

        Parameters
        ----------
        dt : float
            The change in time since the last call.

        """
        m = max(int(dt / 0.025), 1)
        for _ in range(m):
            self._update(dt / m)

    def _update(self, dt):
        """ Private implementation of the `update()` method. This is where most
        of the motion logic lives, along with collision detection.

        Parameters
        ----------
        dt : float
            The change in time since the last call.

        """
        self.rotation = self.rotation_new
        speed = FLYING_SPEED
        d = dt * speed  # distance covered this tick.
        motion_vec = mul(self.get_motion_vector(), d)
        # collisions
        self.position = self.collide(add(self.position, motion_vec))

    def collide(self, position):
        """ Checks to see if the player at the given `position`
        is colliding with any blocks in the world.

        Parameters
        ----------
        position : tuple of len 3
            The (x, y, z) position to check for collisions at.


        Returns
        -------
        position : tuple of len 3
            The new position of the player taking into account collisions.

        """
        # How much overlap with a dimension of a surrounding block you need to
        # have to count as a collision. You can think of the player as having a
        # radius of 0.5 - pad.
        pad = .1
        pos = list(position)
        pos_norm = normalize(position)
        for face in FACES:  # check all surrounding blocks
            neighbour = add(pos_norm, face)
            if neighbour not in self.model.world:
                continue

            res = [0, 0, 0]
            for i in range(3):  # check each dimension independently
                # How much overlap you have with this dimension.
                d = (pos[i] - pos_norm[i]) * face[i]
                if d < pad:
                    continue

                res = sub(res, mul(face, d - pad))
            pos = add(pos, res)

        return pos

    def face_between_blocks(self, src, dest):
        return FACES.index(sub(src, dest))

    def on_mouse_press(self, x, y, button, modifiers):
        """ Called when a mouse button is pressed. See pyglet docs for button
        amd modifier mappings.

        Parameters
        ----------
        x, y : int
            The coordinates of the mouse click. Always center of the screen if
            the mouse is captured.
        button : int
            Number representing mouse button that was clicked. 1 = left button,
            4 = right button.
        modifiers : int
            Number representing any modifying keys that were pressed when the
            mouse button was clicked.

        """
        if self.exclusive:
            vector = self.get_sight_vector()
            block, previous = self.model.hit_test(self.position, vector)
            if (button == mouse.RIGHT) or \
                    ((button == mouse.LEFT) and (modifiers & key.MOD_CTRL)):
                # ON OSX, control + left click = right click.
                if previous and normalize(self.position) != previous:  # todo this doesn't account for pad correctly
                    orientation = self.face_between_blocks(block, previous)
                    self.model.add_block(previous, self.block, orientation)
            elif button == pyglet.window.mouse.LEFT and block in self.model.world:
                block_type = self.model.world[block]
                if block_type != CLOCK:
                    self.model.remove_block(block)
        else:
            self.set_exclusive_mouse(True)

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        self.on_mouse_motion(x, y, dx, dy)

    def on_mouse_motion(self, x, y, dx, dy):
        """ Called when the player moves the mouse.

        Parameters
        ----------
        x, y : int
            The coordinates of the mouse click. Always center of the screen if
            the mouse is captured.
        dx, dy : float
            The movement of the mouse.

        """
        if self.exclusive:
            m = 0.15
            x, y = self.rotation_new
            x, y = x + dx * m, y + dy * m
            y = max(-90, min(90, y))
            self.rotation_new = (x, y)

    def on_key_press(self, symbol, modifiers):
        """ Called when the player presses a key. See pyglet docs for key
        mappings.

        Parameters
        ----------
        symbol : int
            Number representing the key that was pressed.
        modifiers : int
            Number representing any modifying keys that were pressed.

        """
        if symbol == key.W:
            self.strafe[0] -= 1
        elif symbol == key.S:
            self.strafe[0] += 1
        elif symbol == key.A:
            self.strafe[2] -= 1
        elif symbol == key.D:
            self.strafe[2] += 1
        elif symbol == key.SPACE:
            self.strafe[1] += 1
        elif symbol == key.LSHIFT:
            self.strafe[1] -= 1
        elif symbol == key.ESCAPE:
            self.set_exclusive_mouse(False)
        elif symbol in self.num_keys:
            index = (symbol - self.num_keys[0]) % len(self.inventory)
            self.block = self.inventory[index]

    def on_key_release(self, symbol, modifiers):
        """ Called when the player releases a key. See pyglet docs for key
        mappings.

        Parameters
        ----------
        symbol : int
            Number representing the key that was pressed.
        modifiers : int
            Number representing any modifying keys that were pressed.

        """
        if symbol == key.W:
            self.strafe[0] += 1
        elif symbol == key.S:
            self.strafe[0] -= 1
        elif symbol == key.A:
            self.strafe[2] += 1
        elif symbol == key.D:
            self.strafe[2] -= 1
        elif symbol == key.SPACE:
            self.strafe[1] -= 1
        elif symbol == key.LSHIFT:
            self.strafe[1] += 1

    def on_resize(self, width, height):
        """ Called when the window is resized to a new `width` and `height`.

        """
        # label
        self.label.y = height - 10
        self.label2.y = height - 30
        # reticle
        if self.reticle:
            self.reticle.delete()
        x, y = self.width // 2, self.height // 2
        n = 10
        self.reticle = pyglet.graphics.vertex_list(
            4,
            ('v2i', (x - n, y, x + n, y, x, y - n, x, y + n)),
        )

    def set_2d(self):
        """ Configure OpenGL to draw in 2d.

        """
        width, height = self.get_size()
        gl.disable(gl.DEPTH_TEST)
        gl.viewport(0, 0, width, height)
        gl.matrix_mode(gl.PROJECTION)
        gl.load_identity()
        gl.ortho(0, width, 0, height, -1, 1)
        gl.matrix_mode(gl.MODELVIEW)
        gl.load_identity()

    def set_3d(self):
        """ Configure OpenGL to draw in 3d.

        """
        width, height = self.get_size()
        gl.enable(gl.DEPTH_TEST)
        gl.viewport(0, 0, width, height)
        gl.matrix_mode(gl.PROJECTION)
        gl.load_identity()
        glu.perspective(90.0, width / float(height), 0.1, 60.0)
        gl.matrix_mode(gl.MODELVIEW)
        gl.load_identity()
        x, y = self.rotation
        gl.rotatef(x, 0, 1, 0)
        gl.rotatef(-y, math.cos(math.radians(x)), 0, math.sin(math.radians(x)))
        gl.translatef(*mul(self.position, -1))

    def on_draw(self):
        """ Called by pyglet to draw the canvas.

        """
        self.clear()
        self.set_3d()
        gl.color3d(1, 1, 1)
        self.model.batch.draw()
        selected = self.get_focused_block()
        self.draw_focused_block(selected)
        self.set_2d()
        self.draw_label(selected)
        self.draw_reticle()

    def get_focused_block(self):
        vector = self.get_sight_vector()
        return self.model.hit_test(self.position, vector)[0]

    def draw_focused_block(self, selected):
        """ Draw black edges around the block that is currently under the
        crosshairs.

        """
        if selected:
            vertex_data = cube_vertices(selected, 0.51)
            gl.color3d(0, 0, 0)
            gl.polygon_mode(gl.FRONT_AND_BACK, gl.LINE)
            pyglet.graphics.draw(24, gl.QUADS, ('v3f/static', vertex_data))
            gl.polygon_mode(gl.FRONT_AND_BACK, gl.FILL)

    def draw_label(self, sel):
        """ Draw the label in the top left of the screen.

        """
        self.label.text = '%02d (%.2f, %.2f, %.2f) %d' % (
            pyglet.clock.get_fps(), *self.position, len(self.model.world))
        self.label.draw()

        m = self.model
        if sel in m.world:
            block = m.world[sel]
            orientation = FACE_NAMES[m.orientation[sel]]
            line = m.line[sel]
            self.label2.text = f'{sel}, {block}, {orientation}, {line}'
        else:
            self.label2.text = 'None'
        self.label2.draw()

    def draw_reticle(self):
        """ Draw the crosshairs in the center of the screen.

        """
        gl.color3d(0, 0, 0)
        self.reticle.draw(gl.LINES)


def setup_fog():
    """ Configure the OpenGL fog properties.

    """
    # Enable fog. Fog "blends a fog color with each rasterized pixel fragment's
    # post-texturing color."
    gl.enable(gl.FOG)
    # Set the fog color.
    gl.fogfv(gl.FOG_COLOR, (gl.float * 4)(0.5, 0.69, 1.0, 1))
    # Say we have no preference between rendering speed and quality.
    gl.hint(gl.FOG_HINT, gl.DONT_CARE)
    # Specify the equation used to compute the blending factor.
    gl.fogi(gl.FOG_MODE, gl.LINEAR)
    # How close and far away fog starts and ends. The closer the start and end,
    # the denser the fog in the fog range.
    gl.fogf(gl.FOG_START, 20.0)
    gl.fogf(gl.FOG_END, 60.0)


def setup():
    """ Basic OpenGL configuration.

    """
    # Set the color of "clear", i.e. the sky, in rgba.
    gl.clear_color(0.5, 0.69, 1.0, 1)
    # Enable culling (not rendering) of back-facing facets -- facets that aren't
    # visible to you.
    gl.enable(gl.CULL_FACE)
    # Set the texture minification/magnification function to gl.NEAREST (nearest
    # in Manhattan distance) to the specified texture coordinates. gl.NEAREST
    # "is generally faster than gl.LINEAR, but it can produce textured images
    # with sharper edges because the transition between texture elements is not
    # as smooth."
    gl.tex_parameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST)
    gl.tex_parameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST)
    setup_fog()


def main():
    window = Window(width=1500, height=1000, caption='Pyglet', resizable=True)
    # Hide the mouse cursor and prevent the mouse from leaving the window.
    window.set_exclusive_mouse(True)
    setup()
    pyglet.app.run()


if __name__ == '__main__':
    main()
