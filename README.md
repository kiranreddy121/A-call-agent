# Voice AI Agent with Twilio, OpenAI Realtime API, and Google Cloud

## Overview

This project implements a real-time **Voice AI Agent** for a virtual order-taking assistant at **Natures Warehouse**, powered by:

- **OpenAI GPT-4o Realtime API** for streaming conversation
- **Twilio Media Streams** for voice input/output during phone calls
- **FastAPI** backend to manage sessions and stream handling
- **Google Cloud Storage (GCS)** to store raw audio files and chat transcripts

> Ideal for businesses needing AI-powered customer interaction over the phone.

---

## Features

- Real-time 2-way voice conversation via Twilio
- Uses OpenAI GPT-4o to generate natural-sounding responses
- Automatically handles:
  - Order-taking
  - Address verification
  - Payment preference notes
  - Handoff to a human if needed
- Saves:
  - Incoming caller audio (`.ulaw`)
  - AI transcript (`.json`)
- All assets stored securely in **GCS**



