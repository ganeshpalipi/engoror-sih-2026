"""
Modular AI layer (built in Phases 4-7).

Planned modules:
    asr_service.py          Offline Hindi speech recognition (WAV in, CPU)
    translation_service.py  Hindi -> Santhali MT (candidate: IndicTrans2,
                            hin_Deva -> sat_Olck), load-once + cache + batch
    tts_service.py          Offline Santhali TTS (WAV out, pluggable provider,
                            pre-recorded phrase fallback)
    language_detection.py   Language / code-switch check
    pipeline.py             Full speech-to-speech orchestration + latency
    model_manager.py        Lazy loading, caching, model status reporting

Rules:
    - Load models once, cache them, never reload per request.
    - No fake AI outputs. If a model is unavailable, report it honestly
      through the model status endpoint.
    - Mock fallbacks are development-only and clearly labelled.
    - CPU first; CUDA is optional; ONNX is a future optimisation path.
"""
