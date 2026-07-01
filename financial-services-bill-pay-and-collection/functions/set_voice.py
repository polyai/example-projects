from _gen import *  # <AUTO GENERATED>


@func_description("[UTIL] A custom function for setting the voice")
@func_parameter("voice_type", 'Can be either "main" or "disclaimer"')
def set_voice(conv: Conversation, voice_type: str):
    if voice_type.lower().strip() == "main":
        voice = ElevenLabsVoice(
            provider_voice_id="oW8bn5YtBB89X2nJ0DT9",
            model_id="eleven_v3",
            stability=1,
        )
        conv.set_voice(voice)
    elif voice_type.lower().strip() == "disclaimer":
        voice = ElevenLabsVoice(
            provider_voice_id="Tx7VLgfksXHVnoY6jDGU",
            model_id="eleven_v3",
            stability=1,
        )
        conv.set_voice(voice)
    else:
        raise ValueError(f"voice_type set to {voice_type}. Must be 'main' or 'disclaimer' instead.")
