"""
Visual Verifier Model Adapters (visual-verifier-adapters-v1.0.0).

ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
"""

import gc
import time
import json
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
from PIL import Image

import jsonschema
from packages.synthetic_motifs.verifier_compositor import COMPOSITOR_VERSION

import re
import hashlib
from dataclasses import dataclass, asdict

FROZEN_PROMPT_HASH = "f8417b314f6ae54245a1e3e6a17fbdeddf5cd8fe98bdf086e784ee4b516ccaac"
FROZEN_PNG_HASH = "6c63bd619c3b2aabfdb0511404a2c62a4b38ff962f45c9e73e3a537c4c17d13d"
EXPECTED_PROPOSAL_ID = "smoke_001"
EXPECTED_PROPOSED_KEY = "star_like"
MATERIALIZER_VERSION = "visual-verifier-prompt-materializer-v1.0.0"
PROPOSAL_ID_REGEX = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")

FROZEN_17_KEYS = {
    "medallion_like",
    "niche_like",
    "star_like",
    "rosette_like",
    "palmette_like",
    "lotus_like",
    "vine_scroll_like",
    "cloud_band_like",
    "tree_like",
    "horn_like",
    "human_figure_like_geometric",
    "comb_like",
    "hook_like",
    "lattice_like",
    "lozenge_like",
    "octagonal_form",
    "unmapped_visual_motif"
}

FORBIDDEN_CULTURAL_TERMS = {
    "culture", "origin", "dynasty", "period", "religion",
    "meaning", "symbolism", "story", "authenticity", "personality",
    "curator_confirmed", "elibelinde", "mihrab", "tree-of-life", "ram-horn"
}


CANONICAL_MESSAGE_CONTRACT = "canonical-verifier-message-v1.0.0"


@dataclass(frozen=True)
class CanonicalVerifierMessage:
    template_version: str
    template_sha256: str
    materializer_version: str
    proposal_id: str
    proposed_visual_candidate_key: str
    materialized_prompt_text: str

    def to_canonical_dict(self) -> Dict[str, Any]:
        materialized_prompt_sha256 = hashlib.sha256(self.materialized_prompt_text.encode("utf-8")).hexdigest()
        return {
            "contract_version": CANONICAL_MESSAGE_CONTRACT,
            "materializer_version": self.materializer_version,
            "materialized_prompt_sha256": materialized_prompt_sha256,
            "proposal_id": self.proposal_id,
            "proposed_visual_candidate_key": self.proposed_visual_candidate_key,
            "template_sha256": self.template_sha256,
            "template_version": self.template_version
        }

    def compute_canonical_hash(self) -> str:
        payload_bytes = json.dumps(self.to_canonical_dict(), sort_keys=True, separators=(",", ":")).encode("utf-8")
        domain_prefix = f"{CANONICAL_MESSAGE_CONTRACT}\x00".encode("utf-8")
        return hashlib.sha256(domain_prefix + payload_bytes).hexdigest()


