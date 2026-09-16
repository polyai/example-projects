from _gen import *  # <AUTO GENERATED>


VOICE_IDS = {
    "main": "oW8bn5YtBB89X2nJ0DT9",
    "disclaimer": "Tx7VLgfksXHVnoY6jDGU",
}


@func_description("[UTIL] A custom function for setting the voice")
@func_parameter("voice_type", 'Can be either "main" or "disclaimer"')
def set_voice(conv: Conversation, voice_type: str):
    voice_id = VOICE_IDS.get(str(voice_type or "").lower().strip())
    if voice_id is None:
        conv.log.warning(
            "Voice override not applied, unknown voice type", voice_type=voice_type
        )
        return
    try:
        voice = ElevenLabsVoice(
            provider_voice_id=voice_id, model_id="eleven_v3", stability=1
        )
        conv.set_voice(voice)
    except Exception as e:
        conv.log.warning(
            "Voice override not applied", voice_type=voice_type, error=str(e)
        )
