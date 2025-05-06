import csv
from typing import Dict, List, Tuple
from collections import defaultdict
from importlib import resources
import logging

from jinja2 import Template as JinjaTemplate

from alexlab_if.alexlab_models import (
    LanguageEnum,
    AlexlabVariable,
    AlexlabInterpolation,
    CountryEnum,
    PlaceholderArgument,
    AlexlabTemplate,
    PlatformEnum,
    DiffStatus
)

logger = logging.getLogger()


def country_languages(country: CountryEnum, extra_country_languages: List[Tuple[CountryEnum, LanguageEnum]] = []): 
    """
    Retrieves the list of target languages for a given country, including any extra country-language pairs.

    Args:
        country (CountryEnum): The country for which to retrieve languages.
        extra_country_languages (List[Tuple[CountryEnum, LanguageEnum]], optional): Additional country-language pairs.

    Returns:
        list: A list of languages for the specified country.
    """
    try:  
        return country.to_languages() + [l for (c,l) in extra_country_languages if c == country]
    except Exception as e:
        print(extra_country_languages)
        raise e




class PromptCounter:
    value = 0


def template_report(counter, template, **kwargs):
    """
    Generates a report for the given template, including the number of arguments and languages.

    Args:
        counter (PromptCounter): A counter for tracking the number of templates.
        template (AlexlabTemplate): The template to report on.
        **kwargs: Additional keyword arguments.
    """
    relevant_variable = kwargs.get("relevant_variable", None)
    arguments_by_country = kwargs.get("arguments_by_country", None)
    valid_countries = kwargs.get("valid_countries", template.target_countries)
    extra_country_languages = kwargs.get("extra_country_languages", [])

    if len(template.placeholders) == 0:
        print(f"No placeholders found.")
    else:
        print(f"Placeholder '{relevant_variable.placeholder}' found.")

    template_tot = 0
    print(f"\nCountry\tArgs\tLangs\tTotal")
    for country in valid_countries:
        arguments_tot = (
            len(arguments_by_country[country]) if arguments_by_country else 0
        )

        languages_tot = len(country_languages(country, extra_country_languages))
        country_tot = languages_tot * max(arguments_tot, 1)
        template_tot += country_tot

        print(f"{country.value}\t{arguments_tot}\t{languages_tot}\t{country_tot}")

    print(f"\nTemplate would generate {template_tot} actions for each platform.")
    counter.value = counter.value + template_tot


def interpolate_template_and_arguments(
    template: AlexlabTemplate,
    variables: list[AlexlabVariable],
    counter=PromptCounter(),
    extra_country_languages = []
) -> List[AlexlabInterpolation]:
    """
    Interpolates the given template with the provided variables and generates a list of interpolations.

    Args:
        template (AlexlabTemplate): The template to interpolate.
        variables (list[AlexlabVariable]): The variables to use for interpolation.
        counter (PromptCounter, optional): A counter for tracking the number of interpolations.
        extra_country_languages (list, optional): Additional country-language pairs.

    Returns:
        list: A list of interpolations.
    """
   
    # case 0: no placeholders
    if len(template.placeholders) == 0:
        template_report(counter, template)

        return [
            AlexlabInterpolation(
                text=template.values,
                template=template,
                country=country,
                language=target_language,
                placeholder=None,
                rev_date=template.rev_date,
                arguments=[],
                is_translated=(target_language == template.language),
            )
            for country in template.target_countries
            for target_language in template.target_languages if target_language in country_languages(country, extra_country_languages)
        ]

    # case 1: exactly one placeholder
    elif len(template.placeholders) == 1:
        placeholder = list(template.placeholders)[0]
        relevant_placeholders = list(
            filter(lambda v: v.placeholder == placeholder, variables)
        )
        if not relevant_placeholders:
            
            print("Not relevant placeholders: ")
            print(variables)
    
            raise ValueError(
                f"Placeholder {placeholder} was found in the template, but no arguments were provided for it."
            )
        relevant_variable = relevant_placeholders[0]  # since there is only one
        arguments_by_country: defaultdict[CountryEnum, list[str]] = defaultdict(list)
        for argument_value in relevant_variable.arguments:
            for country in argument_value.countries:
                arguments_by_country[country].append(argument_value.value)
        valid_countries = set(template.target_countries).intersection(
            set(arguments_by_country.keys())
        )
        missing_countries = set(template.target_countries).difference(
            set(valid_countries)
        )
        if missing_countries:
            raise ValueError(
                f"Missing arguments for countries {missing_countries} for placeholder '{relevant_variable.placeholder}'"
            )
        jinja_template = JinjaTemplate(template.values)

        template_report(
            counter,
            template,
            relevant_variable=relevant_variable,
            arguments_by_country=arguments_by_country,
            valid_countries=valid_countries,
        )

        return [
            AlexlabInterpolation(
                text=jinja_template.render({relevant_variable.placeholder: value}),
                template=template,
                country=country,
                language=target_language,
                placeholder=relevant_variable.placeholder,
                rev_date=template.rev_date,
                arguments=[value],
                is_translated=(target_language == template.language),
            )
            for country in valid_countries
            for value in arguments_by_country[country]
            for target_language in template.target_languages if target_language in country_languages(country, extra_country_languages)
        ]
    # case 2: more than one placeholder
    else:
        # the result has to be a matrix multiplication product per country
        # if a template references two or more placeholders, they have to be defined for all target countries
        raise NotImplementedError("Only one placeholder is allowed per template")


