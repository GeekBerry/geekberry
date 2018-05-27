#!/usr/bin/env python
# -*- coding:utf-8 -*-

#############################################
# File Name: setup.py
# Author: GeekBerry
# Mail: GeekBerry@qq.com
# Created Time:  2018-05-27
#############################################

"""
打包和上传步骤:
    0.如果没有 twine
    > pip install twine

    1.打包
    > python setup.py sdist
    生成 dist 和 <项目名称>.egg-info 文件夹

    2.上传
    > twine upload dist/<项目名称>-<版本号>.tar.gz
"""

from setuptools import setup, find_packages

description = """
一些常用工具:
    1.结构化查询字典(SQDict)
"""

setup(
    name="geekberry",
    version="1.0.6",
    keywords=("pip", "geekberry", "database"),
    description="Some tools.",
    long_description=description,
    license="MIT Licence",

    url="https://github.com/GeekBerry/geekberry",
    author="GeekBerry",
    author_email="GeekBerry@qq.com",

    packages=find_packages(),
    include_package_data=True,
    platforms="any",
    install_requires=[]
)
