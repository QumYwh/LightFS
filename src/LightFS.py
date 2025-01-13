import os
import struct
import json

# 文件系统常量
LIGHT_FS_FILE = "light.fs"  # 文件系统主文件名
FS_SIZE = 256 * 1024 * 1024  # 文件系统总大小 (256MB)
FS_META_SIZE = 56 * 1024 * 1024  # 元数据区域大小 (56MB)
FS_BLOCK_SIZE = 1 * 1024 * 1024  # 数据块大小 (1MB)
FS_DATA_BLOCKS = (FS_SIZE - FS_META_SIZE) // FS_BLOCK_SIZE  # 可用数据块数量


# 文件元数据结构
class FileMetadata:
    """表示文件或文件夹的元数据"""

    def __init__(self, name, is_folder=False, size=0, blocks=None):
        self.name = name  # 文件名
        self.is_folder = is_folder  # 是否为文件夹
        self.size = size  # 文件大小
        self.blocks = blocks if blocks else []  # 文件占用的块

    def to_dict(self):
        """将文件元数据转换为字典"""
        return {
            "name": self.name,
            "is_folder": self.is_folder,
            "size": self.size,
            "blocks": self.blocks
        }

    @staticmethod
    def from_dict(data):
        """从字典创建文件元数据"""
        return FileMetadata(
            name=data["name"],
            is_folder=data["is_folder"],
            size=data["size"],
            blocks=data["blocks"]
        )


