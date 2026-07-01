from concurrent.futures import ThreadPoolExecutor, as_completed

from _gen import *  # <AUTO GENERATED>

# How long to wait for Claude after GPT returns first (seconds)
CLAUDE_GRACE_PERIOD_SECONDS = 2.0


@func_description("[UTIL] Make a custom LLM call with fallback")
@func_parameter("prompt", "The system prompt to use")
@func_parameter("return_json", "Whether the response should be a json object")
def custom_llm_call(conv: Conversation, prompt: str, return_json: bool):
    """
    Calls Claude and GPT in parallel with Claude-first preference.

    Strategy:
    - If Claude finishes first with a valid result, use it immediately.
    - If GPT finishes first, wait up to CLAUDE_GRACE_PERIOD_SECONDS for Claude.
    - If Claude doesn't respond in time or fails, fall back to GPT's result.
    """

    def call_model(prompt: str, return_json: bool, model=None):
        try:
            kwargs = {"show_history": True, "prompt": prompt, "return_json": return_json}
            if model:
                kwargs["model"] = model
            return conv.utils.prompt_llm(**kwargs)
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=2) as executor:
        claude_future = executor.submit(call_model, prompt, return_json, "claude-sonnet-4")
        gpt_future = executor.submit(call_model, prompt, return_json, "gpt-4o")

        futures = {claude_future: "claude", gpt_future: "gpt"}
        gpt_result = None

        for future in as_completed(futures):
            model_name = futures[future]

            try:
                result = future.result()
            except Exception as e:
                conv.log.warning(f"{model_name} future raised exception", error=str(e))
                continue

            if model_name == "claude":
                if result is not None:
                    return result
                conv.log.warning("Claude returned None")
            else:
                # GPT finished first - save result but wait briefly for Claude
                gpt_result = result
                if not claude_future.done():
                    conv.log.info("GPT finished first, waiting briefly for Claude")
                    try:
                        claude_result = claude_future.result(timeout=CLAUDE_GRACE_PERIOD_SECONDS)
                        if claude_result is not None:
                            return claude_result
                        conv.log.warning("Claude returned None after grace period")
                    except TimeoutError:
                        conv.log.info("Claude timed out after grace period")
                    except Exception as e:
                        conv.log.warning("Claude failed during grace period", error=str(e))
                    # Grace period ended without valid Claude result - use GPT
                    if gpt_result is not None:
                        conv.log.info("Using GPT fallback")
                        return gpt_result

        # Fall back to GPT result if we have one
        if gpt_result is not None:
            conv.log.info("Using GPT fallback")
            return gpt_result

        conv.log.warning("Both models failed")
        if return_json:
            return {}
        return None
