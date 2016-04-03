#!/usr/bin/python
# coding:utf-8
__metaclass__ = type
import pygame
from OpenGL.GL import *
from OpenGL.GLU import *
from pygame.locals import *


class Visualization:
    """
    Class Visualization is building for gyro data visualization.
    It requires pygame and OpenGL library.
    """
    __SCREEN_SIZE = (800, 600)
    __display_yp = [0, 0]  # yaw pitch
    __video_yp = [0, 0]

    def __init(self):
        glEnable(GL_DEPTH_TEST)
        glClearColor(0.0, 0.0, 0.0, 0.0)
        glShadeModel(GL_SMOOTH)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_POLYGON_SMOOTH)
        glHint(GL_POLYGON_SMOOTH_HINT, GL_NICEST)
        glEnable(GL_COLOR_MATERIAL)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glLightfv(GL_LIGHT0, GL_AMBIENT, (0.2, 0.3, 0.3, 1.0))

    def set_yp(display, video):
        """
        Set up yaw and pitch data for display and video.
        params: display_gyro_data(e.g. [3,50])  video_gyro_data
        Notice: gyro data None is acceptable
        """
        if display is not None:
            self.__display_yp = display
        if video is not None:
            self.__video_yp = video

    def __resize(self, width, height):
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(50.0, float(width) / height, 0.001, 10.0)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        gluLookAt(0.0, 1.0, -5.0,
                  0.0, 0.0, 0.0,
                  0.0, 1.0, 0.0)

    def run(self):
        """
        Start pygame to create a window for Visualization.
        """
        pygame.init()
        screen = pygame.display.set_mode(self.__SCREEN_SIZE, HWSURFACE | OPENGL | DOUBLEBUF)
        self.__init()
        self.__resize(*self.__SCREEN_SIZE)
        cube = Cube((1.5, 0.0, 0.0), (.5, .5, .7))
        cube2 = Cube((-1.5, 0.0, 0.0), (.7, .7, .5))

        while True:
            for event in pygame.event.get():
                if event.type == QUIT:
                    return
                    if event.type == KEYUP and event.key == K_ESCAPE:
                        return
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            glColor((1., 1., 1.))
            glLineWidth(1)
            glBegin(GL_LINES)
            for x in range(-30, 32, 2):  # v line bottom
                glVertex3f(x/10., -1, -1)
                glVertex3f(x/10., -1, 1)
            for x in range(-30, 32, 2):  # v line back
                glVertex3f(x/10., -1, 1)
                glVertex3f(x/10., 1, 1)
            for z in range(-10, 12, 2):  # h line bottom
                glVertex3f(-3, -1, z/10.)
                glVertex3f(3, -1, z/10.)
            for z in range(-10, 12, 2):  # v line right
                glVertex3f(-3, -1, z/10.)
                glVertex3f(-3,  1, z/10.)
            for z in range(-10, 12, 2):  # v line left
                glVertex3f(3, -1, z/10.)
                glVertex3f(3,  1, z/10.)
            for y in range(-10, 12, 2):  # h line back
                glVertex3f(-3, y/10., 1)
                glVertex3f(3, y/10., 1)
            for y in range(-10, 12, 2):  # h line right
                glVertex3f(-3, y/10., 1)
                glVertex3f(-3, y/10., -1)
            for y in range(-10, 12, 2):  # h line left
                glVertex3f(3, y/10., 1)
                glVertex3f(3, y/10., -1)
            glEnd()

            glPushMatrix()
            glTranslate(*cube.position)
            glRotate(float(self.__display_yp[0]), 0, 1, 0)
            glRotate(float(self.__display_yp[1]), 1, 0, 0)
            cube2.render()
            glPopMatrix()
            glPushMatrix()
            glTranslate(*cube2.position)
            glRotate(float(self.__video_yp[0]), 0, 1, 0)
            glRotate(float(self.__video_yp[1]), 1, 0, 0)
            cube.render()
            glPopMatrix()
            pygame.display.flip()


class Cube(object):
    """
    A cube class defines how a cube renders with OpenGL.
    """

    def __init__(self, position, color):
        self.position = position
        self.color = color
    # Cube information
    num_faces = 6
    vertices = [(-1.0, -0.05, 0.5),
                (1.0, -0.05, 0.5),
                (1.0, 0.05, 0.5),
                (-1.0, 0.05, 0.5),
                (-1.0, -0.05, -0.5),
                (1.0, -0.05, -0.5),
                (1.0, 0.05, -0.5),
                (-1.0, 0.05, -0.5)]
    normals = [(0.0, 0.0, +1.0),  # front
               (0.0, 0.0, -1.0),  # back
               (+1.0, 0.0, 0.0),  # right
               (-1.0, 0.0, 0.0),  # left
               (0.0, +1.0, 0.0),  # top
               (0.0, -1.0, 0.0)]  # bottom
    vertex_indices = [(0, 1, 2, 3),  # front
                      (4, 5, 6, 7),  # back
                      (1, 5, 6, 2),  # right
                      (0, 4, 7, 3),  # left
                      (3, 2, 6, 7),  # top
                      (0, 1, 5, 4)]  # bottom

    def render(self):
        glColor(self.color)
        vertices = self.vertices
        # Draw all 6 faces of the cube
        glBegin(GL_QUADS)

        for face_no in xrange(self.num_faces):
            glNormal3dv(self.normals[face_no])
            v1, v2, v3, v4 = self.vertex_indices[face_no]
            glVertex(vertices[v1])
            glVertex(vertices[v2])
            glVertex(vertices[v3])
            glVertex(vertices[v4])
        glEnd()
