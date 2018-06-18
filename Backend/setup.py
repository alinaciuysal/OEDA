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
        'colorama', # color on the console
        'tornado',
        'flask_restful',
        'flask_cors',
        'elasticsearch>=6.0.0,<7.0.0', # elasticsearch integration
        'statsmodels', # statistics and statistical testing
        'numpy>=1.14.2', # scientific computing
        'requests', # http integreation
        'freetype-py',
        'pypng',
        'matplotlib',
        'pyjwt',
        'backports.ssl_match_hostname',
        'scikit-optimize>=0.5.2', # gauss optimizer
        'kafka', # integration with kafka
        'paho-mqtt',
        'pandas',
        'seaborn',  # plotting lib
        'paho-mqtt',  # mqtt integration
        'scipy' # numerics and statistics
    ]
)
