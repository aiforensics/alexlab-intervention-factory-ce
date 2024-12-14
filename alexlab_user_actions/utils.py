import os 
import re

from alexlab_user_actions.alexlab_models import CountryEnum, LanguageEnum

def find(lst, condition):
    for item in lst:
        if condition(item):
            return item
    return None

def existing_filepath_type(string):
    if os.path.isfile(string):
        return string
    else:
        raise FileNotFoundError(string)

def valid_filepath_type(string):
    """ Checks if a file path is valid."""
    file_path_regex = re.compile(r'^(\/|(\/?[^\/\0]+\/?)*[^\/\0]+)$')
    if file_path_regex.match(string):
        return string
    else:
        raise ValueError(string)


def trailing_platform_slug(slug, platform):
    return "__".join([slug, platform])


def shorten(string: str):
    return string[:1]


def country_language_pairs(arg):
    # For simplity, assume arg is a pair of integers
    # separated by a colon. If you want to do more
    # validation, raise argparse.ArgumentError if you
    # encounter a problem.
    [country, language] = arg.split(':')
    return (CountryEnum(country),LanguageEnum(language))
