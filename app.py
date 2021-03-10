from flask import Flask, render_template, request
import os
import configparser
from webdav3.client import Client

app = Flask(__name__)

@app.route('/')
def index():
    pool_list = []
    with os.scandir('./pool_list/') as pools:
        for pool in pools:
            pool_list.append(os.path.splitext(pool.name)[0])
    
    return render_template('index.html', pool_list=pool_list)

@app.route('/pool/<pool_name>/', methods=['POST', 'GET'])
@app.route('/pool/<pool_name>/<path:path>', methods=['POST', 'GET'])
def pool(pool_name, path=''):
    client = connect_server(pool_name, 'sub-main')

    if request.method == 'POST':
        upload_files = request.form.get('upload').split()

        for upload_file in upload_files:
            file_name = os.path.split(upload_file)[1]
            client.upload_sync(remote_path=path+file_name, local_path=upload_file)

    files = client.list(path)
    if get_sub_pool_type(pool_name, 'sub-main') == 'jianguo': del files[0]  # 坚果云会多一个标题

    if path == '':
        pass
    elif path[-1:] != '/':
        client.download_sync(remote_path=path, local_path='./download/'+os.path.split(path)[1])
    
    return render_template('pool.html', pool_name=pool_name, path=path, files=files)

# 功能模块--------------

# 连接到指定子储存池
def connect_server(pool_name, sub_pool):
    config = get_config(pool_name)
    
    options = {
        'webdav_hostname': config[sub_pool]['hostname'],
        'webdav_login': config[sub_pool]['username'],
        'webdav_password': config[sub_pool]['password'],
        'disable_check': True,
    }
    
    return Client(options)

# 获取子储存池类型
def get_sub_pool_type(pool_name, sub_pool_name):
    if 'dav.jianguoyun.com' in get_config(pool_name)[sub_pool_name]['hostname']: return 'jianguo'
    else: return 'normal'

# 获取配置
def get_config(pool_name):
    config = configparser.ConfigParser()
    config.read('./pool_list/' + pool_name + '.ini')
    return config

if __name__ == '__main__':
    app.run(debug=True)