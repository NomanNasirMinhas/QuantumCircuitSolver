import base64
import json
import os
import time
import urllib.request
from typing import Any, Dict, List, Tuple

from google import genai
from google.genai import types

SYSTEM_INSTRUCTION = """System Instruction: Quantum Media Producer
Role: You are the Quantum Media Producer Agent, a world-class visual storyteller and prompt engineer. Your mission is to transform abstract quantum data (gates, circuits, and algorithms) into cinematic, metaphorical, and educational visual assets.
Core Objective: Generate precise, high-fidelity prompts for Google Veo (Video) and Imagen (Graphics). Every visual must reinforce a quantum concept through narrative metaphors.

1. The Visualization Framework
Categorize every request into one of three visual styles:
- The Narrative Hook (Cinematic): High-production sci-fi visuals.
- The Conceptual Diagram (Schematic): Clean, glowing 3D representations of the math.
- The Result Visualization (Data Art): Transforming histograms into "Energy Maps" or "Probability Clouds."

2. Output Requirements
Your output must be a structured JSON object:
{
  "asset_type": "VIDEO | IMAGE | ANIMATION",
  "concept_focus": "e.g., Entanglement, Interference",
  "veo_video_prompt": "Cinematic 4k video prompt specifically mapping the user's domain problem to a relatable real-world cinematic visual... do not be generic.",
  "imagen_graphic_prompt": "High-resolution 2D schematic prompt...",
  "audio_script": "A 30-second podcast-style narration script explaining the problem domain and the quantum solution logic as a cohesive, relatable story to a non-quantum person..."
}

3. Style Guide
Color Palette: Quantum Blue (#00E5FF) for Superposition, Entangled Purple (#D500F9) for Bell States, Interference Gold (#FFD600) for measurements.
Atmosphere: Ethereal, vast, and high-tech. Aim for an "Enterprise Learning" or "Sci-Fi Documentary" feel.
Metaphor Mapping:
- Superposition = A coin spinning so fast it is both heads and tails.
- Entanglement = Two glowing threads connecting stars across a galaxy.
- Measurement = A camera flash causing a blurred object to snap into sharp singular reality.
"""


