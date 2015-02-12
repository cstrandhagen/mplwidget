#!/usr/bin/env python
# Created by Christian Strandhagen, March 2014


def configuration(parent_package='', top_path=None):
    from numpy.distutils.misc_util import Configuration

    config = Configuration('icons', parent_package, top_path)
    config.add_data_dir('icons')

    return config

if __name__ == '__main__':
    from numpy.distutils.core import setup

    setup(**configuration(top_path='').todict())
