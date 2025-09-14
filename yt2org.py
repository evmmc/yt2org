#!/usr/bin/env python3

import argparse
import os
import re
import sys

import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi


def extract_video_id(url):
    """
    Extracts the YouTube video ID from a URL using a regular expression.
    """
    # This regex pattern covers standard, shortened, and embed URLs
    pattern = r'(?:https?://)?(?:wwweitet)?(?:youtube\.com/(?:[^/\n\s]+/\S+/|(?:v|e(?:mbed)?)/|\S*?[?&]v=)|youtu\.be/)([a-zA-Z0-9_-]{11})'
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


def format_transcript_with_gemini(transcript):
    """
    Uses the Gemini API to format a raw transcript into an org-mode document.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: The 'GEMINI_API_KEY' environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-pro')

    prompt = f"""
Please take the following raw YouTube video transcript and format it into a well-structured org-mode document.
The document should be a comprehensive summary. Do not leave out any information, but structure it logically with headings, subheadings, bullet points, and lists where appropriate to improve readability.
The final output should be only the org-mode document itself, without any introductory text like "Here is the org-mode document:".

Here is the transcript:
---
{transcript}
---
"""

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Error communicating with Gemini API: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """
    Main function to process the video transcript.
    """
    parser = argparse.ArgumentParser(description="Fetch, format, and save a YouTube video transcript as an org-mode document.")
    parser.add_argument("url", type=str, help="The YouTube video URL.")
    args = parser.parse_args()

    video_id = extract_video_id(args.url)
    if not video_id:
        print("Error: Could not extract video ID from URL.", file=sys.stderr)
        sys.exit(1)

    print(f"Processing video: {args.url}")

    raw_transcript = get_raw_transcript_text(video_id)
    if not raw_transcript.strip():
        print("Error: Fetched transcript was empty.", file=sys.stderr)
        sys.exit(1)

    print("Formatting transcript with Gemini...")
    formatted_document = format_transcript_with_gemini(raw_transcript)

    output_filename = f"{video_id}.org"
    try:
        with open(output_filename, "w") as f:
            f.write(formatted_document)
        print(f"Done. Formatted transcript saved to {output_filename}")
    except IOError as e:
        print(f"Error writing to file {output_filename}: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
