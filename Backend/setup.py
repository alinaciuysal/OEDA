from setuptools import setup, find_packages

# Setup configuration for the tool
setup(
    name='OEDA-Backend',
    version='0.2',
    long_description="",
    packages=find_packages(),
    include_package_data=False,
    zip_safe=False,
    install_requires=[
        'Tempita',
        'colorama',
        'tornado',
        'flask_restful',
        'flask_cors',
        'elasticsearch',
        'statsmodels',
        'numpy',
        'requests',
        'freetype-py',
        'pypng',
        'matplotlib',
        'pyjwt',
        'backports.ssl_match_hostname',
        'scikit-optimize',
        'kafka',
        'paho-mqtt',
    ]
)
