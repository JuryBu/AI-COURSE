from flask import Flask, Response, request, send_from_directory, render_template, redirect, url_for
from flask_cors import CORS
import requests
import os
import logging
import json

app = Flask(__name__, static_folder='static')
CORS(app, resources={r"/*": {"origins": "*"}})

# 设置日志
logging.basicConfig(level=logging.DEBUG)

app.jinja_env.globals.update(enumerate=enumerate)
# 设置上传文件存储路径
UPLOAD_FOLDER = 'static'
ALLOWED_EXTENSIONS = {'mp4', 'mp3', 'txt', 'pdf', 'pptx', 'jpg', 'jpeg', 'png'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['STATIC_FOLDER'] = 'static'

# 确保上传目录存在
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# 章节文件存储结构 (这个变量主要用于初始化，实际数据由 load_uploaded_files 动态加载)
chapters = {}


# 判断文件类型是否合法
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# 读取上传的文件，并将其加载到章节中
def load_uploaded_files():
    chapters.clear()  # 每次加载前清空
    # 检查并创建根上传目录
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    for chapter_name in sorted(os.listdir(app.config['UPLOAD_FOLDER'])):
        chapter_path = os.path.join(app.config['UPLOAD_FOLDER'], chapter_name)
        if os.path.isdir(chapter_path):
            chapters.setdefault(chapter_name, {})
            for section_name in sorted(os.listdir(chapter_path)):
                section_path = os.path.join(chapter_path, section_name)
                if os.path.isdir(section_path):
                    chapters[chapter_name].setdefault(section_name, {
                        'videos': [], 'documents': [], 'classroom_exercises': [],
                        'homework': [], 'discussion_exercises': []
                    })
                    for resource_type in sorted(os.listdir(section_path)):
                        resource_path = os.path.join(section_path, resource_type)
                        if os.path.isdir(resource_path):
                            target_list_name = resource_type if resource_type in chapters[chapter_name][
                                section_name] else 'documents'
                            target = chapters[chapter_name][section_name][target_list_name]
                            for filename in sorted(os.listdir(resource_path)):
                                if allowed_file(filename) and filename not in target:
                                    target.append(filename)


# 读取讨论内容
def read_discussions(chapter_name, section_name):
    discussion_folder = os.path.join('static', chapter_name, section_name)
    discussion_file = os.path.join(discussion_folder, 'discussions.txt')
    discussions = []
    encodings_to_try = ['utf-8', 'gbk', 'mbcs', 'latin1']
    if os.path.exists(discussion_file):
        for enc in encodings_to_try:
            try:
                with open(discussion_file, 'r', encoding=enc) as f:
                    discussions = [line.strip() for line in f.readlines()]
                break
            except (UnicodeDecodeError, PermissionError):
                continue
    return discussions


# 保存讨论内容
def save_discussion(chapter_name, section_name, discussion_content):
    discussion_folder = os.path.join('static', chapter_name, section_name)
    if not os.path.exists(discussion_folder):
        os.makedirs(discussion_folder)
    discussion_file = os.path.join(discussion_folder, 'discussions.txt')
    with open(discussion_file, 'a', encoding='utf-8') as f:
        f.write(discussion_content + '\n')


# 读取参考答案
def read_answer(chapter_name, section_name, number):
    answer_folder = os.path.join('static', chapter_name, section_name, 'answers')
    answer_image_path = os.path.join(answer_folder, f"answer{number}.jpg")
    answer_txt_path = os.path.join(answer_folder, f"answer{number}.txt")
    answer = {}
    if os.path.exists(answer_image_path):
        answer['image'] = f"answer{number}.jpg"
    if os.path.exists(answer_txt_path):
        try:
            with open(answer_txt_path, 'r', encoding='utf-8') as f:
                answer['text'] = f.read()
        except Exception:
            with open(answer_txt_path, 'r', encoding='gbk') as f:
                answer['text'] = f.read()
    return answer


# 读取题目
def read_ques(chapter_name, section_name, part_name, number):
    ques_folder = os.path.join('static', chapter_name, section_name, part_name)
    ques_image_path = os.path.join(ques_folder, f"ques{number}.jpg")
    ques_txt_path = os.path.join(ques_folder, f"ques{number}.txt")
    ques = {}
    if os.path.exists(ques_image_path):
        ques['image'] = f"ques{number}.jpg"
    if os.path.exists(ques_txt_path):
        try:
            with open(ques_txt_path, 'r', encoding='utf-8') as f:
                ques['text'] = f.read()
        except Exception:
            with open(ques_txt_path, 'r', encoding='gbk') as f:
                ques['text'] = f.read()
    return ques


# 路由部分
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/course_description')
def course_description():
    return render_template('course_description.html')


@app.route('/course_content')
def course_content():
    load_uploaded_files()
    discussions = {}
    for chapter_name in chapters:
        for section_name in chapters[chapter_name]:
            discussions.setdefault(chapter_name, {})[section_name] = read_discussions(chapter_name, section_name)
    return render_template('course_content.html', chapters=chapters, discussions=discussions, read_answer=read_answer,
                           read_ques=read_ques)


@app.route('/additional_resources')
def additional_resources():
    return render_template('additional_resources.html')


@app.route('/teaching_staff')
def teaching_staff():
    return render_template('teaching_staff.html')


@app.route('/static', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        file = request.files['file']
        chapter = request.form['chapter']
        section = request.form['section']
        resource_type = request.form['resource_type']
        if file and allowed_file(file.filename):
            filename = file.filename
            save_path = os.path.join('static', chapter, section, resource_type)
            if not os.path.exists(save_path):
                os.makedirs(save_path)
            file.save(os.path.join(save_path, filename))
            return redirect(url_for('course_content'))
    load_uploaded_files()
    return render_template('upload.html', chapters=chapters)


@app.route('/submit_discussion/<chapter_name>/<section_name>', methods=['POST'])
def submit_discussion(chapter_name, section_name):
    discussion_content = request.form['discussion_content']
    save_discussion(chapter_name, section_name, discussion_content)
    return redirect(url_for('course_content'))


# =================================================================
#               【最终修正的AI助手接口】
# =================================================================
@app.route('/receive', methods=['POST'])
def receive_data():
    data = request.json
    model = data.get("model", "deepseek-math")  # 从请求获取模型名，如果没有则使用默认
    messages = data.get("messages", [])

    # 从消息历史中提取最后一条用户输入作为prompt
    # Ollama的 /api/generate 接口需要的是 prompt 字段
    prompt = ""
    if messages and isinstance(messages, list) and len(messages) > 0:
        prompt = messages[-1].get('content', '')

    # 构造Ollama能理解的、正确的数据格式
    ollama_data = {
        "model": model,
        "prompt": prompt,
        "stream": True  # 确保是流式输出
    }

    def generate():
        try:
            # 使用服务器上Ollama的正确地址和API端点
            with requests.post(
                    'http://127.0.0.1:11434/api/generate',
                    json=ollama_data,
                    stream=True
            ) as r:
                r.raise_for_status()  # 如果请求失败 (如404, 500等), 会抛出异常
                for chunk in r.iter_content(chunk_size=None):
                    if chunk:
                        # Ollama的流式响应是逐行JSON，我们需要解析它并只发送内容
                        try:
                            line = chunk.decode('utf-8')
                            json_line = json.loads(line)
                            # 提取'response'字段的内容并格式化为SSE
                            response_content = json_line.get('response', '')
                            # 模拟LM Studio的输出格式，前端代码可能依赖这个格式
                            sse_formatted_chunk = f"data: {{\"choices\": [{{\"delta\": {{\"content\": \"{json.dumps(response_content)[1:-1]}\"}}}}]}}\n\n"
                            yield sse_formatted_chunk.encode('utf-8')
                        except (json.JSONDecodeError, UnicodeDecodeError):
                            continue  # 忽略无法解析的行
        except requests.exceptions.RequestException as e:
            app.logger.error(f"Error forwarding request to Ollama: {e}")
            yield f'data: {{"error": "Failed to connect to AI service: {e}"}}\n\n'.encode('utf-8')

    return Response(generate(), mimetype='text/event-stream')


if __name__ == '__main__':
    # 这里的端口号可以是任意未被占用的，比如5000, 8000等
    # Gunicorn会忽略这里的设置，但为了本地测试方便，可以保留
    app.run(host='0.0.0.0', port=5000, debug=True)

