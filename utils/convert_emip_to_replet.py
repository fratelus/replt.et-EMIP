#!/usr/bin/env python3
import os
import re
import csv
import json
import shutil
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple

# Paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EMIP_ROOT = os.path.join(PROJECT_ROOT, "emip_dataset")
EMIP_STIMULI_DIR = os.path.join(EMIP_ROOT, "stimuli")
EMIP_METADATA_CSV = os.path.join(EMIP_ROOT, "emip_metadata.csv")

# Output dirs (existing in repo)
PARTICIPANTS_DIR = os.path.join(PROJECT_ROOT, "participants")
EQUIPMENT_DIR = os.path.join(PROJECT_ROOT, "equipment")
STIMULI_DIR = os.path.join(PROJECT_ROOT, "stimuli")
STIMULI_RAW_DIR = os.path.join(STIMULI_DIR, "stimuli_raw")
AOIS_DIR = os.path.join(PROJECT_ROOT, "aois")
COLLECTION_DIR = os.path.join(PROJECT_ROOT, "collection")
PREPROCESSING_DIR = os.path.join(PROJECT_ROOT, "preprocessing")
ANALYSIS_DIR = os.path.join(PROJECT_ROOT, "analysis")
VALIDITY_DIR = os.path.join(PROJECT_ROOT, "validity")
REPRO_DIR = os.path.join(PROJECT_ROOT, "reproducibility")

# Schemas (relative references inside each JSON)
SCHEMAS_REL = {
    "participants": "../schemas/participants.schema.json",
    "tracker_specs": "../schemas/tracker_specs.schema.json",
    "screen_setup": "../schemas/screen_setup.schema.json",
    "software_env": "../schemas/software_env.schema.json",
    "stimuli_metadata": "../schemas/stimuli_metadata.schema.json",
    "stimuli_annotations": "../schemas/stimuli_annotations.schema.json",
    "aois_definition": "../schemas/aois_definition.schema.json",
    "protocol": "../schemas/protocol.schema.json",
    "preprocessing": "../schemas/preprocessing.schema.json",
    "analysis": "../schemas/analysis.schema.json",
    "validity": "../schemas/validity.schema.json",
    "reproducibility": "../schemas/reproducibility.schema.json",
    "metadata": "./schemas/metadata.schema.json",
}

# -------------------- Utilities --------------------

def ensure_dirs():
    os.makedirs(PARTICIPANTS_DIR, exist_ok=True)
    os.makedirs(EQUIPMENT_DIR, exist_ok=True)
    os.makedirs(STIMULI_DIR, exist_ok=True)
    os.makedirs(STIMULI_RAW_DIR, exist_ok=True)
    os.makedirs(AOIS_DIR, exist_ok=True)
    os.makedirs(COLLECTION_DIR, exist_ok=True)
    os.makedirs(PREPROCESSING_DIR, exist_ok=True)
    os.makedirs(ANALYSIS_DIR, exist_ok=True)
    os.makedirs(VALIDITY_DIR, exist_ok=True)
    os.makedirs(REPRO_DIR, exist_ok=True)


