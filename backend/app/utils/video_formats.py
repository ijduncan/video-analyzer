ALLOWED_EXTENSIONS: dict[str, str] = {
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".avi": "video/x-msvideo",
    ".mpeg": "video/mpeg",
    ".flv": "video/x-flv",
    ".mpg": "video/mpeg",
    ".webm": "video/webm",
    ".wmv": "video/x-ms-wmv",
    ".3gpp": "video/3gpp",
}

ALLOWED_MIME_TYPES = set(ALLOWED_EXTENSIONS.values())


def get_mime_type(filename: str) -> str | None:
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ALLOWED_EXTENSIONS.get(ext)


def is_allowed_file(filename: str) -> bool:
    return get_mime_type(filename) is not None
