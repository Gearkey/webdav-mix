import configparser
from webdav3.client import Client
from datetime import datetime
import os

class Pool(object):
    def __init__(self, pool_name):
        self.name = pool_name

        try:
            config = self.get_config()
            self.mix_type = config['pool']['mix_type']
            self.target_disk = config['pool']['target_disk']
        except KeyError:
            pass

    # 获取资源池配置
    def get_config(self):
        config = configparser.ConfigParser()
        config.read('./pool_list/' + self.name + '.ini')
        return config
    
    # 连接到指定磁盘
    def connect_server(self, disk, hostname='', username='', password=''):
        config = self.get_config()

        if hostname == '': hostname = config[disk]['hostname']
        if username == '': username = config[disk]['username']
        if password == '': password = config[disk]['password']
        
        options = {
            'webdav_hostname': hostname,
            'webdav_login': username,
            'webdav_password': password,
            'disable_check': True,
        }
        
        return Client(options)

    # 获取磁盘类型
    def get_disk_type(self, disk):
        if 'dav.jianguoyun.com' in self.get_config()[disk]['hostname']: return 'jianguo'
        else: return 'normal'

    # 获取时间戳
    def get_time(self):
        return datetime.now().strftime('%Y%m%d_%H%M%S')

    # 获取文件编号（混合类型1）
    def get_file_number(self, remote_path):
        client = self.connect_server('disk-0')
        client.download_sync(remote_path=remote_path, local_path='temp/temp.txt')

        with open('temp/temp.txt', 'r') as f:
            content = f.read()
            download_client_name = os.path.split(content)[0]
            file_number = os.path.split(content)[1]
        
        return download_client_name, file_number

    # 提取两段 url 相同的部分，并将它截出
    def get_top_url(self, url1, url2):
        i = 0
        while url1[i] == url2[i]: i += 1
        
        top_url = os.path.split(url1[:i])[0]
        url1 = url1[len(top_url):]
        url2 = url2[len(top_url):]

        return top_url, url1, url2

    # 列举文件
    def list_files(self, path):
        client = self.connect_server('disk-0')
        files = client.list(path)

        if self.get_disk_type('disk-0') == 'jianguo': del files[0]  # 坚果云会多一个标题
        return files

    # 上传文件到路径
    def upload(self, remote_path, upload_files):
        ## 资源池类型0：直接上传到 disk-0
        if self.mix_type == '0':
            client = self.connect_server('disk-0')
            for upload_file in upload_files:
                file_name = os.path.split(upload_file)[1]
                client.upload_sync(remote_path=remote_path+file_name, local_path=upload_file)
        
        ## 资源池类型1：上传到目标磁盘后在 disk-0 建立文件结构
        elif self.mix_type == '1':
            client = self.connect_server('disk-0')
            
            i = 0
            for upload_file in upload_files:
                file_name = os.path.split(upload_file)[1]
                remote_path = remote_path+file_name
                
                ### 如果文件已存在，直接以原编码覆盖，否则获取时间戳作为编码上传
                if client.check(remote_path):
                    download_client_name, file_number = self.get_file_number(remote_path)
                    self.target_disk = download_client_name
                else:
                    file_number = self.get_time()+'_'+str(i)

                target_client = self.connect_server(self.target_disk)
                target_client.upload_sync(remote_path=file_number, local_path=upload_file)

                with open('temp/temp.txt', 'w') as f:
                    f.write(self.target_disk + '/' + file_number)
                client.upload_sync(remote_path=remote_path, local_path='temp/temp.txt')
               
                i += 1
        
        ## 资源池类型2：先上传到目标磁盘，然后在 disk-0 将其移动到正确位置
        elif self.mix_type == '2':
            target_client = self.connect_server(self.target_disk)
            for upload_file in upload_files:
                file_name = os.path.split(upload_file)[1]
                target_client.upload_sync(remote_path=remote_path+file_name, local_path=upload_file)
            
            top_url, path1, path2 = self.get_top_url(self.get_config()['disk-0']['hostname'], self.get_config()[self.target_disk]['share_url'])

            client = self.connect_server('disk-0', hostname=top_url)
            for upload_file in upload_files:
                file_name = os.path.split(upload_file)[1]
                path1 = path1 + file_name
                path2 = path2 + file_name
                client.move(remote_path_from=path2, remote_path_to=path1)

        ## 其他
        else: pass
    
    # 下载文件到 Download 目录
    def download(self, remote_path, local_path):
        ## 资源池类型0：直接下载 disk-0 的实际文件
        if self.mix_type == '0':
            client = self.connect_server('disk-0')
            client.download_sync(remote_path=remote_path, local_path=local_path)
        
        ## 资源池类型1：通过 disk-0 文件指向的目标磁盘，下载文件
        elif self.mix_type == '1':
            download_client_name, file_number = self.get_file_number(remote_path)
        
            download_client = self.connect_server(download_client_name)
            download_client.download_sync(remote_path=file_number, local_path=local_path)

        ## 资源池类型2：复制到中转磁盘并下载，之后删除缓存
        elif self.mix_type == '2':
            top_url, path1, path2 = self.get_top_url(self.get_config()['disk-0']['hostname'], self.get_config()[self.target_disk]['share_url'])
            
            client = self.connect_server('disk-0', hostname=top_url)

            # for upload_file in upload_files:
            file_name = os.path.split(remote_path)[1]
            path1 = path1 + file_name
            path2 = path2 + file_name
            client.copy(remote_path_from=path1, remote_path_to=path2)

            download_client = self.connect_server(self.target_disk)
            download_client.download_sync(remote_path=file_name, local_path=local_path)

        ## 其他
        else: pass
