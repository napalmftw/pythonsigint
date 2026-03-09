These are just a few scripts I've been working on in Python - I am NOT a coder, and I've had Gemini Pro and Thinking help me with these.

This is helping me (slowly) learn Python.

rid_correlation:
 DESCRIPTION:
  This script analyzes DSDPlus event logs to identify "cross-over" units.
  It finds Radio IDs (RIDs) that have appeared on a tactical/encrypted 
  talkgroup and then cross-references them against clear-voice dispatch 
  channels to reveal their identity or routine assignments.

Tactical Alert:
 DESCRIPTION:
  This script monitors a DSDPlus event log in real-time and sends an 
  instant Telegram notification whenever encrypted activity is detected.

  TTD Two Tone:

 This script is designed to be called by TwoToneDetect (TTD) when a fire tone is found.
 It waits for the audio file to be finalized, transcribes the dispatch using the 
 Faster-Whisper AI model, applies phonetic corrections for computer-aided dispatch (Locution),
 and sends the transcript and audio file to a designated Telegram bot.

*** NOTE: You will need to install Whisper AI - instructions to follow ***
