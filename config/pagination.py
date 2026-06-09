from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardPagination(PageNumberPagination):
    """Standard pagination for most list views."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class FeedPagination(PageNumberPagination):
    """Pagination specifically for feed (posts from followed users)."""

    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50


class CommentPagination(PageNumberPagination):
    """Pagination for comments on a post."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class NotificationPagination(PageNumberPagination):
    """Pagination for user notifications."""

    page_size = 30
    page_size_query_param = "page_size"
    max_page_size = 100


class ChatMessagePagination(PageNumberPagination):
    """Pagination for chat messages."""

    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200


class JobPagination(PageNumberPagination):
    """Pagination for Job Board jobs."""

    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50


class CustomPagination(PageNumberPagination):
    """Custom pagination with additional metadata."""

    def get_paginated_response(self, data):
        return Response(
            {
                "count": self.page.paginator.count,
                "total_pages": self.page.paginator.num_pages,
                "current_page": self.page.number,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "results": data,
            }
        )
