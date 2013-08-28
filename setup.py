try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup

from contrib.version import get_git_version

setup(name="reschema",
      version=get_git_version(),
      description="reschema - Parse REST API schema into Python objects, support documentation generation",
      author="Riverbed Technology",
      author_email="cwhite@riverbed.com",
      
      packages = find_packages(),
      scripts = [
          'bin/reschema-doc'
        ],
      install_requires = [
          'uritemplate>=0.6',
          'PyYAML>=3.10',
          'jsonpointer>=1.0',
          'Markdown>=2.2.1'
          ],
      include_package_data = True)
