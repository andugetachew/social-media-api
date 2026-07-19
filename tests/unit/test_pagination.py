"""
Tests for config/pagination.py. These are plain PageNumberPagination
subclasses with no custom logic — tests confirm each class's configured
page_size/max_page_size, and CustomPagination's overridden response shape.
"""
from rest_framework.test import APIRequestFactory
from rest_framework.request import Request
from rest_framework.response import Response

from config.pagination import (
    ChatMessagePagination,
    CommentPagination,
    CustomPagination,
    FeedPagination,
    JobPagination,
    NotificationPagination,
    StandardPagination,
)


class TestPaginationClassConfiguration:
    def test_standard_pagination_defaults(self):
        p = StandardPagination()
        assert p.page_size == 20
        assert p.max_page_size == 100
        assert p.page_size_query_param == "page_size"

    def test_feed_pagination_defaults(self):
        p = FeedPagination()
        assert p.page_size == 10
        assert p.max_page_size == 50

    def test_comment_pagination_defaults(self):
        p = CommentPagination()
        assert p.page_size == 20
        assert p.max_page_size == 100

    def test_notification_pagination_defaults(self):
        p = NotificationPagination()
        assert p.page_size == 30
        assert p.max_page_size == 100

    def test_chat_message_pagination_defaults(self):
        p = ChatMessagePagination()
        assert p.page_size == 50
        assert p.max_page_size == 200

    def test_job_pagination_defaults(self):
        p = JobPagination()
        assert p.page_size == 10
        assert p.max_page_size == 50


class TestCustomPagination:
    def test_paginated_response_includes_metadata(self):
        factory = APIRequestFactory()
        request = Request(factory.get("/?page=1"))

        paginator = CustomPagination()
        queryset = list(range(25))
        page = paginator.paginate_queryset(queryset, request)
        response = paginator.get_paginated_response(page)

        assert isinstance(response, Response)
        assert "count" in response.data
        assert "total_pages" in response.data
        assert "current_page" in response.data
        assert "next" in response.data
        assert "previous" in response.data
        assert "results" in response.data
        assert response.data["count"] == 25
        assert response.data["current_page"] == 1

    def test_previous_is_none_on_first_page(self):
        factory = APIRequestFactory()
        request = Request(factory.get("/?page=1"))

        paginator = CustomPagination()
        page = paginator.paginate_queryset(list(range(25)), request)
        response = paginator.get_paginated_response(page)

        assert response.data["previous"] is None

    def test_next_present_when_more_pages_exist(self):
        factory = APIRequestFactory()
        request = Request(factory.get("/?page=1"))

        paginator = CustomPagination()
        page = paginator.paginate_queryset(list(range(50)), request)
        response = paginator.get_paginated_response(page)

        assert response.data["next"] is not None