# LightFS 主类
class LightFS:
    """轻量级文件系统的核心类"""

    def __init__(self):
        self.files = {}  # 存储文件和文件夹的元数据
        self.bitmap = [0] * FS_DATA_BLOCKS  # 数据块位图，用于标记哪些块已被占用
        self.loaded = False  # 文件系统是否已加载

    def initialize(self):
        """初始化文件系统"""
        if not os.path.exists(LIGHT_FS_FILE):
            with open(LIGHT_FS_FILE, "wb") as f:
                f.write(b"\0" * FS_SIZE)  # 写入空的文件系统
            self.files = {}  # 清空文件系统中的文件
            self.bitmap = [0] * FS_DATA_BLOCKS  # 重置位图
            self.save_metadata()  # 保存元数据
        else:
            raise FileExistsError("文件系统已经存在！")

    def load(self):
        """加载文件系统"""
        if os.path.exists(LIGHT_FS_FILE):
            with open(LIGHT_FS_FILE, "rb") as f:
                metadata_size = struct.unpack("I", f.read(4))[0]  # 读取元数据的大小
                metadata = f.read(metadata_size).decode()  # 读取元数据
                # 将元数据解析为字典
                self.files = {
                    name: FileMetadata.from_dict(data)
                    for name, data in json.loads(metadata).items()
                }
                self.bitmap = list(f.read(FS_DATA_BLOCKS))  # 读取数据块位图
            self.loaded = True
        else:
            raise FileNotFoundError("文件系统未找到！")

    def save_metadata(self):
        """保存文件系统的元数据"""
        metadata = json.dumps({name: file.to_dict() for name, file in self.files.items()})
        with open(LIGHT_FS_FILE, "r+b") as f:
            f.write(struct.pack("I", len(metadata)))  # 写入元数据大小
            f.write(metadata.encode())  # 写入元数据内容
            f.write(bytearray(self.bitmap))  # 写入数据块位图

    def create_file(self, name):
        """创建新文件"""
        if name in self.files:
            raise ValueError("文件已经存在！")
        self.files[name] = FileMetadata(name)  # 创建新文件的元数据
        self.save_metadata()  # 保存元数据

    def rename_file(self, old_name, new_name):
        """重命名文件"""
        if old_name not in self.files:
            raise ValueError("文件未找到！")
        if new_name in self.files:
            raise ValueError("新文件名已存在！")
        self.files[new_name] = self.files.pop(old_name)  # 修改文件名
        self.files[new_name].name = new_name  # 更新文件名
        self.save_metadata()  # 保存元数据

    def delete_file(self, name):
        """删除文件"""
        if name not in self.files:
            raise ValueError("文件未找到！")
        file_metadata = self.files.pop(name)  # 删除文件的元数据
        for block in file_metadata.blocks:
            self.bitmap[block] = 0  # 释放文件占用的数据块
        self.save_metadata()  # 保存元数据

    def list_files(self):
        """列出文件系统中的文件和文件夹"""
        return [(name, metadata.is_folder) for name, metadata in self.files.items()]

    def write_to_file(self, name, content):
        """向文件写入内容"""
        if name not in self.files:
            raise ValueError("文件未找到！")
        file_metadata = self.files[name]
        if file_metadata.is_folder:
            raise ValueError("不能向文件夹写入内容！")
        content_bytes = content.encode()  # 转换内容为字节
        blocks_needed = (len(content_bytes) + FS_BLOCK_SIZE - 1) // FS_BLOCK_SIZE  # 计算需要的块数
        blocks = [i for i, bit in enumerate(self.bitmap) if bit == 0][:blocks_needed]
        if len(blocks) < blocks_needed:
            raise ValueError("存储空间不足！")
        for block in blocks:
            self.bitmap[block] = 1  # 标记数据块为已占用
        file_metadata.blocks = blocks  # 更新文件的块列表
        file_metadata.size = len(content_bytes)  # 更新文件大小
        self.save_metadata()  # 保存元数据
        with open(LIGHT_FS_FILE, "r+b") as f:
            for i, block in enumerate(blocks):
                f.seek(FS_META_SIZE + block * FS_BLOCK_SIZE)
                f.write(content_bytes[i * FS_BLOCK_SIZE:(i + 1) * FS_BLOCK_SIZE])  # 写入内容到数据块

    def read_file(self, name):
        """读取文件内容"""
        if name not in self.files:
            raise ValueError("文件未找到！")
        file_metadata = self.files[name]
        if file_metadata.is_folder:
            raise ValueError("不能从文件夹读取内容！")
        content = bytearray()
        with open(LIGHT_FS_FILE, "rb") as f:
            for block in file_metadata.blocks:
                f.seek(FS_META_SIZE + block * FS_BLOCK_SIZE)
                content.extend(f.read(FS_BLOCK_SIZE))  # 从数据块读取内容
        return content[:file_metadata.size].decode()  # 返回实际大小的内容

    def get_storage_statistics(self):
        """返回存储统计信息，已用空间和空闲空间（MB）"""
        used_blocks = sum(self.bitmap)  # 计算已使用的数据块数量
        free_blocks = FS_DATA_BLOCKS - used_blocks  # 计算空闲数据块数量
        used_space = used_blocks * FS_BLOCK_SIZE / (1024 * 1024)  # 计算已用空间 (MB)
        free_space = free_blocks * FS_BLOCK_SIZE / (1024 * 1024)  # 计算空闲空间 (MB)
        return used_space, free_space



import os
import struct
import json

# 文件系统常量
LIGHT_FS_FILE = "light.fs"  # 文件系统主文件名
FS_SIZE = 256 * 1024 * 1024  # 文件系统总大小 (256MB)
FS_META_SIZE = 56 * 1024 * 1024  # 元数据区域大小 (56MB)
FS_BLOCK_SIZE = 1 * 1024 * 1024  # 数据块大小 (1MB)
FS_DATA_BLOCKS = (FS_SIZE - FS_META_SIZE) // FS_BLOCK_SIZE  # 可用数据块数量


# 文件元数据结构
class FileMetadata:
    """表示文件或文件夹的元数据"""

    def __init__(self, name, is_folder=False, size=0, blocks=None):
        self.name = name  # 文件名
        self.is_folder = is_folder  # 是否为文件夹
        self.size = size  # 文件大小
        self.blocks = blocks if blocks else []  # 文件占用的块

    def to_dict(self):
        """将文件元数据转换为字典"""
        return {
            "name": self.name,
            "is_folder": self.is_folder,
            "size": self.size,
            "blocks": self.blocks
        }

    @staticmethod
    def from_dict(data):
        """从字典创建文件元数据"""
        return FileMetadata(
            name=data["name"],
            is_folder=data["is_folder"],
            size=data["size"],
            blocks=data["blocks"]
        )


