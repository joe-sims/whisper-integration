#!/usr/bin/env python3

import sys
import os
from pathlib import Path

def convert_with_whisper_built_in(input_file, output_file=None):
    """Use Whisper's built-in audio loading to convert files"""
    import whisper
    
    if output_file is None:
        output_file = Path(input_file).stem + "_converted.wav"
    
    try:
        # Load audio using Whisper's built-in loader
        audio = whisper.load_audio(input_file)
        
        # Save as WAV using numpy and scipy
        import scipy.io.wavfile as wav
        import numpy as np
        
        # Whisper loads audio at 16kHz
        sample_rate = 16000
        
        # Convert to int16 format for WAV
        audio_int16 = (audio * 32767).astype(np.int16)
        
        wav.write(output_file, sample_rate, audio_int16)
        print(f"Converted {input_file} to {output_file}")
        return output_file
        
    except Exception as e:
        print(f"Error converting audio: {e}")
        return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python convert_audio.py <input_audio_file> [output_wav_file]")
        return
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found.")
        return
    
    converted_file = convert_with_whisper_built_in(input_file, output_file)
    if converted_file:
        print(f"Success! Use: python3 example_usage.py {converted_file}")

if __name__ == "__main__":
    main()