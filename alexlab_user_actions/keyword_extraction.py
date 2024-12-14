import string
from functools import lru_cache
from importlib import resources
import logging

import yake

from alexlab_user_actions.alexlab_models import LanguageEnum
logger = logging.getLogger()

def extract_keywords(text: str, language: LanguageEnum):
    """
    Extracts keywords from the given text using the YAKE keyword extraction algorithm.

    Args:
        text (str): The input text from which to extract keywords.
        language (LanguageEnum): The language of the input text.

    Returns:
        list: A list of extracted keywords.
    """

    max_ngram_size = 3
    deduplication_thresold = 0.9
    deduplication_algo = 'seqm'
    window_size = 1
    num_of_keywords = 5

    kw_extractor = yake.KeywordExtractor(
        lan=language.value,
        n=max_ngram_size,
        dedupLim=deduplication_thresold,
        dedupFunc=deduplication_algo,
        windowsSize=window_size,
        top=num_of_keywords
    )

    keywords = kw_extractor.extract_keywords(text)
    return [keyword for (keyword, score) in keywords]


def prompt_to_search_query(text: str, language: LanguageEnum):
    """
    Converts a prompt text into a search query by removing stopwords and punctuation.

    Args:
        text (str): The input prompt text.
        language (LanguageEnum): The language of the input text.

    Returns:
        str: The search query.
    """    
    return _remove_stopwords(_remove_punctuation(text), language)


@lru_cache
def _get_stopwords(language: LanguageEnum) -> set[str]:
    """
    Retrieves the set of stopwords for the given language.

    Args:
        language (LanguageEnum): The language for which to retrieve stopwords.

    Returns:
        set: A set of stopwords for the specified language.
    """    
    # lists are copied from the yake library
    stopwords_dir = resources.files("alexlab_user_actions").joinpath("stopwords")
    stopwords_file_path = stopwords_dir / f"stopwords_{language.value}.txt"
    if not stopwords_file_path.is_file():
        print(f"WARNING: No stopword file found for {language.value}")
        confirm = input("Continue? [y/n]")
        if confirm != "y":
            print("Aborted")
            exit()
        else:
            return set()
    with open(str(stopwords_file_path), "r+") as stopwords_file:
        return set(stopwords_file.read().lower().split("\n"))


def _remove_punctuation(text: str):
    punctuation_to_remove = "?"
    translator = str.maketrans('', '', punctuation_to_remove)
    return text.translate(translator)


def _remove_stopwords(text: str, language: LanguageEnum):
    stopwords = _get_stopwords(language)
    return ' '.join([word for word in text.lower().split() if word not in stopwords])
