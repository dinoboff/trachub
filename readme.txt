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
        trac.versioncontrol.* = disabled
        

        [trachub]
        # url of your main project
        # all of your commit url should start with it.
        github_url = http://github.com/yourusername/yourprojectname/
        
        # when one of your commit fixed an issue,
        # how should the ticket be updated.
        # (empty mean not change)
        status_for_ticket_update = 
        resolution_for_ticket_update = fixed
        
        # Same settings,
        # but for commit comming from cloned repository
        status_for_clone_ticket_update =
        resolution_for_clone_ticket_update = 
        
    5. Go to the Admin page for your project on GitHub. Then select the services tab.
        Under the: Post-Receive URLs
        Place a link to your Trac repository, in a format like this:
        
        http://yourdomian.com/projects/projectname/github/
