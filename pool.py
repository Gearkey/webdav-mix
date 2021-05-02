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
    def connect_server(self, disk):
        config = self.get_config()
        
        options = {
            'webdav_hostname': config[disk]['hostname'],
            'webdav_login': config[disk]['username'],
            'webdav_password': config[disk]['password'],
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

    # 列举文件
    def list_files(self, path):
        # 资源池类型0：直接展示 disk-0 的文件结构
        # if self.mix_type == '0':
        client = self.connect_server('disk-0')
        files = client.list(path)
        
        # 其他
        # else: pass

        if self.get_disk_type('disk-0') == 'jianguo': del files[0]  # 坚果云会多一个标题
        return files

    # 上传文件到路径
    def upload(self, remote_path, upload_files):
        # 资源池类型0：直接上传到 disk-0
        if self.mix_type == '0':
            client = self.connect_server('disk-0')
            for upload_file in upload_files:
                file_name = os.path.split(upload_file)[1]
                client.upload_sync(remote_path=remote_path+file_name, local_path=upload_file)
        
        # 资源池类型1：上传到目标磁盘后在 disk-0 建立文件结构
        elif self.mix_type == '1':
            client = self.connect_server('disk-0')
            target_client = self.connect_server(self.target_disk)
            
            i = 0
            for upload_file in upload_files:
                file_number = self.get_time()+'_'+str(i)
                target_client.upload_sync(remote_path=file_number, local_path=upload_file)
                
                file_name = os.path.split(upload_file)[1]
                remote_path = remote_path+file_name

                with open('temp/temp.txt', 'w') as f:
                    f.write(self.target_disk + '/' + file_number)
                client.upload_sync(remote_path=remote_path, local_path='temp/temp.txt')
               
                i += 1
        
        # 资源池类型2：先上传到 disk-1 的共享文件夹，然后在 disk-0 将其移动到正确位置
        # elif self.mix_type == '2':
        #     client = self.connect_server('disk-0')
        #     client.upload_sync(remote_path=remote_path, local_path=local_path)
        
        # 其他
        else: pass
    
    # 下载文件到 Download 目录
    def download(self, remote_path, local_path):
        # 资源池类型0：直接下载 disk-0 的实际文件
        if self.mix_type == '0':
            client = self.connect_server('disk-0')
            client.download_sync(remote_path=remote_path, local_path=local_path)
        
        # 资源池类型1：通过 disk-0 文件指向的目标磁盘，下载文件
        elif self.mix_type == '1':
            client = self.connect_server('disk-0')
            client.download_sync(remote_path=remote_path, local_path='temp/temp.txt')
            with open('temp/temp.txt', 'r') as f:
                content = f.read()
                download_client_name = os.path.split(content)[0]
                file_name = os.path.split(content)[1]
        
            download_client = self.connect_server(download_client_name)
            download_client.download_sync(remote_path=file_name, local_path=local_path)

        # 其他
        else: pass
