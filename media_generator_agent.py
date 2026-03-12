import base64
import io
import json
import os
import re
import wave
from typing import Any, Dict, List, Tuple

from google.adk.tools import google_search
from google import genai
from google.genai import types

from adk_runtime import ADKAgentRuntime

STORYBOOK_SYSTEM_INSTRUCTION = """System Instruction: Quantum Storyline Creator
Role: You are a narrative learning designer that converts technical quantum material into a coherent, page-by-page storybook.
Core Objective: Build one integrated storyline where each page combines:
1) a visual illustration concept,
2) narrative text for reading,
3) a narration script for audio playback.

Output requirements:
Return valid JSON only, with this exact top-level structure:
{
  "title": "string",
  "summary": "2-4 sentence overview",
  "target_audience": "Beginner | Intermediate | Advanced",
  "art_direction": "consistent visual style guidance for all pages",
  "pages": [
    {
      "page_number": 1,
      "title": "string",
      "learning_objective": "specific lesson for this page",
      "algorithm_focus": "quantum concept explained here",
      "code_focus": "specific code-level element explained here",
      "page_text": "storybook text shown on the page in markdown",
      "key_takeaways": ["item 1", "item 2"],
      "illustration_prompt": "single-page illustration prompt, visually consistent with other pages",
      "narration_script": "spoken script for this page audio"
    }
  ]
}

Style constraints:
- Maintain one consistent cast, scene style, and tone across all pages.
- Use cumulative teaching flow from problem framing to circuit and simulation insight.
- Keep each page specific to the user's exact scenario and generated code.
- Avoid generic filler and avoid inventing unsupported APIs.
"""

FALLBACK_PLACEHOLDER_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/w8AAgMBAp8z2QAAAABJRU5ErkJggg=="
)