class VisualVerifierPromptMaterializer:
    """
    Deterministic prompt materializer (visual-verifier-prompt-materializer-v1.0.0).
    Safely binds trusted case data into frozen prompt template without changing wording.
    """

    def __init__(self, template_path: Optional[Path] = None):
        if template_path is None:
            template_path = Path(__file__).resolve().parents[2] / "data/vlm/prompts/motif-visual-verifier-prompt-v1.txt"
        self.template_path = template_path
        self.template_text = template_path.read_text(encoding="utf-8")
        self.template_hash = hashlib.sha256(self.template_text.encode("utf-8")).hexdigest()
        assert self.template_hash == FROZEN_PROMPT_HASH, f"Prompt template hash mismatch: {self.template_hash}"

    def materialize(self, proposal_id: str, proposed_key: str) -> CanonicalVerifierMessage:
        # 1. Input validation: proposal_id format check
        if not PROPOSAL_ID_REGEX.match(proposal_id):
            raise ValueError(f"BLOCKED_INVALID_PROPOSAL_ID: proposal_id '{proposal_id}' violates bounded syntax.")

        # 2. Input validation: proposed_key MUST be in FROZEN_17_KEYS
        if proposed_key not in FROZEN_17_KEYS:
            raise ValueError(f"BLOCKED_INVALID_PROPOSED_KEY: key '{proposed_key}' is not in frozen 17 visual candidate keys enum.")

        # 3. Deterministic template placeholder replacement
        materialized_text = self.template_text.replace("<proposal_id>", proposal_id).replace("<proposed_key>", proposed_key)

        # 4. Check no unresolved required placeholders remain
        if "<proposal_id>" in materialized_text or "<proposed_key>" in materialized_text:
            raise ValueError("BLOCKED_UNRESOLVED_PLACEHOLDER: Unresolved template placeholder detected after materialization.")

        return CanonicalVerifierMessage(
            template_version="motif-visual-verifier-prompt-v1.0.0",
            template_sha256=self.template_hash,
            materializer_version=MATERIALIZER_VERSION,
            proposal_id=proposal_id,
            proposed_visual_candidate_key=proposed_key,
            materialized_prompt_text=materialized_text
        )


@dataclass(frozen=True)
class VerifierRuntimeInputRecord:
    run_id: str
    candidate_id: str
    started_at: str
    proposal_id: str
    proposed_visual_candidate_key: str
    prompt_sha256: str
    materialized_prompt_sha256: str
    canonical_semantic_payload_hash: str
    png_sha256: str
    generation_policy_sha256: str
    adapter_id: str
    model_revision: str
    model_snapshot_sha256: str

    def compute_hash(self) -> str:
        data_str = (
            f"{self.run_id}:{self.candidate_id}:{self.proposal_id}:{self.proposed_visual_candidate_key}:"
            f"{self.prompt_sha256}:{self.materialized_prompt_sha256}:{self.canonical_semantic_payload_hash}:"
            f"{self.png_sha256}:{self.generation_policy_sha256}:{self.model_revision}:"
            f"{self.model_snapshot_sha256}"
        )
        return hashlib.sha256(data_str.encode("utf-8")).hexdigest()




