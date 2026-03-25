from src.shared.kernel import IdempotencyStore, paginate


def test_idempotency_store_check_and_set():
    store = IdempotencyStore()
    assert store.check_and_set("cmd-1") is True
    assert store.check_and_set("cmd-1") is False


def test_paginate_returns_expected_page_window():
    items = list(range(1, 51))
    page = paginate(items, page=2, page_size=10)
    assert page.total == 50
    assert page.page == 2
    assert page.page_size == 10
    assert page.items == list(range(11, 21))
