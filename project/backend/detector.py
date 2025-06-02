import random
from model import TrueModel
from utils import extract_answer_reason

true_model = None

def is_ai_generated(image_path):
    """
    替换为你自己的模型调用逻辑。
    这里先用随机返回模拟结果。
    """
    # 示例：假设加载模型，预处理图片，返回预测
    # model.predict(preprocess(image_path)) -> 'ai' or 'real'
   
    global true_model 
    try:
        # 第一次调用时初始化模型
        if true_model is None:
            print("Initializing model...")
            true_model = TrueModel()
            true_model.init_model()
            print("Model initialized.")

        # 加载图片
        true_model.load_sample(image_path)
        # 生成回答
        response = true_model.generate()
        print(response)

        answer, reason = extract_answer_reason(response)

        if 'ai' in answer:
            return {'result': 'ai', 'reason': reason}
        elif 'real' in answer:
            return {'result': 'real', 'reason': reason}
        else:
            return {'result': 'unknown', 'reason': reason}
    
    except Exception as e:
        import traceback
        print(f"Error during detection: {e}")
        traceback.print_exc()
        return {'result': 'unknown', 'reason': ''}
    # return random.choice(['ai', 'real'])  # 模拟结果
