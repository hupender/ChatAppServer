from django.core.paginator import Paginator
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

class Pagination:

    def __init__(self, queryset):
        self.page = 1
        self.page_size = 20
        self.prev = None
        self.next = None
        self.queryset = queryset

    def paginate(self, request):
        page = int(request.GET.get("page", self.page))
        page_size = int(request.GET.get("page_size", self.page_size))

        count = self.queryset.count()

        start_index = page_size * (page - 1)
        end_index = page_size * page

        BASE_URL = request.scheme + "://" + request.get_host()
        full_path = request.get_full_path()

        # previous page exists
        if start_index > 0:
            self.prev = BASE_URL + self.build_path(page-1, page_size, full_path)

        # next page exists
        if end_index < count:
            self.next = BASE_URL + self.build_path(page+1, page_size, full_path)

        return self.queryset[start_index: end_index], self.prev, self.next, count, BASE_URL
    
    def build_path(self, page, page_size, full_path):
        url_parts = urlparse(full_path)
        query_params = parse_qs(url_parts.query)
        query_params['page'] = [str(page)]
        query_params['page_size'] = [str(page_size)]

        updated_query_string = urlencode(query_params, doseq=True)
        updated_url = urlunparse((
            url_parts.scheme,     # e.g., 'http'
            url_parts.netloc,     # e.g., 'example.com'
            url_parts.path,       # e.g., '/search/'
            url_parts.params,     # e.g., ''
            updated_query_string, # Updated query string
            url_parts.fragment    # e.g., ''
        ))

        return updated_url
