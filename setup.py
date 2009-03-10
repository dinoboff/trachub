from setuptools import find_packages, setup

# name can be any name.  This name will be used to create .egg file.
# name that is used in packages is the one that is used in the trac.ini file.
# use package name as entry_points

setup(
    name='TracHub',
    version='0.1',
    author='Damien Lebrun',
    author_email='dinoboff@hotmail.com',
    description = """Integrate a Github and Trac project,
        by replacing the Trac source browser by the Github equivalent
        and by letting commit for project or its clones update tickets.""",
    license = """MIT""",
    url = "",
    packages=find_packages('src'),
    package_dir={'':'src'},

    install_requires = [
        'simplejson>=2.0.5',
        'nose'
    ],
    entry_points = {
        'trac.plugins': [
            'trac_hub = trac_hub',

        ]    
    }

)