class VisualVerificationSemanticValidator:
    """
    Validates model output against frozen V2-09C verifier identity,
    provenance immutability, decision semantics, and 17-key registry rules.
    """

    def __init__(self, schema_path: Optional[Path] = None):
        if schema_path is None:
            schema_path = Path(__file__).resolve().parents[2] / "data/schemas/visual-verifier-v1.schema.json"
        self.schema_path = schema_path
        if schema_path.exists():
            self.schema = json.loads(schema_path.read_text(encoding="utf-8"))
        else:
            self.schema = None

    def validate(self, verifier_input: Dict[str, Any], raw_output_text: str) -> Dict[str, Any]:
        clean_text = raw_output_text.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
        clean_text = clean_text.strip()

        schema_valid = False
        parsed_json = None
        schema_errors = []

        try:
            parsed_json = json.loads(clean_text)
            if self.schema:
                jsonschema.validate(instance=parsed_json, schema=self.schema)
            schema_valid = True
        except Exception as e:
            schema_errors.append(str(e))

        semantic_valid = False
        semantic_reasons = []

        if not schema_valid or not isinstance(parsed_json, dict):
            semantic_reasons.append("SCHEMA_INVALID_OR_NOT_DICT")
            for err in schema_errors:
                semantic_reasons.append(f"SCHEMA_ERROR: {err}")
            return {
                "schema_valid": False,
                "semantic_valid": False,
                "parsed_json": parsed_json,
                "schema_errors": schema_errors,
                "semantic_reasons": semantic_reasons,
                "decision": None,
                "verified_visual_candidate_key": None
            }

        # 1. Proposal ID Immutability
        input_proposal_id = str(verifier_input.get("proposal_id", ""))
        output_proposal_id = str(parsed_json.get("proposal_id", ""))
        if output_proposal_id != input_proposal_id:
            semantic_reasons.append(f"PROPOSAL_ID_MUTATED: expected '{input_proposal_id}', got '{output_proposal_id}'")

        # 2. Proposed Key Immutability & Registry
        input_proposed_key = str(verifier_input.get("proposed_visual_candidate_key", ""))
        output_proposed_key = str(parsed_json.get("proposed_visual_candidate_key", ""))
        if output_proposed_key != input_proposed_key:
            semantic_reasons.append(f"PROPOSED_KEY_MUTATED: expected '{input_proposed_key}', got '{output_proposed_key}'")

        if input_proposed_key not in FROZEN_17_KEYS:
            semantic_reasons.append(f"INPUT_PROPOSED_KEY_NOT_IN_17_REGISTRY: '{input_proposed_key}'")

        if output_proposed_key not in FROZEN_17_KEYS:
            semantic_reasons.append(f"OUTPUT_PROPOSED_KEY_NOT_IN_17_REGISTRY: '{output_proposed_key}'")

        # 3. Decision & Verified Key Semantics
        decision = parsed_json.get("decision")
        verified_key = parsed_json.get("verified_visual_candidate_key")
        abstention_reason = parsed_json.get("abstention_reason")

        if decision == "ACCEPT":
            if verified_key is None or verified_key not in FROZEN_17_KEYS:
                semantic_reasons.append(f"ACCEPT_REQUIRES_VALID_VERIFIED_KEY: got '{verified_key}'")
            if abstention_reason is not None and str(abstention_reason).strip() != "":
                semantic_reasons.append("ACCEPT_REQUIRES_NULL_ABSTENTION_REASON")

        elif decision == "REJECT":
            if verified_key is not None:
                semantic_reasons.append(f"REJECT_REQUIRES_NULL_VERIFIED_KEY: got '{verified_key}'")
            if abstention_reason is not None and str(abstention_reason).strip() != "":
                semantic_reasons.append("REJECT_REQUIRES_NULL_ABSTENTION_REASON")

        elif decision == "ABSTAIN":
            if verified_key is not None:
                semantic_reasons.append(f"ABSTAIN_REQUIRES_NULL_VERIFIED_KEY: got '{verified_key}'")
            if abstention_reason is None or str(abstention_reason).strip() == "":
                semantic_reasons.append("ABSTAIN_REQUIRES_NON_EMPTY_ABSTENTION_REASON")

        else:
            semantic_reasons.append(f"INVALID_DECISION_TOKEN: '{decision}'")

        # 4. Visual Evidence Length
        visual_evidence = str(parsed_json.get("visual_evidence", ""))
        if len(visual_evidence) > 200:
            semantic_reasons.append(f"VISUAL_EVIDENCE_EXCEEDS_200_CHARS: len={len(visual_evidence)}")

        # 5. Cultural Safety
        json_str_lower = json.dumps(parsed_json).lower()
        for term in FORBIDDEN_CULTURAL_TERMS:
            if term in json_str_lower:
                semantic_reasons.append(f"FORBIDDEN_CULTURAL_OR_DOMAIN_TERM_PRESENT: '{term}'")

        semantic_valid = (len(semantic_reasons) == 0)

        return {
            "schema_valid": schema_valid,
            "semantic_valid": semantic_valid,
            "parsed_json": parsed_json,
            "schema_errors": schema_errors,
            "semantic_reasons": semantic_reasons,
            "decision": decision,
            "verified_visual_candidate_key": verified_key
        }


