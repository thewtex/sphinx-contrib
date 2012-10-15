# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

long_desc = '''
This package contains the slide Sphinx extension.

This extension enable you to embed your slides on slideshare_ and other sites.
Following code is sample::

   .. slide:: http://www.slideshare.net/TakeshiKomiya/blockdiag-a-simple-diagram-generator


.. _slideshare: http://www.slideshare.net/
'''

requires = ['Sphinx>=0.6']

setup(
    name='sphinxcontrib-slide',
    version='0.1.1',
    url='http://bitbucket.org/birkenfeld/sphinx-contrib',
    download_url='http://pypi.python.org/pypi/sphinxcontrib-slide',
    license='BSD',
    author='Takeshi KOMIYA',
    author_email='i.tkomiya@gmail.com',
    description='Sphinx "slide" extension',
    long_description=long_desc,
    zip_safe=False,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Documentation',
        'Topic :: Utilities',
    ],
    platforms='any',
    packages=find_packages(),
    include_package_data=True,
    install_requires=requires,
    namespace_packages=['sphinxcontrib'],
)
