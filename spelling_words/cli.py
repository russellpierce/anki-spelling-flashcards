"""Command-line interface for spelling words APKG generator."""

import contextlib
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

import click
import requests_cache
from loguru import logger
from pydantic import ValidationError
from rich.console import Console
from rich.progress import track

from spelling_words.apkg_manager import APKGBuilder, APKGReader
from spelling_words.audio_processor import AudioProcessor
from spelling_words.config import Settings, get_settings
from spelling_words.dictionary_client import (
    MerriamWebsterClient,
    MerriamWebsterCollegiateClient,
)
from spelling_words.word_list import WordListManager

console = Console()


def configure_verbose_logging() -> None:
    """Configure verbose debug logging."""
    logger.remove()
    logger.add(
        lambda msg: console.print(msg, end="", markup=False, highlight=False),
        level="INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
    )
    console.print("[dim]Debug logging enabled[/dim]")


def configure_quiet_logging() -> None:
    """Configure quiet logging - only show errors."""
    logger.remove()
    # Only show ERROR and above in quiet mode
    logger.add(lambda msg: None, level="ERROR")


def load_settings_or_abort() -> Settings:
    """Load settings from .env file or abort with helpful error message."""
    try:
        return get_settings()
    except ValidationError as e:
        console.print("[bold red]Error:[/bold red] Missing configuration")
        console.print("\nPlease ensure your .env file contains:")
        console.print("  MW_ELEMENTARY_API_KEY=your-api-key-here\n")
        console.print(f"Details: {e}")
        raise click.Abort from e


def validate_word_file(words_file: Path) -> None:
    """Validate that the word file exists and is a file."""
    if not words_file.exists():
        console.print(f"[bold red]Error:[/bold red] Word file not found: {words_file}")
        raise click.Abort

    if not words_file.is_file():
        console.print(
            f"[bold red]Error:[/bold red] Path is not a file (it's a directory): {words_file}"
        )
        raise click.Abort


def write_missing_words_file(output_file: Path, missing_words: list[dict]) -> None:
    """Write a report of missing/incomplete words to a text file.

    Args:
        output_file: The APKG output file path (used to generate missing file path)
        missing_words: List of dictionaries with word, reason, and attempted keys
    """
    missing_file = output_file.parent / f"{output_file.stem}-missing.txt"

    with missing_file.open("w", encoding="utf-8") as f:
        f.write("Spelling Words - Missing/Incomplete Words Report\n")
        f.write(f"Generated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC\n")
        f.write(f"APKG: {output_file}\n")
        f.write("\n")
        f.write("=" * 70 + "\n\n")

        for item in missing_words:
            f.write(f'Word: "{item["word"]}"\n')
            f.write(f"Reason: {item['reason']}\n")
            f.write(f"Attempted: {item['attempted']}\n")
            f.write("\n")

        f.write("=" * 70 + "\n")
        f.write(f"Total missing: {len(missing_words)} words\n")

    logger.info(f"Wrote missing words report to {missing_file}")


def load_word_list(word_manager: WordListManager, words_file: Path) -> list[str]:
    """Load word list from file, remove duplicates, and handle errors."""
    logger.debug(f"Loading words from {words_file}...")
    try:
        words = word_manager.load_from_file(str(words_file))
        return word_manager.remove_duplicates(words)
    except (FileNotFoundError, ValueError) as e:
        console.print(f"[bold red]Error:[/bold red] Failed to load word list: {e}")
        raise click.Abort from e


@click.command()
@click.option(
    "--words",
    "-w",
    "words_file",
    required=False,
    type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path),
    help="Path to word list file (one word per line)",
)
@click.option(
    "--output",
    "-o",
    "output_file",
    default="output.apkg",
    type=click.Path(path_type=Path),
    help="Output APKG file path (default: output.apkg)",
)
@click.option(
    "--update",
    "-u",
    "update_file",
    required=False,
    type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path),
    help="Path to existing APKG file to update",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable debug logging",
)
@click.pass_context
def main(
    ctx: click.Context,
    words_file: Path | None,
    output_file: Path,
    verbose: bool,
    update_file: Path | None,
) -> None:
    """Generate or update Anki flashcard deck (APKG) for spelling words.

    Reads a list of words from a file, fetches definitions and audio
    from Merriam-Webster Dictionary API, and creates or updates an Anki deck
    with flashcards for spelling practice.
    """
    if words_file is None:
        click.echo(ctx.get_help())
        ctx.exit()

    if update_file and output_file.name == "output.apkg":
        output_file = update_file

    if verbose:
        configure_verbose_logging()
    else:
        configure_quiet_logging()

    settings = load_settings_or_abort()
    validate_word_file(words_file)

    session = requests_cache.CachedSession(
        "spelling_words_cache",
        backend="sqlite",
        expire_after=timedelta(days=30),
    )
    word_manager = WordListManager()
    dictionary_client = MerriamWebsterClient(settings.mw_elementary_api_key, session)
    collegiate_client = (
        MerriamWebsterCollegiateClient(settings.mw_collegiate_api_key, session)
        if settings.mw_collegiate_api_key
        else None
    )
    audio_processor = AudioProcessor()

    if update_file:
        with APKGReader(update_file) as reader:
            apkg_builder = APKGBuilder("Spelling Words", str(output_file), reader=reader)
    else:
        apkg_builder = APKGBuilder("Spelling Words", str(output_file))

    words = load_word_list(word_manager, words_file)

    logger.info(f"Loaded {len(words)} words")

    missing_words = process_words(
        words=words,
        dictionary_client=dictionary_client,
        collegiate_client=collegiate_client,
        audio_processor=audio_processor,
        apkg_builder=apkg_builder,
        session=session,
        output_file=output_file,
    )

    if len(apkg_builder.deck.notes) == 0:
        console.print("\n[bold yellow]Warning:[/bold yellow] No words were successfully processed")
        console.print("APKG file not created")
        raise click.Abort

    logger.debug("Building APKG file...")
    try:
        apkg_builder.build()
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to build APKG: {e}")
        logger.exception("APKG build failed")
        raise click.Abort from e

    console.print("\n[bold green]✓ Successfully created APKG file![/bold green]")
    console.print(f"\nOutput: [cyan]{output_file}[/cyan]")
    console.print(f"Cards created: [green]{len(apkg_builder.deck.notes)}[/green]")
    console.print(f"Total words processed: [blue]{len(words)}[/blue]")
    if missing_words:
        write_missing_words_file(output_file, missing_words)
        console.print(f"\n[yellow]Missing words report:[/yellow] {output_file.stem}-missing.txt")


