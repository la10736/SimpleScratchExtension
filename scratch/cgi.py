__author__ = 'michele'

class CGI():
    def __init__(self, cgi, headers=None):
        self._cgi = cgi
        if headers is None:
            headers = {}
        self._headers = headers

    def __call__(self, request):
        return self._cgi(request)

    @property
    def headers(self):
        return self._headers
