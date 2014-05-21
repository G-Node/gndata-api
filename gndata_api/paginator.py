import urlparse
from django.core.paginator import Paginator


class ListPaginator(object):

    def __init__(self, sorted_objects, original_url, offset, limit):
        self._original_url = original_url
        self._offset = offset
        self._limit = limit
        self._paginator = Paginator(sorted_objects, limit)

    def _generate_url(self, offset, limit):
        scheme, loc, path, query, frag = urlparse.urlsplit(self._original_url)

        query_dict = {}
        if len(query) > 0:
            query_dict = dict([x.split('=') for x in query.split('&')])

        query_dict['offset'] = str(offset)
        query_dict['limit'] = str(limit)

        new_query = '&'.join(['='.join([k, v]) for k, v in query_dict.items()])

        return urlparse.urlunsplit((scheme, loc, path, new_query, frag))

    def page(self, number=None):
        """ returns object list for a given (or current) page number """
        return self._paginator.page(number or self.current_page_num)

    @property
    def offset(self):
        return self._offset

    @property
    def limit(self):
        return self._limit

    @property
    def num_pages(self):
        return self._paginator.num_pages

    @property
    def current_page_num(self):
        """ 1-based current page number """
        return (self.offset / self.limit) + 1

    @property
    def previous(self):
        """ URL to fetch previous page """
        if self.current_page_num > 1:
            return self._generate_url(self.offset - self.limit, self.limit)
        else:
            return None

    @property
    def pre_previous(self):
        """ URL to fetch pre-previous page """
        if self.current_page_num > 2:
            return self._generate_url(self.offset - (2*self.limit), self.limit)
        else:
            return None

    @property
    def next(self):
        """ URL to fetch next page """
        if self.current_page_num < self._paginator.num_pages:
            return self._generate_url(self.offset + self.limit, self.limit)
        else:
            return None

    @property
    def post_next(self):
        """ URL to fetch post-next page """
        if self.current_page_num < self._paginator.num_pages - 1:
            return self._generate_url(self.offset + (2*self.limit), self.limit)
        else:
            return None