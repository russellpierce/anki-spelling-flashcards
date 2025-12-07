# AnkiDroid Spelling Flashcards (anki-spelling-flashcards)

Keywords: [Anki](https://apps.ankiweb.net/), AnkiDroid, AnkiMobole, AnkiWeb

# What

Create English language flashcards usable in the Anki software to support students in learning spelling.

# Quick Start

* Get API Keys from [Merriam-Webster](https://dictionaryapi.com/).  Project is currently configured to use the [Merriam-Webster's Collegiate® Dictionary with Audio](https://dictionaryapi.com/products/api-collegiate-dictionary) and [Merriam-Webster's Elementary Dictionary with Audio (Grades 3-5)](https://dictionaryapi.com/products/api-elementary-dictionary) products.
* Create a text file with each of your words separated by new lines, e.g. your_words.txt

```
git clone https://github.com/russellpierce/anki-spelling-flashcards.git
cd anki-spelling-flashcards

# Install dependencies
# I'm not going to tell you how to manage your Python environments, but I used uv (https://docs.astral.sh/uv/getting-started/installation/).
uv --version || (wget -qO- https://astral.sh/uv/install.sh | sh)
uv sync

# Set up your API key (see Configuration section below)
cp .env.example .env
# Edit .env and add your MW_ELEMENTARY_API_KEY and/or MW_COLLEGIATE_API_KEY

uv run spelling-words -w your_words.txt -o output.apkg

```

# Why / Story Time

Flashcards are great for learning when the goal is brute force remembering / practicing for quick retrieval. The approaches that the long-lived open source Anki software uses, active recall testing and spaced repetition, are well researched and scientifically backed.  I loved it and used it where needed in my own learning.  Now, I have children.  One of them recently came home with a giant spelling list to learn.  I love spending time with my children, I don't love spending time being a flashcard drill sergeant.  I believe in flashcards, but creating 300+ spelling flashcards recording each word as I went, that also didn't sound like much fun.  Enter this project. Using the definitions and pronunciations from [Merriam-Webster](https://dictionaryapi.com/), 

Creating flashcards for learning spelling is a pain.  

# Requested Improvements

These are improvements to this software I'd welcome help on.

* Modify an existing deck
* Work with decks directly on Ankiweb