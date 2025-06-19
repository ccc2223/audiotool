# Advanced Audio Toolbox

This app started as a quick favor for a family member who needed help cleaning up their podcast recordings. They were dealing with background noise and long pauses. Instead of painstakingly editing out every long pause in the audio and using sub par noise removal I created this tool to automate parts of the process. 

## What It Does

- **🔊 Split Audio Files**  
  Breaks up long WAV files into 12-minute chunks. This is helpful if you're using a local noise reduction AI model that can't handle huge files (like mine).

- **🤖 Detect & Remove Long Pauses**  
  Automatically scans for and removes extended silences(>1500ms) from recordings.

- **🔗 Join Segments Back Together**  
  After processing, stitches the split segments back into a single file.

- **🔄 Convert Between Formats**  
  Easily convert between WAV and M4A (320k AAC)

- **🚀 Fast and Multithreaded**  
  Uses multiple CPU cores.

- **🖼️ Simple GUI**  
  Built with Tkinter. 

## Why This Exists

This wasn’t meant to be a full-blown audio editor — just a focused toolbox to:
- Split files for processing by a local AI
- Remove long silences
- Clean up and repackage audio for podcast use

It does that well, and that’s enough for now.

## Setup

### Requirements
- Python 3.7+
- [FFmpeg](https://ffmpeg.org/) installed and added to your system path

### Running It
Clone the repo and run the script:
```bash
git clone https://github.com/yourusername/audio-toolbox.git
cd audio-toolbox
python audiotoolv3_upgraded.py