class MediaProducerAgent:
    def __init__(self):
        self.client = genai.Client(
            vertexai=True,
            project=os.environ.get("GCP_PROJECT_ID"),
            location="global",
        )
        self.storybook_model = os.getenv("MEDIA_STORYBOOK_MODEL", "gemini-3.1-flash-lite-preview")
        self.imagen_models = self._candidate_models(
            "IMAGEN_MODEL",
            ["imagen-3.0-generate-002", "imagen-3.0-generate-001"],
        )
        self.tts_models = self._candidate_models(
            "GEMINI_TTS_MODEL",
            ["gemini-2.5-pro-tts", "gemini-2.5-flash-preview-tts"],
        )
        self.tts_voice_name = os.getenv("GEMINI_TTS_VOICE", "Kore")
        self.storybook_runtime = ADKAgentRuntime(
            name="media_storybook_agent",
            model=self.storybook_model,
            instruction=STORYBOOK_SYSTEM_INSTRUCTION,
            tools=[google_search],
            generate_content_config=types.GenerateContentConfig(
                temperature=0.75,
                top_p=0.95,
                max_output_tokens=8192,
                response_mime_type="application/json",
            ),
        )

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
    def _safe_int(value: Any, default: int, minimum: int, maximum: int) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            parsed = default
        return max(minimum, min(parsed, maximum))

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

    @staticmethod
    def _pcm_to_wav(pcm_bytes: bytes, sample_rate: int = 24000, channels: int = 1, sample_width: int = 2) -> bytes:
        with io.BytesIO() as buffer:
            with wave.open(buffer, "wb") as wav_file:
                wav_file.setnchannels(channels)
                wav_file.setsampwidth(sample_width)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(pcm_bytes)
            return buffer.getvalue()

    @staticmethod
    def _normalize_audio_blob(audio_bytes: bytes, mime_type: str) -> Tuple[bytes, str]:
        mime = (mime_type or "").lower().strip()
        if not audio_bytes:
            return b"", ""
        if "audio/l16" in mime or "audio/pcm" in mime:
            sample_rate = 24000
            channels = 1
            rate_match = re.search(r"rate=(\d+)", mime)
            channel_match = re.search(r"channels?=(\d+)", mime)
            if rate_match:
                sample_rate = int(rate_match.group(1))
            if channel_match:
                channels = int(channel_match.group(1))
            return MediaProducerAgent._pcm_to_wav(audio_bytes, sample_rate=sample_rate, channels=channels), "audio/wav"
        if mime in {"audio/wav", "audio/x-wav", "audio/wave", "audio/mpeg", "audio/mp3", "audio/ogg"}:
            return audio_bytes, "audio/mpeg" if mime == "audio/mp3" else mime
        return audio_bytes, "audio/wav"

    @staticmethod
    def _placeholder_image_b64(page_number: Any, page_title: str, error: str, detail: str = "") -> str:
        try:
            import matplotlib

            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            from textwrap import wrap

            title = str(page_title or f"Page {page_number}").strip()
            reason = str(error or "image generation failed").strip()
            detail_text = str(detail or "").strip()

            lines: List[str] = [
                f"Storybook Page {page_number} Illustration Unavailable",
                title,
                f"Reason: {reason}",
            ]
            if detail_text:
                lines.append("Details:")
                lines.extend(wrap(detail_text, width=72)[:8])

            figure = plt.figure(figsize=(10, 7), dpi=120)
            figure.patch.set_facecolor("#141d2b")
            axis = figure.add_axes([0, 0, 1, 1])
            axis.set_axis_off()

            y = 0.92
            for index, line in enumerate(lines):
                color = "#f3f4f6" if index == 0 else "#cbd5e1"
                fontsize = 18 if index == 0 else 12
                axis.text(
                    0.05,
                    y - index * 0.08,
                    line,
                    color=color,
                    fontsize=fontsize,
                    ha="left",
                    va="top",
                    wrap=True,
                )

            buffer = io.BytesIO()
            figure.savefig(buffer, format="png", bbox_inches="tight", pad_inches=0.3, facecolor=figure.get_facecolor())
            plt.close(figure)
            return base64.b64encode(buffer.getvalue()).decode("utf-8")
        except Exception:
            return FALLBACK_PLACEHOLDER_PNG_BASE64

    @staticmethod
    def _normalize_storybook_outline(raw_outline: dict, page_count: int) -> dict:
        title = str(raw_outline.get("title", "")).strip() or "Quantum Storybook"
        summary = str(raw_outline.get("summary", "")).strip()
        target_audience = str(raw_outline.get("target_audience", "")).strip() or "Beginner"
        art_direction = str(raw_outline.get("art_direction", "")).strip()

        raw_pages = raw_outline.get("pages", [])
        if isinstance(raw_pages, dict):
            raw_pages = [raw_pages]
        if not isinstance(raw_pages, list):
            raw_pages = []

        normalized_pages: List[Dict[str, Any]] = []
        for index, raw_page in enumerate(raw_pages):
            if not isinstance(raw_page, dict):
                continue
            page_number = MediaProducerAgent._safe_int(
                raw_page.get("page_number"),
                default=index + 1,
                minimum=1,
                maximum=999,
            )
            key_takeaways_raw = raw_page.get("key_takeaways", [])
            key_takeaways: List[str] = []
            if isinstance(key_takeaways_raw, list):
                for item in key_takeaways_raw:
                    text = str(item).strip()
                    if text:
                        key_takeaways.append(text)

            normalized_pages.append(
                {
                    "page_number": page_number,
                    "title": str(raw_page.get("title", "")).strip() or f"Page {page_number}",
                    "learning_objective": str(raw_page.get("learning_objective", "")).strip(),
                    "algorithm_focus": str(raw_page.get("algorithm_focus", "")).strip(),
                    "code_focus": str(raw_page.get("code_focus", "")).strip(),
                    "page_text": str(raw_page.get("page_text", raw_page.get("narrative_text", ""))).strip(),
                    "key_takeaways": key_takeaways,
                    "illustration_prompt": str(raw_page.get("illustration_prompt", raw_page.get("image_prompt", ""))).strip(),
                    "narration_script": str(raw_page.get("narration_script", raw_page.get("audio_script", ""))).strip(),
                }
            )

        normalized_pages.sort(key=lambda item: item.get("page_number", 0))
        capped_pages = normalized_pages[:page_count]

        return {
            "title": title,
            "summary": summary,
            "target_audience": target_audience,
            "art_direction": art_direction,
            "pages": capped_pages,
        }

    def generate_storybook_outline(self, mapping: dict, code: str, page_count: int = 8) -> dict:
        requested_pages = self._safe_int(page_count, default=8, minimum=2, maximum=16)
        summary = self._algo_summary(mapping)
        trimmed_code = (code or "").strip()
        if len(trimmed_code) > 10000:
            trimmed_code = f"{trimmed_code[:10000]}\n# ... truncated for prompt size"

        prompt_text = (
            f"Create a {requested_pages}-page educational storybook.\n"
            "Each page must have story text, an illustration prompt, and narration script.\n"
            "Ensure all pages form one cohesive storyline with visual continuity.\n\n"
            f"Context:\n{json.dumps(summary, indent=2)}\n\n"
            "Generated code to reference:\n"
            f"```python\n{trimmed_code}\n```"
        )

        raw_outline = self.storybook_runtime.run_json(prompt_text)
        if raw_outline.get("error"):
            return raw_outline
        return self._normalize_storybook_outline(raw_outline, requested_pages)

    def generate_page_image(self, prompt: str) -> dict:
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
                        aspect_ratio="4:3",
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

        return {"error": "Imagen page generation failed", "details": errors}

    def generate_page_audio(self, mapping: dict, narration_script: str) -> dict:
        if not narration_script:
            return {"error": "Narration script is empty"}

        summary = self._algo_summary(mapping)
        prompt_text = (
            "Narrate this page as part of a cohesive storybook.\n"
            "Keep pacing natural and expressive, appropriate for page-turn listening.\n\n"
            f"Story context:\n{json.dumps(summary, indent=2)}\n\n"
            f"Page narration script:\n{narration_script}"
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
                    normalized_bytes, normalized_mime = self._normalize_audio_blob(audio_bytes, mime_type)
                    return {
                        "model": model,
                        "mime_type": normalized_mime or "audio/wav",
                        "data": base64.b64encode(normalized_bytes).decode("utf-8"),
                    }
                errors.append(f"{model}: no audio blob in response")
            except Exception as e:
                errors.append(f"{model}: {e}")

        return {"error": "Gemini page TTS generation failed", "details": errors}

    def generate_storybook(
        self,
        mapping: dict,
        code: str,
        page_count: int = 8,
        include_page_images: bool = True,
        include_page_audio: bool = True,
    ) -> dict:
        outline = self.generate_storybook_outline(mapping, code, page_count=page_count)
        if outline.get("error"):
            return outline

        pages = outline.get("pages", [])
        if not isinstance(pages, list) or not pages:
            return {"error": "Storybook generation produced no pages", "outline": outline}

        generation_warnings: List[str] = []
        enriched_pages: List[Dict[str, Any]] = []

        for page in pages:
            page_payload = dict(page)
            page_number = page_payload.get("page_number", len(enriched_pages) + 1)
            page_title = page_payload.get("title", f"Page {page_number}")

            if include_page_images:
                image_prompt = page_payload.get("illustration_prompt", "")
                if image_prompt:
                    image_response = self.generate_page_image(image_prompt)
                    if image_response.get("error"):
                        image_error = str(image_response.get("error", "Imagen page generation failed")).strip()
                        details_raw = image_response.get("details", [])
                        if isinstance(details_raw, list):
                            image_error_detail = " | ".join(str(item) for item in details_raw if item).strip()
                        else:
                            image_error_detail = str(details_raw or "").strip()
                        page_payload["image_error"] = image_error
                        if image_error_detail:
                            page_payload["image_error_detail"] = image_error_detail[:1200]
                        page_payload["illustration"] = {
                            "model": "local-placeholder",
                            "mime_type": "image/png",
                            "data": self._placeholder_image_b64(
                                page_number,
                                str(page_title),
                                image_error,
                                image_error_detail,
                            ),
                            "is_placeholder": True,
                            "source_error": image_error,
                        }
                        warning = f"Page {page_number} image generation failed: {image_error}"
                        if image_error_detail:
                            warning = f"{warning} ({image_error_detail[:240]})"
                        generation_warnings.append(warning)
                    else:
                        page_payload["illustration"] = {
                            "model": image_response.get("model", ""),
                            "mime_type": image_response.get("mime_type", "image/png"),
                            "data": image_response.get("data", ""),
                            "is_placeholder": False,
                        }

            if include_page_audio:
                narration_script = page_payload.get("narration_script", "")
                if narration_script:
                    audio_response = self.generate_page_audio(mapping, narration_script)
                    if audio_response.get("error"):
                        audio_error = str(audio_response.get("error", "Gemini page TTS generation failed")).strip()
                        audio_details_raw = audio_response.get("details", [])
                        if isinstance(audio_details_raw, list):
                            audio_error_detail = " | ".join(str(item) for item in audio_details_raw if item).strip()
                        else:
                            audio_error_detail = str(audio_details_raw or "").strip()
                        page_payload["audio_error"] = audio_error
                        if audio_error_detail:
                            page_payload["audio_error_detail"] = audio_error_detail[:1200]
                        warning = f"Page {page_number} audio generation failed: {audio_error}"
                        if audio_error_detail:
                            warning = f"{warning} ({audio_error_detail[:240]})"
                        generation_warnings.append(warning)
                    else:
                        page_payload["audio"] = {
                            "model": audio_response.get("model", ""),
                            "mime_type": audio_response.get("mime_type", "audio/wav"),
                            "data": audio_response.get("data", ""),
                        }

            page_payload["title"] = str(page_title).strip() or f"Page {page_number}"
            enriched_pages.append(page_payload)

        outline["pages"] = enriched_pages
        if generation_warnings:
            outline["generation_warnings"] = generation_warnings
        return outline
