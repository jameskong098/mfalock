import random
import json
import os

default_words = [
    "elderberry", "kale", "orange", "vanilla", "fig", "quince", "grape", "xigua",
    "jalapeño", "nectarine", "lemon", "watermelon", "parsley", "zucchini", "almond",
    "iceberg", "papaya", "garlic", "apple", "tomato", "quinoa", "yam", "mushroom",
    "radish", "eggplant", "date", "leek", "daikon", "vinegar", "broccoli", "spinach",
    "raspberry", "tangerine", "zest", "mango", "cherry", "honeydew",
    "yogurt", "upland", "nutmeg", "kiwi", "wasabi", "ugly", "strawberry", "oregano",
    "horseradish", "banana", "fennel", "carrot"
]

def _load_words_from_settings(settings_path: str, default_list: list) -> list:
    """Loads the word list from settings.json, falling back to the default list."""
    words_to_use = default_list
    using_default_reason = "Using default word list (reason unspecified)." # Default message if logic below fails unexpectedly

    try:
        # Construct the absolute path to settings.json relative to this script
        script_dir = os.path.dirname(__file__)
        abs_settings_path = os.path.abspath(os.path.join(script_dir, settings_path))

        if os.path.exists(abs_settings_path):
            try:
                with open(abs_settings_path, 'r') as f:
                    settings = json.load(f)
                    loaded_words = settings.get("wordList")

                    if loaded_words is None:
                        using_default_reason = f"Settings file found, but 'wordList' key missing in {abs_settings_path}. Using default words."
                    elif isinstance(loaded_words, list) and loaded_words:
                        # Basic validation: ensure all items are strings
                        if all(isinstance(word, str) for word in loaded_words):
                            print(f"Loaded {len(loaded_words)} words from {abs_settings_path}")
                            words_to_use = loaded_words # Successfully loaded custom words
                            using_default_reason = None # Clear the reason, we are not using default
                        else:
                            using_default_reason = f"Warning: 'wordList' in {abs_settings_path} contains non-string elements. Using default words."
                    else: # Handles empty list or non-list types if key existed
                         using_default_reason = f"Warning: Found empty or invalid 'wordList' in {abs_settings_path}. Using default words."

            except json.JSONDecodeError:
                using_default_reason = f"Error decoding JSON from {abs_settings_path}. Using default words."
            except Exception as e: # Catch errors during file reading/processing
                 using_default_reason = f"An unexpected error occurred while reading settings file {abs_settings_path}: {e}. Using default words."
        else:
            # Specific message when the settings file itself is not found
            using_default_reason = f"Settings file not found at {abs_settings_path}. Using default words."

    except Exception as e: # Catch errors during path calculation etc.
        using_default_reason = f"An unexpected error occurred before loading words: {e}. Using default words."

    # Print the reason only if we ended up deciding to use the default list
    if using_default_reason:
        print(using_default_reason)

    return words_to_use

# Path to settings.json relative to this file (audio/utils -> web_UI)
_settings_file_path = '../../web_UI/settings.json'

# Initialize the words list by trying to load from settings or using the default
words = _load_words_from_settings(_settings_file_path, default_words)

def gen_phrase(num_words: int = 3) -> str:
    return " ".join(random.choices(words, k=num_words))

def add_word(word: str) -> bool:
    word = word.strip().lower()
    if word in words:
        return False
    words.append(word)
    return True

def add_words(wordss: str) -> None:
    added_words = []
    for word in wordss.split(","):
        if add_word(word):
            added_words.append(word)
