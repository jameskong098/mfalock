import random

words = [
    "elderberry", "kale", "orange", "vanilla", "fig", "quince", "grape", "xigua",
    "jalapeño", "nectarine", "lemon", "watermelon", "parsley", "zucchini", "almond",
    "iceberg", "papaya", "garlic", "apple", "tomato", "quinoa", "yam", "mushroom",
    "radish", "eggplant", "date", "leek", "daikon", "vinegar", "broccoli", "spinach",
    "raspberry", "tangerine", "xanthan", "zest", "mango", "cherry", "honeydew",
    "yogurt", "upland", "nutmeg", "kiwi", "wasabi", "ugly", "strawberry", "oregano",
    "horseradish", "banana", "fennel", "carrot"
]

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
