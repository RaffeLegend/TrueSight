from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor
from prompt import DEFAULT_PROMPT
from utils import extract_classification_and_bbox
import torch
import base64
from sam2.sam2_image_predictor import SAM2ImagePredictor
from PIL import Image
from qwen_vl_utils import process_vision_info
import numpy as np
import cv2

model_path = "/mnt/nas_d/yiwei/data/model/so_fake/"
segmentation_model_path = "facebook/sam2-hiera-large"

class TrueModel:
    def __init__(self):
        super(TrueModel, self).__init__()
        self.model = None
        self.prompt = DEFAULT_PROMPT
        self.image = None

    def init_model(self):
        # Load the reasoning model (VLM)
        self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            model_path,
            torch_dtype=torch.bfloat16,
            # attn_implementation="flash_attention_2",
            device_map="auto",
        ).eval()

        # Load the segmentation model (SAM2)
        self.segmentation_model = SAM2ImagePredictor.from_pretrained(segmentation_model_path)
        
        # Default processor
        self.processor = AutoProcessor.from_pretrained(model_path, padding_side="left")

    def load_sample(self, image_path):
        # Load and process the image
        image = Image.open(image_path)
        image = image.convert("RGB")
        self.origin_image = image
        original_width, original_height = image.size
        resize_size = 224
        self.x_factor, self.y_factor = original_width/resize_size, original_height/resize_size
        self.image = image.resize((resize_size, resize_size), Image.BILINEAR)
        # Prepare the message for the reasoning model
        messages = []
        message = [{
            "role": "user",
            "content": [
                {
                    "type": "image", 
                    "image": self.image
                },
                {   
                    "type": "text",
                    "text": self.prompt
                }
            ]
        }]
        messages.append(message)

        # Prepare inputs for the reasoning model
        text = [self.processor.apply_chat_template(msg, tokenize=False, add_generation_prompt=True) for msg in messages]
        image_inputs, video_inputs = process_vision_info(messages)
        inputs = self.processor(text=text, images=image_inputs, videos=video_inputs, padding=True, return_tensors="pt")
        self.inputs = inputs.to("cuda")


    def generate(self):
        # Generate response from the reasoning model
        generated_ids = self.model.generate(**self.inputs, use_cache=True, max_new_tokens=1024, do_sample=False)
        
        generated_ids_trimmed = [
            out_ids[len(in_ids):] for in_ids, out_ids in zip(self.inputs.input_ids, generated_ids)
        ]
        output_text = self.processor.batch_decode(
            generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
        )
        
        # Debug: Print raw output
        print(f"Raw output text: {output_text[0][:]}...")  # Print first 200 chars
        
        # Extract classification and bbox information
        classification, bbox, think = extract_classification_and_bbox(output_text[0], self.x_factor, self.y_factor)
        self.classification = classification
        self.bbox = bbox
        self.seg, self.box = self.segment()
        print(classification, bbox, think)
        print("thinking content:", think)
        print("content:", classification)
        print("bbox", bbox)
        return {'reason': think, 'answer': classification, 'bbox': bbox, 'segmentation': self.seg, 'bbox':self.box}
    
    def segment(self):
        if self.classification == "TAMPERED" and self.bbox is not None:
            with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16):
                self.segmentation_model.set_image(self.origin_image)
                masks, scores, _ = self.segmentation_model.predict(
                    box=self.bbox,
                    multimask_output=True
                )
                sorted_ind = np.argsort(scores)[::-1]
                masks = masks[sorted_ind]

            mask = masks[0].astype(bool)

            # Convert original image to numpy array
            image_np = np.array(self.origin_image)

            # Create masked (Segmentation) version
            masked_img = image_np.copy()
            overlay = (
                image_np * 0.5 +
                mask[:, :, None].astype(np.uint8) * np.array([255, 0, 0]) * 0.5
            ).astype(np.uint8)
            masked_img[mask] = overlay[mask]
            masked_img = cv2.cvtColor(masked_img, cv2.COLOR_RGB2BGR)

            # Encode segmentation image
            _, buffer_seg = cv2.imencode('.png', masked_img)
            seg_base64 = base64.b64encode(buffer_seg).decode('utf-8')
            seg_base64 = f"data:image/png;base64,{seg_base64}"

            # Create BBox version
            bbox_img = image_np.copy()
            bbox_img = cv2.cvtColor(bbox_img, cv2.COLOR_RGB2BGR)
            x1, y1, x2, y2 = map(int, self.bbox)  # Make sure bbox are integers

            cv2.rectangle(bbox_img, (x1, y1), (x2, y2), (0, 255, 0), thickness=4)  # Green bbox
            # Optionally, add label
            cv2.putText(
                bbox_img, "Tampered",
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                1, (0, 255, 0), 2, cv2.LINE_AA
            )

            # Encode bbox image
            _, buffer_bbox = cv2.imencode('.png', bbox_img)
            bbox_base64 = base64.b64encode(buffer_bbox).decode('utf-8')
            bbox_base64 = f"data:image/png;base64,{bbox_base64}"

            return seg_base64, bbox_base64

        return None, None
