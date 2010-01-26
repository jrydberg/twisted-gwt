# integration with twisted.web

from twisted.web import resource, server
from twisted.python import log
from xtwisted.gwt import rpc


class ServiceServlet(rpc._ServiceServlet, resource.Resource):
    """Service servlet to be used with TwistedWeb.
    """
    isLeaf = True
    encoding = "UTF-8"

    def render(self, request):
        def finish(content):
            content = content.encode('utf-8')
            # FIXME: do we need to set the content-length header?
            request.setHeader("Content-Type", "text/x-gwt-rpc; charset=utf-8")
            request.setHeader("Content-length", len(content))
            request.write(content)
            request.finish()
        self.processRequest(request.content.read()).addBoth(finish).addErrback(log.err)
        return server.NOT_DONE_YET

