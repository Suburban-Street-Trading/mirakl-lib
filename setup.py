from setuptools import setup, find_packages

setup(
    name='mirakl_lib',
    version='0.1.1',
    packages=find_packages(),
    install_requires=[
        'requests',
        'pydantic',
        'typing'
    ],
    author='Samuel Benning',
    author_email='bensam1993@gmail.com',
    description='A package for interacting with the Mirakl API',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6'
)