def get_word_data(
    word: str,
    dictionary_client: MerriamWebsterClient,
    collegiate_client: MerriamWebsterCollegiateClient | None,
) -> tuple[dict | None, list[str]]:
    """Fetch word data from the elementary dictionary with fallback to collegiate."""
    logger.debug(f"Fetching data for word from elementary dictionary: {word}")
    word_data = dictionary_client.get_word_data(word)
    attempted_sources = ["Elementary Dictionary"]

    if word_data is None and collegiate_client:
        logger.debug(f"Word not found in elementary dictionary, trying collegiate: {word}")
        word_data = collegiate_client.get_word_data(word)
        attempted_sources.append("Collegiate Dictionary")

    return word_data, attempted_sources


def process_word(
    word: str,
    dictionary_client: MerriamWebsterClient,
    collegiate_client: MerriamWebsterCollegiateClient | None,
    audio_processor: AudioProcessor,
    apkg_builder: APKGBuilder,
    session: requests_cache.CachedSession,
) -> dict | None:
    """Fetch, process, and add a single word to the deck."""
    if apkg_builder.word_exists(word):
        logger.debug(f"Word already exists in deck, skipping: {word}")
        return {"status": "skipped"}

    word_data, attempted_sources = get_word_data(word, dictionary_client, collegiate_client)

    if word_data is None:
        logger.warning(f"Word not found in any dictionary: {word}")
        return {
            "status": "failed",
            "word": word,
            "reason": "Word not found in either dictionary",
            "attempted": ", ".join(attempted_sources),
        }

    definition = None
    try:
        definition = dictionary_client.extract_definition(word_data)
    except ValueError:
        if collegiate_client:
            logger.debug(f"No definition in elementary, trying collegiate: {word}")
            collegiate_data = collegiate_client.get_word_data(word)
            if collegiate_data and "Collegiate Dictionary" not in attempted_sources:
                attempted_sources.append("Collegiate Dictionary")
            if collegiate_data:
                with contextlib.suppress(ValueError):
                    definition = collegiate_client.extract_definition(collegiate_data)

    if definition is None:
        logger.warning(f"No definition found for {word}")
        return {
            "status": "failed",
            "word": word,
            "reason": "No definition found in either dictionary",
            "attempted": ", ".join(attempted_sources),
        }
    pattern = re.compile(word, re.IGNORECASE)
    definition = pattern.sub("[the spelling word]", definition)

    audio_urls = dictionary_client.extract_audio_urls(word_data)
    if not audio_urls and collegiate_client:
        logger.debug(f"No audio in elementary, trying collegiate: {word}")
        collegiate_data = collegiate_client.get_word_data(word)
        if collegiate_data and "Collegiate Dictionary" not in attempted_sources:
            attempted_sources.append("Collegiate Dictionary")
        if collegiate_data:
            audio_urls = collegiate_client.extract_audio_urls(collegiate_data)

    if not audio_urls:
        logger.warning(f"No audio URLs found for {word}")
        return {
            "status": "failed",
            "word": word,
            "reason": "No audio found in either dictionary",
            "attempted": ", ".join(attempted_sources),
        }

    audio_url = audio_urls[0]
    logger.debug(f"Downloading audio from {audio_url}")
    audio_bytes = audio_processor.download_audio(audio_url, session)

    if audio_bytes is None:
        logger.warning(f"Failed to download audio for {word}")
        return {
            "status": "failed",
            "word": word,
            "reason": "Audio download failed",
            "attempted": ", ".join(attempted_sources),
        }

    audio_filename, mp3_bytes = audio_processor.process_audio(audio_bytes, word)

    apkg_builder.add_word(word, definition, audio_filename, mp3_bytes)

    logger.info(f"Successfully processed word: {word}")
    return {"status": "successful"}


def process_words(
    words: list[str],
    dictionary_client: MerriamWebsterClient,
    collegiate_client: MerriamWebsterCollegiateClient | None,
    audio_processor: AudioProcessor,
    apkg_builder: APKGBuilder,
    session: requests_cache.CachedSession,
    output_file: Path,
) -> list[dict]:
    """Process words and add them to the APKG builder."""
    successful = 0
    failed = 0
    skipped = 0
    missing_words = []

    for word in track(words, description="Processing words..."):
        result = process_word(
            word,
            dictionary_client,
            collegiate_client,
            audio_processor,
            apkg_builder,
            session,
        )
        if result["status"] == "successful":
            successful += 1
        elif result["status"] == "skipped":
            skipped += 1
        else:
            failed += 1
            missing_words.append(result)

    console.print("\n[bold]Processing Summary:[/bold]")
    console.print(f"  [green]✓ Successful:[/green] {successful}")
    console.print(f"  [yellow]⊘ Skipped:[/yellow] {skipped}")
    console.print(f"  [red]✗ Failed:[/red] {failed}")
    return missing_words


if __name__ == "__main__":
    main()
