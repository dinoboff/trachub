"""
Created on 12 Mar 2009

@author: Damien Lebrun
"""
from datetime import datetime

from trac.core import Component, implements
from trac.ticket.model import Ticket
from trac.util.datefmt import utc
from trac.config import Option

from trac_hub.post_parser import IGitHubPostObserver


class GitHubTicketUpdater(Component):
    """
    Update ticket from commit message sent to a github project and its clones.
    """

    implements(IGitHubPostObserver)
    
    status_for_ticket_update = Option('trachub', 'status_for_ticket_update', '',
        doc="""
        When a commit from your main repository updates a ticket,
        what should the status of the ticket been set to?""")
    resolution_for_ticket_update = Option('trachub', 'resolution_for_ticket_update', 'fixed',
        doc="""
        When a commit from your main repository updates a ticket,
        what should the resolution of the ticket been set to?""")
    
    status_for_clone_ticket_update = Option('trachub', 'status_for_clone_ticket_update', '',
        doc="""
        When a commit from a cloned repository updates a ticket,
        what should the status of the ticket been set to?""")
    resolution_for_clone_ticket_update = Option('trachub', 'resolution_for_clone_ticket_update', '',
        doc="""
        When a commit from a cloned repository updates a ticket,
        what should the resolution of the ticket been set to?""")
    
    def process_commit(self, commit):
        """
        Update ticket using message from commit
        """
        try:
            original = commit.get_original_commit()
        except:
            original = None
        
        if not commit.is_clone() or \
            original is None  or \
            commit.message != original.message:
            
            for action, ticket_id in commit.parse_message():
                try:
                    ticket = Ticket(self.env, ticket_id)
                    self._update_ticket(ticket, action, commit)                   
                    msg = "Commit %s:\n\n%s\n\nSource: [%s]" % (commit.id, commit.message, commit.url,)
                    ticket.save_changes(
                        commit.author,
                        msg,
                        when=datetime.fromtimestamp(commit.time, utc))
                except Exception, e:
                    self.log.error('Could not update ticket %s with commit %s: %s' % (
                        ticket_id,commit.id,str(e),))
    
    def _update_ticket(self, ticket, action, commit):
        """
        Will set tickets resolution and status according default and depending
        of the kind of repository the commit comes from.
        """
        if commit.is_clone():
            if self.resolution_for_clone_ticket_update:
                ticket['resolution'] = self.resolution_for_clone_ticket_update
            if self.status_for_clone_ticket_update:
                ticket['status'] = self.status_for_clone_ticket_update
        else:
            if self.resolution_for_ticket_update:
                ticket['resolution'] = self.resolution_for_ticket_update
            if self.status_for_ticket_update:
                ticket['status'] = self.status_for_ticket_update