"""Entry point.

The loop is async so the same file runs both as a desktop app and, once
compiled by pygbag, inside a browser: WebAssembly has a single thread shared
with the page, so each frame has to yield control back or the tab freezes.
"""
import asyncio

# pygbag reads the imports of *this* file to decide which packages to load into
# the WebAssembly runtime, so pygame has to be named here even though main.py
# never calls it directly. Without this the browser build gets a stub module and
# dies on pygame.init().
import pygame  # noqa: F401

from game import Game


async def main():
    await Game().run()


asyncio.run(main())
