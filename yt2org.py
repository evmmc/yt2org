#!/usr/bin/env python3

import argparse
import os
import re
import sys
import time

import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
from yt_dlp import YoutubeDL


def get_video_title(url):
    """
    Fetches the video title from a YouTube URL and sanitizes it for use as a filename.
    """
    try:
        ydl_opts = {"quiet": True}
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get("title", "Unknown Title")

        # Sanitize the title to be filesystem-friendly
        sanitized_title = re.sub(r"[^\w\s-]", "", title).strip()
        sanitized_title = re.sub(r"[-\s]+", "-", sanitized_title)
        return sanitized_title
    except Exception as e:
        print(f"Error fetching video title: {e}", file=sys.stderr)
        sys.exit(1)


def extract_live_video_id(url):
    """
    Extracts the YouTube video ID from a /live/ URL using a regular expression.
    """
    pattern = r"(?:https?://)?(?:www\.)?(?:youtube\.com/(?:[^/\n\s]+/[^/]+/|(?:v|e(?:mbed)?|live)/|\S*?[?&]v=)|youtu\.be/)([a-zA-Z0-9_-]{11})"
    match = re.search(pattern, url)
    return match.group(1) if match else None


def extract_standard_video_id(url):
    """
    Extracts the YouTube video ID from a standard URL using a regular expression.
    """
    pattern = r"(?:https?://)?(?:www\.)?(?:youtube\.com/(?:[^/\n\s]+/[^/]+/|(?:v|e(?:mbed)?)/|\S*?[?&]v=|)|youtu\.be/)([a-zA-Z0-9_-]{11})"
    match = re.search(pattern, url)
    return match.group(1) if match else None


def get_raw_transcript_text(video_id):
    """
    Fetches the raw transcript and returns it as a single string.
    """
    ytt_api = YouTubeTranscriptApi()
    try:
        fetched_transcript = ytt_api.fetch(video_id)
        return " ".join([snippet.text for snippet in fetched_transcript])
    except Exception as e:
        print(f"Error fetching transcript: {e}", file=sys.stderr)
        sys.exit(1)


def chunk_text(text, chunk_size=20000):
    """
    Splits text into chunks of approximately chunk_size characters,
    respecting word boundaries.
    """
    chunks = []
    while len(text) > chunk_size:
        # Find the last space within the chunk_size limit
        split_index = text.rfind(" ", 0, chunk_size)
        if split_index == -1:
            # If no space found (unlikely), just split at chunk_size
            split_index = chunk_size

        chunks.append(text[:split_index])
        text = text[split_index:].strip()

    if text:
        chunks.append(text)
    return chunks


def generate_summary(model, transcript):
    """
    Generates a comprehensive summary of the transcript.
    """
    print("Generating comprehensive summary...")
    prompt = f"""
You are an expert content analyzer.
Please provide a highly detailed and comprehensive summary of the following video transcript.

**Instructions:**
- **Goal:** Create a summary that serves as a complete substitute for watching the video.
- **Detail Level:** Extremely high. Do not omit technical details, specific examples, numbers, or nuanced arguments.
- **Structure:** Use org-mode formatting.
  - Use top-level headings (*) for main sections.
  - Use sub-headings (**, ***) for deeper levels.
  - Use bullet points (-) for lists.
  - Use bold text (*bold*) for key terms.
- **Content:**
  - Start with a "Core Thesis" or "Executive Summary".
  - Follow with a chronological or thematic breakdown of the entire content.
  - Include a "Key Takeaways" section at the end.

**Transcript:**
{transcript}
"""
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Error generating summary: {e}", file=sys.stderr)
        return "Error generating summary."


def generate_formatted_transcript(model, transcript):
    """
    Formats the raw transcript into readable text, chunk by chunk.
    """
    print("Formatting transcript (this may take a while for long videos)...")
    chunks = chunk_text(transcript)
    formatted_parts = []

    for i, chunk in enumerate(chunks):
        print(f"  - Processing chunk {i + 1}/{len(chunks)}...")
        prompt = f"""
You are an expert editor.
Please format the following raw transcript segment into highly readable prose.

**Instructions:**
- **Goal:** Transform the raw spoken text into a clean, written format.
- **Formatting:**
  - Fix capitalization, punctuation, and grammar.
  - Break the text into logical paragraphs.
  - Identify speaker changes if evident (use "Speaker:" or similar if clear, otherwise just paragraphs).
- **Constraints:**
  - **DO NOT** summarize. You must preserve the full content and meaning.
  - **DO NOT** omit sentences.
  - Output *only* the formatted text.

**Raw Transcript Segment:**
{chunk}
"""
        try:
            # Add a small delay to avoid rate limits if necessary, though Gemini usually handles bursts well.
            # time.sleep(1)
            response = model.generate_content(prompt)
            formatted_parts.append(response.text)
        except Exception as e:
            print(f"Error formatting chunk {i + 1}: {e}", file=sys.stderr)
            formatted_parts.append(f"\n[Error formatting chunk {i + 1}]\n")

    return "\n\n".join(formatted_parts)


def format_transcript_with_gemini(transcript):
    """
    Uses the Gemini API to format a raw transcript into an org-mode document.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print(
            "Error: The 'GEMINI_API_KEY' environment variable is not set.",
            file=sys.stderr,
        )
        sys.exit(1)

    genai.configure(api_key=api_key)
    # Using gemini-1.5-pro for large context window and better reasoning
    model = genai.GenerativeModel("gemini-3.0-pro")

    summary = generate_summary(model, transcript)
    formatted_transcript = generate_formatted_transcript(model, transcript)

    final_document = f"""* Comprehensive Summary
{summary}

* Formatted Transcript
{formatted_transcript}
"""
    return final_document


def main():
    """
    Main function to process the video transcript.
    """
    parser = argparse.ArgumentParser(
        description="Fetch, format, and save a YouTube video transcript as an org-mode document."
    )
    parser.add_argument("url", type=str, help="The YouTube video URL.")
    parser.add_argument(
        "-o",
        "--outdir",
        type=str,
        help="The output directory for the org file.",
        default=".",
    )
    args = parser.parse_args()

    if "/live/" in args.url:
        video_id = extract_live_video_id(args.url)
    else:
        video_id = extract_standard_video_id(args.url)

    if not video_id:
        print("Error: Could not extract video ID from URL.", file=sys.stderr)
        sys.exit(1)

    print(f"Processing video: {args.url}")

    video_title = get_video_title(args.url)

    print("Fetching raw transcript...")
    raw_transcript = get_raw_transcript_text(video_id)
    if not raw_transcript.strip():
        print("Error: Fetched transcript was empty.", file=sys.stderr)
        sys.exit(1)

    print("Formatting with Gemini...")
    formatted_document = format_transcript_with_gemini(raw_transcript)

    output_filename = f"{video_title}-{video_id}.org"
    output_path = os.path.join(args.outdir, output_filename)

    try:
        os.makedirs(args.outdir, exist_ok=True)
        with open(output_path, "w") as f:
            f.write(formatted_document)
        print(f"Done. Formatted transcript saved to {output_path}")
    except IOError as e:
        print(f"Error writing to file {output_path}: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