# LightFS 主类
class LightFS:
    """轻量级文件系统的核心类"""

    def __init__(self):
        self.files = {}  # 存储文件和文件夹的元数据
        self.bitmap = [0] * FS_DATA_BLOCKS  # 数据块位图，用于标记哪些块已被占用
        self.loaded = False  # 文件系统是否已加载

    def initialize(self):
        """初始化文件系统"""
        if not os.path.exists(LIGHT_FS_FILE):
            with open(LIGHT_FS_FILE, "wb") as f:
                f.write(b"\0" * FS_SIZE)  # 写入空的文件系统
            self.files = {}  # 清空文件系统中的文件
            self.bitmap = [0] * FS_DATA_BLOCKS  # 重置位图
            self.save_metadata()  # 保存元数据
        else:
            raise FileExistsError("文件系统已经存在！")

    def load(self):
        """加载文件系统"""
        if os.path.exists(LIGHT_FS_FILE):
            with open(LIGHT_FS_FILE, "rb") as f:
                metadata_size = struct.unpack("I", f.read(4))[0]  # 读取元数据的大小
                metadata = f.read(metadata_size).decode()  # 读取元数据
                # 将元数据解析为字典
                self.files = {
                    name: FileMetadata.from_dict(data)
                    for name, data in json.loads(metadata).items()
                }
                self.bitmap = list(f.read(FS_DATA_BLOCKS))  # 读取数据块位图
            self.loaded = True
        else:
            raise FileNotFoundError("文件系统未找到！")

    def save_metadata(self):
        """保存文件系统的元数据"""
        metadata = json.dumps({name: file.to_dict() for name, file in self.files.items()})
        with open(LIGHT_FS_FILE, "r+b") as f:
            f.write(struct.pack("I", len(metadata)))  # 写入元数据大小
            f.write(metadata.encode())  # 写入元数据内容
            f.write(bytearray(self.bitmap))  # 写入数据块位图

    def create_file(self, name):
        """创建新文件"""
        if name in self.files:
            raise ValueError("文件已经存在！")
        self.files[name] = FileMetadata(name)  # 创建新文件的元数据
        self.save_metadata()  # 保存元数据

    def rename_file(self, old_name, new_name):
        """重命名文件"""
        if old_name not in self.files:
            raise ValueError("文件未找到！")
        if new_name in self.files:
            raise ValueError("新文件名已存在！")
        self.files[new_name] = self.files.pop(old_name)  # 修改文件名
        self.files[new_name].name = new_name  # 更新文件名
        self.save_metadata()  # 保存元数据

    def delete_file(self, name):
        """删除文件"""
        if name not in self.files:
            raise ValueError("文件未找到！")
        file_metadata = self.files.pop(name)  # 删除文件的元数据
        for block in file_metadata.blocks:
            self.bitmap[block] = 0  # 释放文件占用的数据块
        self.save_metadata()  # 保存元数据

    def list_files(self):
        """列出文件系统中的文件和文件夹"""
        return [(name, metadata.is_folder) for name, metadata in self.files.items()]

    def write_to_file(self, name, content):
        """向文件写入内容"""
        if name not in self.files:
            raise ValueError("文件未找到！")
        file_metadata = self.files[name]
        if file_metadata.is_folder:
            raise ValueError("不能向文件夹写入内容！")
        content_bytes = content.encode()  # 转换内容为字节
        blocks_needed = (len(content_bytes) + FS_BLOCK_SIZE - 1) // FS_BLOCK_SIZE  # 计算需要的块数
        blocks = [i for i, bit in enumerate(self.bitmap) if bit == 0][:blocks_needed]
        if len(blocks) < blocks_needed:
            raise ValueError("存储空间不足！")
        for block in blocks:
            self.bitmap[block] = 1  # 标记数据块为已占用
        file_metadata.blocks = blocks  # 更新文件的块列表
        file_metadata.size = len(content_bytes)  # 更新文件大小
        self.save_metadata()  # 保存元数据
        with open(LIGHT_FS_FILE, "r+b") as f:
            for i, block in enumerate(blocks):
                f.seek(FS_META_SIZE + block * FS_BLOCK_SIZE)
                f.write(content_bytes[i * FS_BLOCK_SIZE:(i + 1) * FS_BLOCK_SIZE])  # 写入内容到数据块

    def read_file(self, name):
        """读取文件内容"""
        if name not in self.files:
            raise ValueError("文件未找到！")
        file_metadata = self.files[name]
        if file_metadata.is_folder:
            raise ValueError("不能从文件夹读取内容！")
        content = bytearray()
        with open(LIGHT_FS_FILE, "rb") as f:
            for block in file_metadata.blocks:
                f.seek(FS_META_SIZE + block * FS_BLOCK_SIZE)
                content.extend(f.read(FS_BLOCK_SIZE))  # 从数据块读取内容
        return content[:file_metadata.size].decode()  # 返回实际大小的内容

    def get_storage_statistics(self):
        """返回存储统计信息，已用空间和空闲空间（MB）"""
        used_blocks = sum(self.bitmap)  # 计算已使用的数据块数量
        free_blocks = FS_DATA_BLOCKS - used_blocks  # 计算空闲数据块数量
        used_space = used_blocks * FS_BLOCK_SIZE / (1024 * 1024)  # 计算已用空间 (MB)
        free_space = free_blocks * FS_BLOCK_SIZE / (1024 * 1024)  # 计算空闲空间 (MB)
        return used_space, free_space



