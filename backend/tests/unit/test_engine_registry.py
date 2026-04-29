import app.engine  # noqa: F401  side-effect: register tools
from app.engine.registry import all_specs, specs_for_modules


def test_drivers_module_has_expected_tools() -> None:
    names = {s.name for s in specs_for_modules(["drivers"])}
    expected = {
        "get_price_move",
        "get_benchmark_move",
        "get_peer_returns",
        "get_sector_proxy_return",
        "get_macro_snapshot",
        "get_news_for_company",
        "get_attribution",
    }
    assert expected.issubset(names)


def test_shared_module_has_meta_and_query_tools() -> None:
    names = {s.name for s in specs_for_modules(["shared"])}
    assert "get_company_meta" in names
    assert "ad_hoc_query" in names


def test_descriptions_are_substantive() -> None:
    for spec in all_specs():
        assert len(spec.description) >= 40, spec.name