class VisualVerifierRuntimeAdapter:
    """Base runtime adapter for visual verifier candidates."""

    def __init__(self, candidate_id: str, model_path: Path):
        self.candidate_id = candidate_id
        self.model_path = model_path
        self.model = None
        self.processor = None

    def load(self) -> Dict[str, Any]:
        raise NotImplementedError

    def verify_case(self, image: Image.Image, canonical_message: CanonicalVerifierMessage, input_record: Optional[VerifierRuntimeInputRecord] = None) -> Dict[str, Any]:
        raise NotImplementedError

    def verify_smoke(self, image: Image.Image, canonical_message: CanonicalVerifierMessage, png_sha256: str = FROZEN_PNG_HASH, input_record: Optional[VerifierRuntimeInputRecord] = None) -> Dict[str, Any]:
        raise NotImplementedError

    def unload(self) -> Dict[str, Any]:
        import torch  # Yalnız GPU kaynağı kullanılırken yüklenir.
        if self.model is not None:
            del self.model
            self.model = None
        if self.processor is not None:
            del self.processor
            self.processor = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            post_alloc = round(torch.cuda.memory_allocated() / (1024**3), 3)
            post_res = round(torch.cuda.memory_reserved() / (1024**3), 3)
        else:
            post_alloc = 0.0
            post_res = 0.0
        return {
            "post_unload_allocated_gib": post_alloc,
            "post_unload_reserved_gib": post_res
        }


class Qwen3VLAdapter(VisualVerifierRuntimeAdapter):
    """Adapter for Qwen3-VL-2B-Instruct (C1)."""

    def load(self) -> Dict[str, Any]:
        import torch  # Gerçek çıkarım yolu; şema/prompt doğrulama bundan bağımsız.
        from transformers import AutoProcessor, AutoModelForImageTextToText
        t0 = time.perf_counter()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.reset_peak_memory_stats()

        self.processor = AutoProcessor.from_pretrained(str(self.model_path), local_files_only=True)
        self.model = AutoModelForImageTextToText.from_pretrained(
            str(self.model_path),
            torch_dtype=torch.bfloat16,
            device_map="auto",
            local_files_only=True
        )
        dur = round(time.perf_counter() - t0, 2)
        peak_alloc = round(torch.cuda.max_memory_allocated() / (1024**3), 3) if torch.cuda.is_available() else 0.0
        return {
            "load_seconds": dur,
            "peak_allocated_gib": peak_alloc,
            "dtype": "bfloat16",
            "device": str(next(self.model.parameters()).device)
        }

    def verify_case(
        self,
        image: Image.Image,
        canonical_message: CanonicalVerifierMessage,
        input_record: Optional[VerifierRuntimeInputRecord] = None
    ) -> Dict[str, Any]:
        import torch
        assert canonical_message.template_sha256 == FROZEN_PROMPT_HASH, "Template hash mismatch"
        assert canonical_message.materializer_version == MATERIALIZER_VERSION, "Materializer version mismatch"

        materialized_text = canonical_message.materialized_prompt_text
        assert canonical_message.proposal_id in materialized_text, f"proposal_id '{canonical_message.proposal_id}' missing in materialized prompt"
        assert canonical_message.proposed_visual_candidate_key in materialized_text, f"proposed_key '{canonical_message.proposed_visual_candidate_key}' missing in materialized prompt"
        assert "<proposal_id>" not in materialized_text, "Unresolved <proposal_id> placeholder in materialized prompt"
        assert "<proposed_key>" not in materialized_text, "Unresolved <proposed_key> placeholder in materialized prompt"

        canonical_hash = canonical_message.compute_canonical_hash()

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": materialized_text}
                ]
            }
        ]
        raw_prompt_formatted = self.processor.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=False
        )
        materialized_text_hash = hashlib.sha256(raw_prompt_formatted.encode("utf-8")).hexdigest()

        inputs = self.processor.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt"
        ).to("cuda" if torch.cuda.is_available() else "cpu")

        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()
        t0 = time.perf_counter()
        with torch.no_grad():
            output_ids = self.model.generate(**inputs, max_new_tokens=128, do_sample=False)
        dur = round(time.perf_counter() - t0, 3)

        infer_alloc = round(torch.cuda.max_memory_allocated() / (1024**3), 3) if torch.cuda.is_available() else 0.0
        infer_reserved = round(torch.cuda.max_memory_reserved() / (1024**3), 3) if torch.cuda.is_available() else 0.0

        input_len = inputs["input_ids"].shape[1]
        gen_ids = output_ids[0][input_len:]
        gen_tokens = len(gen_ids)
        first_token_id = int(gen_ids[0].item()) if gen_tokens > 0 else None
        last_token_id = int(gen_ids[-1].item()) if gen_tokens > 0 else None
        token_seq_sha256 = hashlib.sha256(gen_ids.cpu().numpy().tobytes()).hexdigest() if gen_tokens > 0 else ""

        raw_text = self.processor.decode(gen_ids, skip_special_tokens=True).strip()
        raw_output_sha256 = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

        return {
            "inference_seconds": dur,
            "peak_allocated_gib": infer_alloc,
            "peak_reserved_gib": infer_reserved,
            "model_generate_call_count": 1,
            "response_cache_hit": False,
            "canonical_semantic_payload_hash": canonical_hash,
            "materialized_model_input_sha256": materialized_text_hash,
            "generated_tokens": gen_tokens,
            "first_token_id": first_token_id,
            "last_token_id": last_token_id,
            "token_sequence_sha256": token_seq_sha256,
            "raw_output": raw_text,
            "raw_output_sha256": raw_output_sha256,
            "trusted_input_hash": input_record.compute_hash() if input_record else None
        }

    def verify_smoke(
        self,
        image: Image.Image,
        canonical_message: CanonicalVerifierMessage,
        png_sha256: str = FROZEN_PNG_HASH,
        input_record: Optional[VerifierRuntimeInputRecord] = None
    ) -> Dict[str, Any]:
        assert png_sha256 == FROZEN_PNG_HASH, "PNG hash mismatch"
        return self.verify_case(image=image, canonical_message=canonical_message, input_record=input_record)


