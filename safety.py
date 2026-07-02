"""
Last-resort safety net for every Gradio event handler.

Why this exists:
Individual handlers (chat, handle_pdf_upload) already have their own
try/except around the specific things most likely to fail (Groq calls,
PDF parsing, empty ChromaDB). @safe_call is the outer net that catches
ANYTHING else unexpected — a bug, a library edge case, a malformed
upload — so the user NEVER sees a raw Python traceback in the browser.

Instead, the full traceback is printed to the server logs (so you can
debug it) and the user sees a clean gr.Error toast message.

Works for both normal functions and generator functions (chat() streams
intermediate "thinking..." states via `yield`, so it needs the generator
branch).
"""
import functools
import inspect
import traceback

import gradio as gr


def safe_call(func):
    if inspect.isgeneratorfunction(func):
        @functools.wraps(func)
        def generator_wrapper(*args, **kwargs):
            try:
                for output in func(*args, **kwargs):
                    yield output
            except gr.Error:
                raise  # already an intentional, user-facing message
            except Exception as e:
                traceback.print_exc()  # full detail server-side only
                raise gr.Error(f"Something went wrong: {e}")
        return generator_wrapper

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except gr.Error:
            raise
        except Exception as e:
            traceback.print_exc()
            raise gr.Error(f"Something went wrong: {e}")
    return wrapper