class MediaProducerAgent:
    def __init__(self):
        self.client = genai.Client(
            vertexai=True,
            project=os.environ.get("GCP_PROJECT_ID"),
            location="global",
        )
        self.structured_model = os.getenv("MEDIA_STRUCTURED_MODEL", "gemini-3.1-flash-lite-preview")
        self.interleaved_models = self._candidate_models(
            "GEMINI_INTERLEAVED_MODEL",
            ["gemini-2.5-flash-image-preview", "gemini-2.0-flash-exp-image-generation"],
        )
        self.imagen_models = self._candidate_models(
            "IMAGEN_MODEL",
            ["imagen-3.0-generate-002", "imagen-3.0-generate-001"],
        )
        self.veo_models = self._candidate_models(
            "VEO_MODEL",
            ["veo-2.0-generate-001", "veo-3.0-generate-preview"],
        )
        self.tts_models = self._candidate_models(
            "GEMINI_TTS_MODEL",
            ["gemini-2.5-pro-tts", "gemini-2.5-flash-preview-tts"],
        )
        self.tts_voice_name = os.getenv("GEMINI_TTS_VOICE", "Kore")

    @staticmethod
    def _candidate_models(env_var: str, defaults: List[str]) -> List[str]:
        primary = os.getenv(env_var, "").strip()
        models = []
        if primary:
            models.append(primary)
        models.extend(defaults)
        deduped = []
        for model in models:
            if model and model not in deduped:
                deduped.append(model)
        return deduped

    @staticmethod
    def _algo_summary(mapping: dict) -> dict:
        return {
            "algorithm": mapping.get("identified_algorithm", "Unknown"),
            "problem_class": mapping.get("problem_class", "Unknown"),
            "qubit_count": mapping.get("qubit_requirement_estimate", "Unknown"),
            "story_explanation": mapping.get("story_explanation", ""),
        }

    @staticmethod
    def _extract_interleaved_parts(response: Any) -> Tuple[List[str], List[Dict[str, str]]]:
        narrative_segments: List[str] = []
        images: List[Dict[str, str]] = []

        candidates = getattr(response, "candidates", None) or []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            parts = getattr(content, "parts", None) or []
            for part in parts:
                if getattr(part, "text", None):
                    segment = part.text.strip()
                    if segment:
                        narrative_segments.append(segment)
                inline_data = getattr(part, "inline_data", None)
                if inline_data and getattr(inline_data, "data", None):
                    images.append(
                        {
                            "mime_type": getattr(inline_data, "mime_type", "image/png"),
                            "data": base64.b64encode(inline_data.data).decode("utf-8"),
                        }
                    )

        if not narrative_segments and getattr(response, "text", None):
            narrative_segments.append(response.text.strip())
        return narrative_segments, images

    @staticmethod
    def _extract_audio_blob(response: Any) -> Tuple[bytes, str]:
        candidates = getattr(response, "candidates", None) or []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            parts = getattr(content, "parts", None) or []
            for part in parts:
                inline_data = getattr(part, "inline_data", None)
                if not inline_data:
                    continue
                blob = getattr(inline_data, "data", None)
                mime = getattr(inline_data, "mime_type", "audio/wav")
                if blob and isinstance(blob, (bytes, bytearray)) and str(mime).startswith("audio/"):
                    return bytes(blob), mime
        return b"", ""

    def generate_visuals(self, mapping: dict, code: str) -> dict:
        algo_summary = self._algo_summary(mapping)
        prompt_text = (
            "Algorithm mapping with User Problem Context:\n"
            f"{json.dumps(algo_summary, indent=2)}\n\n"
            "Please generate the visual assets and audio script. IMPORTANT: Make the video prompt "
            "and audio script exceptionally specific to the user's problem and story_explanation."
        )

        contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt_text)])]
        generate_content_config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.7,
            top_p=0.95,
            max_output_tokens=8192,
            response_mime_type="application/json",
        )

        response = self.client.models.generate_content(
            model=self.structured_model,
            contents=contents,
            config=generate_content_config,
        )

        try:
            if not response.text:
                return {
                    "error": "Empty response from API (possibly safety blocked or resource exhausted).",
                    "raw_output": str(response),
                }
            return json.loads(response.text)
        except Exception as e:
            return {
                "error": f"Media agent failed to return JSON: {str(e)}",
                "raw_output": getattr(response, "text", str(response)),
            }

    def generate_interleaved_story(self, mapping: dict, code: str) -> dict:
        summary = self._algo_summary(mapping)
        prompt_text = (
            "Create an interleaved response with narrative + generated images.\n"
            "Return rich storytelling text and image assets in the same response.\n"
            f"Context:\n{json.dumps(summary, indent=2)}"
        )
        contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt_text)])]
        errors: List[str] = []

        for model in self.interleaved_models:
            try:
                response = self.client.models.generate_content(
                    model=model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        temperature=0.8,
                        top_p=0.95,
                        max_output_tokens=4096,
                        response_modalities=[types.Modality.TEXT, types.Modality.IMAGE],
                        image_config=types.ImageConfig(aspect_ratio="16:9"),
                    ),
                )
                narrative_segments, images = self._extract_interleaved_parts(response)
                if narrative_segments or images:
                    return {
                        "model": model,
                        "narrative_segments": narrative_segments,
                        "images": images,
                    }
                errors.append(f"{model}: empty response")
            except Exception as e:
                errors.append(f"{model}: {e}")

        return {"error": "No interleaved model succeeded", "details": errors}

    def generate_imagen_image(self, prompt: str) -> dict:
        if not prompt:
            return {"error": "Prompt is empty"}

        errors: List[str] = []
        for model in self.imagen_models:
            try:
                response = self.client.models.generate_images(
                    model=model,
                    prompt=prompt,
                    config=types.GenerateImagesConfig(
                        number_of_images=1,
                        aspect_ratio="16:9",
                        output_mime_type="image/png",
                    ),
                )
                generated = (response.generated_images or [None])[0]
                image = getattr(generated, "image", None) if generated else None
                image_bytes = getattr(image, "image_bytes", None) if image else None
                if image_bytes:
                    return {
                        "model": model,
                        "mime_type": getattr(image, "mime_type", "image/png"),
                        "data": base64.b64encode(image_bytes).decode("utf-8"),
                    }
                errors.append(f"{model}: no image bytes")
            except Exception as e:
                errors.append(f"{model}: {e}")

        return {"error": "Imagen generation failed", "details": errors}

    def generate_veo_video(self, prompt: str, timeout_sec: int = 300) -> dict:
        if not prompt:
            return {"error": "Prompt is empty"}

        errors: List[str] = []
        for model in self.veo_models:
            try:
                op = self.client.models.generate_videos(
                    model=model,
                    prompt=prompt,
                    config=types.GenerateVideosConfig(
                        aspect_ratio="16:9",
                        duration_seconds=8,
                        generate_audio=False,
                    ),
                )

                deadline = time.time() + timeout_sec
                while not op.done and time.time() < deadline:
                    time.sleep(5)
                    op = self.client.operations.get(op)

                if not op.done:
                    errors.append(f"{model}: timed out")
                    continue
                if op.error:
                    errors.append(f"{model}: {op.error}")
                    continue

                response = op.response or op.result
                videos = getattr(response, "generated_videos", None) or []
                if not videos:
                    errors.append(f"{model}: no generated videos")
                    continue

                video_obj = getattr(videos[0], "video", None)
                video_bytes = getattr(video_obj, "video_bytes", None) if video_obj else None
                if video_bytes:
                    return {
                        "model": model,
                        "mime_type": getattr(video_obj, "mime_type", "video/mp4"),
                        "data": base64.b64encode(video_bytes).decode("utf-8"),
                    }

                uri = getattr(video_obj, "uri", "") if video_obj else ""
                if uri.startswith("http://") or uri.startswith("https://"):
                    with urllib.request.urlopen(uri, timeout=30) as resp:
                        downloaded = resp.read()
                    return {
                        "model": model,
                        "mime_type": getattr(video_obj, "mime_type", "video/mp4"),
                        "data": base64.b64encode(downloaded).decode("utf-8"),
                        "uri": uri,
                    }
                if uri:
                    return {
                        "model": model,
                        "mime_type": getattr(video_obj, "mime_type", "video/mp4"),
                        "data": "",
                        "uri": uri,
                    }
                errors.append(f"{model}: no video bytes or URI")
            except Exception as e:
                errors.append(f"{model}: {e}")

        return {"error": "Veo generation failed", "details": errors}

    def generate_contextual_narration_audio(self, mapping: dict, audio_script: str) -> dict:
        if not audio_script:
            return {"error": "Audio script is empty"}

        summary = self._algo_summary(mapping)
        prompt_text = (
            "Narrate this in a highly contextual, informative storytelling style.\n"
            "Sound like a confident documentary host explaining the exact user's quantum scenario.\n"
            "Use natural pauses and clear emphasis for non-experts.\n\n"
            f"Context:\n{json.dumps(summary, indent=2)}\n\n"
            f"Narration script:\n{audio_script}"
        )

        errors: List[str] = []
        for model in self.tts_models:
            try:
                response = self.client.models.generate_content(
                    model=model,
                    contents=[prompt_text],
                    config=types.GenerateContentConfig(
                        response_modalities=[types.Modality.AUDIO],
                        speech_config=types.SpeechConfig(
                            voice_config=types.VoiceConfig(
                                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                    voice_name=self.tts_voice_name
                                )
                            )
                        ),
                        temperature=0.6,
                        top_p=0.95,
                    ),
                )
                audio_bytes, mime_type = self._extract_audio_blob(response)
                if audio_bytes:
                    return {
                        "model": model,
                        "mime_type": mime_type or "audio/wav",
                        "data": base64.b64encode(audio_bytes).decode("utf-8"),
                    }
                errors.append(f"{model}: no audio blob in response")
            except Exception as e:
                errors.append(f"{model}: {e}")

        return {"error": "Gemini TTS generation failed", "details": errors}
