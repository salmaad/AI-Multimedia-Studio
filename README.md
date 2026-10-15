# 🎬 Prompt2Video — AI Multimedia Studio (WIP)

> **⚠️ Unfinished Project / Work in Progress**  
> This repository contains an experimental local multimedia application. Features are actively evolving, and parts of the system are still under development.

---

## 🚀 About the Project

**Prompt2Video** is a local Streamlit application designed to transform simple text prompts into fully narrated, multi-scene videos equipped with synchronized audio voiceovers, scene-specific backgrounds, and clean subtitle overlays.

### 🛠️ Tech Stack
* **Frontend:** [Streamlit](https://streamlit.io/)
* **Script Generation:** Google Gemini API (`gemini-3.8-flash`)
* **Video Rendering:** [MoviePy 2.x](https://github.com/Zulko/moviepy)
* **Visual Asset Engine:** Local fallback generator / Optional local Stable Diffusion (`OFA-Sys/small-stable-diffusion-v0`) via PyTorch.
* **Text-to-Speech (TTS):** `pyttsx3`

---

## 📸 Application Preview

### 1. Script Configuration & Generation
Users can configure video formatting, narration tone, and target duration in the sidebar, input any topic, and generate a structured scene-by-scene script.
<p align="center">
  <img src="media1.png" alt="Prompt2Video UI and Script Generation" width="90%">
</p>

### 2. Full Video Rendering Pipeline
Once the script is reviewed, clicking the generation button runs scene-by-scene compilation, building assets, generating narration tracks, and stitching clips together via MoviePy.
<p align="center">
  <img src="media2.png" alt="Rendering Progress" width="90%">
</p>

### 3. Playback & Export
The completed video displays directly in the app interface with styled subtitle boxes, alongside options to download the final MP4 or view generated individual scene assets[cite: 7].
<p align="center">
  <img src="media3.png" alt="Video Player and Output" width="90%">
</p>

---

## 📂 Project Structure

* `app.py` : Main Streamlit web application and orchestration logic.
* `asset_gen.py` : Visual generation and fallback image routine.
* `requirements.txt` : Python package dependencies.
* `video_projects/` : Local output directory for cached media, audio, and compiled videos.

---

## ⚙️ Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/votre-nom-utilisateur/prompt2video.git](https://github.com/votre-nom-utilisateur/prompt2video.git)
   cd prompt2video