class SmolVLM2Adapter(VisualVerifierRuntimeAdapter):
    """Adapter for SmolVLM2-2.2B-Instruct (C2)."""

    def load(self) -> Dict[str, Any]:
        import torch  # Gerçek çıkarım yolu; şema/prompt doğrulama bundan bağımsız.
        from transformers import AutoProcessor, AutoModelForImageTextToText
        t0 = time.perf_counter()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.reset_peak_memory_stats()

        self.processor = AutoProcessor.from_pretrained(str(self.model_path), local_files_only=True)
        self.model = AutoModelForImageTextToText.from_pretrained(
            str(self.model_path),
            torch_dtype=torch.bfloat16,
            device_map="auto",
            local_files_only=True
        )
        dur = round(time.perf_counter() - t0, 2)
        peak_alloc = round(torch.cuda.max_memory_allocated() / (1024**3), 3) if torch.cuda.is_available() else 0.0
        return {
            "load_seconds": dur,
            "peak_allocated_gib": peak_alloc,
            "dtype": "bfloat16",
            "device": str(next(self.model.parameters()).device)
        }

    def verify_case(
        self,
        image: Image.Image,
        canonical_message: CanonicalVerifierMessage,
        input_record: Optional[VerifierRuntimeInputRecord] = None
    ) -> Dict[str, Any]:
        import torch
        assert canonical_message.template_sha256 == FROZEN_PROMPT_HASH, "Template hash mismatch"
        assert canonical_message.materializer_version == MATERIALIZER_VERSION, "Materializer version mismatch"

        materialized_text = canonical_message.materialized_prompt_text
        assert canonical_message.proposal_id in materialized_text, f"proposal_id '{canonical_message.proposal_id}' missing in materialized prompt"
        assert canonical_message.proposed_visual_candidate_key in materialized_text, f"proposed_key '{canonical_message.proposed_visual_candidate_key}' missing in materialized prompt"
        assert "<proposal_id>" not in materialized_text, "Unresolved <proposal_id> placeholder in materialized prompt"
        assert "<proposed_key>" not in materialized_text, "Unresolved <proposed_key> placeholder in materialized prompt"

        canonical_hash = canonical_message.compute_canonical_hash()

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": materialized_text}
                ]
            }
        ]
        raw_prompt_formatted = self.processor.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=False
        )
        materialized_text_hash = hashlib.sha256(raw_prompt_formatted.encode("utf-8")).hexdigest()

        inputs = self.processor.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt"
        ).to("cuda" if torch.cuda.is_available() else "cpu")

        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()
        t0 = time.perf_counter()
        with torch.no_grad():
            output_ids = self.model.generate(**inputs, max_new_tokens=128, do_sample=False)
        dur = round(time.perf_counter() - t0, 3)

        infer_alloc = round(torch.cuda.max_memory_allocated() / (1024**3), 3) if torch.cuda.is_available() else 0.0
        infer_reserved = round(torch.cuda.max_memory_reserved() / (1024**3), 3) if torch.cuda.is_available() else 0.0

        input_len = inputs["input_ids"].shape[1]
        gen_ids = output_ids[0][input_len:]
        gen_tokens = len(gen_ids)
        first_token_id = int(gen_ids[0].item()) if gen_tokens > 0 else None
        last_token_id = int(gen_ids[-1].item()) if gen_tokens > 0 else None
        token_seq_sha256 = hashlib.sha256(gen_ids.cpu().numpy().tobytes()).hexdigest() if gen_tokens > 0 else ""

        raw_text = self.processor.decode(gen_ids, skip_special_tokens=True).strip()
        raw_output_sha256 = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

        return {
            "inference_seconds": dur,
            "peak_allocated_gib": infer_alloc,
            "peak_reserved_gib": infer_reserved,
            "model_generate_call_count": 1,
            "response_cache_hit": False,
            "canonical_semantic_payload_hash": canonical_hash,
            "materialized_model_input_sha256": materialized_text_hash,
            "generated_tokens": gen_tokens,
            "first_token_id": first_token_id,
            "last_token_id": last_token_id,
            "token_sequence_sha256": token_seq_sha256,
            "raw_output": raw_text,
            "raw_output_sha256": raw_output_sha256,
            "trusted_input_hash": input_record.compute_hash() if input_record else None
        }

    def verify_smoke(
        self,
        image: Image.Image,
        canonical_message: CanonicalVerifierMessage,
        png_sha256: str = FROZEN_PNG_HASH,
        input_record: Optional[VerifierRuntimeInputRecord] = None
    ) -> Dict[str, Any]:
        assert png_sha256 == FROZEN_PNG_HASH, "PNG hash mismatch"
        return self.verify_case(image=image, canonical_message=canonical_message, input_record=input_record)


