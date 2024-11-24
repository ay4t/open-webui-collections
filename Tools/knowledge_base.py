import requests
import typing
import logging
import asyncio
import inspect
from typing import List, Dict, Optional, Union
import sys
import time

logger = logging.getLogger(__name__)

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

    async def fail(self, description="Unknown error"):
        """Emit a failure event."""
        await self.status(description=description, status="error", done=True)

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

class Tools:
    def __init__(self, base_url: str = "http://0.0.0.0:8082", token: str = "your-secret-token"):
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.headers = {
            "token": self.token,
            "Content-Type": "application/json"
        }
    
    async def query(
        self,
        query: str,
        k: int = 10,
        filter_dict: Optional[Dict] = None,
        score_threshold: float = 0.3,
        __event_emitter__: typing.Callable[[dict], typing.Any] = None
    ) -> List[Dict]:
        """
        Query the knowledge base for relevant documents.
        
        :param query: The query text
        """
        emitter = EventEmitter(__event_emitter__)
        
        try:
            await emitter.status(
                description="Preparing to search knowledge base...",
                status="in_progress"
            )
            time.sleep(1)

            payload = {
                "query": query,
                "k": k,
                "filter_dict": filter_dict,
                "score_threshold": score_threshold
            }
            
            await emitter.status(
                description=f"Searching knowledge base for: {query}",
                status="searching"
            )
            time.sleep(1)
            
            response = requests.post(
                f"{self.base_url}/query",
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            
            response_data = response.json()
            results = response_data.get("results", [])
            
            if response_data["status"] == "success":
                if results:
                    await emitter.status(
                        description=f"Found {len(results)} relevant documents",
                        status="success",
                        done=True
                    )
                    time.sleep(1)
                    # Emit each result as a citation
                    for result in results:
                        await emitter.citation(
                            document=result.get("content", ""),
                            metadata=result.get("metadata", {}),
                            source=result.get("source", "knowledge_base")
                        )
                else:
                    await emitter.status(
                        description=response_data.get("message", "No relevant documents found"),
                        status="no_results",
                        done=True
                    )
            else:
                await emitter.status(
                    description=response_data.get("message", "Query failed"),
                    status="error",
                    done=True
                )
            
            return results
            
        except Exception as e:
            error_msg = f"Error querying knowledge base: {str(e)}"
            logger.error(error_msg)
            await emitter.fail(description=error_msg)
            return []