#!/usr/bin/env python
# Created by Christian Strandhagen, March 2014


def configuration(parent_package='', top_path=None):
    from numpy.distutils.misc_util import Configuration

    config = Configuration('models', parent_package, top_path)

    return config

if __name__ == '__main__':
    from numpy.distutils.core import setup

    setup(**configuration(top_path='').todict())
