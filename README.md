# Quantum Circuit Orchestrator
A Multi-Agent Framework for Generative Quantum Software Engineering

## Project Overview
The **Quantum Circuit Orchestrator** is an advanced, end-to-end AI pipeline that translates complex, real-world human problems into verified quantum computational circuits. By utilizing a swarm of specialized Google Generative AI agents working sequentially, the system takes a natural language prompt, designs an optimized quantum algorithm, rigorously audits its physical feasibility, simulates the execution locally, and packages the findings into a rich, multimodal presentation layer.

## Architecture & Agent Roles
The backend drives a cyclic, self-correcting workflow utilizing 5 distinct AI personas:

1. **Translator Agent (Logic Mapper)**
   - **Role:** Understands the user's natural language problem and classifies it into a quantum problem space (e.g., Unstructured Search, Combinatorial Optimization).
   - **Output:** Identifies the target quantum algorithm (e.g., Grover's, QAOA) and provides a pedagogical "Quantum Story Context" explaining the approach.

2. **Circuit Architect Agent (Qiskit Engineer)**
   - **Role:** Takes the logical mapping and writes production-ready Qiskit 1.x Python code.
   - **Output:** Generates the actual quantum circuit code, enforcing constraints like NISQ (Noisy Intermediate-Scale Quantum) scaling to maintain a realistic, compilable circuit payload.

3. **Scientist Agent (Technical Auditor)**
   - **Role:** Acts as the strict scientific quality gate. It verifies that the generated code aligns with physical quantum mechanics laws (e.g., No-Cloning Theorem, Reversibility) and realistic hardware coherence limits.
   - **Behavior:** It checks the circuit depth and can provide detailed mathematical feedback to force the Architect to rewrite invalid circuits.

4. **Evaluator Agent (Simulation Gatekeeper)**
   - **Role:** Executes the generated Qiskit circuit payload on a local machine (using `AerSimulator`).
   - **Output:** Analyzes the simulator's standard output (histograms/shot counts) to ensure the circuit compiles, runs without syntax errors, and solves the core logic. Generates a Pass/Fail verdict.

5. **Media Producer Agent (Visual Storyteller)**
   - **Role:** Condenses the highly technical output into a digestible, cinematic format for human stakeholders.
   - **Output:** Generates rich narrative audio scripts (played via Text-to-Speech) and sophisticated prompts for generative video models (e.g., Google Veo) to visualize the quantum mechanics at play.

## Presentation Layer (Frontend)
The user interacts with the system via a visually stunning **Next.js & React Three Fiber** environment:
- **3D Quantum Particle Field:** A dynamic, immersive background that reacts to the simulation state.
- **Real-Time Execution Graph:** A live, re-arrangeable `React Flow` node graph that maps every websocket event, visually plotting the back-and-forth interactions and attempts among the agents.
- **Multimodal Delivery:** Once the pipeline completes, the UI renders the final generated code, the plotted Qiskit `circuit_diagram`, a matplotlib-parsed `result_diagram` (Histogram), the video prompt, and plays the generated narrative audio script.
