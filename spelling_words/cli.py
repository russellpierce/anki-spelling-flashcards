"""Command-line interface for spelling words APKG generator."""

from datetime import timedelta
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
from spelling_words.dictionary_client import MerriamWebsterClient
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
        audio_processor=audio_processor,
        apkg_builder=apkg_builder,
        session=session,
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


def process_words(
    words: list[str],
    dictionary_client: MerriamWebsterClient,
    audio_processor: AudioProcessor,
    apkg_builder: APKGBuilder,
    session: requests_cache.CachedSession,
) -> None:
    """Process words and add them to the APKG builder.

    Args:
        words: List of words to process
        dictionary_client: Dictionary API client
        audio_processor: Audio processor
        apkg_builder: APKG builder
        session: Cached session for HTTP requests
    """
    successful = 0
    failed = 0
    skipped = 0

    for word in track(words, description="Processing words..."):
        try:
            # Fetch word data from dictionary
            logger.debug(f"Fetching data for word: {word}")
            word_data = dictionary_client.get_word_data(word)

            if word_data is None:
                logger.warning(f"Word not found in dictionary: {word}")
                console.print(f"  [yellow]⊘[/yellow] [dim]{word}[/dim] - not found in dictionary")
                skipped += 1
                continue

            # Extract definition and audio URLs
            try:
                definition = dictionary_client.extract_definition(word_data)
            except ValueError as e:
                logger.warning(f"No definition found for {word}: {e}")
                console.print(f"  [yellow]⊘[/yellow] [dim]{word}[/dim] - no definition")
                skipped += 1
                continue

            audio_urls = dictionary_client.extract_audio_urls(word_data)
            if not audio_urls:
                logger.warning(f"No audio URLs found for {word}")
                console.print(f"  [yellow]⊘[/yellow] [dim]{word}[/dim] - no audio")
                skipped += 1
                continue

            # Download and process audio (use first URL)
            audio_url = audio_urls[0]
            logger.debug(f"Downloading audio from {audio_url}")
            audio_bytes = audio_processor.download_audio(audio_url, session)

            if audio_bytes is None:
                logger.warning(f"Failed to download audio for {word}")
                console.print(f"  [yellow]⊘[/yellow] [dim]{word}[/dim] - audio download failed")
                skipped += 1
                continue

            # Process audio to MP3
            audio_filename, mp3_bytes = audio_processor.process_audio(audio_bytes, word)

            # Add to APKG
            apkg_builder.add_word(word, definition, audio_filename, mp3_bytes)

            logger.info(f"Successfully processed word: {word}")
            successful += 1

        except Exception as e:
            logger.error(f"Failed to process word '{word}': {e}", exc_info=True)
            console.print(f"  [red]✗[/red] [dim]{word}[/dim] - error: {e}")
            failed += 1

    # Print summary
    console.print("\n[bold]Processing Summary:[/bold]")
    console.print(f"  [green]✓ Successful:[/green] {successful}")
    console.print(f"  [yellow]⊘ Skipped:[/yellow] {skipped}")
    console.print(f"  [red]✗ Failed:[/red] {failed}")


if __name__ == "__main__":
    main()
