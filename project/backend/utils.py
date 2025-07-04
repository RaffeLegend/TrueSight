import math
import numpy as np
import torch
import torchvision.transforms as T
from decord import VideoReader, cpu
from PIL import Image
from torchvision.transforms.functional import InterpolationMode
from transformers import AutoModel, AutoTokenizer, AutoConfig
import re

IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)

def build_transform(input_size):
    MEAN, STD = IMAGENET_MEAN, IMAGENET_STD
    transform = T.Compose([
        T.Lambda(lambda img: img.convert('RGB') if img.mode != 'RGB' else img),
        T.Resize((input_size, input_size), interpolation=InterpolationMode.BICUBIC),
        T.ToTensor(),
        T.Normalize(mean=MEAN, std=STD)
    ])
    return transform

def find_closest_aspect_ratio(aspect_ratio, target_ratios, width, height, image_size):
    best_ratio_diff = float('inf')
    best_ratio = (1, 1)
    area = width * height
    for ratio in target_ratios:
        target_aspect_ratio = ratio[0] / ratio[1]
        ratio_diff = abs(aspect_ratio - target_aspect_ratio)
        if ratio_diff < best_ratio_diff:
            best_ratio_diff = ratio_diff
            best_ratio = ratio
        elif ratio_diff == best_ratio_diff:
            if area > 0.5 * image_size * image_size * ratio[0] * ratio[1]:
                best_ratio = ratio
    return best_ratio

def dynamic_preprocess(image, min_num=1, max_num=12, image_size=448, use_thumbnail=False):
    orig_width, orig_height = image.size
    aspect_ratio = orig_width / orig_height

    # calculate the existing image aspect ratio
    target_ratios = set(
        (i, j) for n in range(min_num, max_num + 1) for i in range(1, n + 1) for j in range(1, n + 1) if
        i * j <= max_num and i * j >= min_num)
    target_ratios = sorted(target_ratios, key=lambda x: x[0] * x[1])

    # find the closest aspect ratio to the target
    target_aspect_ratio = find_closest_aspect_ratio(
        aspect_ratio, target_ratios, orig_width, orig_height, image_size)

    # calculate the target width and height
    target_width = image_size * target_aspect_ratio[0]
    target_height = image_size * target_aspect_ratio[1]
    blocks = target_aspect_ratio[0] * target_aspect_ratio[1]

    # resize the image
    resized_img = image.resize((target_width, target_height))
    processed_images = []
    for i in range(blocks):
        box = (
            (i % (target_width // image_size)) * image_size,
            (i // (target_width // image_size)) * image_size,
            ((i % (target_width // image_size)) + 1) * image_size,
            ((i // (target_width // image_size)) + 1) * image_size
        )
        # split the image
        split_img = resized_img.crop(box)
        processed_images.append(split_img)
    assert len(processed_images) == blocks
    if use_thumbnail and len(processed_images) != 1:
        thumbnail_img = image.resize((image_size, image_size))
        processed_images.append(thumbnail_img)
    return processed_images

def load_image(image_file, input_size=448, max_num=12):
    image = Image.open(image_file).convert('RGB')
    transform = build_transform(input_size=input_size)
    images = dynamic_preprocess(image, image_size=input_size, use_thumbnail=True, max_num=max_num)
    pixel_values = [transform(image) for image in images]
    pixel_values = torch.stack(pixel_values)
    return pixel_values

def split_model(model_name, model_path):
    device_map = {}
    world_size = torch.cuda.device_count()
    config = AutoConfig.from_pretrained(model_path, trust_remote_code=True)
    num_layers = config.llm_config.num_hidden_layers
    # Since the first GPU will be used for ViT, treat it as half a GPU.
    num_layers_per_gpu = math.ceil(num_layers / (world_size - 0.5))
    num_layers_per_gpu = [num_layers_per_gpu] * world_size
    num_layers_per_gpu[0] = math.ceil(num_layers_per_gpu[0] * 0.5)
    layer_cnt = 0
    for i, num_layer in enumerate(num_layers_per_gpu):
        for j in range(num_layer):
            device_map[f'language_model.model.layers.{layer_cnt}'] = i
            layer_cnt += 1
    device_map['vision_model'] = 0
    device_map['mlp1'] = 0
    device_map['language_model.model.tok_embeddings'] = 0
    device_map['language_model.model.embed_tokens'] = 0
    device_map['language_model.output'] = 0
    device_map['language_model.model.norm'] = 0
    device_map['language_model.model.rotary_emb'] = 0
    device_map['language_model.lm_head'] = 0
    device_map[f'language_model.model.layers.{num_layers - 1}'] = 0

    return device_map


def extract_answer_reason(response):
    """
    从模型回复中提取 <answer> 和 <reason> 内容。
    """
    try:
        answer_match = re.search(r'<answer>(.*?)</answer>', response, re.DOTALL)
        reason_match = re.search(r'<reason>(.*?)</reason>', response, re.DOTALL)

        answer = answer_match.group(1).strip() if answer_match else 'unknown'
        reason = reason_match.group(1).strip() if reason_match else ''

        return answer.lower(), reason
    except Exception as e:
        print(f"Error extracting answer and reason: {e}")
        return 'unknown', ''
    
def format_data(image_path, prompt):
    with Image.open(image_path) as image:
        image = image.convert("RGB")
    return [
                {
                    "role": "system",
                    "content": prompt
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "image": image
                        }
                    ]
                },
            ]

def extract_classification_and_bbox(output_text, x_factor, y_factor):
    # Print the complete output for debugging
    print(f"Complete output text: {output_text}")
    
    # Extract thinking process
    think_pattern = r'<think>([\s\S]+?)</think>'
    think_match = re.search(think_pattern, output_text)
    if think_match:
        think_text = think_match.group(1).strip()
    else:
        think_text = "No thinking process found."
    
    # Extract answer
    answer_pattern = r'<answer>([\s\S]+?)</answer>'
    answer_match = re.search(answer_pattern, output_text)
    
    if not answer_match:
        print("WARNING: No answer tag found in output text")
        return "UNKNOWN", None, think_text
    
    answer = answer_match.group(1).strip()
    print(f"Extracted answer: {answer}")
    
    # Check classification
    if "FULL_SYNTHETIC" in answer.upper():
        return "FULL_SYNTHETIC", None, think_text
    elif "REAL" in answer.upper():
        return "REAL", None, think_text
    elif "TAMPERED" in answer.upper():
        # Extract bounding box
        bbox_pattern = re.compile(
            r'(?:<\|box_start\|>)?\s*\((\d+),\s*(\d+)\)\s*,\s*\((\d+),\s*(\d+)\)\s*(?:<\|box_end\|>)?',
            re.I
        )
        bbox_match = re.search(bbox_pattern, answer)
        if bbox_match:
            x1 = round(int(bbox_match.group(1)) * x_factor)
            y1 = round(int(bbox_match.group(2)) * y_factor)
            x2 = round(int(bbox_match.group(3)) * x_factor)
            y2 = round(int(bbox_match.group(4)) * y_factor)
            return "TAMPERED", [x1, y1, x2, y2], think_text
        else:
            print("WARNING: TAMPERED image but no bbox found")
            return "TAMPERED", None, think_text
    else:
        print(f"WARNING: Unknown classification in answer: {answer}")
        return "UNKNOWN", None, think_text

