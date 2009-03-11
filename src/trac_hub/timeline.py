"""
Created on 8 Mar 2009

@author: damien
"""
from datetime import datetime

from trac.core import implements, Component
from trac.timeline.api import ITimelineEventProvider
from trac.config import Option
from trac.util.datefmt import utc, to_timestamp
from genshi.builder import tag

from trac_hub.model import GitHubCommit as GitHubEvent
from trac.util import html
from cgi import escape

__all__ = ['GitHubEventProvider']

class GitHubEventProvider(Component):
    """
    Save new commits event to the database
    and provide GitHub event to Trac's time line
    """
    implements(ITimelineEventProvider)
    
    github_url = Option('trachub', 'github_url', '',
        doc="""Your main GitHub repository (like http://github.com/username/projectname).""")

        
    def get_timeline_filters(self, req):
        """
        Return a list of filters that this provider support: commits for the main repository
        and commits from its clones.
        """
        return (
            ('main_git_repository','Main repository commits'),
            ('cloned_git_repository','Cloned repository commits'),
            )

    def get_timeline_events(self, req, start, stop, filters):
        """
        Return a list of events in the time range given by the `start` and
        `stop` parameters.

        The `filters` parameters is a list of the enabled filters, each item
        being the name of the tuples returned by `get_timeline_filters`.

        Since 0.11, the events are `(kind, date, author, data)` tuples,
        where `kind` is a string used for categorizing the event, `date`
        is a `datetime` object, `author` is a string and `data` is some
        private data that the component will reuse when rendering the event.

        When the event has been created indirectly by another module,
        like this happens when calling `AttachmentModule.get_timeline_events()`
        the tuple can also specify explicitly the provider by returning tuples
        of the following form: `(kind, date, author, data, provider)`.
        """
        if 'main_git_repository' in filters or \
            'cloned_git_repository' in filters:
            
            for event in GitHubEvent.get_commit_by_date(
                self.env, to_timestamp(start), to_timestamp(stop), git_url=self.github_url):
                
                if event.is_clone() and 'cloned_git_repository' in filters:
                    yield ('cloned_git_repository',
                        datetime.fromtimestamp(event.time, utc),
                        event.author,
                        event)
                elif not event.is_clone() and 'main_git_repository' in filters:
                    yield ('main_git_repository',
                        datetime.fromtimestamp(event.time, utc),
                        event.author,
                        event) # TODO: only sent needed data


    def render_timeline_event(self, context, field, event):
        """
        Display the title of the event in the given context.

        :param context: the rendering `Context` object that can be used for
                        rendering
        :param field: what specific part information from the event should
                      be rendered: can be the 'title', the 'description' or
                      the 'url'
        :param event: the event tuple, as returned by `get_timeline_events`
        """
        ghevent = event[3]
        if field == 'url':
            return tag(ghevent.url) # TODO find out how do you use context
        elif field == 'title':
            return tag('Revision ', tag.em(ghevent.id))
        elif field == 'description':
            return tag(ghevent.message)