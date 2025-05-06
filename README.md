# Alexlab Intervention Factory Community Edition ![Alexlab User Actions Community Edition](alexlab-user-actions.png "Alexlab Intervention Factory Community Edition") 

The software processes templates and arguments to generate interventions at scale (i.e. localised prompts for chatbot platforms such as Copilot and Gemini, or localised search queries for TikTok and Youtube). 

1. **Templates and Arguments**: Please see the `example_data/` folder for an example structure of templates and arguments.
The basic requirement is that each value in the template file may or may not contain a placehoder enclosed in curly brackets, such as "{TOPIC}", and that the arguments file contains one or more arguments, each relevant to one or more different countries, for each of the placeholders mentioned in the templates.

2. **Template Interpolation**: The software interpolates the templates with the provided arguments. This involves replacing the placeholders in the templates with the corresponding argument values.

3. **Prompts and Search Queries Production**: The interpolated templates are used to generate user actions which:
    - **(translation)** 
    may or may not be translated, based on the target countries and languages
    - **(stopword removal)** may have their stopwords removed through the YAKE algorithm, in case they are to be a search query. 

These actions are then saved to a CSV file.

## Country implies language, if you will
By default, there is a strong assumption that for each target country actions should be generated only in English (if it is the original language of the template) and in the language whose code corresponds to the country code (e.g. `es` for Spanish and Spain). You change change this behaviour by using the `--ecl` parameter.

## Translation 
By default, to perform translations the module will use the HuggingFace Space [`aiforensics/opus-mt-translation-ce`](https://huggingface.co/spaces/aiforensics/opus-mt-translation-ce) which hosts a Gradio service to run the open-source machine translation Opus-MT models, developed by the Language Technology Research Group at the University of Helsinki, through the EasyNMT library. 

Translations are supported for French, German, Italian, Arabic, English, Dutch, Polish, Spanish, Greek, Czech, Danish, Slovak, Swedish, Swahili, Romanian for any of the translation directions listed as source-target language pairs [here](https://huggingface.co/models?search=opus-mt). Please note that for the lack of it in said list, English to Polish is performed as a double translation: first into German, and then into Polish, with translations that require extra care in quality assessment.

To make translations quicker, you can either:
- make your own private clone of our HF Space, assign additional resources to it, rather than the default CPU, and then use the `--hf-space` and `--hf-token` to access it.
- run with Docker (see below).

## How to install

`git clone https://github.com/aiforensics/alexlab-intervention-factory-ce.git`

`cd alexlab-intervention-factory-ce`

`pip install -r requirements.x`

`pip install .`

## How to run

```
python -m alexlab_if --input-templates 'example_data/templates.csv' --input-arguments 'example_data/arguments.csv' --output './output.csv'
````



### Run translations with Docker (optional)

Please ensure you have nvidia-docker2 installed ([see here](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)).
Then run:

```
docker run -it -p 7860:7860 --platform=linux/amd64 --gpus all \
	registry.hf.space/aiforensics-opus-mt-translation-ce:gpu-3e6cebd python app.py
```

Use `localhost:7860` as the URL for `--hf-space`.

## Options
  **--input-templates** INPUT_TEMPLATES (required)

  Path to the input templates CSV file.
  
  **--input-arguments** INPUT_ARGUMENTS (required)

  Path to the input arguments CSV file.
  
  **--output** OUTPUT (required)
  
  Path to the output CSV file. 
  
  **--dry-run** | **--no-dry-run**
  
  Don't generate the actions, only report the changes that would be made by running the input files                        
  
  **--translate** | --no-translate
                                              
  Use the translation service (default: true)
  
  **--hf-space** HF_SPACE   
  
  HuggingFace Space to use for translations (optional)
  
  **--hf-token** HF_TOKEN   
  
  HuggingFace Token to use for translations (optional)
  
  
  
  **--ecl** ECL [ECL ...]   
  
  List of target extra country-language pairs for the user actions in  (see the "Country implies language section"). 
  
  E.g., to generate for example French and Dutch translations for Belgium), use `--ecl be:fr be:nl`.

## Funding
This contribution from AI Forensics is funded by a project grant from [NGI Search](https://www.ngisearch.eu/view/Main/).
