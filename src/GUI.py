import os
from LightFS import LightFS
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import simpledialog


# GUI 界面实现
class LightFSGUI:
    """GUI 界面，用于交互操作文件系统"""

    def __init__(self, root):
        self.fs = LightFS()  # 初始化文件系统
        self.root = root
        self.root.title("轻量级文件系统")  # 设置窗口标题
        self.root.geometry("700x600")  # 设置窗口大小

        self.left_frame = tk.Frame(self.root)  # 左侧按钮区域
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y)

        self.log_text = tk.Text(self.root, state="disabled", width=50)  # 日志显示区域
        self.log_text.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # 各种操作按钮
        self.initialize_button = tk.Button(self.left_frame, text="初始化", command=self.initialize_fs)
        self.initialize_button.pack(fill=tk.X)

        self.load_button = tk.Button(self.left_frame, text="加载", command=self.load_fs)
        self.load_button.pack(fill=tk.X)

        self.create_file_button = tk.Button(self.left_frame, text="创建文件", command=self.create_file)
        self.create_file_button.pack(fill=tk.X)

        self.rename_file_button = tk.Button(self.left_frame, text="重命名文件", command=self.rename_file)
        self.rename_file_button.pack(fill=tk.X)

        self.delete_file_button = tk.Button(self.left_frame, text="删除文件", command=self.delete_file)
        self.delete_file_button.pack(fill=tk.X)

        self.import_button = tk.Button(self.left_frame, text="导入文件", command=self.import_file)
        self.import_button.pack(fill=tk.X)

        self.export_button = tk.Button(self.left_frame, text="导出文件", command=self.export_file)
        self.export_button.pack(fill=tk.X)

        self.read_file_button = tk.Button(self.left_frame, text="读取文件", command=self.read_file)
        self.read_file_button.pack(fill=tk.X)

        self.write_file_button = tk.Button(self.left_frame, text="写入文件", command=self.write_file)
        self.write_file_button.pack(fill=tk.X)

        self.storage_stats_button = tk.Button(self.left_frame, text="显示存储统计",
                                              command=self.show_storage_statistics)
        self.storage_stats_button.pack(fill=tk.X)

        self.file_listbox = tk.Listbox(self.left_frame)  # 文件列表
        self.file_listbox.pack(fill=tk.BOTH, expand=True)

    def log(self, message):
        """在日志区域显示消息"""
        self.log_text.configure(state="normal")
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.configure(state="disabled")

    def get_selected_file(self):
        """获取当前选中的文件"""
        selected_file = self.file_listbox.curselection()
        if not selected_file:
            self.log("错误: 请先选择文件！")
            return None
        return self.file_listbox.get(selected_file[0]).split(" ", 1)[-1]

    def initialize_fs(self):
        """初始化文件系统"""
        try:
            self.fs.initialize()
            self.log("文件系统已初始化！")
        except Exception as e:
            self.log(f"错误: {e}")

    def load_fs(self):
        """加载文件系统"""
        try:
            self.fs.load()
            self.refresh_file_list()
            self.log("文件系统已加载！")
        except Exception as e:
            self.log(f"错误: {e}")

    def refresh_file_list(self):
        """刷新文件列表"""
        self.file_listbox.delete(0, tk.END)
        for name, is_folder in self.fs.list_files():
            self.file_listbox.insert(tk.END, f"{'[文件]' if not is_folder else ''} {name}")

    def create_file(self):
        """创建文件"""
        name = simpledialog.askstring("创建", "输入文件名称：")
        if name:
            try:
                self.fs.create_file(name)
                self.refresh_file_list()
                self.log(f"文件 {name} 已创建！")
            except Exception as e:
                self.log(f"错误: {e}")

    def rename_file(self):
        """重命名文件"""
        old_name = self.get_selected_file()
        if not old_name:
            return
        new_name = simpledialog.askstring("重命名", "输入新的文件名称：")
        if new_name:
            try:
                self.fs.rename_file(old_name, new_name)
                self.refresh_file_list()
                self.log(f"文件 {old_name} 已重命名为 {new_name}！")
            except Exception as e:
                self.log(f"错误: {e}")

    def delete_file(self):
        """删除文件"""
        name = self.get_selected_file()
        if not name:
            return
        confirm = messagebox.askyesno("删除", f"确认删除 {name}？")
        if confirm:
            try:
                self.fs.delete_file(name)
                self.refresh_file_list()
                self.log(f"文件 {name} 已删除！")
            except Exception as e:
                self.log(f"错误: {e}")

    def import_file(self):
        """导入文件"""
        file_path = filedialog.askopenfilename(title="选择导入文件")
        if file_path:
            name = os.path.basename(file_path)
            try:
                with open(file_path, "r") as f:
                    content = f.read()
                self.fs.create_file(name)
                self.fs.write_to_file(name, content)
                self.refresh_file_list()
                self.log(f"文件 {name} 已导入！")
            except Exception as e:
                self.log(f"错误: {e}")

    def export_file(self):
        """导出文件"""
        name = self.get_selected_file()
        if not name:
            return
        file_path = filedialog.asksaveasfilename(title="导出文件为", initialfile=name)
        if file_path:
            try:
                content = self.fs.read_file(name)
                with open(file_path, "w") as f:
                    f.write(content)
                self.log(f"文件 {name} 已导出到 {file_path}！")
            except Exception as e:
                self.log(f"错误: {e}")

    def read_file(self):
        """读取文件"""
        name = self.get_selected_file()
        if not name:
            return
        try:
            content = self.fs.read_file(name)
            self.log(f"文件内容：\n{content}")
        except Exception as e:
            self.log(f"错误: {e}")

    def write_file(self):
        """写入文件"""
        name = self.get_selected_file()
        if not name:
            return
        content = simpledialog.askstring("写入文件", "输入要写入的内容：")
        if content:
            try:
                self.fs.write_to_file(name, content)
                self.log(f"内容已写入文件 {name}！")
            except Exception as e:
                self.log(f"错误: {e}")

    def show_storage_statistics(self):
        """显示存储统计信息"""
        used_space, free_space = self.fs.get_storage_statistics()
        self.log(f"已用空间: {used_space:.2f} MB")
        self.log(f"空闲空间: {free_space:.2f} MB")


if __name__ == "__main__":
    root = tk.Tk()
    gui = LightFSGUI(root)
    root.mainloop()
