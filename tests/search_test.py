from gateway.search import should_run_crawl


def test_should_run_crawl():
    # If force_crawl and skip_crawl are False, then run the crawl if crawled_recently is False or searching_path is True.
    assert (
        should_run_crawl(
            force_crawl=False,
            skip_crawl=False,
            searching_path=False,
            crawled_recently=False,
        )
        == True
    )
    assert (
        should_run_crawl(
            force_crawl=False,
            skip_crawl=False,
            searching_path=False,
            crawled_recently=True,
        )
        == False
    )
    assert (
        should_run_crawl(
            force_crawl=False,
            skip_crawl=False,
            searching_path=True,
            crawled_recently=True,
        )
        == True
    )
    assert (
        should_run_crawl(
            force_crawl=False,
            skip_crawl=False,
            searching_path=True,
            crawled_recently=False,
        )
        == True
    )

    # Should always crawl if force_crawl is True
    assert (
        should_run_crawl(
            force_crawl=True,
            skip_crawl=True,
            crawled_recently=False,
            searching_path=True,
        )
        == True
    )

    assert (
        should_run_crawl(
            force_crawl=True,
            skip_crawl=False,
            searching_path=True,
            crawled_recently=False,
        )
        == True
    )

    # If force_crawl is False, and skip_crawl is True, then never crawl.
    assert (
        should_run_crawl(
            force_crawl=False,
            skip_crawl=True,
            crawled_recently=False,
            searching_path=True,
        )
        == False
    )
