"""
Visual Verifier Model Adapters (visual-verifier-adapters-v1.0.0).

ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
"""

import gc
import time
import json
import torch
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
from PIL import Image

from packages.synthetic_motifs.verifier_compositor import COMPOSITOR_VERSION


class VisualVerifierRuntimeAdapter:
    """Base runtime adapter for visual verifier candidates."""

    def __init__(self, candidate_id: str, model_path: Path):
        self.candidate_id = candidate_id
        self.model_path = model_path
        self.model = None
        self.processor = None

    def load(self) -> Dict[str, Any]:
        raise NotImplementedError

    def verify_smoke(self, image: Image.Image, prompt_text: str) -> Dict[str, Any]:
        raise NotImplementedError

    def unload(self) -> Dict[str, Any]:
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

    def verify_smoke(self, image: Image.Image, prompt_text: str) -> Dict[str, Any]:
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": prompt_text}
                ]
            }
        ]
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
        dur = round(time.perf_counter() - t0, 2)

        infer_alloc = round(torch.cuda.max_memory_allocated() / (1024**3), 3) if torch.cuda.is_available() else 0.0
        infer_reserved = round(torch.cuda.max_memory_reserved() / (1024**3), 3) if torch.cuda.is_available() else 0.0

        input_len = inputs["input_ids"].shape[1]
        gen_ids = output_ids[0][input_len:]
        gen_tokens = len(gen_ids)
        raw_text = self.processor.decode(gen_ids, skip_special_tokens=True).strip()

        return {
            "inference_seconds": dur,
            "peak_allocated_gib": infer_alloc,
            "peak_reserved_gib": infer_reserved,
            "generated_tokens": gen_tokens,
            "raw_output": raw_text
        }


class SmolVLM2Adapter(VisualVerifierRuntimeAdapter):
    """Adapter for SmolVLM2-2.2B-Instruct (C2)."""

    def load(self) -> Dict[str, Any]:
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

    def verify_smoke(self, image: Image.Image, prompt_text: str) -> Dict[str, Any]:
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": prompt_text}
                ]
            }
        ]
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
        dur = round(time.perf_counter() - t0, 2)

        infer_alloc = round(torch.cuda.max_memory_allocated() / (1024**3), 3) if torch.cuda.is_available() else 0.0
        infer_reserved = round(torch.cuda.max_memory_reserved() / (1024**3), 3) if torch.cuda.is_available() else 0.0

        input_len = inputs["input_ids"].shape[1]
        gen_ids = output_ids[0][input_len:]
        gen_tokens = len(gen_ids)
        raw_text = self.processor.decode(gen_ids, skip_special_tokens=True).strip()

        return {
            "inference_seconds": dur,
            "peak_allocated_gib": infer_alloc,
            "peak_reserved_gib": infer_reserved,
            "generated_tokens": gen_tokens,
            "raw_output": raw_text
        }


class Qwen2VLAdapter(VisualVerifierRuntimeAdapter):
    """Adapter for Qwen2-VL-2B-Instruct (C3)."""

    def load(self) -> Dict[str, Any]:
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

    def verify_smoke(self, image: Image.Image, prompt_text: str) -> Dict[str, Any]:
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": prompt_text}
                ]
            }
        ]
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
        dur = round(time.perf_counter() - t0, 2)

        infer_alloc = round(torch.cuda.max_memory_allocated() / (1024**3), 3) if torch.cuda.is_available() else 0.0
        infer_reserved = round(torch.cuda.max_memory_reserved() / (1024**3), 3) if torch.cuda.is_available() else 0.0

        input_len = inputs["input_ids"].shape[1]
        gen_ids = output_ids[0][input_len:]
        gen_tokens = len(gen_ids)
        raw_text = self.processor.decode(gen_ids, skip_special_tokens=True).strip()

        return {
            "inference_seconds": dur,
            "peak_allocated_gib": infer_alloc,
            "peak_reserved_gib": infer_reserved,
            "generated_tokens": gen_tokens,
            "raw_output": raw_text
        }


class Qwen25VLAWQAdapter(VisualVerifierRuntimeAdapter):
    """Adapter for Qwen2.5-VL-3B-Instruct-AWQ (R0)."""

    def load(self) -> Dict[str, Any]:
        raise RuntimeError(
            "Loading Qwen2.5-VL-3B-Instruct-AWQ requires gptqmodel/autoawq build tools "
            "which are not supported in current Python 3.14 Windows environment."
        )

    def verify_smoke(self, image: Image.Image, prompt_text: str) -> Dict[str, Any]:
        raise NotImplementedError
