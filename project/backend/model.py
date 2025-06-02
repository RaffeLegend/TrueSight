import torch
import torch
from utils import split_model, load_image
from transformers import AutoModel, AutoTokenizer, AutoProcessor
from prompt import PROMPT

model_path = 'OpenGVLab/InternVL3-14B'

class TrueModel:
    def __init__(self):
        super(TrueModel, self).__init__()
        self.model = None
        self.prompt = PROMPT
        self.image = None

    def init_model(self):
        device_map = split_model('InternVL3-14B', model_path)
        self.model = AutoModel.from_pretrained(
                            model_path,
                            torch_dtype=torch.bfloat16,
                            load_in_8bit=False,
                            low_cpu_mem_usage=True,
                            use_flash_attn=True,
                            trust_remote_code=True,
                            device_map=device_map
                            ).eval()
        
        self.tokenizer = AutoTokenizer.from_pretrained(
                            model_path, 
                            trust_remote_code=True, 
                            use_fast=False
                            )
        
        self.processor = AutoProcessor.from_pretrained(
                            model_path, 
                            trust_remote_code=True, 
                            use_fast=False
                            )
        
    def load_sample(self, image_path):
        pixel_values = load_image(image_path).to(torch.bfloat16).cuda()
        self.image = pixel_values

    def generate(self):
        generation_config = dict(max_new_tokens=1024, do_sample=True)
        response = self.model.chat(self.tokenizer, self.image, self.prompt, generation_config)
        # print(f'User: {self.prompt}\nAssistant: {response}')
        return response
