# -*- coding: utf-8 -*-

from trac.core import *
from trac.ticket import ITicketChangeListener
import subprocess
import re
import textwrap
import shlex

quoted_re = re.compile('^(?:> ?\n)*> .+\n(?:>(?: .*)?\n)*', re.MULTILINE)

class ZephyrPlugin(Component):
    implements(ITicketChangeListener)
    
    def zwrite(self, id, message, extra_sig=None):
        zclass = self.config.get('ZephyrPlugin', 'class')
        if zclass == '':
            return
        command = shlex.split(self.config.get('ZephyrPlugin', 'command').encode('utf-8'))
        if not command:
            command = ['zwrite', '-q', '-l', '-d', '-x', 'UTF-8']
        opcode = self.config.get('ZephyrPlugin', 'opcode')
        if opcode:
            command += ['-O', opcode]
        signature = self.config.get('ZephyrPlugin', 'signature')
        if extra_sig:
            if signature:
                signature = "%s: %s" % (signature, extra_sig, )
            else:
                signature = extra_sig
        if signature:
            command += ['-s', signature]
        p = subprocess.Popen(command +
                             ['-c', zclass,
                              '-i', 'trac-#%s' % id],
                             stdin=subprocess.PIPE)
        p.stdin.write(message.replace('@', '@@').encode('utf-8', 'replace'))
        p.stdin.close()
        p.wait()

    def format_text(self, text):
        text = re.sub(quoted_re, u'> […]\n', text)
        lines = textwrap.fill(text).split('\n')
        if len(lines) > 5:
            lines = lines[:5] + [u'[…]']
        return '\n'.join(lines)
    
    def get_url(self, ticket):
        return ticket.env.abs_href.ticket(ticket.id)

    def ticket_created(self, ticket):
        ttype='ticket'
        if ticket['type'] != 'defect':
            ttype=ticket['type']
        message = "%s filed a new %s %s:\n%s\n\n%s" % (ticket['reporter'],
                                                           ticket['priority'],
                                                           ttype,
                                                           ticket['summary'],
                                                           self.format_text(ticket['description']))
        self.zwrite(ticket.id, message, extra_sig=self.get_url(ticket))
    
    def ticket_changed(self, ticket, comment, author, old_values):
        message = "(%s)\n" % ticket['summary']
        for field in ticket.fields:
            name = field['name']
            if name not in old_values:
                pass
            elif field['type'] == 'textarea':
                message += "%s changed %s to:\n%s\n" % (author, name, self.format_text(ticket[name]))
            elif ticket[name] and old_values[name]:
                message += "%s changed %s from %s to %s.\n" % (author, name, old_values[name], ticket[name])
            elif ticket[name]:
                message += "%s set %s to %s.\n" % (author, name, ticket[name])
            elif old_values[name]:
                message += "%s deleted %s.\n" % (author, name)
            else:
                message += "%s changed %s.\n" % (author, name)
        if comment:
            message += "%s commented:\n%s\n" % (author, self.format_text(comment))
        self.zwrite(ticket.id, message, extra_sig=self.get_url(ticket))
    
    def ticket_deleted(self, ticket):
        message = "%s deleted ticket %d" % (author, ticket.id)
        self.zwrite(ticket.id, message, extra_sig=self.get_url(ticket))
