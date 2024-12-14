from functools import cached_property
from pydantic import BaseModel, validator
from typing import Optional
import enum
from aenum import Enum as AEnum, extend_enum
import re

from jinja2 import Environment, meta

ALEXLAB_JINJA_ENV = Environment(variable_start_string="{{", variable_end_string="}}")

class LanguageEnum(str, enum.Enum):
    NA = 0
    fr = "fr"
    de = "de"
    it = "it"
    ar = "ar"
    en = "en"
    nl = "nl"
    pl = "pl"
    es = "es"
    el = "el"
    cs = "cs" 
    da = "da"
    sk = "sk" 
    sv = "sv"
    sw = "sw"
    ro = "ro"

    def __str__(self):
        return str(self.value)


country_mapping = {
    'NA': 'NA',
    'Switzerland': 'ch',
    'Germany': 'de',
    'France': 'fr',
    'Netherlands': 'nl',
    'Spain': 'es',
    'Italy': 'it',
    'Poland': 'pl',
    'Great Britain': 'gb',
    'United States': 'us'
}
subregion_mapping = {
    'Bavaria': 'de', 'Hessen': 'de'
}

# Map Country, Subregion and Country Code names to Country Codes
region_mapping = {**subregion_mapping, **country_mapping, **{value: value for value in country_mapping.values()}}

# The class was originally overloaded to also inadvertently
# include Bavaria and Hessen this should be called RegionEnum
# when we're able to replace all its invocations lying around
class CountryEnum(AEnum):  
    def __str__(self): return self.name
    def to_cc(self): return region_mapping[self.name]

    # Country implies language
    # TODO: no match between a 'ar', 'cs', 'gb' country and a language
    def to_languages(self) -> list[LanguageEnum]:
        return [LanguageEnum(self.value), LanguageEnum.en]

class DiffStatus(str, enum.Enum):
    new = "new"
    upd = "upd"
    dup = "dup"


class PlatformEnum(str, enum.Enum):
    tiktok = "tiktok"
    youtube = "youtube"
    copilot = "copilot"
    gemini = "gemini"

    @property
    def is_search_engine(self):
        return self in [PlatformEnum.tiktok, PlatformEnum.youtube]


class ArgumentStatus(str, enum.Enum):
    discarded = "discarded"
    draft = "draft"

class PlaceholderArgument(BaseModel):
    """
    Represents an argument for a placeholder in a template.

    Attributes:
        value (str): The value of the argument.
        countries (list[CountryEnum]): The list of countries where this argument is applicable.
        status (ArgumentStatus): The status of the argument.
    """
    
    value: str
    countries: list[CountryEnum]
    status: ArgumentStatus


class AlexlabVariable(BaseModel):
    """
    Represents a variable in a template, consisting of a placeholder and its arguments.

    Attributes:
        placeholder (str): The placeholder name.
        arguments (list[PlaceholderArgument]): The list of arguments for the placeholder.
    """
    placeholder: str
    arguments: list[PlaceholderArgument]


class AlexlabTemplate(BaseModel):
    """
    Represents a template for generating prompts.

    Attributes:
        name (str): The name of the template.
        values (str): The template string with placeholders.
        target_countries (list[CountryEnum]): The list of target countries for the template.
        target_platforms (list[PlatformEnum]): The list of target platforms for the template.
        language (LanguageEnum): The language of the template.
        target_languages (list[LanguageEnum]): The list of target languages for the template.
        status (str): The status of the template.
        rev_date (str): The revision date of the template.
        experiment_slug (str): The experiment slug associated with the template.
    """
    name: str
    values: str
    target_countries: list[CountryEnum]
    target_platforms: list[PlatformEnum]
    language: LanguageEnum
    target_languages: list[LanguageEnum]
    status: str  # TODO: StatusEnum?
    rev_date: str
    experiment_slug: str

    @property
    def placeholders(self) -> list[str]:
        """
        Retrieves the list of placeholders in the template string.

        Returns:
            list: A list of placeholders in the template string.
        """
        return list(meta.find_undeclared_variables(
            ALEXLAB_JINJA_ENV.parse(self.values)
        ))

    @validator('values')
    def canonise_values(cls, v):
        """
        Canonizes the placeholder values in the template string to a standard format.

        Args:
            v (str): The template string with placeholders.

        Returns:
            str: The template string with placeholders in the standard format.
        """
        pattern = r"\{(.*?)\}"

        # TODO: just like interpolate_template_and_arguments() this only supports max 1 placeholder 
        def replacement(match):
            return f"{{{{{match.group(1).lower()}}}}}"

        # Replace placeholders with the desired format
        v = re.sub(pattern, replacement, v)
        return v


class AlexlabInterpolation(BaseModel):
    """
    Represents an interpolation of a template with specific arguments.

    Attributes:
        language (LanguageEnum): The language of the interpolation.
        country (CountryEnum): The country of the interpolation.
        text (str): The interpolated text.
        rev_date (str): The revision date of the interpolation.
        placeholder (Optional[str]): The placeholder used in the interpolation.
        template (AlexlabTemplate): The template used for the interpolation.
        target_platforms (Optional[list[PlatformEnum]]): The list of target platforms for the interpolation.
        arguments (list[str]): The list of arguments used in the interpolation.
        is_translated (bool): Indicates whether the interpolation is translated.
        is_latest_rev (bool): Indicates whether this is the latest revision of the interpolation.
    """    
    language: LanguageEnum
    country: CountryEnum
    text: str
    rev_date: str
    placeholder: Optional[str]
    template: AlexlabTemplate
    target_platforms: Optional[list[PlatformEnum]] = []
    arguments: list[str]
    is_translated: bool
    is_latest_rev = True

    @staticmethod
    def sluggify(s: str) -> str:
        return s.strip().lower().replace(" ", "-").replace("\n", "-")

    @property
    def slug(self) -> str:
        values_to_use_in_slug = [self.template.name, self.country.value, self.language.value, *self.arguments]
        return "__".join([self.sluggify(v) for v in values_to_use_in_slug])

    @property
    def experiment_slug(self) -> str:
        return self.template.experiment_slug