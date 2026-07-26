"""Debug: compare intermediate breath values between DDD and Legacy paths"""
import sys, os, numpy as np
sys.path.insert(0, '.')
os.environ.setdefault('VAS_DISABLE_RATE_LIMIT', 'TRUE')

test_file = "uploads/melody.wav"

# -- Load audio the same way AudioService does --
import librosa
from config import config
from services.feature_flags import FeatureFlags

audio_data, sr = librosa.load(test_file, sr=config.AUDIO_SAMPLE_RATE, mono=True)

# Get f0 the same way
from services.audio_service import AudioService
audio_svc = AudioService(config)
flags = FeatureFlags.for_quick()

# Manually do what audio_service.analyze does
# First load and resample
TARGET_SR = 16000
if sr > TARGET_SR:
    audio_data = librosa.resample(audio_data, orig_sr=sr, target_sr=TARGET_SR)
    sr = TARGET_SR

# Get f0
pitch_result = audio_svc._analyze_pitch(audio_data, sr, flags)
f0 = pitch_result['f0']
voiced_flags = ~np.isnan(f0)

# --- Legacy path: extract all features ---
from services.audio_features_service import AudioFeaturesService
from services.features.acoustic import AcousticAnalyzer

features_svc = AudioFeaturesService(sr)
advanced = features_svc.extract_all_features(audio_data, f0, singing_style='pop', feature_flags=flags)

print("=== Legacy Features ===")
bs = advanced.breath_stability
print(f"  breath_stability.professional_breath_score = {bs.professional_breath_score:.1f}")
print(f"  breath_stability.long_note_support_score   = {bs.long_note_support_score:.1f}")
print(f"  breath_stability.dynamic_control_score     = {bs.dynamic_control_score:.1f}")
print(f"  breath_stability.breath_design_score       = {bs.breath_design_score:.1f}")
print(f"  breath_stability.breath_technique_score    = {bs.breath_technique_score:.1f}")
print(f"  breath_stability.rms_fluctuation           = {bs.rms_fluctuation:.4f}")
print(f"  HNR used for breath                        = {advanced.hnr:.2f}")
print(f"  vocal_segments                             = {advanced._vocal_segment_count}")

# --- DDD path ---
from backend.domain.audio.acoustic_feature_extractor import LibrosaAcousticExtractor
from backend.domain.audio.breath_extractor import LibrosaBreathExtractor
from backend.domain.audio.feature_types import AcousticFeatures

acoustic_ext = LibrosaAcousticExtractor()
breath_ext = LibrosaBreathExtractor()

# VAD vocal segments for DDD
segments_ddd = AcousticAnalyzer.find_vocal_segments(f0, 512, sr)
print(f"\n  DDD vocal_segments found = {len(segments_ddd)}")
if segments_ddd:
    breath_y = AcousticAnalyzer.filter_audio_to_vocal_segments(audio_data, segments_ddd, 512)
    print(f"  DDD using vocal audio: {len(breath_y)} samples (full: {len(audio_data)})")
else:
    breath_y = audio_data
    print(f"  DDD using full audio: {len(breath_y)} samples")

acoustic_features = acoustic_ext.extract(audio_data, sr)
print(f"\n=== DDD AcousticFeatures ===")
print(f"  HNR  = {acoustic_features.hnr:.2f}")
print(f"  CPP  = {acoustic_features.cpp:.4f}")
print(f"  hnr_mean = {acoustic_features.hnr_mean:.2f}")

ddd_breath = breath_ext.extract(breath_y, sr, acoustic_features, f0=f0, is_clean_vocal=False)
print(f"\n=== DDD BreathFeatures ===")
print(f"  professional_breath_score = {ddd_breath.professional_breath_score:.1f}")
print(f"  long_note_support         = {ddd_breath.long_note_support:.1f}")
print(f"  dynamic_control           = {ddd_breath.dynamic_control:.1f}")
print(f"  breath_design             = {ddd_breath.breath_design:.1f}")
print(f"  breath_technique          = {ddd_breath.breath_technique:.1f}")
print(f"  rms_fluctuation           = {ddd_breath.rms_fluctuation:.4f}")

# Compare the breath scores directly
print(f"\n=== COMPARISON ===")
print(f"  professional_breath: Legacy={bs.professional_breath_score:.1f}  DDD={ddd_breath.professional_breath_score:.1f}  delta={ddd_breath.professional_breath_score-bs.professional_breath_score:.1f}")
print(f"  long_note_support:  Legacy={bs.long_note_support_score:.1f}  DDD={ddd_breath.long_note_support:.1f}  delta={ddd_breath.long_note_support-bs.long_note_support_score:.1f}")
print(f"  dynamic_control:    Legacy={bs.dynamic_control_score:.1f}  DDD={ddd_breath.dynamic_control:.1f}  delta={ddd_breath.dynamic_control-bs.dynamic_control_score:.1f}")
print(f"  breath_design:      Legacy={bs.breath_design_score:.1f}  DDD={ddd_breath.breath_design:.1f}  delta={ddd_breath.breath_design-bs.breath_design_score:.1f}")
print(f"  breath_technique:   Legacy={bs.breath_technique_score:.1f}  DDD={ddd_breath.breath_technique:.1f}  delta={ddd_breath.breath_technique-bs.breath_technique_score:.1f}")
print(f"  rms_fluctuation:    Legacy={bs.rms_fluctuation:.4f}  DDD={ddd_breath.rms_fluctuation:.4f}")
print(f"  HNR:                Legacy={advanced.hnr:.2f}  DDD={acoustic_features.hnr_mean:.2f}")