def load_templates_from_csv(input_template_path) -> list[AlexlabTemplate]:
    """
    Loads templates from a CSV file.

    Args:
        input_template_path (str): The path to the CSV file containing templates.

    Returns:
        list: A list of loaded templates.
    """
    
    csv_rows = _load_csv_file(
        input_template_path
    )
    
    header = csv_rows[0]
    rows = csv_rows[1:]

    templates = []
    for raw_row in rows:
        row = { col_name: raw_row[i] for i, col_name in enumerate(header) }
        template = AlexlabTemplate(
                name=row["template_slug"],
                values=row["values"],
                language=LanguageEnum(row["language"]),
                target_countries=[
                    CountryEnum(tc) for tc in row["target_countries"].split(",")
                ],
                rev_date = row["rev_date"],
                target_platforms=[
                    PlatformEnum(tp) for tp in row["target_platforms"].split(",")
                ],
                target_languages=[
                    LanguageEnum(tl) for tl in row["target_languages"].split(',')
                ],
                status=row["status"],
                experiment_slug=row["experiment_slug"],
            )

        templates.append(template)

    return templates


def load_arguments_from_csv(input_argument_path) -> dict[str, list[AlexlabVariable]]:
    """
    Loads arguments from a CSV file.

    Args:
        input_argument_path (str): The path to the CSV file containing arguments.

    Returns:
        dict: A dictionary of arguments grouped by placeholder.
    """
    # skipping the header
    
    csv_rows = _load_csv_file(
        input_argument_path
    )
    header = csv_rows[0]
    rows = csv_rows[1:]
    csv_rows = rows

    rows_by_placeholder = defaultdict(list)
    for raw_row in csv_rows:
        row = { col_name: raw_row[i] for i, col_name in enumerate(header) }
        placeholder = row["placeholder"]
        rows_by_placeholder[placeholder].append(row)

    variables = []
    for placeholder, placeholder_rows in rows_by_placeholder.items():
        arguments = []
        for placeholder_row in placeholder_rows:

            arguments.append(
                PlaceholderArgument(
                    value=placeholder_row["value"],
                    countries=[
                        CountryEnum(country) for country in placeholder_row["target_countries"].split(",")
                    ],
                    status=placeholder_row["status"]
                )
            )
        variables.append(AlexlabVariable(placeholder=placeholder.lower(), arguments=arguments))

    return {variable.placeholder: variable for variable in variables}


def _load_csv_file(csv_file_path: str):
    """
    Loads the contents of a CSV file.

    Args:
        csv_file_path (str): The path to the CSV file.

    Returns:
        list: A list of rows from the CSV file.
    """
    with open(csv_file_path, "rt") as csvfile:
        return [row for row in csv.reader(csvfile)]
