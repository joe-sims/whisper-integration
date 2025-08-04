import whisper
import os
from pathlib import Path
from typing import Optional, Dict, Any

class WhisperTranscriber:
    def __init__(self, model_name: str = "base"):
        """
        Initialize Whisper transcriber with specified model.
        
        Args:
            model_name: Whisper model size ("tiny", "base", "small", "medium", "large")
        """
        self.model_name = model_name
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load the Whisper model."""
        try:
            self.model = whisper.load_model(self.model_name)
            print(f"Loaded Whisper model: {self.model_name}")
        except Exception as e:
            raise RuntimeError(f"Failed to load Whisper model: {e}")
    
    def transcribe_file(self, audio_path: str, **kwargs) -> Dict[str, Any]:
        """
        Transcribe audio file to text.
        
        Args:
            audio_path: Path to audio file
            **kwargs: Additional arguments for whisper.transcribe()
                     (e.g., language="en", task="transcribe")
        
        Returns:
            Dictionary containing transcription results
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        if self.model is None:
            raise RuntimeError("Whisper model not loaded")

        # Add local ffmpeg to path
        bin_dir = Path(__file__).parent.parent / 'bin'
        original_path = os.environ.get('PATH', '')
        os.environ['PATH'] = f"{bin_dir}{os.pathsep}{original_path}"

        try:
            result = self.model.transcribe(audio_path, **kwargs)
            return result
        except Exception as e:
            raise RuntimeError(f"Transcription failed: {e}")
        finally:
            os.environ['PATH'] = original_path
    
    def transcribe_with_timestamps(self, audio_path: str, **kwargs) -> Dict[str, Any]:
        """
        Transcribe audio with word-level timestamps.
        
        Args:
            audio_path: Path to audio file
            **kwargs: Additional arguments for whisper.transcribe()
        
        Returns:
            Dictionary containing transcription with timestamps
        """
        kwargs['word_timestamps'] = True
        return self.transcribe_file(audio_path, **kwargs)
    
    def get_text_only(self, audio_path: str, **kwargs) -> str:
        """
        Get only the transcribed text without metadata.
        
        Args:
            audio_path: Path to audio file
            **kwargs: Additional arguments for whisper.transcribe()
        
        Returns:
            Transcribed text as string
        """
        result = self.transcribe_file(audio_path, **kwargs)
        return result.get('text', '').strip()