from app.crawlers import all_names, build


def test_all_nine_crawlers_registered() -> None:
    expected = {
        "yahoo_finance",
        "mfn",
        "riksbank",
        "scb",
        "fred",
        "esap",
        "fi_insider",
        "fi_short",
        "company_ir_rss",
    }
    assert set(all_names()) == expected


def test_each_crawler_constructible() -> None:
    for name in all_names():
        crawler = build(name)
        assert crawler.name == name
