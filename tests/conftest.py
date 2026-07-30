def pytest_addoption(parser):
    parser.addoption(
        "--api-key", action="store", default=None, help="API key for supermarkets API"
    )
