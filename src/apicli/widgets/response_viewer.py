"""Response viewer: status line + body / headers / timing tabs."""

from __future__ import annotations

import json

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import ScrollableContainer, Vertical
from textual.widgets import Static, TabbedContent, TabPane, TextArea

from ..export import pretty_json
from ..models import ResponseData

_STATUS_STYLES = {
    (200, 299): "bold green",
    (300, 399): "bold cyan",
    (400, 499): "bold yellow",
    (500, 599): "bold red",
}


class ResponseViewer(Vertical):
    """Paint a ResponseData into the response pane."""

    def compose(self) -> ComposeResult:
        yield Static("No response yet", id="response-status")
        with TabbedContent(id="response-tabs"):
            with TabPane("Body", id="tab-resp-body"):
                yield TextArea(id="response-body", read_only=True, classes="resp-content")
            with TabPane("Headers", id="tab-resp-headers"):
                with ScrollableContainer(id="resp-headers-scroll", classes="resp-scroll"):
                    yield Static("", id="response-headers", classes="resp-content")
            with TabPane("Timing", id="tab-resp-timing"):
                with ScrollableContainer(id="resp-timing-scroll", classes="resp-scroll"):
                    yield Static("", id="response-timing", classes="resp-content")

    def on_mount(self) -> None:
        self.border_title = "Response"

    def reset(self) -> None:
        self.query_one("#response-status", Static).update("No response yet")
        self.query_one("#response-body", TextArea).load_text("")
        self.query_one("#response-headers", Static).update("")
        self.query_one("#response-timing", Static).update("")

    def show_response(self, data: ResponseData) -> None:
        self._update_status(data)
        status = self.query_one("#response-status", Static)
        body = self.query_one("#response-body", TextArea)
        headers = self.query_one("#response-headers", Static)
        timing = self.query_one("#response-timing", Static)

        if data.error:
            status.update(Text(f"ERROR  {data.error}", style="bold red"))
            body.load_text(data.error)
            self._set_language(body, None)
            headers.update("")
            timing.update(self._render_timing(data))
            return

        self._populate_body(body, data)
        header_text = "\n".join(f"{k}: {v}" for k, v in data.headers)
        headers.update(Text(header_text or "(no headers)", style="dim"))
        timing.update(self._render_timing(data))

    def _populate_body(self, body: TextArea, data: ResponseData) -> None:
        text, language = self._body_parts(data)
        body.load_text(text)
        self._set_language(body, language)

    def _body_parts(self, data: ResponseData) -> tuple[str, str | None]:
        text = data.text
        strip = text.lstrip()
        is_json = "json" in " ".join(k.lower() for k, _ in data.headers).lower() or (
            strip.startswith("{") or strip.startswith("[")
        )
        if is_json:
            try:
                json.loads(text)
            except (ValueError, TypeError):
                pass
            else:
                return pretty_json(text), "json"
        if strip.startswith("<"):
            return text, "xml"
        return text, None

    def _set_language(self, body: TextArea, language: str | None) -> None:
        try:
            body.language = language
        except ValueError:
            pass

    def _render_timing(self, data: ResponseData) -> str:
        lines = [
            f"Method:     {data.request_method}",
            f"URL:        {data.url}",
            f"HTTP:       {data.http_version}",
            f"Status:     {data.status_code} {data.reason}".strip(),
            f"Elapsed:    {data.elapsed_ms} ms",
            f"Size:       {data.size_bytes} B",
        ]
        if data.timeline:
            lines.append("")
            lines.append("Timeline")
            lines.append("---------")
            for event in data.timeline:
                lines.append(f"{event.elapsed_ms:>8} ms  {event.label}")
        return "\n".join(lines)

    def _update_status(self, data: ResponseData) -> None:
        status = self.query_one("#response-status", Static)
        if data.error:
            status.update(Text(f"ERROR  {data.error}", style="bold red"))
            return
        style = "-"
        for (lo, hi), color in _STATUS_STYLES.items():
            if lo <= data.status_code <= hi:
                style = color
                break
        line = Text()
        line.append(f"{data.request_method}  {data.url}\n", style="bold")
        line.append(f"{data.status_code} {data.reason}", style=style)
        line.append(f"  ·  {data.elapsed_ms} ms  ·  {data.size_bytes} B  ·  {data.http_version}", style="dim")
        status.update(line)