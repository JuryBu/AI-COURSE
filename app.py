from flask import Flask, Response, request, send_from_directory, render_template, redirect, url_for
from flask_cors import CORS
import requests
import os
import time
from collections import deque
import logging

app = Flask(__name__, static_folder='static')
CORS(app, resources={r"/*": {"origins": "*"}})

# 配置参数
LM_STUDIO_URL = "http://127.0.0.1:1234/v1/chat/completions"

# 负载均衡配置
MODEL_INSTANCES = {
    "deepseek-math-7b-instruct": [
        {
            "name": "deepseek-math-7b-instruct",
            "host": "http://127.0.0.1:1234",
            "endpoint": "/v1/chat/completions",
            "active_requests": 0,
            "response_times": deque(maxlen=10)
        }
    ]
}

# 设置日志
logging.basicConfig(level=logging.DEBUG)

app.jinja_env.globals.update(enumerate=enumerate)
# 设置上传文件存储路径
UPLOAD_FOLDER = 'static'
ALLOWED_EXTENSIONS = {'mp4', 'mp3', 'txt', 'pdf', 'pptx', 'jpg', 'jpeg', 'png'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['STATIC_FOLDER'] = 'static'  # 确保static文件夹路径

# 确保上传目录存在
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# 章节文件存储结构
chapters = {
    '第一章': {
        '小节1': {
            'videos': [],
            'documents': [],
            'classroom_exercises': [],
            'homework': [],
            'discussion_exercises': []
        },
        '小节2': {
            'videos': [],
            'documents': [],
            'classroom_exercises': [],
            'homework': [],
            'discussion_exercises': []
        }
    },
    '第二章': {
        '小节1': {
            'videos': [],
            'documents': [],
            'classroom_exercises': [],
            'homework': [],
            'discussion_exercises': []
        },
        '小节2': {
            'videos': [],
            'documents': [],
            'classroom_exercises': [],
            'homework': [],
            'discussion_exercises': []
        }
    },
}


# 判断文件类型是否合法
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# 读取上传的文件，并将其加载到章节中
def load_uploaded_files():
    chapters.clear()
    for chapter_name in os.listdir(app.config['UPLOAD_FOLDER']):
        chapter_path = os.path.join(app.config['UPLOAD_FOLDER'], chapter_name)
        if os.path.isdir(chapter_path):
            chapters.setdefault(chapter_name, {})
            for section_name in os.listdir(chapter_path):
                section_path = os.path.join(chapter_path, section_name)
                if os.path.isdir(section_path):
                    # 初始化小节数据结构
                    chapters[chapter_name].setdefault(section_name, {
                        'videos': [],
                        'documents': [],
                        'classroom_exercises': [],
                        'homework': [],
                        'discussion_exercises': []
                    })

                    # 遍历小节下的所有子目录
                    for resource_type in os.listdir(section_path):
                        resource_path = os.path.join(section_path, resource_type)
                        if os.path.isdir(resource_path):
                            # 根据子目录类型分类文件
                            if resource_type == 'classroom_exercises':
                                target = chapters[chapter_name][section_name]['classroom_exercises']
                            elif resource_type == 'videos':
                                target = chapters[chapter_name][section_name]['videos']
                            elif resource_type == 'homework':
                                target = chapters[chapter_name][section_name]['homework']
                            elif resource_type == 'discussion_exercises':
                                target = chapters[chapter_name][section_name]['discussion_exercises']
                            else:
                                target = chapters[chapter_name][section_name]['documents']

                            # 加载具体文件
                            for filename in os.listdir(resource_path):
                                if allowed_file(filename):
                                    target.append(filename)


# 读取讨论内容
def read_discussions(chapter_name, section_name):
    discussion_folder = os.path.join('static', chapter_name, section_name)
    discussion_file = os.path.join(discussion_folder, 'discussions.txt')
    discussions = []

    encodings_to_try = ['utf-8', 'mbcs', 'gbk', 'cp936', 'latin1', 'iso-8859-1']

    if os.path.exists(discussion_file):
        for enc in encodings_to_try:
            try:
                with open(discussion_file, 'r', encoding=enc) as f:
                    discussions = [line.strip() for line in f.readlines()]
                break  # 读取成功就跳出循环
            except UnicodeDecodeError:
                continue  # 尝试下一个编码

    return discussions


# 保存讨论内容
def save_discussion(chapter_name, section_name, discussion_content):
    discussion_folder = os.path.join('static', chapter_name, section_name)
    if not os.path.exists(discussion_folder):
        os.makedirs(discussion_folder)

    discussion_file = os.path.join(discussion_folder, 'discussions.txt')
    with open(discussion_file, 'a') as f:
        f.write(discussion_content + '\n')


# 读取参考答案
def read_answer(chapter_name, section_name, number):
    answer_folder = os.path.join('static', chapter_name, section_name, 'answers')
    answer_image = f"answer{number}.jpg"
    answer_txt = f"answer{number}.txt"
    answer_image_path = os.path.join(answer_folder, answer_image)
    answer_txt_path = os.path.join(answer_folder, answer_txt)

    print(f"有 {answer_image_path}")
    print(f"有 {answer_txt_path}")

    answer = {}
    if os.path.exists(answer_image_path):
        answer = {
            'image': answer_image,
            'text': None
        }

    if os.path.exists(answer_txt_path):
        with open(answer_txt_path, 'r', encoding='utf-8') as f:
            answer['text'] = f.read()

    if answer:
        print("answer yes")

    return answer


# 读取题目tup
def read_ques(chapter_name, section_name, part_name, number):
    ques_folder = os.path.join('static', chapter_name, section_name, part_name)
    ques_image = f"ques{number}.jpg"
    ques_txt = f"ques{number}.txt"
    ques_image_path = os.path.join(ques_folder, ques_image)
    ques_txt_path = os.path.join(ques_folder, ques_txt)

    print(f"有 {ques_image_path}")

    ques = {}
    if os.path.exists(ques_image_path):
        ques = {
            'image': ques_image,
            'text': None
        }

    if os.path.exists(ques_txt_path):
        with open(ques_txt_path, 'r', encoding='utf-8') as f:
            ques['text'] = f.read()

    if ques:
        print("ques yes")

    return ques


def select_best_instance(model):
    """选择最优实例：综合 活跃请求数 和 平均响应时间"""
    if model not in MODEL_INSTANCES:
        return model

    instances = MODEL_INSTANCES[model]

    # 计算每个实例的负载评分（活跃请求数 + 标准化响应时间）
    scores = []
    for instance in instances:
        avg_response_time = sum(instance["response_times"]) / len(instance["response_times"]) if instance[
            "response_times"] else 0
        # 权重系数可调整（活跃请求数权重更高）
        score = instance["active_requests"] * 2 + avg_response_time * 0
        scores.append(score)

    # 选择评分最低的实例
    print(scores)
    best_index = scores.index(min(scores))
    return instances[best_index]["name"]


# 首页
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/static/<filename>')
def serve_video(filename):
    file_path = os.path.join('static', filename)
    if os.path.exists(file_path):
        return send_from_directory('static', filename)
    else:
        return "File not found", 404


# 课程简介
@app.route('/course_description')
def course_description():
    return render_template('course_description.html')


# 课程内容
@app.route('/course_content')
def course_content():
    load_uploaded_files()  # 每次加载页面时加载上传的文件
    discussions = {}
    homework = {}
    classroom_exercises = {}
    discussion_exercises = {}

    for chapter_name in chapters.keys():
        for section_name in chapters[chapter_name]:
            # 获取每个小节的讨论内容
            discussions[section_name] = read_discussions(chapter_name, section_name)

        return render_template('course_content.html', chapters=chapters, discussions=discussions, read_answer=read_answer
         , read_ques=read_ques)  # 传递read_answer函数到模板中


# 额外教学资源
@app.route('/additional_resources')
def additional_resources():
    return render_template('additional_resources.html')


# 参与本教学人员
@app.route('/teaching_staff')
def teaching_staff():
    return render_template('teaching_staff.html')


#上传
@app.route('/static', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        file = request.files['file']
        chapter = request.form['chapter']  # 获取选择的章节
        section = request.form['section']  # 获取选择的小节
        resource_type = request.form['resource_type']

        if file and allowed_file(file.filename):
            filename = file.filename
            save_path = os.path.join('static', chapter, section, resource_type)
            if not os.path.exists(save_path):
                os.makedirs(save_path)
            file.save(os.path.join(save_path, filename))

            return redirect(url_for('course_content'))
    return render_template('upload.html', chapters=chapters)


# 删除资源功能
@app.route('/delete/<filename>')
def delete_file(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    # 删除文件时，也要从章节列表中删除
    for chapter in chapters.values():
        if filename in chapter:
            chapter.remove(filename)

    return redirect(url_for('course_content'))


# 下载资源功能
@app.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(file_path):
        # 设置响应头，让浏览器下载文件，而不是直接打开
        response = send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
        response.headers["Content-Disposition"] = f"attachment; filename={filename}"
        return response
    else:
        return "文件不存在", 404


# 重命名资源功能
@app.route('/rename/<old_filename>', methods=['GET', 'POST'])
def rename_file(old_filename):
    if request.method == 'POST':
        new_filename = request.form['new_filename']
        old_file_path = os.path.join(app.config['UPLOAD_FOLDER'], old_filename)
        new_file_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
        if os.path.exists(old_file_path):
            os.rename(old_file_path, new_file_path)

            # 更新章节列表中的文件名
            for chapter in chapters.values():
                if old_filename in chapter:
                    chapter[chapter.index(old_filename)] = new_filename

            return redirect(url_for('course_content'))
    return render_template('rename.html', old_filename=old_filename)


# 提交讨论内容
@app.route('/submit_discussion/<chapter_name>/<section_name>', methods=['POST'])
def submit_discussion(chapter_name, section_name):
    discussion_content = request.form['discussion_content']
    save_discussion(chapter_name, section_name, discussion_content)
    return redirect(url_for('course_content'))


@app.route('/receive', methods=['POST'])
def receive_data():
    data = request.json
    model = data.get("model")
    messages = data.get("messages", [])
    temperature = data.get("temperature", 0.7)

    # 负载均衡逻辑
    if model in MODEL_INSTANCES:
        selected_instance = select_best_instance(model)
    else:
        selected_instance = model

    def generate():
        start_time = time.time()
        instance = next((i for i in MODEL_INSTANCES.get(model, []) if i["name"] == selected_instance), None)
        if instance:
            instance["active_requests"] += 1  # 标记实例为忙碌

        try:
            with requests.post(
                LM_STUDIO_URL,
                json={
                    "model": selected_instance,
                    "messages": messages,
                    "stream": True,
                    "temperature": temperature
                },
                stream=True
            ) as r:
                for chunk in r.iter_content(chunk_size=None):
                    if chunk:
                        yield chunk
        except Exception as e:
            print(f"Error forwarding request: {e}")
            yield 'data: {"error": "Failed to forward request to LM Studio"}\n\n'
        finally:
            if instance:
                # 记录响应时间并减少活跃请求数
                instance["active_requests"] -= 1
                response_time = time.time() - start_time
                instance["response_times"].append(response_time)

    return Response(generate(), mimetype='text/event-stream')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