import os
import struct
import json

# 文件系统常量
LIGHT_FS_FILE = "light.fs"  # 文件系统主文件名
FS_SIZE = 256 * 1024 * 1024  # 文件系统总大小 (256MB)
FS_META_SIZE = 56 * 1024 * 1024  # 元数据区域大小 (56MB)
FS_BLOCK_SIZE = 1 * 1024 * 1024  # 数据块大小 (1MB)
FS_DATA_BLOCKS = (FS_SIZE - FS_META_SIZE) // FS_BLOCK_SIZE  # 可用数据块数量


# 文件元数据结构
class FileMetadata:
    """表示文件或文件夹的元数据"""

    def __init__(self, name, is_folder=False, size=0, blocks=None):
        self.name = name  # 文件名
        self.is_folder = is_folder  # 是否为文件夹
        self.size = size  # 文件大小
        self.blocks = blocks if blocks else []  # 文件占用的块

    def to_dict(self):
        """将文件元数据转换为字典"""
        return {
            "name": self.name,
            "is_folder": self.is_folder,
            "size": self.size,
            "blocks": self.blocks
        }

    @staticmethod
    def from_dict(data):
        """从字典创建文件元数据"""
        return FileMetadata(
            name=data["name"],
            is_folder=data["is_folder"],
            size=data["size"],
            blocks=data["blocks"]
        )


