"""Command-line interface for spelling words APKG generator."""

import contextlib
from datetime import UTC, datetime, timedelta
from pathlib import Path

import click
import requests_cache
from loguru import logger
from pydantic import ValidationError
from rich.console import Console
from rich.progress import track

from spelling_words.apkg_manager import APKGBuilder
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
        level="DEBUG",
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
    )
    console.print("[dim]Debug logging enabled[/dim]")


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
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable debug logging",
)
@click.pass_context
def main(ctx: click.Context, words_file: Path | None, output_file: Path, verbose: bool) -> None:
    """Generate Anki flashcard deck (APKG) for spelling words.

    Reads a list of words from a file, fetches definitions and audio
    from Merriam-Webster Dictionary API, and creates an Anki deck
    with flashcards for spelling practice.
    """
    # Show help if no words file provided
    if words_file is None:
        click.echo(ctx.get_help())
        ctx.exit()

    # Configure logging level
    if verbose:
        configure_verbose_logging()

    console.print("\n[bold blue]Spelling Words APKG Generator[/bold blue]\n")

    # Load settings
    settings = load_settings_or_abort()

    # Validate word file
    validate_word_file(words_file)

    # Initialize components
    console.print("[dim]Initializing components...[/dim]")

    # Create cached session for HTTP requests
    session = requests_cache.CachedSession(
        "spelling_words_cache",
        backend="sqlite",
        expire_after=timedelta(days=30),
    )

    word_manager = WordListManager()
    dictionary_client = MerriamWebsterClient(settings.mw_elementary_api_key, session)

    # Initialize collegiate dictionary client if API key is configured
    collegiate_client = None
    if settings.mw_collegiate_api_key:
        collegiate_client = MerriamWebsterCollegiateClient(settings.mw_collegiate_api_key, session)
        console.print("[dim]Collegiate dictionary fallback enabled[/dim]")

    audio_processor = AudioProcessor()
    apkg_builder = APKGBuilder("Spelling Words", str(output_file))

    # Load word list
    console.print(f"[dim]Loading words from {words_file}...[/dim]")
    try:
        words = word_manager.load_from_file(str(words_file))
        words = word_manager.remove_duplicates(words)
    except (FileNotFoundError, ValueError) as e:
        console.print(f"[bold red]Error:[/bold red] Failed to load word list: {e}")
        raise click.Abort from e

    console.print(f"Loaded {len(words)} words\n")

    # Process words
    process_words(
        words=words,
        dictionary_client=dictionary_client,
        collegiate_client=collegiate_client,
        audio_processor=audio_processor,
        apkg_builder=apkg_builder,
        session=session,
        output_file=output_file,
    )

    # Build APKG if we have any notes
    if len(apkg_builder.deck.notes) == 0:
        console.print("\n[bold yellow]Warning:[/bold yellow] No words were successfully processed")
        console.print("APKG file not created")
        raise click.Abort

    console.print("\n[dim]Building APKG file...[/dim]")
    try:
        apkg_builder.build()
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to build APKG: {e}")
        logger.exception("APKG build failed")
        raise click.Abort from e

    # Display summary
    console.print("\n[bold green]✓ Successfully created APKG file![/bold green]")
    console.print(f"\nOutput: [cyan]{output_file}[/cyan]")
    console.print(f"Cards created: [green]{len(apkg_builder.deck.notes)}[/green]")
    console.print(f"Total words processed: [blue]{len(words)}[/blue]")


def process_words(  # noqa: PLR0912, PLR0915
    words: list[str],
    dictionary_client: MerriamWebsterClient,
    collegiate_client: MerriamWebsterCollegiateClient | None,
    audio_processor: AudioProcessor,
    apkg_builder: APKGBuilder,
    session: requests_cache.CachedSession,
    output_file: Path,
) -> None:
    """Process words and add them to the APKG builder.

    Args:
        words: List of words to process
        dictionary_client: Elementary dictionary API client
        collegiate_client: Collegiate dictionary API client (optional fallback)
        audio_processor: Audio processor
        apkg_builder: APKG builder
        session: Cached session for HTTP requests
        output_file: Output APKG file path (used to generate missing words file)
    """
    successful = 0
    failed = 0
    skipped = 0
    missing_words = []  # Track words that couldn't be completely processed

    for word in track(words, description="Processing words..."):
        # Fetch word data from elementary dictionary
        logger.debug(f"Fetching data for word from elementary dictionary: {word}")
        word_data = dictionary_client.get_word_data(word)
        attempted_sources = ["Elementary Dictionary"]

        # Fallback to collegiate dictionary if word not found
        if word_data is None and collegiate_client:
            logger.debug(f"Word not found in elementary dictionary, trying collegiate: {word}")
            word_data = collegiate_client.get_word_data(word)
            attempted_sources.append("Collegiate Dictionary")

        if word_data is None:
            logger.warning(f"Word not found in any dictionary: {word}")
            console.print(f"  [yellow]⊘[/yellow] [dim]{word}[/dim] - not found in dictionary")
            missing_words.append(
                {
                    "word": word,
                    "reason": "Word not found in either dictionary",
                    "attempted": ", ".join(attempted_sources),
                }
            )
            skipped += 1
            continue

        # Extract definition (with fallback)
        definition = None
        try:
            definition = dictionary_client.extract_definition(word_data)
        except ValueError:
            # Try collegiate dictionary for definition if available
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
            console.print(f"  [yellow]⊘[/yellow] [dim]{word}[/dim] - no definition")
            missing_words.append(
                {
                    "word": word,
                    "reason": "No definition found in either dictionary",
                    "attempted": ", ".join(attempted_sources),
                }
            )
            skipped += 1
            continue

        # Extract audio URLs (with fallback)
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
            console.print(f"  [yellow]⊘[/yellow] [dim]{word}[/dim] - no audio")
            missing_words.append(
                {
                    "word": word,
                    "reason": "No audio found in either dictionary",
                    "attempted": ", ".join(attempted_sources),
                }
            )
            skipped += 1
            continue

        # Download and process audio (use first URL)
        audio_url = audio_urls[0]
        logger.debug(f"Downloading audio from {audio_url}")
        audio_bytes = audio_processor.download_audio(audio_url, session)

        if audio_bytes is None:
            logger.warning(f"Failed to download audio for {word}")
            console.print(f"  [yellow]⊘[/yellow] [dim]{word}[/dim] - audio download failed")
            missing_words.append(
                {
                    "word": word,
                    "reason": "Audio download failed",
                    "attempted": ", ".join(attempted_sources),
                }
            )
            skipped += 1
            continue

        # Process audio to MP3
        audio_filename, mp3_bytes = audio_processor.process_audio(audio_bytes, word)

        # Add to APKG
        apkg_builder.add_word(word, definition, audio_filename, mp3_bytes)

        logger.info(f"Successfully processed word: {word}")
        successful += 1

    # Print summary
    console.print("\n[bold]Processing Summary:[/bold]")
    console.print(f"  [green]✓ Successful:[/green] {successful}")
    console.print(f"  [yellow]⊘ Skipped:[/yellow] {skipped}")
    console.print(f"  [red]✗ Failed:[/red] {failed}")

    # Write missing words file if there are any
    if missing_words:
        write_missing_words_file(output_file, missing_words)
        console.print(f"\n[yellow]Missing words report:[/yellow] {output_file.stem}-missing.txt")


if __name__ == "__main__":
    main()
