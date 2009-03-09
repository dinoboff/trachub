This trac plugin is designed to accept a GitHub Post-Receive url for a project and its clone.

It also allows you to replace the builtin Trac browser with redirects to the GitHub source browser (TODO).

More information about the Post-Receive Hook can be found here:
http://github.com/guides/post-receive-hooks

To install this Trac Plugin:

    1. Clone the repository:
        git clone git@github.com:dinoboff/trachub.git

    2. Install SimpleJSON:
        easy_install simplejson

    3. Install the Plugin:
        cd trachub
        sudo python setup.py install

    4. Configure Trac by editing your trac.ini
        
        [components]
        trachub.* = enabled

        [trachub]
		github_url = http://github.com/yourusername/yourprojectname/
        
    5. Go to the Admin page for your project on GitHub. Then select the services tab.
        Under the: Post-Receive URLs
        Place a link to your Trac repository, in a format like this:
        
        http://yourdomian.com/projects/projectname/github/