# LightFS 主类
class LightFS:
    """轻量级文件系统的核心类"""

    def __init__(self):
        self.files = {}  # 存储文件和文件夹的元数据
        self.bitmap = [0] * FS_DATA_BLOCKS  # 数据块位图，用于标记哪些块已被占用
        self.loaded = False  # 文件系统是否已加载

    def initialize(self):
        """初始化文件系统"""
        if not os.path.exists(LIGHT_FS_FILE):
            with open(LIGHT_FS_FILE, "wb") as f:
                f.write(b"\0" * FS_SIZE)  # 写入空的文件系统
            self.files = {}  # 清空文件系统中的文件
            self.bitmap = [0] * FS_DATA_BLOCKS  # 重置位图
            self.save_metadata()  # 保存元数据
        else:
            raise FileExistsError("文件系统已经存在！")

    def load(self):
        """加载文件系统"""
        if os.path.exists(LIGHT_FS_FILE):
            with open(LIGHT_FS_FILE, "rb") as f:
                metadata_size = struct.unpack("I", f.read(4))[0]  # 读取元数据的大小
                metadata = f.read(metadata_size).decode()  # 读取元数据
                # 将元数据解析为字典
                self.files = {
                    name: FileMetadata.from_dict(data)
                    for name, data in json.loads(metadata).items()
                }
                self.bitmap = list(f.read(FS_DATA_BLOCKS))  # 读取数据块位图
            self.loaded = True
        else:
            raise FileNotFoundError("文件系统未找到！")

    def save_metadata(self):
        """保存文件系统的元数据"""
        metadata = json.dumps({name: file.to_dict() for name, file in self.files.items()})
        with open(LIGHT_FS_FILE, "r+b") as f:
            f.write(struct.pack("I", len(metadata)))  # 写入元数据大小
            f.write(metadata.encode())  # 写入元数据内容
            f.write(bytearray(self.bitmap))  # 写入数据块位图

    def create_file(self, name):
        """创建新文件"""
        if name in self.files:
            raise ValueError("文件已经存在！")
        self.files[name] = FileMetadata(name)  # 创建新文件的元数据
        self.save_metadata()  # 保存元数据

    def rename_file(self, old_name, new_name):
        """重命名文件"""
        if old_name not in self.files:
            raise ValueError("文件未找到！")
        if new_name in self.files:
            raise ValueError("新文件名已存在！")
        self.files[new_name] = self.files.pop(old_name)  # 修改文件名
        self.files[new_name].name = new_name  # 更新文件名
        self.save_metadata()  # 保存元数据

    def delete_file(self, name):
        """删除文件"""
        if name not in self.files:
            raise ValueError("文件未找到！")
        file_metadata = self.files.pop(name)  # 删除文件的元数据
        for block in file_metadata.blocks:
            self.bitmap[block] = 0  # 释放文件占用的数据块
        self.save_metadata()  # 保存元数据

    def list_files(self):
        """列出文件系统中的文件和文件夹"""
        return [(name, metadata.is_folder) for name, metadata in self.files.items()]

    def write_to_file(self, name, content):
        """向文件写入内容"""
        if name not in self.files:
            raise ValueError("文件未找到！")
        file_metadata = self.files[name]
        if file_metadata.is_folder:
            raise ValueError("不能向文件夹写入内容！")
        content_bytes = content.encode()  # 转换内容为字节
        blocks_needed = (len(content_bytes) + FS_BLOCK_SIZE - 1) // FS_BLOCK_SIZE  # 计算需要的块数
        blocks = [i for i, bit in enumerate(self.bitmap) if bit == 0][:blocks_needed]
        if len(blocks) < blocks_needed:
            raise ValueError("存储空间不足！")
        for block in blocks:
            self.bitmap[block] = 1  # 标记数据块为已占用
        file_metadata.blocks = blocks  # 更新文件的块列表
        file_metadata.size = len(content_bytes)  # 更新文件大小
        self.save_metadata()  # 保存元数据
        with open(LIGHT_FS_FILE, "r+b") as f:
            for i, block in enumerate(blocks):
                f.seek(FS_META_SIZE + block * FS_BLOCK_SIZE)
                f.write(content_bytes[i * FS_BLOCK_SIZE:(i + 1) * FS_BLOCK_SIZE])  # 写入内容到数据块

    def read_file(self, name):
        """读取文件内容"""
        if name not in self.files:
            raise ValueError("文件未找到！")
        file_metadata = self.files[name]
        if file_metadata.is_folder:
            raise ValueError("不能从文件夹读取内容！")
        content = bytearray()
        with open(LIGHT_FS_FILE, "rb") as f:
            for block in file_metadata.blocks:
                f.seek(FS_META_SIZE + block * FS_BLOCK_SIZE)
                content.extend(f.read(FS_BLOCK_SIZE))  # 从数据块读取内容
        return content[:file_metadata.size].decode()  # 返回实际大小的内容

    def get_storage_statistics(self):
        """返回存储统计信息，已用空间和空闲空间（MB）"""
        used_blocks = sum(self.bitmap)  # 计算已使用的数据块数量
        free_blocks = FS_DATA_BLOCKS - used_blocks  # 计算空闲数据块数量
        used_space = used_blocks * FS_BLOCK_SIZE / (1024 * 1024)  # 计算已用空间 (MB)
        free_space = free_blocks * FS_BLOCK_SIZE / (1024 * 1024)  # 计算空闲空间 (MB)
        return used_space, free_space



