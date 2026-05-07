from . import the_silver_searcher


class ThePlatinumSearcher(the_silver_searcher.TheSilverSearcher):
    # same implementation, different executable
    pass


engine_class = ThePlatinumSearcher
