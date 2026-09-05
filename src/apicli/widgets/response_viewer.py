"""Response viewer: status line + body / headers / timing tabs."""

from __future__ import annotations

import json

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import ScrollableContainer, Vertical
from textual.widgets import Static, TabbedContent, TabPane
from rich.syntax import Syntax

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
                with ScrollableContainer(id="resp-body-scroll", classes="resp-scroll"):
                    yield Static("", id="response-body", classes="resp-content")
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
        self.query_one("#response-body", Static).update("")
        self.query_one("#response-headers", Static).update("")
        self.query_one("#response-timing", Static).update("")

    def show_response(self, data: ResponseData) -> None:
        self._update_status(data)
        status = self.query_one("#response-status", Static)
        body = self.query_one("#response-body", Static)
        headers = self.query_one("#response-headers", Static)
        timing = self.query_one("#response-timing", Static)

        if data.error:
            status.update(Text(f"ERROR  {data.error}", style="bold red"))
            body.update(Text(data.error, style="red"))
            headers.update("")
            timing.update(self._render_timing(data))
            return

        body.update(self._renderable_body(data))
        header_text = "\n".join(f"{k}: {v}" for k, v in data.headers)
        headers.update(Text(header_text or "(no headers)", style="dim"))
        timing.update(self._render_timing(data))

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

    def _renderable_body(self, data: ResponseData):
        text = data.text
        strip = text.lstrip()
        is_json = "json" in " ".join(k.lower() for k, _ in data.headers).lower() or (
            strip.startswith("{") or strip.startswith("[")
        )
        if is_json:
            try:
                parsed = json.loads(text)
                from rich.pretty import Pretty

                return Pretty(parsed)
            except (ValueError, TypeError):
                pass
        if text.strip().startswith("<"):
            try:
                return Syntax(text, "xml", theme="monokai", word_wrap=False)
            except Exception:
                pass
        return Text(text, style="", no_wrap=True)