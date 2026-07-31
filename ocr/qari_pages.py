#!/usr/bin/env python3
"""Best-effort Qari-OCR (omerxai/Qari-OCR-v0.3) on a few pages. Never fatal."""
import sys, os

def main():
    imgs = sys.argv[1:-1]
    outdir = sys.argv[-1]
    os.makedirs(outdir, exist_ok=True)
    import torch
    from transformers import AutoProcessor
    try:
        from transformers import Qwen2VLForConditionalGeneration as M
    except Exception:
        from transformers import AutoModelForVision2Seq as M
    model_id = "omerxai/Qari-OCR-v0.3"
    print(f"[qari] loading {model_id}")
    processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)
    model = M.from_pretrained(model_id, torch_dtype=torch.bfloat16,
                              trust_remote_code=True, device_map=None)
    model.eval()
    try:
        from qwen_vl_utils import process_vision_info
    except Exception:
        process_vision_info = None

    for img in imgs:
        base = os.path.splitext(os.path.basename(img))[0]
        outp = os.path.join(outdir, base + ".qari.txt")
        try:
            messages = [{"role": "user", "content": [
                {"type": "image", "image": "file://" + os.path.abspath(img)},
                {"type": "text", "text": "استخرج النص العربي من هذه الصفحة بدقة كاملة مع التشكيل."}]}]
            text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            if process_vision_info:
                image_inputs, video_inputs = process_vision_info(messages)
            else:
                from PIL import Image
                image_inputs, video_inputs = [Image.open(img).convert("RGB")], None
            inputs = processor(text=[text], images=image_inputs, videos=video_inputs,
                               padding=True, return_tensors="pt")
            with torch.no_grad():
                gen = model.generate(**inputs, max_new_tokens=4096, do_sample=False)
            trimmed = [o[len(i):] for i, o in zip(inputs.input_ids, gen)]
            out = processor.batch_decode(trimmed, skip_special_tokens=True)[0]
            with open(outp, "w", encoding="utf-8") as fh:
                fh.write(out + "\n")
            print(f"[qari] wrote {outp} ({len(out)} chars)")
        except Exception as e:
            print(f"[qari] page {img} failed: {e}")

try:
    main()
except Exception as e:
    print(f"[qari] aborted: {e}")
