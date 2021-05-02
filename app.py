from flask import Flask, render_template, request
import os
from pool import *

app = Flask(__name__)

# 首页：资源池列表
@app.route('/')
def index():
    pool_list = []
    with os.scandir('./pool_list/') as pools:
        for pool in pools:
            pool_list.append(os.path.splitext(pool.name)[0])
    
    return render_template('index.html', pool_list=pool_list)

# 资源池页：展示指定配置文件的资源列表
@app.route('/pool/<pool_name>/', methods=['POST', 'GET'])
@app.route('/pool/<pool_name>/<path:path>', methods=['POST', 'GET'])
def pool_web(pool_name, path=''):
    pool_0 = Pool(pool_name)

    # 上传文件
    if request.method == 'POST':
        upload_files = request.form.get('upload').split()
        pool_0.upload(path, upload_files)

    # 下载文件
    if path == '':
        pass
    elif path[-1:] != '/':
        pool_0.download(path, './download/'+os.path.split(path)[1])
        path = os.path.split(path)[0]

    # 列举文件
    files = pool_0.list_files(path)
    
    return render_template('pool.html', pool_name=pool_name, path=path, files=files)

if __name__ == '__main__':
    app.run(debug=True)