class Qwen2VLAdapter(VisualVerifierRuntimeAdapter):
    """Adapter for Qwen2-VL-2B-Instruct (C3)."""

    def load(self) -> Dict[str, Any]:
        import torch  # Gerçek çıkarım yolu; şema/prompt doğrulama bundan bağımsız.
        from transformers import AutoProcessor, AutoModelForImageTextToText
        t0 = time.perf_counter()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.reset_peak_memory_stats()

        self.processor = AutoProcessor.from_pretrained(str(self.model_path), local_files_only=True)
        self.model = AutoModelForImageTextToText.from_pretrained(
            str(self.model_path),
            torch_dtype=torch.bfloat16,
            device_map="auto",
            local_files_only=True
        )
        dur = round(time.perf_counter() - t0, 2)
        peak_alloc = round(torch.cuda.max_memory_allocated() / (1024**3), 3) if torch.cuda.is_available() else 0.0
        return {
            "load_seconds": dur,
            "peak_allocated_gib": peak_alloc,
            "dtype": "bfloat16",
            "device": str(next(self.model.parameters()).device)
        }

    def verify_case(
        self,
        image: Image.Image,
        canonical_message: CanonicalVerifierMessage,
        input_record: Optional[VerifierRuntimeInputRecord] = None
    ) -> Dict[str, Any]:
        import torch
        assert canonical_message.template_sha256 == FROZEN_PROMPT_HASH, "Template hash mismatch"
        assert canonical_message.materializer_version == MATERIALIZER_VERSION, "Materializer version mismatch"

        materialized_text = canonical_message.materialized_prompt_text
        assert canonical_message.proposal_id in materialized_text, f"proposal_id '{canonical_message.proposal_id}' missing in materialized prompt"
        assert canonical_message.proposed_visual_candidate_key in materialized_text, f"proposed_key '{canonical_message.proposed_visual_candidate_key}' missing in materialized prompt"
        assert "<proposal_id>" not in materialized_text, "Unresolved <proposal_id> placeholder in materialized prompt"
        assert "<proposed_key>" not in materialized_text, "Unresolved <proposed_key> placeholder in materialized prompt"

        canonical_hash = canonical_message.compute_canonical_hash()

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": materialized_text}
                ]
            }
        ]
        raw_prompt_formatted = self.processor.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=False
        )
        materialized_text_hash = hashlib.sha256(raw_prompt_formatted.encode("utf-8")).hexdigest()

        inputs = self.processor.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt"
        ).to("cuda" if torch.cuda.is_available() else "cpu")

        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()
        t0 = time.perf_counter()
        with torch.no_grad():
            output_ids = self.model.generate(**inputs, max_new_tokens=128, do_sample=False)
        dur = round(time.perf_counter() - t0, 3)

        infer_alloc = round(torch.cuda.max_memory_allocated() / (1024**3), 3) if torch.cuda.is_available() else 0.0
        infer_reserved = round(torch.cuda.max_memory_reserved() / (1024**3), 3) if torch.cuda.is_available() else 0.0

        input_len = inputs["input_ids"].shape[1]
        gen_ids = output_ids[0][input_len:]
        gen_tokens = len(gen_ids)
        first_token_id = int(gen_ids[0].item()) if gen_tokens > 0 else None
        last_token_id = int(gen_ids[-1].item()) if gen_tokens > 0 else None
        token_seq_sha256 = hashlib.sha256(gen_ids.cpu().numpy().tobytes()).hexdigest() if gen_tokens > 0 else ""

        raw_text = self.processor.decode(gen_ids, skip_special_tokens=True).strip()
        raw_output_sha256 = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

        return {
            "inference_seconds": dur,
            "peak_allocated_gib": infer_alloc,
            "peak_reserved_gib": infer_reserved,
            "model_generate_call_count": 1,
            "response_cache_hit": False,
            "canonical_semantic_payload_hash": canonical_hash,
            "materialized_model_input_sha256": materialized_text_hash,
            "generated_tokens": gen_tokens,
            "first_token_id": first_token_id,
            "last_token_id": last_token_id,
            "token_sequence_sha256": token_seq_sha256,
            "raw_output": raw_text,
            "raw_output_sha256": raw_output_sha256,
            "trusted_input_hash": input_record.compute_hash() if input_record else None
        }

    def verify_smoke(
        self,
        image: Image.Image,
        canonical_message: CanonicalVerifierMessage,
        png_sha256: str = FROZEN_PNG_HASH,
        input_record: Optional[VerifierRuntimeInputRecord] = None
    ) -> Dict[str, Any]:
        assert png_sha256 == FROZEN_PNG_HASH, "PNG hash mismatch"
        return self.verify_case(image=image, canonical_message=canonical_message, input_record=input_record)


class Qwen25VLAWQAdapter(VisualVerifierRuntimeAdapter):
    """Adapter for Qwen2.5-VL-3B-Instruct-AWQ (R0)."""

    def load(self) -> Dict[str, Any]:
        raise RuntimeError(
            "Loading Qwen2.5-VL-3B-Instruct-AWQ requires gptqmodel/autoawq build tools "
            "which are not supported in current Python 3.14 Windows environment."
        )

    def verify_case(self, image: Image.Image, canonical_message: CanonicalVerifierMessage, input_record: Optional[VerifierRuntimeInputRecord] = None) -> Dict[str, Any]:
        raise NotImplementedError

    def verify_smoke(self, image: Image.Image, prompt_text: str) -> Dict[str, Any]:
        raise NotImplementedError
