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
        'Tempita', # MIT license
        'colorama', # BSD license (BSD)
        'tornado', # Apache license
        'flask_restful', # BSD License (BSD)
        'flask_cors', # MIT License (MIT)
        'elasticsearch>=6.0.0,<7.0.0', # Apache Software License (Apache License, Version 2.0)
        'statsmodels', # statistics and statistical testing, BSD License (BSD License)
        'numpy>=1.14.2', # scientific computing, OSI Approved (BSD)
        'requests', # http integreation, Apache Software License (Apache 2.0)
        'freetype-py', # bindings for the FreeType library, GNU General Public License (GPL)
        'pypng', # PNG image files to be read and written using pure Python, MIT License
        'matplotlib', # Python Software Foundation License (BSD)
        'pyjwt', # JSON Web Token implementation in Python, MIT License (MIT)
        'backports.ssl_match_hostname', # The ssl.match_hostname() function from Python 3.5, Python Software Foundation License
        'scikit-optimize>=0.5.2', # gauss optimizer, BSD
        'kafka', # Pure Python client for Apache Kafka, Apache Software License (Apache License 2.0)
        'paho-mqtt', # MQTT version 3.1.1 client class, OSI Approved (Eclipse Public License v1.0 / Eclipse Distribution License v1.0)
        'pandas', # Powerful data structures for data analysis, time series, and statistics, BSD
        'seaborn', # statistical data visualization, BSD License (BSD (3-clause))
        'scipy' # Scientific Library for Python, BSD License (BSD)
    ]
)
