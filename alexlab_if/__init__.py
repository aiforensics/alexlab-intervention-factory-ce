import argparse
import logging

from alexlab_if.interpolate_templates import interpolate_templates

from alexlab_if.translation import TranslationService
from alexlab_if.utils import country_language_pairs, valid_filepath_type, existing_filepath_type

logger = logging.getLogger()


def main():
    parser = argparse.ArgumentParser()
    
    parser.add_argument(
        "--translate", action=argparse.BooleanOptionalAction, default=True
    )
    parser.add_argument(
        "--hf-space", type=str, default='aiforensics/opus-mt-translation-ce'
    )
    parser.add_argument(
        "--hf-token", type=str, default=None
    )
    parser.add_argument(
        "--dry-run", action=argparse.BooleanOptionalAction, default=False
    )
    parser.add_argument(
        "--input-templates", type=existing_filepath_type, required=True
    )
    parser.add_argument(
        "--input-arguments", type=existing_filepath_type, required=True
    )
    parser.add_argument(
        "--output", type=valid_filepath_type, required=True
    )
    parser.add_argument(
        "--ecl", nargs='+', help='<Optional> Extra country-language pairs, space-separated, e.g.: --ecl de:ar it:ar', default=[]
    )
    args = parser.parse_args()

    translation_service = TranslationService(args.hf_space, args.hf_token)

    import_args = {
        "should_translate": args.translate,        
        "extra_country_languages": [country_language_pairs(cl) for cl in args.ecl],
        "input_template_path": args.input_templates,
        "input_argument_path": args.input_arguments,
        "output_path": args.output,
        "translation_service": translation_service
        
    }

    # Always launch a dry run first
    interpolate_templates(**import_args, dry_run=True)

    # Then launch actual run only if it's not a dry run
    if (not args.dry_run):
        confirm = input("Confirm? [y/n]")
        if confirm != "y":
            print("Aborted")
            exit()
        else:
            interpolate_templates(**import_args, dry_run=False)


if __name__ == "__main__":
    main()