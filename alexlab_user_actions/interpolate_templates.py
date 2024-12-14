import logging
from alexlab_user_actions.ActionDataFrame import ActionDataFrame
from alexlab_user_actions.alexlab_models import AlexlabInterpolation, DiffStatus, PlaceholderArgument
from alexlab_user_actions.keyword_extraction import prompt_to_search_query
from alexlab_user_actions.template_rendering import PromptCounter, interpolate_template_and_arguments, load_arguments_from_csv, load_templates_from_csv
from alexlab_user_actions.translation import TranslationService
from alexlab_user_actions.utils import shorten, trailing_platform_slug

from dateutil import tz

import pandas as pd
from dateutil.parser import parse as parsedate
from tqdm import tqdm

from collections import Counter

logger = logging.getLogger()

UTC = tz.gettz("UTC")

def interpolate_templates(
    output_path: str = None,
    should_translate: bool = True,
    extra_country_languages = [],
    input_template_path: str = None,
    input_argument_path: str = None,
    dry_run: bool = True,
    translation_service: TranslationService = None,
):
    """
    Interpolates templates with arguments and generates user actions.

    Args:
        output_path (str, optional): The path which might contain the existing list of actions and where to save the updated list as a CSV file.
        should_translate (bool, optional): Whether to translate the interpolations.
        extra_country_languages (list, optional): Additional country-language pairs.
        input_template_path (str, optional): The path to the input template CSV file.
        input_argument_path (str, optional): The path to the input argument CSV file.
        dry_run (bool, optional): Whether to perform a dry run without saving the output.
    """

    ts = translation_service

    if dry_run:
        print(f"Dry run launched")

    templates_to_import = load_templates_from_csv(input_template_path)
    arguments_by_placeholder = load_arguments_from_csv(input_argument_path)

    try :
        output_df = pd.read_csv(output_path)
    except FileNotFoundError:
        output_df = ActionDataFrame()

    if output_df.empty:
        print("No existing file found")

    else:
        print("Existing file found")

    existing_action_records = output_df[output_df["is_latest_rev"] == True] if not output_df.empty else ActionDataFrame()

    # get slugs in the format name__cc__lang__platform
    existing_slugs = {
        trailing_platform_slug(record["slug"], record["platform"]): {
            "id": index,
            "rev_date": record["rev_date"],
        }
        for index, record in existing_action_records.iterrows()
    }

    print(f"Found {len(existing_slugs)} existing records")

    counter = PromptCounter()
    diff_counter = Counter({DiffStatus.new.name:0, DiffStatus.dup.name:0, DiffStatus.upd.name: 0})
    outdated_arguments = set([])


    for template in tqdm(templates_to_import,
        desc="Rendering template",
        total=len(templates_to_import),
        disable=dry_run,
    ):
        try:

            print(
                f"\n\n\033[1m{template.name}\033[0m now processing…",
            )

            interpolations = interpolate_template_and_arguments(
                template=template,
                variables=arguments_by_placeholder.values(),
                counter=counter,
                extra_country_languages=extra_country_languages
            )

            relevant_interpolations = []

            outdated_record_ids = []

            print("\nChanges")

            for interpolation in interpolations:

                target_platforms = []

                # For reporting only
                new = []
                dup = []
                upd = []

                interpolation_rev = parsedate(interpolation.rev_date)
                interpolation_rev = interpolation_rev.replace(tzinfo=UTC)


                for platform in template.target_platforms:

                    # get slug in the format name__cc__lang__platform
                    candidate_slug = trailing_platform_slug(
                        interpolation.slug, platform
                    )

                    slug_already_exists = candidate_slug in existing_slugs

                    # Case 1: never existed
                    if not slug_already_exists:
                        new.append(platform.value)
                        target_platforms.append(platform)
                    else:
                        # Case 2: exists and is the same (template string is the same, argument slug is the same)

                        candidate_rev = parsedate(existing_slugs[candidate_slug]["rev_date"])
                        candidate_rev = candidate_rev.replace(tzinfo=UTC)

                        # TODO: look in the database to also resume when half-done with new source files
                        if slug_already_exists and (interpolation_rev == candidate_rev):
                            dup.append(platform.value)
                            pass

                        # Case 3: exists but got an update
                        # TODO: look in the database to also resume when half-done with new source files
                        elif slug_already_exists and  (interpolation_rev != candidate_rev):
                            upd.append(platform.value)
                            outdated_record_ids.append(existing_slugs[candidate_slug]["id"])

                            target_platforms.append(platform)

                # Interpolation report
                prefix = f"{interpolation.country.value} {interpolation.language.value} {' '.join(interpolation.arguments)}"
                for label, lst in [("NEW", new), ("DUP", dup), ("UPD", upd)]:
                    if len(lst) > 0:
                        print(
                            f"{label} {prefix}:\t{','.join (map(shorten, lst))}",
                        )

                if len(target_platforms) > 0:
                    interpolation.target_platforms = target_platforms

                    relevant_interpolations.append(interpolation)

                diff_counter.update({
                    DiffStatus.new.name: len(new),
                    DiffStatus.dup.name: len(dup),
                    DiffStatus.upd.name: len(upd)
                })

            # Template report
            logger.debug(f"Outdated records for {template.name}: {outdated_record_ids}")

            # TODO: just like interpolate_template_and_arguments() this only supports max 1 placeholder 
            if len(template.placeholders) == 1:
                # Identify outdated arguments
                placeholder = template.placeholders[0]

                if placeholder in arguments_by_placeholder:

                    template_outdated_arguments: list[PlaceholderArgument] = [
                        argument
                        for argument in arguments_by_placeholder[placeholder].arguments
                        if argument.status == 'discarded'
                    ]

                    outdated_arguments.update([argument.value for argument in template_outdated_arguments])

                    template_outdated_argument_slugs = []
                    if len(template_outdated_argument_slugs) > 0:

                        print(f"Outdated arguments for template: {template_outdated_argument_slugs}")

                        for slug in existing_slugs:
                            slug_parts = slug.split("__")

                            if slug_parts[0] != AlexlabInterpolation.sluggify(
                                template.name
                            ):
                                continue

                            for argument in template_outdated_arguments:
                                for country in argument.countries:
                                    for lang in country.to_languages():
                                        # Early fail
                                        if (
                                            slug_parts[3]
                                            == AlexlabInterpolation.sluggify(argument.value)
                                            and slug_parts[2] == lang.value
                                            and slug_parts[1] == country.value
                                        ):
                                            template_outdated_argument_slugs.append(slug)
                                            outdated_record_ids.append(
                                                existing_slugs[slug]["id"]
                                            )

                        print(f"Outdated argument slugs: {template_outdated_argument_slugs}")
                else:
                    raise ValueError(f"Found no arguments for placeholder '{placeholder}'")

            if dry_run:
                print(
                    "-------------------------------------------------------------------------"
                )
                continue

            translated_interpolations = []
            if should_translate:
                for interpolation in tqdm(
                    relevant_interpolations, desc="\ttranslating", leave=False
                ):
                    if not interpolation.is_translated:
                        if not translation_service:
                            raise ValueError("Translation service is required for translation.")
                        print(
                            f"Translating {interpolation.slug}",
                        )
                        translation = ts.translate(
                            text=interpolation.text,
                            source_lang=interpolation.template.language,
                            target_lang=interpolation.language,
                        )
                        interpolation.text = translation
                        interpolation.is_translated = True

                    translated_interpolations.append(interpolation)
            else:
                translated_interpolations = relevant_interpolations

            # Marks every row in the df where record_id is in outdated_record_ids
            output_df.loc[output_df.index.isin(outdated_record_ids), 'is_latest_rev'] = False

            new_records = []
            for interpolation in translated_interpolations:
                for platform in interpolation.target_platforms:

                    values = (
                        prompt_to_search_query(
                            interpolation.text, interpolation.language
                        )
                        if platform.is_search_engine
                        else interpolation.text
                    )
                    print(
                        f"Adding {trailing_platform_slug(interpolation.slug, platform)}",
                    )
                    new_records.append(
                        dict(
                            country=interpolation.country.value,
                            language=interpolation.language.value,
                            platform=platform,
                            values=values,
                            rev_date=interpolation.rev_date,
                            slug=interpolation.slug,
                            experiment_slug=interpolation.experiment_slug,
                            is_latest_rev=True,
                        )
                    )

            new_records_df = pd.DataFrame(new_records)
            output_df = pd.concat([output_df, new_records_df], ignore_index=True)
            output_df.to_csv(output_path, index=False)

        except Exception as e:
            logger.error(f"ERROR: {e}")
            raise e

    if dry_run:
        print(
            f"\n{counter.value} user actions would be generated by this run for each platform."
        )

        print(f"\nTotal {DiffStatus.new.name} actions: {diff_counter[DiffStatus.new.name]}")
        print(f"Total {DiffStatus.dup.name} actions: {diff_counter[DiffStatus.dup.name]}")
        print(f"Total {DiffStatus.upd.name} actions: {diff_counter[DiffStatus.upd.name]}")


        print(f'\nOutdated arguments: {"; ".join(outdated_arguments)}.')
        print("\n")
    else:
        print(f"Successfully updated {output_path}.")