import json
import re
from tkinter import filedialog
from tkinter import ttk
from urllib import parse
from urllib import request
from urllib.error import HTTPError
from urllib.error import URLError

from state import AppState

APP_USER_AGENT = "PrintTheBars/1.0 (https://github.com/manda/Print-The-Bars)"
REQUEST_TIMEOUT_SECONDS = 12

MUSICBRAINZ_RELEASE_RE = re.compile(
    r"/release/([0-9a-fA-F-]{36})(?:$|[/?#])"
)
MUSICBRAINZ_RELEASE_GROUP_RE = re.compile(
    r"/release-group/([0-9a-fA-F-]{36})(?:$|[/?#])"
)
DISCOGS_RELEASE_RE = re.compile(r"/(?:release|releases)/(\d+)(?:$|[-/?#])")
DISCOGS_MASTER_RE = re.compile(r"/(?:master|masters)/(\d+)(?:$|[-/?#])")
FEATURE_FALLBACK_RE = re.compile(
    r"(?:\(|\s)(?:feat\.?|ft\.?|featuring)\s+([^\)]+)(?:\)|$)",
    flags=re.IGNORECASE,
)

MB_FEATURE_ROLE_KEYWORDS = ("vocal", "perform")
DISCOGS_INCLUDE_ROLE_KEYWORDS = (
    "vocal",
    "vocals",
    "singer",
    "rap",
    "mc",
    "perform",
    "guest",
    "featured",
    "featuring",
    "backing vocal",
)
DISCOGS_EXCLUDE_ROLE_KEYWORDS = (
    "producer",
    "engineer",
    "master",
    "artwork",
    "design",
    "writer",
    "written",
    "composer",
    "composed",
)


