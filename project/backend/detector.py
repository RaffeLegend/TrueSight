import random
# from model import TrueModel
from so_fake import TrueModel
from utils import extract_answer_reason
from flask import jsonify

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

        # answer, reason = extract_answer_reason(response)
        if 'REAL' in response['answer']:
            return {
                'result': 'real', 
                'reason': response['reason'] or '', 
                'segmentation': response['segmentation'] or '', 
                'bbox': response['bbox'] or ''
                }, 200
        elif 'TAMPERED' in response['answer']:
            return {
                'result': 'tampered', 
                'reason': response['reason'] or '', 
                'segmentation': response['segmentation'] or '',
                'bbox': response['bbox'] or ''
                }, 200
        elif 'FULL_SYNTHETIC' in response['answer']:
            return {
                'result': 'ai',
                'reason': response['reason'] or '',
                'segmentation': response['segmentation'] or '',
                'bbox': response['bbox'] or ''
                }, 200
        else:
            return {
                'result': 'unknown', 
                'reason': response['reason'] or '', 
                'segmentation': response['segmentation'] or '', 
                'bbox': response['bbox'] or ''
                }, 200
    
    except Exception as e:
        import traceback
        print(f"Error during detection: {e}")
        traceback.print_exc()
        return {'result': 'unknown', 'reason': ''}
    # return random.choice(['ai', 'real'])  # 模拟结果