def write_json(path: str, data: Dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def parse_years_to_int(value: str) -> int:
    if value is None:
        return 0
    s = str(value).strip().lower()
    # Normalize common forms
    s = s.replace("years", "").replace("year", "").replace("y", "")
    s = s.replace("+", "")
    s = s.replace(",", ".")
    # Extract first number
    m = re.search(r"\d+(?:\.\d+)?", s)
    if not m:
        return 0
    try:
        return int(float(m.group(0)))
    except Exception:
        return 0


def parse_programming_languages(value: str) -> List[str]:
    if not value or str(value).strip() in {"-", "none", "None"}:
        return []
    raw = str(value)
    # EMIP formats: "c++_low; php_medium; delphi_low" or "C# (high), Python (low)"
    tokens = re.split(r"[;|,]", raw)
    langs: List[str] = []
    for tok in tokens:
        tok = tok.strip()
        if not tok:
            continue
        # Remove level suffixes like _low, _high, (low), (high)
        tok = re.sub(r"\s*\([^)]*\)", "", tok)  # remove parentheses
        tok = re.sub(r"_(low|medium|high)$", "", tok, flags=re.IGNORECASE)
        tok = tok.strip()
        # Drop obviously non-language entries
        if tok and tok.lower() not in {"vb", "basic", "html/css"}:  # keep VB, BASIC as-is if present
            langs.append(tok)
    # Normalize duplicates/casing
    normalized = []
    seen = set()
    for l in langs:
        name = l.strip()
        if not name:
            continue
        key = name.lower()
        if key not in seen:
            seen.add(key)
            normalized.append(name)
    return normalized


# -------------------- Participants --------------------

def convert_participants(emip_csv_path: str) -> Dict:
    participants: List[Dict] = []
    if not os.path.exists(emip_csv_path):
        raise FileNotFoundError(f"EMIP metadata CSV not found at {emip_csv_path}")

    with open(emip_csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = str(row.get("id", "")).strip()
            if not pid:
                continue
            age = int(float(row.get("age", 0) or 0))
            gender = str(row.get("gender", "unknown"))
            visual_aid = str(row.get("visual_aid", "no")).strip().lower()
            if visual_aid in {"glasses", "spectacles"}:
                vision = "glasses"
            elif visual_aid in {"contact lenses", "contacts"}:
                vision = "contact_lenses"
            elif visual_aid in {"no", "none"}:
                vision = "none"
            else:
                vision = visual_aid or "unknown"

            experience_years = parse_years_to_int(row.get("time_programming") or row.get("time_programming_original"))
            programming_languages = parse_programming_languages(row.get("other_languages_original") or row.get("other_languages"))

            participant = {
                "participant_id": f"P{pid}",
                "age": age,
                "gender": gender,
                "handedness": "unknown",
                "vision": vision,
                "experience_years": experience_years,
                "programming_languages": programming_languages,
            }
            participants.append(participant)

    data = {
        "$schema": SCHEMAS_REL["participants"],
        "participants": participants,
        "inclusion_criteria": "Adults who completed the EMIP code comprehension tasks."
    }
    return data


# -------------------- Stimuli --------------------

def discover_stimuli() -> List[Tuple[str, str]]:
    items: List[Tuple[str, str]] = []
    if not os.path.isdir(EMIP_STIMULI_DIR):
        return items
    for name in os.listdir(EMIP_STIMULI_DIR):
        if name.lower().endswith((".jpg", ".png")):
            base = os.path.splitext(name)[0]
            items.append((base, name))
    items.sort()
    return items


def copy_stimulus_images(stimuli: List[Tuple[str, str]]):
    for base, filename in stimuli:
        src = os.path.join(EMIP_STIMULI_DIR, filename)
        dst = os.path.join(STIMULI_RAW_DIR, filename)
        if not os.path.exists(dst):
            shutil.copy2(src, dst)


def build_stimuli_metadata(stimuli: List[Tuple[str, str]]) -> Dict:
    stimuli_entries: List[Dict] = []
    for base, filename in stimuli:
        entry = {
            "stimulus_id": base,
            "type": "code_image",
            "description": f"EMIP stimulus {base}",
            "file_name": filename
        }
        stimuli_entries.append(entry)

    return {
        "$schema": SCHEMAS_REL["stimuli_metadata"],
        "stimuli": stimuli_entries
    }


# -------------------- AOIs from EMIP CSVs --------------------

def read_emip_aoi_csv(csv_path: str) -> List[Dict]:
    aois: List[Dict] = []
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        line_index = 0
        for row in reader:
            level = (row.get("level") or "").strip().lower()
            try:
                x1 = float(row.get("x1", 0))
                y1 = float(row.get("y1", 0))
                x2 = float(row.get("x2", 0))
                y2 = float(row.get("y2", 0))
            except Exception:
                continue
            if level != "line":
                # Only treat line-level boxes as AOIs; element-level could be separate if needed
                continue
            x = min(x1, x2)
            y = min(y1, y2)
            width = abs(x2 - x1)
            height = abs(y2 - y1)
            line_index += 1
            aois.append({
                "label": f"line_{line_index}",
                "shape": "rectangle",
                "coordinates": {"x": x, "y": y, "width": width, "height": height}
            })
    return aois


def build_aois_definition(stimuli: List[Tuple[str, str]]) -> Dict:
    aois_all: List[Dict] = []
    for base, filename in stimuli:
        emip_csv = os.path.join(EMIP_STIMULI_DIR, f"{base}.csv")
        if not os.path.exists(emip_csv):
            # No AOIs available for this stimulus
            continue
        aoi_rows = read_emip_aoi_csv(emip_csv)
        for idx, aoi in enumerate(aoi_rows, start=1):
            aois_all.append({
                "aoi_id": f"{base}_AOI_{idx}",
                "stimulus_id": base,
                "label": aoi["label"],
                "shape": aoi["shape"],
                "coordinates": aoi["coordinates"],
            })

    return {
        "$schema": SCHEMAS_REL["aois_definition"],
        "aois": aois_all,
        "aoi_strategy": "EMIP line bounding boxes"
    }


# -------------------- Annotations (minimal) --------------------

def build_stimuli_annotations(stimuli: List[Tuple[str, str]]) -> Dict:
    annotations: List[Dict] = []
    for base, filename in stimuli:
        # Minimal placeholder: ground truth as labels of lines if AOIs exist
        emip_csv = os.path.join(EMIP_STIMULI_DIR, f"{base}.csv")
        ground_truth: List[Dict] = []
        if os.path.exists(emip_csv):
            aoi_rows = read_emip_aoi_csv(emip_csv)
            for aoi in aoi_rows:
                ground_truth.append({
                    "region": aoi["label"],
                    "label": "code_line"
                })
        annotations.append({
            "stimulus_id": base,
            "ground_truth": ground_truth
        })
    return {
        "$schema": SCHEMAS_REL["stimuli_annotations"],
        "annotations": annotations
    }


# -------------------- Equipment / Protocol / Preprocessing --------------------

def build_equipment_defaults() -> Tuple[Dict, Dict, Dict]:
    tracker_specs = {
        "$schema": SCHEMAS_REL["tracker_specs"],
        "manufacturer": "unknown",
        "model": "unknown",
        "sampling_rate_hz": 60,
        "accuracy_deg": 0.5,
        "firmware_version": "unknown"
    }
    screen_setup = {
        "$schema": SCHEMAS_REL["screen_setup"],
        "screen_size_inch": 24.0,
        "resolution_px": [1920, 1080],
        "refresh_rate_hz": 60,
        "distance_cm": 60.0,
        "background_color": "#FFFFFF"
    }
    software_env = {
        "$schema": SCHEMAS_REL["software_env"],
        "os": "unknown",
        "experiment_software": "unknown",
        "tracker_driver_version": "unknown",
        "python_version": "3",
        "additional_packages": []
    }
    return tracker_specs, screen_setup, software_env


def build_protocol_defaults() -> Dict:
    return {
        "$schema": SCHEMAS_REL["protocol"],
        "calibration": {
            "type": "n-point",
            "criteria": "default",
            "recalibration_threshold": "if drift > 1deg",
            "validation_points": 5
        },
        "drift_check": {
            "interval_minutes": 5,
            "criteria": "visual inspection",
            "correction_procedure": "quick recalibration"
        },
        "exclusion_criteria": [
            "incomplete session",
            "excessive data loss"
        ],
        "session_structure": {
            "practice_trials": 0,
            "main_trials": 2,
            "break_intervals": "none"
        },
        "instructions_to_participants": "Read code stimuli and answer comprehension questions."
    }


def build_preprocessing_defaults() -> Dict:
    return {
        "$schema": SCHEMAS_REL["preprocessing"],
        "steps": [
            {
                "step": "import",
                "method": "convert_from_emip",
                "parameters": {
                    "source": "EMIP",
                    "version": "unknown"
                }
            }
        ],
        "software_used": "custom_python_script"
    }


def build_analysis_defaults() -> Dict:
    return {
        "$schema": SCHEMAS_REL["analysis"],
        "metrics": ["fixation_count", "total_fixation_duration"],
        "aoi_based_metrics": ["time_on_line", "transitions_between_lines"],
        "statistical_methods": ["descriptive"],
        "dependent_variables": ["accuracy", "response_time"],
        "software_used": ["python", "pandas"],
        "scripts": ["utils/convert_emip_to_replet.py"]
    }


def build_validity_defaults() -> Dict:
    return {
        "$schema": SCHEMAS_REL["validity"],
        "threats": [
            {"type": "construct", "description": "Stimuli are images of code, not editable code."}
        ],
        "limitations": ["Equipment defaults used; exact EMIP hardware not encoded."],
        "confounding_factors": ["Programming experience variability"]
    }


def build_reproducibility_defaults() -> Dict:
    return {
        "$schema": SCHEMAS_REL["reproducibility"],
        "data_availability": "Converted from included EMIP dataset subset.",
        "code_availability": "This repository",
        "environment": "Python 3",
        "replication_instructions": "Run utils/convert_emip_to_replet.py",
        "doi": "unknown"
    }


def build_metadata_defaults() -> Dict:
    return {
        "$schema": SCHEMAS_REL["metadata"],
        "study_title": "EMIP to REPL.et Conversion",
        "study_objective": "Provide EMIP dataset in REPL.et standard format.",
        "paradigm": "code comprehension",
        "task_description": "Read code image and answer comprehension questions.",
        "keywords": ["eye-tracking", "code comprehension", "EMIP", "REPL.et"],
        "authors": [
            {"name": "EMIP Team", "orcid": "0000-0000-0000-0000"}
        ],
        "date": "2025-01-01",
        "license": "CC BY 4.0"
    }


# -------------------- Main conversion --------------------

def main():
    ensure_dirs()

    # Discover and copy stimuli
    stimuli = discover_stimuli()
    copy_stimulus_images(stimuli)

    # Write stimuli metadata and annotations
    stimuli_metadata = build_stimuli_metadata(stimuli)
    write_json(os.path.join(STIMULI_DIR, "stimuli_metadata.json"), stimuli_metadata)

    stimuli_annotations = build_stimuli_annotations(stimuli)
    write_json(os.path.join(STIMULI_DIR, "stimuli_annotations.json"), stimuli_annotations)

    # Build AOIs from EMIP CSV annotations
    aois_definition = build_aois_definition(stimuli)
    write_json(os.path.join(AOIS_DIR, "aois_definition.json"), aois_definition)

    # Participants from EMIP metadata CSV
    participants = convert_participants(EMIP_METADATA_CSV)
    write_json(os.path.join(PARTICIPANTS_DIR, "participants.json"), participants)

    # Equipment / Protocol / Preprocessing / Analysis / Validity / Reproducibility / Metadata
    tracker_specs, screen_setup, software_env = build_equipment_defaults()
    write_json(os.path.join(EQUIPMENT_DIR, "tracker_specs.json"), tracker_specs)
    write_json(os.path.join(EQUIPMENT_DIR, "screen_setup.json"), screen_setup)
    write_json(os.path.join(EQUIPMENT_DIR, "software_env.json"), software_env)

    write_json(os.path.join(COLLECTION_DIR, "protocol.json"), build_protocol_defaults())
    write_json(os.path.join(PREPROCESSING_DIR, "preprocessing.json"), build_preprocessing_defaults())
    write_json(os.path.join(ANALYSIS_DIR, "analysis.json"), build_analysis_defaults())
    write_json(os.path.join(VALIDITY_DIR, "validity.json"), build_validity_defaults())
    write_json(os.path.join(PROJECT_ROOT, "reproducibility", "reproducibility.json"), build_reproducibility_defaults())
    write_json(os.path.join(PROJECT_ROOT, "metadata.json"), build_metadata_defaults())

    print("Conversion complete.")
    print(f"- Stimuli copied: {len(stimuli)}")
    print(f"- AOIs generated: {asdict_counts(aois_definition)}")
    print(f"- Participants: {len(participants.get('participants', []))}")


def asdict_counts(aois_def: Dict) -> int:
    try:
        return len(aois_def.get("aois", []))
    except Exception:
        return 0


if __name__ == "__main__":
    main() 