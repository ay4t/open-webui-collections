import os
import requests
from datetime import datetime
import typing
import asyncio
import inspect
import json
import sys
import logging
import time
from urllib.parse import urljoin
import re

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(handler)


class Tools:
    def __init__(self):
        self.citation = True
        self.base_url = "r.jina.ai/"
        self.timeout = 30  # timeout in seconds
        self.headers = {
            "X-No-Cache": "true",
            "X-With-Images-Summary": "true",
            "X-With-Links-Summary": "true",
        }
        # URL regex pattern
        self.url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s]*'


    async def jina_web_scrape(
        self, 
        query: str, 
        __event_emitter__: typing.Callable[[dict], typing.Any] = None
    ) -> str:
        """
        Scrape websites found in the query using Jina's r.jina.ai service.
        
        :param query: The text that may contain one or more URLs to scrape.
        :param __event_emitter__: An optional event emitter function.
        """
        emitter = EventEmitter(__event_emitter__)
        
        # Extract URLs from query
        urls = re.findall(self.url_pattern, query)
        if not urls:
            logger.info("No valid URLs found in the input")
            await emitter.status("No valid URLs found in the input", "complete", True)
            return "No valid URLs found to scrape."

        await emitter.status(f"Found {len(urls)} URLs to scrape")
        
        all_results = []
        
        for url in urls:
            try:
                # Validate and prepare URL
                if not url.startswith(('http://', 'https://')):
                    url = f'https://{url}'
                
                jina_url = urljoin(self.base_url, url)
                
                await emitter.status(f"Initiating Jina web scrape for: {url}")
                
                # Simulate request preparation
                await emitter.status(f"Preparing request to Jina service for {url}...")
                time.sleep(1)
                
                # Simulate API call
                await emitter.status(f"Sending request to Jina service for {url}...")
                time.sleep(2)
                
                try:
                    # Make the actual request to Jina's service
                    response = requests.get(jina_url, headers=self.headers, timeout=self.timeout)
                    response.raise_for_status()
                    
                    await emitter.status(f"Processing response from Jina service for {url}...")
                    
                    # Extract content and remove Links/Buttons section
                    content = response.text
                    links_section_start = content.rfind("Images:")
                    if links_section_start != -1:
                        content = content[:links_section_start].strip()
                    
                    all_results.append(f"## Web Scrape Result for {url}: \n\n{content}\n\n")
                    
                except requests.RequestException as e:
                    error_msg = f"Failed to scrape {url}: {str(e)}"
                    await emitter.status(error_msg, "error", False)
                    all_results.append(f"## Error scraping {url}: \n{error_msg}\n\n")
                    continue
                    
            except Exception as e:
                error_msg = f"Unexpected error while processing {url}: {str(e)}"
                await emitter.status(error_msg, "error", False)
                all_results.append(f"## Error processing {url}: \n{error_msg}\n\n")
                continue
        
        await emitter.status(
            f"Completed scraping {len(urls)} URLs", 
            "complete", 
            True
        )
        
        # Combine all results
        return "".join(all_results)


class EventEmitter:
    """
    Helper wrapper for OpenWebUI event emissions.
    Handles various types of events and provides debug capabilities.
    """

    def __init__(
        self,
        event_emitter: typing.Callable[[dict], typing.Any] = None,
        debug: bool = False,
    ):
        self.event_emitter = event_emitter
        self._debug = debug
        self._status_prefix = None

    def set_status_prefix(self, status_prefix):
        """Set a prefix for all status messages."""
        self._status_prefix = status_prefix

    async def _emit(self, typ, data):
        """Internal method to emit events."""
        if self._debug:
            print(f"Emitting {typ} event: {data}", file=sys.stderr)
        if not self.event_emitter:
            return None
        maybe_future = self.event_emitter(
            {
                "type": typ,
                "data": data,
            }
        )
        if asyncio.isfuture(maybe_future) or inspect.isawaitable(maybe_future):
            return await maybe_future

    async def status(
        self, description="Unknown state", status="in_progress", done=False
    ):
        """Emit a status update event."""
        if self._status_prefix is not None:
            description = f"{self._status_prefix}{description}"
        await self._emit(
            "status",
            {
                "status": status,
                "description": description,
                "done": done,
            },
        )
        if not done and len(description) <= 1024:
            await self._emit(
                "status",
                {
                    "status": status,
                    "description": description,
                    "done": done,
                },
            )

    async def fail(self, description="Unknown error"):
        """Emit a failure event."""
        await self.status(description=description, status="error", done=True)

    async def message(self, content):
        """Emit a message event."""
        await self._emit(
            "message",
            {
                "content": content,
            },
        )

    async def citation(self, document, metadata, source):
        """Emit a citation event."""
        await self._emit(
            "citation",
            {
                "document": document,
                "metadata": metadata,
                "source": source,
            },
        )

    async def code_execution_result(self, output):
        """Emit a code execution result event."""
        await self._emit(
            "code_execution_result",
            {
                "output": output,
            },
        )
