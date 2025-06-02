from transformers import AutoModelForCausalLM, AutoTokenizer
from prompt import PROMPT
from utils import format_data

model_name = "Qwen/Qwen3-8B"

class TrueModel:
    def __init__(self):
        super(TrueModel, self).__init__()
        self.model = None
        self.prompt = PROMPT
        self.image = None

    def init_model(self):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype="auto",
            device_map="auto"
        )

    def load_sample(self, image_path):
        message = format_data(image_path, PROMPT)

        text = self.tokenizer.apply_chat_template(
            message['message'],
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=True # Switches between thinking and non-thinking modes. Default is True.
        )
        self.model_inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)

    def generate(self):
        generated_ids = self.model.generate(
            **self.model_inputs,
            max_new_tokens=32768
        )
        output_ids = generated_ids[0][len(self.model_inputs.input_ids[0]):].tolist() 
        try:
            # rindex finding 151668 (</think>)
            index = len(output_ids) - output_ids[::-1].index(151668)
        except ValueError:
            index = 0

        thinking_content = self.tokenizer.decode(output_ids[:index], skip_special_tokens=True).strip("\n")
        content = self.tokenizer.decode(output_ids[index:], skip_special_tokens=True).strip("\n")

        print("thinking content:", thinking_content)
        print("content:", content)