#!/usr/bin/env python3

import argparse
import os
import re
import sys

import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
from yt_dlp import YoutubeDL


def get_video_title(url):
    """
    Fetches the video title from a YouTube URL and sanitizes it for use as a filename.
    """
    try:
        ydl_opts = {'quiet': True}
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Unknown Title')
            
        # Sanitize the title to be filesystem-friendly
        sanitized_title = re.sub(r'[^\w\s-]', '', title).strip()
        sanitized_title = re.sub(r'[-\s]+', '-', sanitized_title)
        return sanitized_title
    except Exception as e:
        print(f"Error fetching video title: {e}", file=sys.stderr)
        sys.exit(1)


def extract_live_video_id(url):
    """
    Extracts the YouTube video ID from a /live/ URL using a regular expression.
    """
    pattern = r'(?:https?://)?(?:www\.)?(?:youtube\.com/(?:[^/\n\s]+/[^/]+/|(?:v|e(?:mbed)?|live)/|\S*?[?&]v=)|youtu\.be/)([a-zA-Z0-9_-]{11})'
    match = re.search(pattern, url)
    return match.group(1) if match else None


def extract_standard_video_id(url):
    """
    Extracts the YouTube video ID from a standard URL using a regular expression.
    """
    pattern = r'(?:https?://)?(?:www\.)?(?:youtube\.com/(?:[^/\n\s]+/[^/]+/|(?:v|e(?:mbed)?)/|\S*?[?&]v=|)|youtu\.be/)([a-zA-Z0-9_-]{11})'
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
    parser.add_argument("-o", "--outdir", type=str, help="The output directory for the org file.", default=".")
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

    raw_transcript = get_raw_transcript_text(video_id)
    if not raw_transcript.strip():
        print("Error: Fetched transcript was empty.", file=sys.stderr)
        sys.exit(1)

    print("Formatting transcript with Gemini...")
    formatted_document = format_transcript_with_gemini(raw_transcript)

    formatted_document += "\n\n* transcript\n" + raw_transcript

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