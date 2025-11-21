# spelling-words

## Features

### Version 1.1

**Collegiate Dictionary Fallback**
- Automatically falls back to the Merriam-Webster Collegiate Dictionary when words, definitions, or audio are not found in the Elementary Dictionary
- Configure by setting `MW_COLLEGIATE_API_KEY` in your `.env` file (optional)
- Improves word coverage and audio availability

**Missing Words Report**
- Automatically generates a `{filename}-missing.txt` report for any words that couldn't be completely processed
- Lists each missing word with the reason and which dictionaries were attempted
- Helps identify and resolve data gaps

**Enhanced Card Formatting**
- Answer word displayed in Heading 1 (H1) font for better readability
- Definition prefixed with "definition:" label for clarity and future extensibility
