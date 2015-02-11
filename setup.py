#!/usr/bin/env python
'''
Created on Aug 1, 2013

@author: strandha
'''


def configuration(parent_package='',top_path=None):
    from numpy.distutils.misc_util import Configuration
    config = Configuration(None,parent_package,top_path)
    config.set_options(ignore_setup_xxx_py=True,
                       assume_default_configuration=True,
                       delegate_options_to_subpackages=True,
                       quiet=True)
    
    config.add_subpackage('mplwidget')
    #config.add_scripts(glob.glob('bin/*'))
    #config.add_data_files(('darkmatter','*.txt'))
    
    return config

if __name__ == '__main__':
    from numpy.distutils.core import setup
    
    setup(version='0.1.0',
        description='mplwidget - A Matplotlib Widget',
        author='Christian Strandhagen',
        author_email='strandhagen@pit.physik.uni-tuebingen.de',
        license='no idea',
        **configuration(top_path='').todict())
