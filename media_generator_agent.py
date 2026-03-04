from google import genai
from google.genai import types
import os
import json

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
            api_key=os.environ.get("GOOGLE_CLOUD_API_KEY"),
            location='global'
        )
        self.model = "gemini-3.1-flash-lite-preview"

    def generate_visuals(self, mapping: dict, code: str) -> dict:
        # Only pass the algorithm name and key details, not the full code
        algo_summary = {
            "algorithm": mapping.get("identified_algorithm", "Unknown"),
            "problem_class": mapping.get("problem_class", "Unknown"),
            "qubit_count": mapping.get("qubit_requirement_estimate", "Unknown"),
            "story_explanation": mapping.get("story_explanation", ""),
        }
        prompt_text = f"Algorithm mapping with User Problem Context:\n{json.dumps(algo_summary, indent=2)}\n\nPlease generate the visual assets and audio script. IMPORANT: Make the video prompt and audio script exceptionally specific to the user's problem and the story_explanation provided. Return a relatable podcast-style story for the audio."

        contents = [
          types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt_text)]
          )
        ]

        generate_content_config = types.GenerateContentConfig(
          system_instruction=SYSTEM_INSTRUCTION,
          temperature=0.7,
          top_p=0.95,
          max_output_tokens=2048,  # Increased for longer podcast audio scripts
          response_mime_type="application/json",
          thinking_config=types.ThinkingConfig(thinking_budget=0),  # No thinking needed
        )

        response = self.client.models.generate_content(
          model=self.model,
          contents=contents,
          config=generate_content_config,
        )

        try:
            return json.loads(response.text)
        except json.JSONDecodeError:
            return {"error": "Media agent failed to return JSON", "raw_output": response.text}