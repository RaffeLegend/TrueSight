# PROMPT = (
#     "Please determine whether this image is AI-generated or real."
#     "Write 'AI' or 'Real' only inside <answer> tags without any other content."
#     "Then, briefly explain your reasoning inside <reason> tags.\n"
#     "Example:\n"
#     "<reason>The image shows unnatural details and repetitive textures typically seen in AI-generated images.</reason>"
#     "<answer>AI</answer>\n"
# )

PROMPT = (
    "Please determine whether this image is AI-generated or real. "
    "Think step-by-step from multiple perspectives, including: "
    "details, texture consistency, lighting and shadows, composition and semantics, and any other anomalies. "
    "Then, write your final concise reasoning inside <reason> tags. "
    "Finally, write 'AI' or 'Real' only inside <answer> tags without any other content.\n"
    "Example:\n"
    "<reason>The image shows unnatural textures, inconsistent lighting, and distorted facial features, which are typical signs of AI generation.</reason>"
    "<answer>AI</answer>\n"
)