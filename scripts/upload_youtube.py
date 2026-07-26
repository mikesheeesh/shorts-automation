"""Uploads a rendered video to YouTube as a Short via the YouTube Data API v3.

First run opens a browser for one-time OAuth consent (needs credentials/client_secret.json,
see README.md for how to create it in Google Cloud Console). After that, the token is
cached in credentials/token.json and reused silently.
"""
import argparse
import os
import sys

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import CREDENTIALS_DIR

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CLIENT_SECRET_PATH = os.path.join(CREDENTIALS_DIR, "client_secret.json")
TOKEN_PATH = os.path.join(CREDENTIALS_DIR, "token.json")


def get_authenticated_service():
    if not os.path.exists(CLIENT_SECRET_PATH):
        raise FileNotFoundError(
            f"Missing {CLIENT_SECRET_PATH}. Follow the Google Cloud OAuth setup steps in README.md first."
        )

    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

    return build("youtube", "v3", credentials=creds)


def upload_short(youtube, file_path, title, description, tags, category_id="22", privacy_status="private"):
    body = {
        "snippet": {
            "title": title[:100],
            "description": description,
            "tags": tags,
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False,
        },
    }
    media = MediaFileUpload(file_path, chunksize=-1, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"  Uploaded {int(status.progress() * 100)}%")
    return response


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="path to the mp4 to upload")
    parser.add_argument("--title", required=True)
    parser.add_argument("--description", default="")
    parser.add_argument("--tags", default="", help="comma-separated tags")
    parser.add_argument("--privacy", default="private", choices=["private", "unlisted", "public"])
    args = parser.parse_args()

    youtube = get_authenticated_service()
    tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    try:
        response = upload_short(youtube, args.file, args.title, args.description, tags, privacy_status=args.privacy)
    except HttpError as e:
        print(f"YouTube API error: {e}")
        sys.exit(1)

    video_id = response["id"]
    print(f"Uploaded: https://youtube.com/shorts/{video_id} (privacy={args.privacy})")


if __name__ == "__main__":
    main()
