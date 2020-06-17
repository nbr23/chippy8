#!/usr/bin/env python3

from setuptools import setup

setup(name='chippy8',
      version='1.0',
      description='Chip8 Emulator and tools',
      author='Maxence Ardouin',
      author_email='max@23.tf',
      packages=['chippy8'],
      zip_safe = True,
      install_requires=[
          'parse',
          ],
      entry_points={
          'console_scripts': [
              "chippy8 = chippy8.__main__:main",
              ],
          },
      )