class SourcePanel:
    def __init__(
        self,
        parent: ttk.Frame,
        state: AppState,
        bind_mousewheel_recursive,
    ) -> None:
        self.parent = parent
        self.state = state
        self.bind_mousewheel_recursive = bind_mousewheel_recursive

    def build(self, row: int) -> ttk.LabelFrame:
        frame = ttk.LabelFrame(self.parent, text="1. Album source", padding=12)
        frame.grid(row=row, column=0, sticky="ew", pady=8)
        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(2, weight=0)

        ttk.Button(frame, text="Upload cover", command=self._upload_cover).grid(
            row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8)
        )

        ttk.Label(frame, text="Album link").grid(
            row=1, column=0, sticky="w", pady=4
        )
        ttk.Entry(frame, textvariable=self.state.album_link_var).grid(
            row=1, column=1, sticky="ew", padx=(10, 0), pady=4
        )

        ttk.Button(frame, text="Validate link", command=self._on_validate_link).grid(
            row=1,
            column=2,
            sticky="e",
            padx=(10, 0),
            pady=4,
        )

        self.feedback_label = ttk.Label(
            frame,
            textvariable=self.state.album_validation_message_var,
            foreground="#666666",
            wraplength=300,
            justify="left",
        )
        self.feedback_label.grid(row=2, column=0, columnspan=3, sticky="w", pady=(2, 0))

        self.bind_mousewheel_recursive(frame)
        return frame

    def _upload_cover(self) -> None:
        selected_path = filedialog.askopenfilename(
            title="Select album cover",
            filetypes=[
                (
                    "Image files",
                    "*.png *.jpg *.jpeg *.bmp *.gif *.tif *.tiff *.webp *.ico *.ppm *.pgm",
                ),
                ("All files", "*.*"),
            ],
        )
        if selected_path:
            self.state.cover_image_path_var.set(selected_path)

    def _on_validate_link(self) -> None:
        if self.state.album_loading_var.get():
            return

        link = self.state.album_link_var.get().strip()
        if not link:
            self._set_feedback("error", "Please paste an album link first.")
            return

        parsed = self._parse_recognized_link(link)
        if parsed is None:
            self._set_feedback("error", "Unsupported link format.")
            return

        self._set_feedback("loading", "Checking album link...")
        self.parent.update_idletasks()

        try:
            normalized = self._fetch_and_normalize(parsed)
        except Exception as exc:
            self._apply_failure(str(exc))
            return

        self._apply_success(normalized)

    def _set_feedback(self, status: str, message: str) -> None:
        self.state.album_validation_status_var.set(status)
        self.state.album_validation_message_var.set(message)
        self.state.album_loading_var.set(status == "loading")

        if not hasattr(self, "feedback_label"):
            return

        color = "#666666"
        if status == "success":
            color = "#2e7d32"
        elif status == "error":
            color = "#b71c1c"
        elif status == "loading":
            color = "#555555"
        self.feedback_label.configure(foreground=color)

    def _parse_recognized_link(self, link: str) -> dict[str, str] | None:
        try:
            parsed = parse.urlparse(link)
        except ValueError:
            return None

        host = parsed.netloc.lower().strip()
        path = parsed.path
        if not host:
            return None

        if "musicbrainz.org" in host:
            release_match = MUSICBRAINZ_RELEASE_RE.search(path)
            if release_match:
                return {
                    "provider": "musicbrainz",
                    "entity": "release",
                    "id": release_match.group(1),
                    "hint": "",
                }
            group_match = MUSICBRAINZ_RELEASE_GROUP_RE.search(path)
            if group_match:
                return {
                    "provider": "musicbrainz",
                    "entity": "release-group",
                    "id": group_match.group(1),
                    "hint": "",
                }
            return None

        if "discogs.com" in host:
            hint = self._extract_discogs_hint(path)
            release_match = DISCOGS_RELEASE_RE.search(path)
            if release_match:
                return {
                    "provider": "discogs",
                    "entity": "release",
                    "id": release_match.group(1),
                    "hint": hint,
                }
            master_match = DISCOGS_MASTER_RE.search(path)
            if master_match:
                return {
                    "provider": "discogs",
                    "entity": "master",
                    "id": master_match.group(1),
                    "hint": hint,
                }
            return None

        return None

    def _apply_success(self, normalized: dict[str, object]) -> None:
        self.state.album_metadata = normalized
        self.state.album_metadata_version_var.set(self.state.album_metadata_version_var.get() + 1)
        self._set_feedback("success", "Album data loaded successfully.")

    def _apply_failure(self, message: str) -> None:
        user_message = message.strip() if message else "Could not validate this album link."
        self.state.album_metadata = {
            "title": "",
            "artist": "",
            "release_date": "",
            "tracklist": [],
            "cover_url": "",
            "source_provider": "",
            "source_id": "",
            "validation_status": "error",
            "error_message": user_message,
        }
        self.state.album_metadata_version_var.set(self.state.album_metadata_version_var.get() + 1)
        self._set_feedback("error", user_message)

    def _fetch_and_normalize(self, parsed_link: dict[str, str]) -> dict[str, object]:
        provider = parsed_link["provider"]
        entity = parsed_link["entity"]
        source_id = parsed_link["id"]

        if provider == "musicbrainz":
            data = self._fetch_musicbrainz(entity, source_id)
            if not data:
                data = self._fallback_discogs_search(parsed_link.get("hint", ""))
        elif provider == "discogs":
            data = self._fetch_discogs(entity, source_id)
            if not data:
                data = self._fallback_musicbrainz_search(parsed_link.get("hint", ""))
        else:
            raise ValueError("Unsupported provider")

        if not data:
            raise ValueError("Could not validate this album link.")

        title = self._pick_text(data.get("title"))
        artist = self._pick_text(data.get("artist"))
        release_date = self._pick_text(data.get("release_date"))
        tracklist = self._normalize_tracklist(data.get("tracklist"))
        cover_url = self._pick_text(data.get("cover_url"))

        if not title and not artist:
            raise ValueError("Album link was valid, but album data was not found.")

        return {
            "title": title,
            "artist": artist,
            "release_date": release_date,
            "tracklist": tracklist,
            "cover_url": cover_url,
            "source_provider": provider,
            "source_id": source_id,
            "validation_status": "success",
            "error_message": "",
        }

    def _fetch_json(self, url: str) -> dict[str, object]:
        request_obj = request.Request(
            url,
            headers={
                "User-Agent": APP_USER_AGENT,
                "Accept": "application/json",
            },
        )
        with request.urlopen(request_obj, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            payload = response.read().decode("utf-8")
        return json.loads(payload)

    def _fetch_musicbrainz(self, entity: str, source_id: str) -> dict[str, object]:
        try:
            if entity == "release":
                endpoint = (
                    f"https://musicbrainz.org/ws/2/release/{source_id}"
                    "?fmt=json&inc=artist-credits+recordings+artist-rels+recording-level-rels"
                )
                release_json = self._fetch_json(endpoint)
                return {
                    "title": release_json.get("title", ""),
                    "artist": self._musicbrainz_artist_name(release_json),
                    "release_date": release_json.get("date", ""),
                    "tracklist": self._musicbrainz_tracklist(release_json),
                    "cover_url": f"https://coverartarchive.org/release/{source_id}/front-500",
                }

            if entity == "release-group":
                endpoint = (
                    f"https://musicbrainz.org/ws/2/release-group/{source_id}"
                    "?fmt=json&inc=artist-credits+releases"
                )
                group_json = self._fetch_json(endpoint)
                tracklist: list[dict[str, object]] = []
                releases = group_json.get("releases") or []
                if isinstance(releases, list) and releases:
                    first_release_id = ""
                    for release in releases:
                        if isinstance(release, dict) and release.get("id"):
                            first_release_id = str(release.get("id"))
                            break
                    if first_release_id:
                        tracklist = self._musicbrainz_release_tracklist(first_release_id)
                return {
                    "title": group_json.get("title", ""),
                    "artist": self._musicbrainz_artist_name(group_json),
                    "release_date": group_json.get("first-release-date", ""),
                    "tracklist": tracklist,
                    "cover_url": f"https://coverartarchive.org/release-group/{source_id}/front-500",
                }
        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError):
            return {}
        return {}

    def _musicbrainz_release_tracklist(self, release_id: str) -> list[dict[str, object]]:
        try:
            endpoint = (
                f"https://musicbrainz.org/ws/2/release/{release_id}"
                "?fmt=json&inc=artist-credits+recordings+artist-rels+recording-level-rels"
            )
            release_json = self._fetch_json(endpoint)
            return self._musicbrainz_tracklist(release_json)
        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError):
            return []

    def _musicbrainz_artist_name(self, payload: dict[str, object]) -> str:
        credit = payload.get("artist-credit")
        if not isinstance(credit, list):
            return ""
        names: list[str] = []
        for item in credit:
            if isinstance(item, dict):
                if isinstance(item.get("name"), str):
                    names.append(item["name"])
                elif isinstance(item.get("artist"), dict) and isinstance(item["artist"].get("name"), str):
                    names.append(item["artist"]["name"])
        return " & ".join(names)

    def _musicbrainz_tracklist(self, payload: dict[str, object]) -> list[dict[str, object]]:
        media = payload.get("media")
        if not isinstance(media, list):
            return []
        album_artist = self._musicbrainz_artist_name(payload)
        album_artist_ids = self._musicbrainz_album_artist_ids(payload)
        tracks: list[dict[str, object]] = []
        for medium in media:
            if not isinstance(medium, dict):
                continue
            medium_tracks = medium.get("tracks")
            if not isinstance(medium_tracks, list):
                continue
            for track in medium_tracks:
                if not isinstance(track, dict):
                    continue
                title = track.get("title")
                if not isinstance(title, str) or not title.strip():
                    continue
                recording = track.get("recording")
                features: list[str] = []
                if isinstance(recording, dict):
                    features = self._musicbrainz_featured_artists(
                        recording,
                        album_artist,
                        album_artist_ids,
                    )
                tracks.append(
                    {
                        "title": title.strip(),
                        "featured_artists": features,
                    }
                )
        return tracks

    def _musicbrainz_album_artist_ids(self, payload: dict[str, object]) -> set[str]:
        credit = payload.get("artist-credit")
        if not isinstance(credit, list):
            return set()

        ids: set[str] = set()
        for item in credit:
            if not isinstance(item, dict):
                continue
            artist = item.get("artist")
            if isinstance(artist, dict) and isinstance(artist.get("id"), str):
                ids.add(artist["id"].strip())
        return ids

    def _fetch_discogs(self, entity: str, source_id: str) -> dict[str, object]:
        try:
            if entity == "release":
                endpoint = f"https://api.discogs.com/releases/{source_id}"
                release_json = self._fetch_json(endpoint)
                album_artist = self._discogs_artist_name(release_json)
                return {
                    "title": release_json.get("title", ""),
                    "artist": album_artist,
                    "release_date": release_json.get("released", "") or release_json.get("year", ""),
                    "tracklist": self._discogs_tracklist(release_json, album_artist),
                    "cover_url": self._discogs_cover_url(release_json),
                }

            if entity == "master":
                endpoint = f"https://api.discogs.com/masters/{source_id}"
                master_json = self._fetch_json(endpoint)
                release_date = master_json.get("year", "")
                album_artist = self._discogs_artist_name(master_json)
                tracklist = self._discogs_tracklist(master_json, album_artist)
                cover_url = self._discogs_cover_url(master_json)

                main_release = master_json.get("main_release")
                if isinstance(main_release, int) and main_release > 0:
                    release_json = self._fetch_json(f"https://api.discogs.com/releases/{main_release}")
                    if not release_date:
                        release_date = release_json.get("released", "") or release_json.get("year", "")
                    if not tracklist:
                        tracklist = self._discogs_tracklist(release_json, album_artist)
                    if not cover_url:
                        cover_url = self._discogs_cover_url(release_json)

                return {
                    "title": master_json.get("title", ""),
                    "artist": album_artist,
                    "release_date": release_date,
                    "tracklist": tracklist,
                    "cover_url": cover_url,
                }
        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError):
            return {}
        return {}

    def _discogs_artist_name(self, payload: dict[str, object]) -> str:
        artists = payload.get("artists")
        if not isinstance(artists, list):
            return ""
        names: list[str] = []
        for item in artists:
            if isinstance(item, dict) and isinstance(item.get("name"), str):
                clean = re.sub(r"\s*\(\d+\)$", "", item["name"]).strip()
                if clean:
                    names.append(clean)
        return " & ".join(names)

    def _discogs_tracklist(
        self,
        payload: dict[str, object],
        album_artist: str,
    ) -> list[dict[str, object]]:
        raw_tracklist = payload.get("tracklist")
        if not isinstance(raw_tracklist, list):
            return []
        tracks: list[dict[str, object]] = []
        for entry in raw_tracklist:
            if not isinstance(entry, dict):
                continue
            if entry.get("type_") not in {None, "track"}:
                continue
            title = entry.get("title")
            if not isinstance(title, str) or not title.strip():
                continue
            features = self._discogs_featured_artists(entry, album_artist)
            tracks.append(
                {
                    "title": title.strip(),
                    "featured_artists": features,
                }
            )
        return tracks

    def _discogs_cover_url(self, payload: dict[str, object]) -> str:
        if isinstance(payload.get("thumb"), str) and payload.get("thumb"):
            return str(payload.get("thumb"))

        images = payload.get("images")
        if isinstance(images, list):
            for image in images:
                if isinstance(image, dict) and isinstance(image.get("uri"), str):
                    return image["uri"]
        return ""

    def _musicbrainz_featured_artists(
        self,
        recording: dict[str, object],
        album_artist: str,
        album_artist_ids: set[str],
    ) -> list[str]:
        relations = recording.get("relations")
        if not isinstance(relations, list):
            return []

        candidates: list[dict[str, str]] = []
        for relation in relations:
            if not isinstance(relation, dict):
                continue

            target_type = str(relation.get("target-type") or "").strip().lower()
            if target_type and target_type != "artist":
                continue

            rel_type = str(relation.get("type") or "").strip().lower()
            attributes = relation.get("attributes")
            rel_attributes = [
                str(attribute).strip().lower()
                for attribute in attributes
                if isinstance(attribute, str)
            ] if isinstance(attributes, list) else []

            role_matches = any(keyword in rel_type for keyword in MB_FEATURE_ROLE_KEYWORDS) or any(
                any(keyword in attribute for keyword in MB_FEATURE_ROLE_KEYWORDS)
                for attribute in rel_attributes
            )
            if not role_matches:
                continue

            artist = relation.get("artist")
            if not isinstance(artist, dict):
                continue
            artist_name = artist.get("name")
            if not isinstance(artist_name, str) or not artist_name.strip():
                continue
            artist_id = ""
            if isinstance(artist.get("id"), str):
                artist_id = artist["id"].strip()
            candidates.append(
                {
                    "id": artist_id,
                    "name": artist_name.strip(),
                }
            )

        album_keys = self._split_artist_keys(album_artist)
        seen_ids: set[str] = set()
        seen_keys: set[str] = set()
        result: list[str] = []
        for candidate in candidates:
            candidate_name = candidate["name"]
            candidate_id = candidate["id"]
            clean = re.sub(r"\s*\(\d+\)$", "", candidate_name).strip()
            if not clean:
                continue
            key = self._artist_key(clean)
            if not key:
                continue
            if candidate_id and candidate_id in album_artist_ids:
                continue
            if candidate_id and candidate_id in seen_ids:
                continue
            if key in album_keys or key in seen_keys:
                continue

            if candidate_id:
                seen_ids.add(candidate_id)
            seen_keys.add(key)
            result.append(clean)
        return result

    def _discogs_featured_artists(
        self,
        entry: dict[str, object],
        album_artist: str,
    ) -> list[str]:
        candidates: list[str] = []

        artists = entry.get("artists")
        if isinstance(artists, list):
            for artist in artists:
                if not isinstance(artist, dict):
                    continue
                if isinstance(artist.get("name"), str):
                    candidates.append(artist["name"])

        structured_found = False
        extraartists = entry.get("extraartists")
        if isinstance(extraartists, list):
            for artist in extraartists:
                if not isinstance(artist, dict):
                    continue
                role_text = str(artist.get("role") or "").lower()
                if not role_text:
                    continue
                role_chunks = [chunk.strip() for chunk in role_text.replace(";", ",").split(",") if chunk.strip()]
                include = any(
                    any(keyword in chunk for keyword in DISCOGS_INCLUDE_ROLE_KEYWORDS)
                    for chunk in role_chunks
                )
                exclude = any(
                    any(keyword in chunk for keyword in DISCOGS_EXCLUDE_ROLE_KEYWORDS)
                    for chunk in role_chunks
                )
                if include and not exclude and isinstance(artist.get("name"), str):
                    structured_found = True
                    candidates.append(artist["name"])

        filtered = self._dedupe_and_filter_features(candidates, album_artist)
        if structured_found or filtered:
            return filtered

        title = entry.get("title")
        if not isinstance(title, str):
            return []
        fallback_candidates = self._extract_features_from_title(title)
        return self._dedupe_and_filter_features(fallback_candidates, album_artist)

    def _extract_features_from_title(self, title: str) -> list[str]:
        match = FEATURE_FALLBACK_RE.search(title)
        if not match:
            return []
        raw = match.group(1).strip()
        if not raw:
            return []
        raw = re.sub(r"\s+(?:with|and)\s+", ",", raw, flags=re.IGNORECASE)
        raw = raw.replace("&", ",")
        parts = [part.strip() for part in raw.split(",") if part.strip()]
        return parts

    def _dedupe_and_filter_features(
        self,
        candidates: list[str],
        album_artist: str,
    ) -> list[str]:
        album_keys = self._split_artist_keys(album_artist)
        seen: set[str] = set()
        result: list[str] = []
        for candidate in candidates:
            clean = re.sub(r"\s*\(\d+\)$", "", candidate).strip()
            if not clean:
                continue
            key = self._artist_key(clean)
            if not key or key in album_keys or key in seen:
                continue
            seen.add(key)
            result.append(clean)
        return result

    def _split_artist_keys(self, artist_text: str) -> set[str]:
        if not artist_text:
            return set()
        parts = re.split(r"\s*(?:,|&| and )\s*", artist_text, flags=re.IGNORECASE)
        keys = {self._artist_key(part) for part in parts if part.strip()}
        return {key for key in keys if key}

    def _artist_key(self, value: str) -> str:
        normalized = re.sub(r"\s+", " ", value.lower()).strip()
        normalized = re.sub(r"[^a-z0-9 ]", "", normalized)
        return normalized

    def _pick_text(self, value: object) -> str:
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, int):
            return str(value)
        return ""

    def _normalize_tracklist(self, value: object) -> list[dict[str, object]]:
        if not isinstance(value, list):
            return []
        normalized: list[dict[str, object]] = []
        for item in value:
            if isinstance(item, dict):
                title = item.get("title")
                if not isinstance(title, str) or not title.strip():
                    continue
                artists = item.get("featured_artists")
                featured_artists: list[str] = []
                if isinstance(artists, list):
                    featured_artists = [
                        artist.strip()
                        for artist in artists
                        if isinstance(artist, str) and artist.strip()
                    ]
                normalized.append(
                    {
                        "title": title.strip(),
                        "featured_artists": featured_artists,
                    }
                )
            elif isinstance(item, str) and item.strip():
                normalized.append(
                    {
                        "title": item.strip(),
                        "featured_artists": [],
                    }
                )
        return normalized

    def _extract_discogs_hint(self, path: str) -> str:
        path_lower = path.strip().lower()
        if "/release/" in path_lower:
            tail = path_lower.split("/release/", 1)[1]
        elif "/master/" in path_lower:
            tail = path_lower.split("/master/", 1)[1]
        else:
            return ""

        if "-" not in tail:
            return ""
        maybe_slug = tail.split("-", 1)[1]
        maybe_slug = maybe_slug.replace("/", " ")
        maybe_slug = re.sub(r"[^a-z0-9\s-]", " ", maybe_slug)
        maybe_slug = re.sub(r"\s+", " ", maybe_slug).strip()
        return maybe_slug

    def _fallback_musicbrainz_search(self, hint: str) -> dict[str, object]:
        if not hint:
            return {}
        query = parse.quote(hint)
        endpoint = f"https://musicbrainz.org/ws/2/release?fmt=json&limit=1&query={query}"
        try:
            payload = self._fetch_json(endpoint)
        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError):
            return {}

        releases = payload.get("releases")
        if not isinstance(releases, list) or not releases:
            return {}
        first = releases[0]
        if not isinstance(first, dict) or not first.get("id"):
            return {}
        return self._fetch_musicbrainz("release", str(first.get("id")))

    def _fallback_discogs_search(self, hint: str) -> dict[str, object]:
        if not hint:
            return {}
        query = parse.quote(hint)
        endpoint = f"https://api.discogs.com/database/search?q={query}&type=release"
        try:
            payload = self._fetch_json(endpoint)
        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError):
            return {}

        results = payload.get("results")
        if not isinstance(results, list) or not results:
            return {}
        first = results[0]
        if not isinstance(first, dict):
            return {}
        first_id = first.get("id")
        if not isinstance(first_id, int):
            return {}
        return self._fetch_discogs("release", str(first_id))

