def pytest_addoption(parser):
    try:
        parser.addoption(
            "--postgresql",
            action="store",
            default=False,
            help="Run the test using postresql"
        )
    except ValueError:
        pass
